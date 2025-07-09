from otree.api import *
import random
import json
import math
import time
import sys
import os
from typing import Dict, Any, List, Tuple, Optional, Union
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.shared_utils import (
    update_price_history,
    record_trade,
    cancel_player_orders,
    _generate_market_price,
    initialize_player_roles
)
from utils.trading_utils import (
    parse_orders,
    save_orders,
    validate_order,
    find_matching_orders,
    execute_trade,
    process_new_order,
    process_accept_offer,
    calculate_locked_resources,
    TradingError,
    InsufficientResourcesError,
    InvalidOrderError
)
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
    market_price = models.CurrencyField()
    price_history = models.LongStringField(initial='[]')
    start_time = models.IntegerField()  # 新增：記錄開始時間
    # 新增：社會最適產量和配額分配相關欄位
    total_optimal_emissions = models.FloatField()
    cap_multiplier = models.FloatField()
    cap_total = models.IntegerField()
    allocation_details = models.LongStringField(initial='[]')  # 儲存分配詳細資訊
    executed_trades = models.LongStringField(initial='[]')  # 新增：記錄成交的訂單

def initialize_roles(subsession: Subsession) -> None:
    """使用共享工具庫和配置文件初始化角色"""

    # 設定每回合的開始時間（確保每回合都重置時間）
    subsession.start_time = int(time.time())
    print(f"第{subsession.round_number}回合開始時間已設定")

    # 碳交易組特有的市場價格設定
    if config.carbon_trading_use_fixed_price:
        subsession.market_price = config.carbon_trading_fixed_market_price
        print(f"使用固定市場價格: {subsession.market_price}")
    else:
        subsession.market_price = _generate_market_price()
        print(f"隨機抽取市場價格: {subsession.market_price}")

    # 初始化玩家角色（會用到 subsession.market_price）
    initialize_player_roles(subsession, initial_capital=C.INITIAL_CAPITAL)
    
    # 計算社會最適產量和碳權分配
    players = subsession.get_players()
    allowance_allocation = calculate_optimal_allowance_allocation(players, subsession.market_price)
    
    # 儲存結果到 subsession
    subsession.total_optimal_emissions = allowance_allocation['TE_opt_total']
    subsession.cap_multiplier = allowance_allocation['r']
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
            print(f"Configuration: method = {allowance_allocation['config']['allocation_method']}, "
                  f"fixed_price = {allowance_allocation['config']['use_fixed_price']}")
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
    market_price: float
) -> Dict[str, Any]:
    """
    計算社會最適產量和碳權分配
    
    Args:
        players: 玩家列表
        market_price: 市場價格 (p)
    
    Returns:
        包含分配結果的字典
    """
    
    p = float(market_price)  # 市場價格
    c = config.carbon_trading_social_cost_per_unit_carbon  # 每單位碳的社會成本
    N = len(players)
    decimal_places = config.carbon_trading_decimal_places
    
    firm_details = []
    TE_opts = []
    
    # 計算每家廠商的社會最適產量和最適排放量
    for player in players:
        a_i = float(player.marginal_cost_coefficient)  # 邊際成本係數
        b_i = float(player.carbon_emission_per_unit)   # 每單位排放量
        
        # 社會最適產量：q_opt_i = (p - b_i * c) / a_i
        q_opt_i = int((p - b_i * c) / a_i)
        
        # 最適排放量：TE_opt_i = b_i * q_opt_i
        TE_opt_i = int(b_i * q_opt_i)
        
        firm_details.append({
            'a': a_i,
            'b': b_i,
            'q_opt': q_opt_i,
            'TE_opt': TE_opt_i,
        })
        
        TE_opts.append(TE_opt_i)
    
    # 社會最適排放總量
    TE_opt_total = sum(TE_opts)
    
    # 從配置檔案讀取配額倍率選項
    multipliers = config.carbon_trading_cap_multipliers
    r = random.choice(multipliers)
    
    # 計算總配額
    cap_total = r * TE_opt_total
    if config.carbon_trading_round_cap_total:
        cap_total_int = int(round(cap_total))  # 轉為整數
    else:
        cap_total_int = int(cap_total)  # 直接截斷
    
    # 平均分配給每個廠商
    base = cap_total_int // N  # 每人的基礎配額
    remainder = cap_total_int % N  # 剩餘配額
    
    # 初始分配
    allocations = [base] * N
    
    # 隨機分配剩餘配額（根據配置檔案的分配方法）
    allocation_method = config.carbon_trading_allocation_method
    if allocation_method == "equal_with_random_remainder" and remainder > 0:
        lucky_indices = random.sample(range(N), remainder)
        for idx in lucky_indices:
            allocations[idx] += 1
    
    return {
        'firm_details': firm_details,
        'TE_opt_total': round(TE_opt_total, decimal_places),
        'r': r,
        'cap_total': cap_total_int,
        'allocations': allocations,
        'config': {
            'market_price': p,
            'social_cost_per_unit_carbon': c,
            'decimal_places': decimal_places,
            'allocation_method': allocation_method,
            'cap_multipliers': multipliers,
            'use_fixed_price': config.carbon_trading_use_fixed_price
        }
    }

def creating_session(subsession: Subsession) -> None:
    """創建會話時的初始化"""
    # 讓所有人進入同一組
    subsession.set_group_matrix([subsession.get_players()])

    # 如果還沒抽過，先抽一個 shared selected round
    if "selected_round" not in subsession.session.vars:
        subsession.session.vars["selected_round"] = random.randint(1, C.NUM_ROUNDS)
    print(f"選中的報酬回合為：{subsession.session.vars['selected_round']}")
    
    # 初始化角色（start_time 將在每回合開始時設定）
    initialize_roles(subsession)

class Group(BaseGroup):
    buy_orders = models.LongStringField(initial='[]')
    sell_orders = models.LongStringField(initial='[]')

class Player(BasePlayer):
    # 添加這個欄位
    is_dominant = models.BooleanField()
    
    # 其他現有欄位
    marginal_cost_coefficient = models.IntegerField()
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
    
    # 新增：記錄生產成本表
    production_cost_table = models.LongStringField(initial='[]')
    
    selected_round = models.IntegerField()  # 新增：隨機選中的回合用於最終報酬
    # 新增：社會最適產量相關欄位
    optimal_production = models.FloatField()  # 個人最適產量 q_opt_i
    optimal_emissions = models.FloatField()   # 個人最適排放量 TE_opt_i

# ========== 輔助函數 ==========

def _record_submitted_offer(player: Player, direction: str, price: int, quantity: int) -> None:
    """記錄提交的訂單"""
    try:
        submitted_offers = json.loads(player.submitted_offers)
    except json.JSONDecodeError:
        submitted_offers = []
    
    # 計算時間戳（格式：MM:SS）
    current_time = int(time.time())
    if hasattr(player.subsession, 'start_time') and player.subsession.start_time:
        elapsed_seconds = current_time - player.subsession.start_time
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        timestamp = f"{minutes:02d}:{seconds:02d}"
    else:
        timestamp = "00:00"
    
    submitted_offers.append({
        'timestamp': timestamp,  # MM:SS 格式
        'direction': direction,
        'price': price,
        'quantity': quantity
    })
    player.submitted_offers = json.dumps(submitted_offers)

def _process_carbon_trading_order(
    player: Player,
    group: BaseGroup,
    direction: str,
    price: int,
    quantity: int
) -> Dict[int, Dict[str, Any]]:
    """處理碳交易訂單"""
    # 驗證訂單
    try:
        validate_order(player, direction, price, quantity, "碳權")
    except TradingError as e:
        return {player.id_in_group: {
            'type': 'fail',
            'message': str(e)
        }}
    
    # 解析現有訂單
    buy_orders, sell_orders = parse_orders(group)
    
    # 尋找匹配的訂單
    if direction == 'buy':
        # 尋找價格不高於出價且數量足夠的賣單
        matching_orders = [
            (i, order) for i, order in enumerate(sell_orders)
            if int(order[0]) != player.id_in_group and 
               float(order[1]) <= price and 
               int(order[2]) >= quantity  # 賣單數量必須足夠
        ]
        
        if matching_orders:
            # 找到最低價格的匹配賣單
            best_idx, best_order = min(matching_orders, key=lambda x: float(x[1][1]))
            seller_id = int(best_order[0])
            
            try:
                seller = grouget_player_by_id(seller_id)
                execute_trade(group, player, seller, float(best_order[1]), quantity, 'current_permits')
                
                # 保留：交易成功時取消雙方其他訂單
                cancel_player_orders(group, player.id_in_group, 'buy')
                cancel_player_orders(group, seller_id, 'sell')
                
                # 移除已成交的訂單
                buy_orders, sell_orders = parse_orders(group)
                sell_orders = [o for o in sell_orders if not (
                    int(o[0]) == seller_id and 
                    float(o[1]) == float(best_order[1]) and 
                    int(o[2]) == int(best_order[2])
                )]
                save_orders(group, buy_orders, sell_orders)
                
                # 創建通知
                notifications = {
                    player.id_in_group: f'交易成功：您以價格 {float(best_order[1])} 買入了 {quantity} 個碳權',
                    seller_id: f'交易成功：您以價格 {float(best_order[1])} 賣出了 {quantity} 個碳權'
                }
                
                return {'notifications': notifications, 'update_all': True}
                
            except Exception as e:
                print(f"交易執行失敗: {e}")
        
        # 添加新買單
        buy_orders.append([player.id_in_group, price, quantity])
        buy_orders.sort(key=lambda x: (-float(x[1]), int(x[0])))
        save_orders(group, buy_orders, sell_orders)
        
    else:  # sell
        # 尋找價格不低於要價且數量足夠的買單
        matching_orders = [
            (i, order) for i, order in enumerate(buy_orders)
            if int(order[0]) != player.id_in_group and 
               float(order[1]) >= price and 
               int(order[2]) >= quantity  # 買單數量必須足夠
        ]
        
        if matching_orders:
            # 找到最高價格的匹配買單
            best_idx, best_order = max(matching_orders, key=lambda x: float(x[1][1]))
            buyer_id = int(best_order[0])
            
            try:
                buyer = group.get_player_by_id(buyer_id)
                execute_trade(group, buyer, player, float(best_order[1]), quantity, 'current_permits')
                
                # 保留：交易成功時取消雙方其他訂單
                cancel_player_orders(group, buyer_id, 'buy')
                cancel_player_orders(group, player.id_in_group, 'sell')
                
                # 移除已成交的訂單
                buy_orders, sell_orders = parse_orders(group)
                buy_orders = [o for o in buy_orders if not (
                    int(o[0]) == buyer_id and 
                    float(o[1]) == float(best_order[1]) and 
                    int(o[2]) == int(best_order[2])
                )]
                save_orders(group, buy_orders, sell_orders)
                
                # 創建通知
                notifications = {
                    player.id_in_group: f'交易成功：您以價格 {float(best_order[1])} 賣出了 {quantity} 個碳權',
                    buyer_id: f'交易成功：您以價格 {float(best_order[1])} 買入了 {quantity} 個碳權'
                }
                
                return {'notifications': notifications, 'update_all': True}
                
            except Exception as e:
                print(f"交易執行失敗: {e}")
        
        # 添加新賣單
        sell_orders.append([player.id_in_group, price, quantity])
        sell_orders.sort(key=lambda x: (float(x[1]), int(x[0])))
        save_orders(group, buy_orders, sell_orders)
    
    return {'update_all': True}

def before_next_round(subsession: Subsession):
    """每回合重新初始化 dominant firm、成本係數、碳排係數等屬性"""
    initialize_player_roles(subsession, initial_capital=C.INITIAL_CAPITAL)

def _process_accept_carbon_offer(
    player: Player,
    group: BaseGroup,
    offer_type: str,
    target_id: int,
    price: float,
    quantity: int
) -> Dict[int, Dict[str, Any]]:
    """處理接受碳交易訂單"""
    # 檢查是否嘗試與自己交易
    if target_id == player.id_in_group:
        return {player.id_in_group: {
            'type': 'fail',
            'message': '不能與自己交易'
        }}
    
    # 解析現有訂單
    buy_orders, sell_orders = parse_orders(group)
    
    try:
        if offer_type == 'sell':
            # 接受賣單（玩家是買方）
            seller = group.get_player_by_id(target_id)
            execute_trade(group, player, seller, price, quantity, 'current_permits')
            
            # 取消雙方其他訂單
            cancel_player_orders(group, player.id_in_group, 'buy')
            cancel_player_orders(group, target_id, 'sell')
            
            # 移除已成交的訂單
            buy_orders, sell_orders = parse_orders(group)
            sell_orders = [o for o in sell_orders if not (
                int(o[0]) == target_id and 
                float(o[1]) == price and 
                int(o[2]) == quantity
            )]
            save_orders(group, buy_orders, sell_orders)
            
            notifications = {
                player.id_in_group: f'交易成功：您以價格 {price} 買入了 {quantity} 個碳權',
                target_id: f'交易成功：您以價格 {price} 賣出了 {quantity} 個碳權'
            }
            
            return {'notifications': notifications, 'update_all': True}
            
        else:  # offer_type == 'buy'
            # 接受買單（玩家是賣方）
            # 檢查可用碳權
            locked_permits = sum(
                int(o[2]) for o in sell_orders 
                if int(o[0]) == player.id_in_group
            )
            available_permits = player.current_permits - locked_permits
            
            if available_permits < quantity:
                return {player.id_in_group: {
                    'type': 'fail',
                    'message': f'碳權不足！您已有掛單佔用碳權 {locked_permits}，'
                              f'可用碳權只有 {available_permits}，但此交易需要 {quantity}'
                }}
            
            buyer = group.get_player_by_id(target_id)
            execute_trade(group, buyer, player, price, quantity, 'current_permits')
            
            # 取消雙方其他訂單
            cancel_player_orders(group, target_id, 'buy')
            cancel_player_orders(group, player.id_in_group, 'sell')
            
            # 移除已成交的訂單
            buy_orders, sell_orders = parse_orders(group)
            buy_orders = [o for o in buy_orders if not (
                int(o[0]) == target_id and 
                float(o[1]) == price and 
                int(o[2]) == quantity
            )]
            save_orders(group, buy_orders, sell_orders)
            
            notifications = {
                player.id_in_group: f'交易成功：您以價格 {price} 賣出了 {quantity} 個碳權',
                target_id: f'交易成功：您以價格 {price} 買入了 {quantity} 個碳權'
            }
            
            return {'notifications': notifications, 'update_all': True}
            
    except Exception as e:
        print(f"接受訂單失敗: {e}")
        return {player.id_in_group: {
            'type': 'fail',
            'message': '交易失敗：找不到交易對象'
        }}

def _cancel_specific_order(
    group: BaseGroup,
    player_id: int,
    direction: str,
    price: float,
    quantity: int
) -> None:
    """取消特定訂單"""
    buy_orders, sell_orders = parse_orders(group)
    
    if direction == 'buy':
        buy_orders = [o for o in buy_orders if not (
            int(o[0]) == player_id and
            float(o[1]) == price and 
            int(o[2]) == quantity
        )]
    else:
        sell_orders = [o for o in sell_orders if not (
            int(o[0]) == player_id and
            float(o[1]) == price and 
            int(o[2]) == quantity
        )]
    
    save_orders(group, buy_orders, sell_orders)

def _create_notification_states(
    group: BaseGroup,
    notifications: Dict[int, str]
) -> Dict[int, Dict[str, Any]]:
    """創建包含通知的市場狀態"""
    market_states = {}
    for p in group.get_players():
        state = TradingMarket.market_state(p)
        if p.id_in_group in notifications:
            state['notification'] = {
                'type': 'success',
                'message': notifications[p.id_in_group]
            }
        market_states[p.id_in_group] = state
    return market_states

# 更新價格歷史的函數
def update_price_history(subsession, trade_price, event='trade'):
    try:
        price_history = json.loads(subsession.price_history)
    except json.JSONDecodeError:
        price_history = []
    
    # 獲取當前時間
    current_time = int(time.time())
    # 使用相對時間格式 (當前時間 - 開始時間)
    if hasattr(subsession, 'start_time') and subsession.start_time:
        elapsed_seconds = current_time - subsession.start_time
    else:
        elapsed_seconds = 0  # 如果沒有開始時間，則使用0
    
    minutes = elapsed_seconds // 60
    seconds = elapsed_seconds % 60
    
    price_record = {
        'timestamp': f"{minutes:02d}:{seconds:02d}",  # 使用分:秒格式
        'price': float(trade_price),
        'event': event,
        'market_price': float(subsession.market_price),
        'round': subsession.round_number
    }
    
    price_history.append(price_record)
    subsession.price_history = json.dumps(price_history)
    
    return price_history

# 使用共用的 record_trade 函數（已從 utils.shared_utils 匯入）

# 新增函數：取消玩家所有同方向的掛單
def cancel_player_orders(group, player_id, order_type):
    if order_type == 'buy':
        try:
            buy_orders = json.loads(group.buy_orders)
            # 計算取消數量
            old_count = len([o for o in buy_orders if int(o[0]) == player_id])
            # 過濾掉該玩家的所有買單
            buy_orders = [o for o in buy_orders if int(o[0]) != player_id]
            group.buy_orders = json.dumps(buy_orders)
            print(f"已自動取消玩家 {player_id} 的 {old_count} 筆買單")
        except json.JSONDecodeError:
            pass
    elif order_type == 'sell':
        try:
            sell_orders = json.loads(group.sell_orders)
            # 計算取消數量
            old_count = len([o for o in sell_orders if int(o[0]) == player_id])
            # 過濾掉該玩家的所有賣單
            sell_orders = [o for o in sell_orders if int(o[0]) != player_id]
            group.sell_orders = json.dumps(sell_orders)
            print(f"已自動取消玩家 {player_id} 的 {old_count} 筆賣單")
        except json.JSONDecodeError:
            pass

def set_payoffs(group: BaseGroup):
    for p in group.get_players():
        if p.production is None:
            p.production = 0
        
        # 使用與前端相同的邏輯：累加每個單位的邊際成本和擾動
        random.seed(p.id_in_group * 1000 + p.round_number)
        cost = 0
        for i in range(1, p.production + 1):
            unit_marginal_cost = p.marginal_cost_coefficient * i
            unit_disturbance = round(random.uniform(-1, 1), 3)  # 四捨五入到3位小數，與前端一致
            cost += unit_marginal_cost + unit_disturbance
        random.seed()  # 重置隨機種子
        revenue = p.production * p.market_price
        
        # 修改利潤計算：改為總資金減去初始資金
        # 總資金 = 當前現金 + 剩餘碳權價值（按市場價格計算）
        # 注意：這裡假設碳權的市場價格為一個固定值，您可能需要根據實際情況調整
        # 暫時使用一個合理的碳權價格估算，或者只計算現金部分
        
        # 計算最終現金（扣除生產成本後）
        final_cash_after_production = p.current_cash - cost
        
        # 計算利潤：最終總資金 - 初始資金
        # 這裡我們將利潤定義為：(最終現金 + 生產收入) - 初始資金
        total_final_value = final_cash_after_production + revenue
        profit = total_final_value - p.initial_capital
        
        p.revenue = revenue
        p.total_cost = float(cost)  # 轉換為浮點數
        p.net_profit = float(profit)  # 修改：使用新的利潤計算
        p.final_cash = final_cash_after_production + revenue  # 最終現金（包含收入）
        p.payoff = profit

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

class ReadyWaitPage(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = initialize_roles

class TradingMarket(Page):
    timeout_seconds = C.TRADING_TIME

    @staticmethod
    def vars_for_template(player):

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
        )

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
            _record_submitted_offer(player, direction, price, quantity)
            
            print(f"玩家 {player.id_in_group} 提交{direction}單: "
                  f"價格={price}, 數量={quantity}, "
                  f"現金={player.current_cash}, 碳權={player.current_permits}")
            
            # 使用新的處理函數
            result = _process_carbon_trading_order(
                player, group, direction, price, quantity
            )
            
            # 如果需要更新所有玩家
            if result.get('update_all'):
                return {p.id_in_group: TradingMarket.market_state(p) 
                        for p in group.get_players()}
            else:
                return result
        
        # 處理接受訂單
        elif data.get('type') == 'accept_offer':
            offer_type = data.get('offer_type')
            target_id = int(data.get('player_id', 0))
            price = float(data.get('price', 0))
            quantity = int(data.get('quantity', 0))
            
            print(f"玩家 {player.id_in_group} 接受{offer_type}單: "
                  f"對象玩家={target_id}, 價格={price}, 數量={quantity}")
            
            # 使用新的處理函數
            result = _process_accept_carbon_offer(
                player, group, offer_type, target_id, price, quantity
            )
            
            # 處理通知
            if result.get('notifications'):
                return _create_notification_states(group, result['notifications'])
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
            _cancel_specific_order(group, player.id_in_group, direction, price, quantity)
            
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
            
            # 修改: 不排除自己的訂單，讓所有掛單參與最優價格競爭
            all_buy_offers = [{'player_id': int(pid), 'price': int(float(price)), 'quantity': int(qt)} 
                            for pid, price, qt in buy_sorted]
            
            all_sell_offers = [{'player_id': int(pid), 'price': int(float(price)), 'quantity': int(qt)} 
                             for pid, price, qt in sell_sorted]
            
            # 合併顯示同單位掛單邏輯
            public_buy_offers = []
            public_sell_offers = []
            
            # 按數量分組，只保留每組中最高買價/最低賣價
            qty_buy_map = {}
            for offer in all_buy_offers:  # 修改: 使用all_buy_offers
                qty = offer['quantity']
                if qty not in qty_buy_map or offer['price'] > qty_buy_map[qty]['price']:
                    qty_buy_map[qty] = offer
            
            qty_sell_map = {}
            for offer in all_sell_offers:  # 修改: 使用all_sell_offers
                qty = offer['quantity']
                if qty not in qty_sell_map or offer['price'] < qty_sell_map[qty]['price']:
                    qty_sell_map[qty] = offer
            
            # 將合併後的訂單添加到公共列表
            for qty, offer in qty_buy_map.items():
                public_buy_offers.append(offer)
            
            for qty, offer in qty_sell_map.items():
                public_sell_offers.append(offer)
            
            # 排序
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

        # 添加獲利預估表
        profit_table = []
        # 重新使用相同的隨機種子以確保一致性
        random.seed(player.id_in_group * 1000 + player.round_number)
        for q in range(1, player.max_production + 1):
            # 計算總成本：累加每個單位的邊際成本和擾動
            total_cost = 0
            temp_seed = player.id_in_group * 1000 + player.round_number
            random.seed(temp_seed)
            for i in range(1, q + 1):
                unit_marginal_cost = player.marginal_cost_coefficient * i
                unit_disturbance = random.uniform(-1, 1)
                total_cost += unit_marginal_cost + unit_disturbance
            
            # 計算第q個單位的邊際成本（用於表格顯示）
            random.seed(temp_seed)
            for i in range(1, q):  # 跳過前面的隨機數
                random.uniform(-1, 1)
            q_unit_marginal_cost = player.marginal_cost_coefficient * q + random.uniform(-1, 1)
            
            rev = q * player.market_price
            profit_table.append({
                'quantity': q,
                'marginal_cost': round(q_unit_marginal_cost, 2),
                'profit': rev - total_cost,  # 保持浮點數精度
            })
        random.seed()  # 重置隨機種子

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
            'profit_table': profit_table,
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
        
        # 為每個生產量預先計算固定的隨機擾動值
        random.seed(player.id_in_group * 1000 + player.round_number)
        disturbance_values = []
        for q in range(1, player.max_production + 1):
            disturbance_values.append(round(random.uniform(-1, 1), 3))
        random.seed()  # 重置隨機種子
        
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
            disturbance_values=disturbance_values,  # 新增：固定的擾動值列表
        )

    @staticmethod
    def before_next_page(player, timeout_happened):
        # 在進入下一頁前更新玩家的現金，扣除生產成本
        if player.production is not None and player.production > 0:
            cost = (player.marginal_cost_coefficient * player.production**2) / 2
            # 現金用於交易，不扣除生產成本
            # player.current_cash -= cost
        
        # 記錄生產成本表
        if not timeout_happened:
            from utils.shared_utils import generate_production_cost_table
            import json
            
            cost_table = generate_production_cost_table(player)
            player.production_cost_table = json.dumps(cost_table)



class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs

# 碳交易組 Results 類
class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        # 安全地訪問total_cost，如果為None則重新計算
        if player.field_maybe_none('total_cost') is not None:
            production_cost = player.total_cost
        else:
            # 如果total_cost為None，重新計算（使用新的累加邏輯）
            random.seed(player.id_in_group * 1000 + player.round_number)
            production_cost = 0
            for i in range(1, player.production + 1):
                unit_marginal_cost = player.marginal_cost_coefficient * i
                unit_disturbance = round(random.uniform(-1, 1), 3)  # 四捨五入到3位小數，與前端一致
                production_cost += unit_marginal_cost + unit_disturbance
            random.seed()  # 重置隨機種子
        
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
            # 使用相同的隨機種子計算最後一個單位的邊際成本
            random.seed(player.id_in_group * 1000 + player.round_number)
            for i in range(1, player.production):  # 跳過前面的隨機數
                random.uniform(-1, 1)
            final_unit_disturbance = random.uniform(-1, 1)
            final_marginal_cost = int(player.marginal_cost_coefficient * player.production + final_unit_disturbance)
            random.seed()  # 重置隨機種子
        
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
            
            # 重新計算被選中回合的成本（確保一致性）
            random.seed(player.id_in_group * 1000 + selected_round)
            selected_cost = 0
            for i in range(1, selected_round_player.production + 1):
                unit_marginal_cost = selected_round_player.marginal_cost_coefficient * i
                unit_disturbance = round(random.uniform(-1, 1), 3)
                selected_cost += unit_marginal_cost + unit_disturbance
            random.seed()
            
            selected_revenue = selected_round_player.production * selected_round_player.market_price
            selected_emissions = selected_round_player.production * selected_round_player.carbon_emission_per_unit
            
            # 修改：使用新的利潤計算方式
            # 計算被選中回合的最終總資金
            selected_final_cash_after_production = selected_round_player.current_cash - selected_cost
            selected_total_final_value = selected_final_cash_after_production + selected_revenue
            selected_profit = selected_total_final_value - selected_round_player.initial_capital
            
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
                'cost': selected_cost,
                'profit': selected_profit,
                'emissions': selected_emissions,
                'group_emissions': selected_group_emissions,
                'permits_used': selected_emissions,
                'profit_formatted': f"{int(round(selected_profit))}",
                'cost_formatted': f"{int(round(selected_cost))}",
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
            production_cost_formatted=f"{int(round(production_cost))}",  # 格式化顯示
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
