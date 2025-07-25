from otree.api import *
import random
import sys
import os
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.shared_utils import (
    initialize_player_roles,
    get_parameter_set_for_round,
    calculate_general_payoff,
)
from utils.trading_utils import *
from configs.config import config

doc = """
碳交易組：受試者需要先進行碳權交易，然後決定生產量
生產量受碳權、現金持有量限制
"""

class C(BaseConstants):
    NAME_IN_URL: str = config.get_stage_name_in_url('carbon_trading')
    PLAYERS_PER_GROUP: int = config.players_per_group
    NUM_ROUNDS: int = config.num_rounds
    TRADING_TIME: int = config.carbon_trading_time
    INITIAL_CAPITAL: int = config.get_stage_initial_capital('carbon_trading')
    MAX_PRODUCTION: int = config.max_production
    # 控制是否每輪重置現金
    RESET_CASH_EACH_ROUND: bool = config.carbon_trading_reset_cash_each_round
    # 碳權配置
    CARBON_ALLOWANCE_PER_PLAYER: int = config.carbon_allowance_per_player

class Subsession(BaseSubsession):
    market_price = models.IntegerField()
    price_history = models.LongStringField(initial='[]')
    start_time = models.IntegerField()  # 新增：記錄開始時間
    # 新增：社會最適產量和配額分配相關欄位
    total_optimal_emissions = models.IntegerField() # 社會最適產排放總量
    cap_total = models.IntegerField() # 發出的碳排放權總量
    allocation_details = models.LongStringField(initial='[]')  # 儲存分配詳細資訊
    executed_trades = models.LongStringField(initial='[]')  # 新增：記錄成交的訂單
    carbon_multiplier = models.FloatField()
    tax_rate = models.IntegerField()
    dominant_mc = models.IntegerField()
    non_dominant_mc = models.IntegerField()
    allocation_method = models.StringField()

def initialize_roles(subsession: Subsession, allocation_method) -> None:
    """使用共享工具庫和配置文件初始化角色"""

    # 初始化玩家角色（會用到 subsession.market_price）
    initialize_player_roles(subsession, initial_capital=C.INITIAL_CAPITAL)

    # 計算社會最適產量和碳權分配
    players = subsession.get_players()
    allowance_allocation = calculate_optimal_allowance_allocation(players, subsession.market_price, subsession.carbon_multiplier, allocation_method)
    
    # 儲存結果到 subsession
    subsession.total_optimal_emissions = allowance_allocation['TE_opt_total']
    subsession.carbon_multiplier = allowance_allocation['r']
    subsession.cap_total = allowance_allocation['cap_total']
    subsession.allocation_details = json.dumps(allowance_allocation['firm_details'])
    
    for i, p in enumerate(players):
        # 設置市場價格
        p.market_price = subsession.market_price
        
        # 現金管理
        if C.RESET_CASH_EACH_ROUND or p.round_number == 1:
            p.current_cash = C.INITIAL_CAPITAL
        else:
            p.current_cash = p.in_round(p.round_number - 1).final_cash
        
        p.initial_capital = p.current_cash
        
        # 碳權管理：使用新的動態分配邏輯
        allocated_permits = allowance_allocation['allocations'][i]
        # 只有在第一輪或permits為None時才設定初始分配
        if p.round_number == 1 or p.field_maybe_none('permits') is None:
            p.permits = allocated_permits  # 記錄初始分配的碳權
        p.current_permits = allocated_permits  # 設定當前碳權餘額
        
        # 儲存最適產量和排放量資訊
        p.optimal_production = allowance_allocation['firm_details'][i]['q_opt']
        p.optimal_emissions = allowance_allocation['firm_details'][i]['TE_opt']
        p.mkt_production = allowance_allocation['firm_details'][i]['q_mkt']
        p.mkt_emissions = allowance_allocation['firm_details'][i]['TE_mkt']
        
        # 為每個玩家設置selected_round
        if p.round_number == 1:
            # 在第一輪隨機選擇一個回合用於最終報酬
            p.selected_round = subsession.session.vars["selected_round"]
        else:
            # 在後續回合中保持與第一輪相同的selected_round
            p.selected_round = subsession.session.vars["selected_round"]

    
    # 根據配置檔案決定是否輸出詳細資訊
    if config.carbon_trading_show_detailed_calculation:
        output_format = config.carbon_trading_console_output_format
        decimal_places = config.carbon_trading_decimal_places
        
        if output_format == "detailed":
            print("\n" + "="*60)
            print("社會最適產量與碳權分配計算結果")
            print("="*60)
            
            for i, details in enumerate(allowance_allocation['firm_details']):
                print(f"Firm {i+1}: a = {details['a']}, b = {details['b']}, "
                      f"q_opt = {details['q_opt']:.{decimal_places}f}, TE_opt = {details['TE_opt']:.{decimal_places}f}, "
                      f"allocated_allowance = {allowance_allocation['allocations'][i]}")
            
            print(f"\nTotal optimal emissions = {allowance_allocation['TE_opt_total']:.{decimal_places}f}")
            print(f"Cap multiplier = {allowance_allocation['r']}")
            print(f"Cap total = {allowance_allocation['cap_total']}")
            print(f"Parameters: p = {allowance_allocation['config']['market_price']}, "
                  f"c = {allowance_allocation['config']['social_cost_per_unit_carbon']}")
            print("="*60 + "\n")
        
        elif output_format == "simple":
            print(f"碳權分配完成：總排放={allowance_allocation['TE_opt_total']:.{decimal_places}f}, "
                  f"配額倍率={allowance_allocation['r']}, 總配額={allowance_allocation['cap_total']}")
    
    # 簡化版玩家資訊輸出
    for i, p in enumerate(players):
        print(f"玩家 {i+1}: {'Dominant' if p.is_dominant else 'Non-dominant'}, "
              f"a={p.marginal_cost_coefficient}, b={p.carbon_emission_per_unit}, "
              f"配額={allowance_allocation['allocations'][i]}")
    
    print(f"碳交易組初始化完成")

def calculate_optimal_allowance_allocation(
    players: List[BasePlayer], 
    market_price: float,
    carbon_multiplier: float,
    allocation_method: str,
) -> Dict[str, Any]:
    """
    計算社會最適產量和碳權分配
    """
    
    def _allocate_discrete_share(indices: List[int], total: int) -> Dict[int, int]:
        """將 total 配額離散分配給指定 indices，餘數隨機給"""
        n = len(indices)
        base = total // n
        remainder = total % n
        allocations = {idx: base for idx in indices}
        if remainder > 0:
            lucky = random.sample(indices, remainder)
            for idx in lucky:
                allocations[idx] += 1
        return allocations
        
    p = float(market_price)
    c = config.carbon_trading_social_cost_per_unit_carbon
    N = len(players)
    decimal_places = config.carbon_trading_decimal_places
    r = carbon_multiplier

    firm_details = []
    TE_opts = []
    TE_subopts = []
    TE_mkts = []

    for player in players:
        a_i = float(player.marginal_cost_coefficient)
        b_i = float(player.carbon_emission_per_unit)
        q_opt_i = int((p - b_i * c) / a_i)
        q_subopt_i = int((p - b_i * c * r) / a_i)
        q_mkt_i = int( p  / a_i)
        TE_opt_i = int(b_i * q_opt_i)
        TE_subopt_i = int(b_i * q_subopt_i)
        TE_mkt_i = int(b_i * q_mkt_i)

        firm_details.append({
            'a': a_i,
            'b': b_i,
            'q_opt': q_opt_i,
            'q_subopt': q_subopt_i,
            'q_mkt': q_mkt_i,
            'TE_opt': TE_opt_i,
            'TE_subopt': TE_subopt_i,
            'TE_mkt': TE_mkt_i,
        })

        TE_opts.append(TE_opt_i)
        TE_subopts.append(TE_subopt_i)
        TE_mkts.append(TE_mkt_i)

    TE_opt_total = sum(TE_opts) # 理論上社會最適當的碳權總數
    cap_total = sum(TE_subopts) # 實際會發的碳權總數
    TE_mkt_total = sum(TE_mkts) # 理論上社會最適當的碳權總數
    cap_total_int = int(round(cap_total)) if config.carbon_trading_round_cap_total else int(cap_total)

    allocations = [0] * N

    if allocation_method == "equal":
        all_indices = list(range(N))
        alloc_map = _allocate_discrete_share(all_indices, cap_total_int)
        for i in range(N):
            allocations[i] = alloc_map.get(i, 0)

    elif allocation_method == "grandfathering":
        dominant_cap_share = config.grandfathering_rule.get("dominant_share_of_cap", 0.3)
        dominant_indices = [i for i, p in enumerate(players) if getattr(p, 'is_dominant', 0) == 1]
        non_dominant_indices = [i for i in range(N) if i not in dominant_indices]

        if not dominant_indices:
            raise ValueError("Grandfathering 分配錯誤：找不到任何大廠")
        if not non_dominant_indices:
            raise ValueError("Grandfathering 分配錯誤：沒有小廠")

        dominant_total = int(round(cap_total_int * dominant_cap_share))
        remaining_cap = cap_total_int - dominant_total

        dominant_allocs = _allocate_discrete_share(dominant_indices, dominant_total)
        small_allocs = _allocate_discrete_share(non_dominant_indices, remaining_cap)

        for i in range(N):
            allocations[i] = dominant_allocs.get(i, 0) + small_allocs.get(i, 0)

    return {
        'firm_details': firm_details,
        'TE_opt_total': TE_opt_total,
        'r': r,
        'cap_total': cap_total_int,
        'TE_mkt_total': TE_mkt_total,
        'allocations': allocations,
        'config': {
            'market_price': p,
            'social_cost_per_unit_carbon': c,
            'decimal_places': decimal_places,
            'cap_multipliers': r,
            'use_fixed_price': config.carbon_trading_use_fixed_price
        }
    }
    
def creating_session(subsession: Subsession) -> None:
    # 設定分組
    subsession.set_group_matrix([subsession.get_players()])

    # 選擇報酬回合（僅第 1 輪）
    if "selected_round" not in subsession.session.vars:
        subsession.session.vars["selected_round"] = random.randint(1, C.NUM_ROUNDS)

    param = get_parameter_set_for_round(subsession.session, subsession.round_number)

    subsession.market_price = param['market_price']
    subsession.tax_rate = param['tax_rate']
    subsession.carbon_multiplier = param['carbon_multiplier']
    subsession.dominant_mc = param['dominant_mc']
    subsession.non_dominant_mc = param['non_dominant_mc']

    allocation_method = subsession.session.config.get('allocation_method')
    subsession.allocation_method = allocation_method
    
    initialize_roles(subsession, allocation_method)

class Group(BaseGroup):
    buy_orders = models.LongStringField(initial='[]')
    sell_orders = models.LongStringField(initial='[]')

class Player(BasePlayer):
    # 添加這個欄位
    is_dominant = models.BooleanField()
    
    # 其他現有欄位
    marginal_cost_coefficient = models.IntegerField()
    disturbance_values = models.LongStringField()
    carbon_emission_per_unit = models.IntegerField()
    market_price = models.CurrencyField()
    production = models.IntegerField(min=0, max=C.MAX_PRODUCTION)
    revenue = models.CurrencyField()
    total_cost = models.FloatField()  # 改為FloatField以保持浮點數精度
    net_profit = models.FloatField()  # 改為FloatField以保持浮點數精度
    initial_capital = models.CurrencyField()
    final_cash = models.CurrencyField()
    max_production = models.IntegerField()
    current_cash = models.CurrencyField()
    permits = models.IntegerField()  # 初始分配的碳權數量
    current_permits = models.IntegerField()  # 當前碳權餘額
    submitted_offers = models.LongStringField(initial='[]')
    total_bought = models.IntegerField(default=0)   # 總買入數量：玩家在本回合買入的碳權總數
    total_sold = models.IntegerField(default=0)     # 總賣出數量：玩家在本回合賣出的碳權總數
    total_spent = models.CurrencyField(default=0)   # 總支出金額：玩家在本回合買入碳權花費的總金額
    total_earned = models.CurrencyField(default=0)  # 總收入金額：玩家在本回合賣出碳權獲得的總金額
    
    selected_round = models.IntegerField()  # 新增：隨機選中的回合用於最終報酬
    # 新增：社會最適產量相關欄位
    optimal_production = models.FloatField()  # 社會最適產量 q_opt_i
    optimal_emissions = models.FloatField()   # 社會最適排放量 TE_opt_i
    mkt_production = models.FloatField()  # 利潤極大化產量 q_mkt_i
    mkt_emissions = models.FloatField()   # 利潤極大化排放量 TE_mkt_i

class Introduction(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player):
        return dict(
            treatment='trading',
            treatment_text='碳交易',
            num_rounds=C.NUM_ROUNDS,
            reset_cash=C.RESET_CASH_EACH_ROUND,
        )

class ReadyWaitPage(CommonReadyWaitPage):
    pass

class TradingMarket(Page):
    timeout_seconds = C.TRADING_TIME

    @staticmethod  
    def vars_for_template(player):

        try:
            disturbance_vector = np.array(json.loads(player.disturbance_values))
        except Exception as e:
            disturbance_vector = np.zeros(player.max_production)
        max_q = player.max_production
        a = player.marginal_cost_coefficient
        market_price = float(player.market_price)
        q = np.arange(1, max_q + 1)
        marginal_costs = a * q + disturbance_vector[:max_q]
        cumulative_cost = np.cumsum(marginal_costs)
        revenue = market_price * q
        profit = revenue - cumulative_cost
        profit_table = [
            {
                'quantity': int(qi),
                'marginal_cost': round(mc, 2),
                'profit': round(float(p), 2)
            }
            for qi, mc, p in zip(q, marginal_costs, profit)
        ]
        
        return dict(
            cash=int(player.current_cash),
            permits=int(player.current_permits),
            marginal_cost_coefficient=int(player.marginal_cost_coefficient),
            carbon_emission_per_unit=player.carbon_emission_per_unit,
            timeout_seconds=TradingMarket.timeout_seconds,
            player_id=player.id_in_group,
            market_price=int(player.market_price),
            treatment='trading',
            treatment_text='碳交易',
            reset_cash=C.RESET_CASH_EACH_ROUND,
            disturbance_values=json.loads(player.disturbance_values),
            profit_table = profit_table,
        )

    # 在 live_method 中的修改部分
    
    @staticmethod
    def live_method(player: Player, data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """處理即時交易請求"""
        # 初次連線或 ping
        if data is None or data.get('type') == 'ping':
            return {p.id_in_group: TradingMarket.market_state(p) for p in player.group.get_players()}
        
        group = player.group
        
        # 處理新訂單提交
        if data.get('type') == 'submit_offer':
            direction = data.get('direction')
            price = int(data.get('price', 0))
            quantity = int(data.get('quantity', 0))
            
            # 記錄提交的訂單
            record_submitted_offer(player, direction, price, quantity)
            
            print(f"玩家 {player.id_in_group} 提交{direction}單: "
                  f"價格={price}, 數量={quantity}, "
                  f"現金={player.current_cash}, 碳權={player.current_permits}")
            
            # 修改：使用統一的 process_new_order 函數
            result = process_new_order(
                player, group, direction, price, quantity, 
                "碳權", 'current_permits'  # 使用碳權相關參數
            )
            
            # 處理通知
            if result.get('notifications'):
                market_states = {}
                for p in group.get_players():
                    state = TradingMarket.market_state(p)
                    if p.id_in_group in result['notifications']:
                        # 修改：根據 result.type 決定通知類型
                        notification_type = 'success'
                        if result.get('type') == 'fail':
                            notification_type = 'error'  # 前端會轉換為 danger
                        
                        state['notification'] = {
                            'type': notification_type,
                            'message': result['notifications'][p.id_in_group]
                        }
                    market_states[p.id_in_group] = state
                return market_states
        
        # 處理接受訂單
        elif data.get('type') == 'accept_offer':
            offer_type = data.get('offer_type')
            target_id = int(data.get('player_id', 0))
            price = float(data.get('price', 0))
            quantity = int(data.get('quantity', 0))
            
            print(f"玩家 {player.id_in_group} 接受{offer_type}單: "
                  f"對象玩家={target_id}, 價格={price}, 數量={quantity}")
            
            # 修改：使用統一的 process_accept_offer 函數
            result = process_accept_offer(
                player, group, offer_type, target_id, price, quantity,
                "碳權", 'current_permits'  # 使用碳權相關參數
            )
            
            # 處理通知
            if result.get('notifications'):
                market_states = {}
                for p in group.get_players():
                    state = TradingMarket.market_state(p)
                    if p.id_in_group in result['notifications']:
                        state['notification'] = {
                            'type': 'success',
                            'message': result['notifications'][p.id_in_group]
                        }
                    market_states[p.id_in_group] = state
                return market_states
            elif result.get('update_all'):
                return {p.id_in_group: TradingMarket.market_state(p) 
                        for p in group.get_players()}
            else:
                return result
    
        # 處理取消訂單
        elif data.get('type') == 'cancel_offer':
            direction = data.get('direction')
            price = float(data.get('price', 0))
            quantity = int(data.get('quantity', 0))
            
            print(f"玩家 {player.id_in_group} 取消{direction}單: "
                  f"價格={price}, 數量={quantity}")
            
            # 取消訂單
            cancel_specific_order(group, player.id_in_group, direction, price, quantity)
            
            return {p.id_in_group: TradingMarket.market_state(p) 
                    for p in group.get_players()}
        
        # 預設回應
        return {p.id_in_group: TradingMarket.market_state(p) 
                for p in group.get_players()}

    @staticmethod
    def market_state(player: Player) -> Dict[str, Any]:
        """獲取市場狀態"""
        group = player.group
        
            # 解析訂單
        buy_orders, sell_orders = parse_orders(group)
            
        # 排序訂單
        buy_sorted = sorted(buy_orders, key=lambda x: (-float(x[1]), int(x[0])))
        sell_sorted = sorted(sell_orders, key=lambda x: (float(x[1]), int(x[0])))
        
        try:
            # 提取玩家自己的買單和賣單
            my_buy_offers = [{'player_id': int(pid), 'price': int(float(price)), 'quantity': int(qt)} 
                          for pid, price, qt in buy_sorted if int(pid) == player.id_in_group]
            my_sell_offers = [{'player_id': int(pid), 'price': int(float(price)), 'quantity': int(qt)} 
                           for pid, price, qt in sell_sorted if int(pid) == player.id_in_group]
            
            # 修改：使用新的過濾函數，每個數量級別顯示最好的3筆
            display_buy_orders = filter_top_buy_orders_for_display(buy_sorted, max_per_quantity=3)
            display_sell_orders = filter_top_sell_orders_for_display(sell_sorted, max_per_quantity=3)
            
            # 轉換為前端格式
            public_buy_offers = [{'player_id': int(pid), 'price': int(float(price)), 'quantity': int(qt)} 
                               for pid, price, qt in display_buy_orders]
            public_sell_offers = [{'player_id': int(pid), 'price': int(float(price)), 'quantity': int(qt)} 
                                for pid, price, qt in display_sell_orders]
            
            # 排序（保持原有的排序邏輯）
            public_buy_offers.sort(key=lambda x: (-x['price'], x['player_id']))
            public_sell_offers.sort(key=lambda x: (x['price'], x['player_id']))
            
        except Exception as e:
            my_buy_offers = []
            my_sell_offers = []
            public_buy_offers = []
            public_sell_offers = []
        
        # 計算已鎖定資源
        # 買單邏輯改為無限制掛單，不再鎖定現金
        locked_cash = 0  # sum(o['price'] * o['quantity'] for o in my_buy_offers)
        locked_permits = sum(o['quantity'] for o in my_sell_offers)
    
        # 剩餘可用
        available_cash = int(player.current_cash)  # 保持原樣，允許負數
        available_permits = int(player.current_permits)
        
        # 提取交易歷史
        try:
            trade_history = json.loads(player.subsession.executed_trades)
            # 顯示全體玩家的交易記錄
            my_trades = trade_history  # 修改：顯示所有交易而不是個人交易
            # 將時間戳轉換為可讀格式
            for trade in my_trades:
                if 'timestamp' in trade and isinstance(trade['timestamp'], str):
                    trade['time'] = trade['timestamp']  # 已經是 MM:SS 格式
                elif 'timestamp' in trade:
                    trade['time'] = time.strftime('%H:%M:%S', time.localtime(trade['timestamp']))
                trade['is_buyer'] = (trade['buyer_id'] == player.id_in_group)
        except:
            my_trades = []
            
        # 提取價格歷史
        try:
            price_history = json.loads(player.subsession.price_history)
        except:
            price_history = []
        
        result = {
            'type': 'update',
            'cash': available_cash,
            'permits': available_permits,
            'marginal_cost_coefficient': int(player.marginal_cost_coefficient),
            'carbon_emission_per_unit': player.carbon_emission_per_unit,
            'my_buy_offers': my_buy_offers,
            'my_sell_offers': my_sell_offers,
            'buy_offers': public_buy_offers,
            'sell_offers': public_sell_offers,
            'trade_history': my_trades,  # 確保這裡返回交易歷史
            'price_history': price_history,
            #'profit_table': profit_table,
            'locked_cash': locked_cash,
            'locked_permits': locked_permits,
            'reset_cash': C.RESET_CASH_EACH_ROUND,
        }
        
        return result

    @staticmethod
    def before_next_page(player, timeout_happened):
        if timeout_happened and player.id_in_group == 1:
            player.group.buy_orders = '[]'
            player.group.sell_orders = '[]'
        if timeout_happened:
            player.current_cash = max(player.current_cash, 0)
            player.current_permits = max(player.current_permits, 0)

    @staticmethod
    def js_vars(player):

        return {
            'start_time': player.group.subsession.start_time,
            'player_id': player.id_in_group,
            'timeout_seconds': C.TRADING_TIME
        }


class ProductionDecision(Page):
    form_model = 'player'
    form_fields = ['production']

    @staticmethod
    def error_message(player, values):
        # 修正：生產量 × 每單位碳排放 不能超過持有的碳權
        required_permits = values['production'] * player.carbon_emission_per_unit
        if required_permits > player.current_permits:
            return f'生產{values["production"]}單位需要{required_permits}單位碳權，但您只有{player.current_permits}單位碳權'

    @staticmethod
    def vars_for_template(player):
        # 計算基於現金的最大產量 (解方程: a*q^2/2 = cash, 得到 q = sqrt(2*cash/a))
        # 添加防護措施，確保不會除以零
        mc_coefficient = max(0.001, float(player.marginal_cost_coefficient))
        
        # 添加防護措施，確保current_cash為正數
        current_cash = max(0, float(player.current_cash))
        
        # 註解掉現金限制計算
        # cash_limit = int(math.floor(math.sqrt(2 * current_cash / mc_coefficient)))
        cash_limit = C.MAX_PRODUCTION  # 設定為最大生產量上限，實際上不再限制
        
        # 修正：計算基於碳權的最大產量
        # 碳權限制：生產量 × 每單位碳排放 ≤ 碳權持有量
        # 所以：最大生產量 = 碳權持有量 ÷ 每單位碳排放
        carbon_emission_per_unit = max(1, player.carbon_emission_per_unit)  # 防止除以零
        permit_limit = int(player.current_permits // carbon_emission_per_unit)
        
        # 移除現金限制，只考慮碳權和最大生產量
        maxp = min(player.max_production, permit_limit)
        unit_income = int(player.market_price)
        
        # 獲取交易歷史
        try:
            trade_history = json.loads(player.subsession.executed_trades)
            # 顯示全體玩家的交易記錄
            my_trades = trade_history  # 修改：顯示所有交易而不是個人交易
            # 將時間戳轉換為可讀格式
            for trade in my_trades:
                if 'timestamp' in trade and isinstance(trade['timestamp'], str):
                    trade['time'] = trade['timestamp']  # 已經是 MM:SS 格式
                elif 'timestamp' in trade:
                    trade['time'] = time.strftime('%H:%M:%S', time.localtime(trade['timestamp']))
                trade['is_buyer'] = (trade['buyer_id'] == player.id_in_group)
        except:
            my_trades = []
            
        # 獲取價格歷史
        try:
            price_history = json.loads(player.subsession.price_history)
        except:
            price_history = []
        
        return dict(
            max_production=player.max_production,
            max_possible_production=maxp,
            cash_limit=cash_limit,
            marginal_cost_coefficient=int(player.marginal_cost_coefficient),
            carbon_emission_per_unit=player.carbon_emission_per_unit,
            market_price=player.market_price,
            current_permits=player.current_permits,
            current_cash=int(player.current_cash),
            treatment='trading',
            treatment_text='碳交易',
            unit_income=unit_income,
            trade_history=my_trades,
            price_history=price_history,
            reset_cash=C.RESET_CASH_EACH_ROUND,
            disturbance_values=json.loads(player.disturbance_values),  # 新增：固定的擾動值列表
        )

#    @staticmethod
#    def before_next_page(player, timeout_happened):
#        # 在進入下一頁前更新玩家的現金，扣除生產成本
#        if player.production is not None and player.production > 0:
#            cost = (player.marginal_cost_coefficient * player.production**2) / 2
            # 現金用於交易，不扣除生產成本
            # player.current_cash -= cost

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = lambda group: calculate_general_payoff(group, use_trading=True)

# 碳交易組 Results 類
class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        # 安全地訪問total_cost，如果為None則重新計算
        if player.field_maybe_none('total_cost') is not None:
            production_cost = player.total_cost
#        else:
#            # 如果total_cost為None，重新計算（使用新的累加邏輯）
#            random.seed(player.id_in_group * 1000 + player.round_number)
#            production_cost = 0
#            for i in range(1, player.production + 1):
#                unit_marginal_cost = player.marginal_cost_coefficient * i
#                unit_disturbance = round(random.uniform(-1, 1), 3)  # 四捨五入到3位小數，與前端一致
#                production_cost += unit_marginal_cost + unit_disturbance
#            random.seed()  # 重置隨機種子
        
        # 計算個人碳排放量
        total_emissions = player.production * player.carbon_emission_per_unit
        
        # 計算全體玩家的碳排放量
        group_emissions = 0
        for p in player.group.get_players():
            p_emissions = p.production * p.carbon_emission_per_unit
            group_emissions += p_emissions
        
        # 計算進度條百分比
        progress_percentage = round((player.round_number / C.NUM_ROUNDS) * 100)
        
        # 計算最終邊際成本（第production個單位的邊際成本）
        final_marginal_cost = 0
        if player.production > 0:
            final_unit_disturbance = np.array(json.loads(player.disturbance_values))[player.production - 1]
            final_marginal_cost = int(player.marginal_cost_coefficient * player.production + final_unit_disturbance)
#            # 使用相同的隨機種子計算最後一個單位的邊際成本
#            random.seed(player.id_in_group * 1000 + player.round_number)
#            for i in range(1, player.production):  # 跳過前面的隨機數
#                random.uniform(-1, 1)
#            final_unit_disturbance = random.uniform(-1, 1)
#        random.seed()  # 重置隨機種子
        
        # 計算平均成本
        avg_cost = 0
        if player.production > 0:
            avg_cost = round(production_cost / player.production, 2)
        
        # 預先計算加法值
        initial_cash = player.current_cash + production_cost  # 初始現金（生產前）
        cost_percentage = round((production_cost / initial_cash) * 100) if initial_cash > 0 else 0
        final_cash_percentage = round((player.final_cash / initial_cash) * 100) if initial_cash > 0 else 0
        
        # 獲取交易歷史
        try:
            trade_history = json.loads(player.subsession.executed_trades)
            # 顯示全體玩家的交易記錄
            my_trades = trade_history  # 修改：顯示所有交易而不是個人交易
            # 將時間戳轉換為可讀格式
            for trade in my_trades:
                if 'timestamp' in trade and isinstance(trade['timestamp'], str):
                    trade['time'] = trade['timestamp']  # 已經是 MM:SS 格式
                elif 'timestamp' in trade:
                    trade['time'] = time.strftime('%H:%M:%S', time.localtime(trade['timestamp']))
                trade['is_buyer'] = (trade['buyer_id'] == player.id_in_group)
        except:
            my_trades = []
            
        # 獲取價格歷史
        try:
            price_history = json.loads(player.subsession.price_history)
        except:
            price_history = []
            
        # 獲取統計數據
        avg_buy_price = round(player.total_spent / player.total_bought, 2) if player.total_bought > 0 else 0
        avg_sell_price = round(player.total_earned / player.total_sold, 2) if player.total_sold > 0 else 0
        
        # 計算最終報酬（基於隨機選中的回合）
        final_payoff_info = None
        if player.round_number == C.NUM_ROUNDS:  # 只在最後一輪顯示最終報酬
            # 安全檢查selected_round欄位
            selected_round = player.field_maybe_none('selected_round')
            if selected_round is None:
                # 如果selected_round為None，隨機選擇一個回合
                selected_round = random.randint(1, C.NUM_ROUNDS)
                player.selected_round = selected_round
            
            # 獲取被選中回合的數據
            selected_round_player = player.in_round(selected_round)
            
            selected_revenue = selected_round_player.production * selected_round_player.market_price
            selected_emissions = selected_round_player.production * selected_round_player.carbon_emission_per_unit
            
            # 修改：使用新的利潤計算方式
            # 計算被選中回合的最終總資金
            selected_final_cash_after_production = selected_round_player.current_cash - selected_round_player.total_cost
            selected_total_final_value = selected_final_cash_after_production + selected_revenue
            selected_profit = selected_total_final_value - selected_round_player.initial_capital
            selected_cost = selected_round_player.total_cost
            
            # 計算被選中回合全體玩家的碳排放量
            selected_group_emissions = 0
            for p in selected_round_player.group.get_players():
                p_emissions = p.production * p.carbon_emission_per_unit
                selected_group_emissions += p_emissions
            
            final_payoff_info = {
                'selected_round': selected_round,
                'initial_capital': float(selected_round_player.initial_capital),
                'final_cash': float(selected_final_cash_after_production + selected_revenue),
                'total_final_value': float(selected_total_final_value),
                'production': selected_round_player.production,
                'market_price': selected_round_player.market_price,
                'revenue': selected_revenue,
                'cost': selected_round_player.total_cost,
                'profit': selected_profit,
                'emissions': selected_emissions,
                'group_emissions': selected_group_emissions,
                'permits_used': selected_emissions,
                'profit_formatted': f"{int(round(selected_profit))}",
                'cost_formatted': f"{selected_cost}",
                'revenue_formatted': f"{int(round(selected_revenue))}",
                'emissions_formatted': f"{int(round(selected_emissions))}",
                'group_emissions_formatted': f"{int(round(selected_group_emissions))}",
                'initial_capital_formatted': f"{int(round(float(selected_round_player.initial_capital)))}",
                'final_cash_formatted': f"{int(round(float(selected_final_cash_after_production + selected_revenue)))}",
                'total_final_value_formatted': f"{int(round(float(selected_total_final_value)))}"
            }
        
        # 儲存數據以供 Payment Info 使用
        if final_payoff_info is not None:
            player.participant.vars["carbon_trade_summary"] = {
                "profit": final_payoff_info["profit"],
                "emission": final_payoff_info["emissions"],
                "group_emission": final_payoff_info["group_emissions"]
            }
 
        # 計算當前輪的總資金和利潤（用於顯示）
        current_final_cash_after_production = player.current_cash - production_cost
        current_total_final_value = current_final_cash_after_production + (player.field_maybe_none('revenue') or 0)
        current_profit = current_total_final_value - (player.initial_capital if hasattr(player, 'initial_capital') else C.INITIAL_CAPITAL)
        
        return dict(
            market_price=player.market_price,
            revenue=player.field_maybe_none('revenue') or 0,
            net_profit=player.field_maybe_none('net_profit') or 0,
            net_profit_formatted=f"{int(round(player.field_maybe_none('net_profit') or 0))}",  # 格式化顯示
            final_cash=player.field_maybe_none('final_cash') or player.current_cash,
            current_cash=player.current_cash,  # 添加當前現金，已扣除生產成本
            initial_cash=initial_cash,  # 生產前的現金
            treatment='trading',
            treatment_text='碳交易',
            production_cost=production_cost,  # 原始數值
            production_cost_formatted=f"{production_cost} 法幣",  # 格式化顯示
            remaining_rounds=C.NUM_ROUNDS - player.round_number,
            total_emissions=total_emissions,
            group_emissions=group_emissions,
            is_last_round=(player.round_number == C.NUM_ROUNDS),
            total_rounds=C.NUM_ROUNDS,
            progress_percentage=progress_percentage,
            final_marginal_cost=final_marginal_cost,
            avg_cost=avg_cost,
            cost_percentage=cost_percentage,
            final_cash_percentage=final_cash_percentage,
            trade_history=my_trades,
            price_history=price_history,
            reset_cash=C.RESET_CASH_EACH_ROUND,
            # 碳權信息
            permits=player.field_maybe_none('permits') or player.current_permits,  # 初始分配的碳權（如果為None則使用當前碳權）
            current_permits=player.current_permits,  # 當前碳權餘額
            permits_used=total_emissions,  # 本輪使用的碳權（等於碳排放量）
            permits_remaining=player.current_permits - total_emissions,  # 生產後剩餘的碳權
            # 交易統計
            total_bought=player.total_bought,
            total_sold=player.total_sold,
            total_spent=player.total_spent,
            total_earned=player.total_earned,
            avg_buy_price=avg_buy_price,
            avg_sell_price=avg_sell_price,
            final_payoff_info=final_payoff_info,  # 新增：最終報酬資訊
            # 新增：利潤計算相關
            current_total_final_value=current_total_final_value,
            current_profit=current_profit,
            current_profit_formatted=f"{int(round(current_profit))}",
            current_total_final_value_formatted=f"{int(round(current_total_final_value))}",
            initial_capital=player.initial_capital if hasattr(player, 'initial_capital') else C.INITIAL_CAPITAL,
            initial_capital_formatted=f"{int(round(float(player.initial_capital if hasattr(player, 'initial_capital') else C.INITIAL_CAPITAL)))}",
        )

class WaitForInstruction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

page_sequence = [
    Introduction,
    ReadyWaitPage,
    TradingMarket,
    ProductionDecision,
    ResultsWaitPage,
    Results, 
    WaitForInstruction
]
