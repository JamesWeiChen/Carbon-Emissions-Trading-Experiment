from otree.api import *
import random
import json
import time
import sys
import os
from typing import Dict, Any, List
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.shared_utils import (
    update_price_history,
    record_trade,
    cancel_player_orders
)
from utils.trading_utils import (
    parse_orders,
    save_orders,
    process_new_order,
    process_accept_offer,
    TradingError
)
from configs.config import config

doc = config.get_stage_description('muda')

class C(BaseConstants):
    NAME_IN_URL = config.get_stage_name_in_url('muda')
    PLAYERS_PER_GROUP = config.players_per_group
    NUM_ROUNDS = config.muda_num_rounds
    TRADING_TIME = config.muda_trading_time
    INITIAL_CAPITAL = config.get_stage_initial_capital('muda')
    ITEM_NAME = config.muda_item_name
    RESET_CASH_EACH_ROUND = config.muda_reset_cash_each_round

class Subsession(BaseSubsession):
    item_market_price = models.CurrencyField()
    price_history = models.LongStringField(initial='[]')
    start_time = models.IntegerField()
    executed_trades = models.LongStringField(initial='[]')  # 新增：記錄成交的訂單

def creating_session(subsession: Subsession) -> None:
    """創建會話時的初始化"""
    # 讓所有人進入同一組
    subsession.set_group_matrix([subsession.get_players()])

    # 所有人共用 selected_round
    if "selected_round" not in subsession.session.vars:
        subsession.session.vars["selected_round"] = random.randint(1, C.NUM_ROUNDS)
        print(f"[MUDA] 共用的 selected_round 抽中第 {subsession.session.vars['selected_round']} 輪")
    
    # 設定參考價格
    reference_price = random.choice(config.muda_item_price_options)
    subsession.item_market_price = reference_price
    print(f"第{subsession.round_number}輪 - MUDA參考碳權價格: {reference_price}")
    
    # 初始化玩家
    for p in subsession.get_players():
        p.selected_round = subsession.session.vars["selected_round"]
        _initialize_player(p)

def _initialize_player(player: BasePlayer) -> None:
    """初始化單個玩家"""
    player.current_cash = C.INITIAL_CAPITAL
    player.initial_capital = C.INITIAL_CAPITAL
    player.current_items = random.randint(3, 8)
        
    # 設定個人碳權價值
    player.personal_item_value = random.choice(config.muda_item_price_options)
    print(f"玩家 {player.id_in_group} 的碳權價值: {player.personal_item_value} "
          f"(持有數量: {player.current_items})")

class Group(BaseGroup):
    buy_orders = models.LongStringField(initial='[]')
    sell_orders = models.LongStringField(initial='[]')

class Player(BasePlayer):
    # 交易相關欄位
    buy_quantity = models.IntegerField(min=0)
    buy_price = models.FloatField(min=0)
    sell_quantity = models.IntegerField(min=0)
    sell_price = models.FloatField(min=0)
    
    # 財務相關
    cash = models.CurrencyField()
    items = models.IntegerField()
    initial_capital = models.CurrencyField()
    final_cash = models.CurrencyField()
    current_cash = models.CurrencyField()
    current_items = models.IntegerField()
    personal_item_value = models.CurrencyField()
    
    # 交易統計
    total_bought = models.IntegerField(default=0)  # 總買入數量：玩家在本回合買入的碳權總數
    total_sold = models.IntegerField(default=0)    # 總賣出數量：玩家在本回合賣出的碳權總數
    total_spent = models.CurrencyField(default=0)  # 總支出金額：玩家在本回合買入碳權花費的總金額
    total_earned = models.CurrencyField(default=0) # 總收入金額：玩家在本回合賣出碳權獲得的總金額
    
    # 結算相關
    item_value = models.CurrencyField()
    total_value = models.CurrencyField()
    submitted_offers = models.LongStringField(initial='[]')
    selected_round = models.IntegerField()

def set_payoffs(group: BaseGroup) -> None:
    """設置玩家報酬"""
    for p in group.get_players():
        # 計算資產價值
        personal_value = p.field_maybe_none('personal_item_value') or p.subsession.item_market_price
        p.item_value = p.current_items * personal_value
        p.total_value = p.current_cash + p.item_value
        p.final_cash = p.current_cash
        
        # 計算利潤
        profit = p.total_value - p.initial_capital
        p.payoff = profit

class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player) -> bool:
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        return {
            'num_rounds': C.NUM_ROUNDS,
            'item_name': C.ITEM_NAME,
            'initial_capital': C.INITIAL_CAPITAL,
        }

class ReadyWaitPage(WaitPage):
    wait_for_all_groups = True
    
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        subsession.start_time = int(time.time()+2) #延遲兩秒
        print(f"[MUDA] 所有人準備就緒，start_time 設為 {subsession.start_time}")

class TradingMarket(Page):
    form_model = 'player'
    form_fields = ['buy_quantity', 'buy_price', 'sell_quantity', 'sell_price']
    timeout_seconds = C.TRADING_TIME

    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        
        personal_value = player.field_maybe_none('personal_item_value') or player.subsession.item_market_price
        total_item_value = player.current_items * personal_value
        
        return {
            'cash': int(player.current_cash),
            'items': player.current_items,
            'timeout_seconds': TradingMarket.timeout_seconds,
            'player_id': player.id_in_group,
            'item_name': C.ITEM_NAME,
            'market_price': int(player.subsession.item_market_price),
            'personal_item_value': int(personal_value),
            'total_item_value': int(total_item_value),
            'start_time': player.subsession.start_time,
        }

    @staticmethod
    def live_method(player: Player, data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """處理即時交易請求"""
        # 初次連線或 ping
        if data is None or data.get('type') == 'ping':
            return {p.id_in_group: TradingMarket.market_state(p) for p in player.group.get_players()}
            
        group = player.group
        
        # 處理新訂單
        if data.get('type') == 'place_order':
            direction = data.get('direction')
            price = int(data.get('price', 0))
            quantity = int(data.get('quantity', 0))
            
            # 記錄提交的訂單
            _record_submitted_offer(player, direction, price, quantity)
            
            print(f"玩家 {player.id_in_group} 提交{direction}單: "
                  f"價格={price}, 數量={quantity}, "
                  f"現金={player.current_cash}, {C.ITEM_NAME}={player.current_items}")
            
            # 處理訂單
            result = process_new_order(
                player, group, direction, price, quantity, 
                C.ITEM_NAME, 'current_items'
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
            target_id = int(data.get('target_id') or data.get('player_id'))
            price = float(data.get('price'))
            quantity = int(data.get('quantity'))
            
            print(f"玩家 {player.id_in_group} 接受{offer_type}單: "
                  f"對象玩家={target_id}, 價格={price}, 數量={quantity}")
            
            # 處理接受訂單
            result = process_accept_offer(
                player, group, offer_type, target_id, price, quantity,
                C.ITEM_NAME, 'current_items'
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
        elif data.get('type') == 'cancel_order':
            order_type = data.get('order_type')
            order_index = int(data.get('order_index', -1))
            
            if order_type in ['buy', 'sell'] and order_index >= 0:
                buy_orders, sell_orders = parse_orders(group)
                
                if order_type == 'buy' and order_index < len(buy_orders):
                    if int(buy_orders[order_index][0]) == player.id_in_group:
                        del buy_orders[order_index]
                        save_orders(group, buy_orders, sell_orders)
                        print(f"玩家 {player.id_in_group} 取消了買單 #{order_index}")
                elif order_type == 'sell' and order_index < len(sell_orders):
                    if int(sell_orders[order_index][0]) == player.id_in_group:
                        del sell_orders[order_index]
                        save_orders(group, buy_orders, sell_orders)
                        print(f"玩家 {player.id_in_group} 取消了賣單 #{order_index}")
                
                return {p.id_in_group: TradingMarket.market_state(p) 
                        for p in group.get_players()}
        
        return {}

    @staticmethod
    def market_state(player: Player) -> Dict[str, Any]:
        """獲取市場狀態"""
        group = player.group
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
            for offer in all_buy_offers:
                qty = offer['quantity']
                if qty not in qty_buy_map or offer['price'] > qty_buy_map[qty]['price']:
                    qty_buy_map[qty] = offer
            
            qty_sell_map = {}
            for offer in all_sell_offers:
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
        
        # 獲取交易歷史
        try:
            trade_history = json.loads(player.subsession.executed_trades)
            recent_trades = trade_history[-10:]  # 最近10筆交易
        except (json.JSONDecodeError, AttributeError):
            recent_trades = []
        
        # 獲取價格歷史
        try:
            price_history = json.loads(player.subsession.price_history)
        except (json.JSONDecodeError, AttributeError):
            price_history = []
        
        return {
            'type': 'market_update',
            'cash': int(player.current_cash),
            'items': player.current_items,
            'my_buy_offers': my_buy_offers,
            'my_sell_offers': my_sell_offers,
            'buy_offers': public_buy_offers,
            'sell_offers': public_sell_offers,
            'trade_history': recent_trades,
            'price_history': price_history,
            'total_bought': player.total_bought,
            'total_sold': player.total_sold,
            'total_spent': int(player.total_spent),
            'total_earned': int(player.total_earned),
        }

    @staticmethod
    def before_next_page(player: Player, timeout_happened: bool) -> None:
        """頁面結束前的處理"""
        # 清理未成交的訂單
        if timeout_happened:
            cancel_player_orders(player.group, player.id_in_group, 'buy')
            cancel_player_orders(player.group, player.id_in_group, 'sell')

    @staticmethod
    def js_vars(player: Player) -> Dict[str, Any]:
        """提供給 JavaScript 的變數"""
        return {
            'player_id': player.id_in_group,
            'item_name': C.ITEM_NAME,
            'start_time': player.subsession.start_time,
        }

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

def _format_orders(orders: List[List], current_player_id: int) -> List[Dict[str, Any]]:
    """格式化訂單列表"""
    formatted_orders = []
    for i, order in enumerate(orders):
        player_id, price, quantity = int(order[0]), float(order[1]), int(order[2])
        formatted_orders.append({
            'index': i,
            'player_id': player_id,
            'price': price,
            'quantity': quantity,
            'is_mine': player_id == current_player_id
        })
    return formatted_orders

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs

class Results(Page):
    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        # 計算全體玩家的物品總量
        group_items_total = sum(p.current_items for p in player.group.get_players())
        
        # 獲取交易歷史
        try:
            trade_history = json.loads(player.subsession.executed_trades)
        except (json.JSONDecodeError, AttributeError):
            trade_history = []
        
        # 獲取最終報酬資訊
        final_payoff_info = _calculate_final_payoff_info(player)
        
        # 計算進度資訊
        is_last_round = player.round_number == C.NUM_ROUNDS
        remaining_rounds = C.NUM_ROUNDS - player.round_number
        progress_percentage = (player.round_number / C.NUM_ROUNDS) * 100
        
        return {
            # 基本資訊
            'current_cash': player.current_cash,
            'current_items': player.current_items,
            'item_value': player.item_value,
            'total_value': player.total_value,
            'initial_capital': player.initial_capital,
            'profit': player.payoff,
            
            # 交易統計
            'total_bought': player.total_bought,
            'total_sold': player.total_sold,
            'total_spent': player.total_spent,
            'total_earned': player.total_earned,
            'trade_count': len(trade_history),
            
            # 市場資訊
            'market_price': player.subsession.item_market_price,
            'personal_item_value': player.personal_item_value,
            'group_items_total': group_items_total,
            
            # 回合資訊
            'current_round': player.round_number,
            'total_rounds': C.NUM_ROUNDS,
            'is_last_round': is_last_round,
            'remaining_rounds': remaining_rounds,
            'progress_percentage': progress_percentage,
            
            # 其他
            'item_name': C.ITEM_NAME,
            'final_payoff_info': final_payoff_info,

            # 顯示用格式化值
            'total_value_formatted': f"{int(round(player.total_value))}",
            'initial_capital_formatted': f"{int(round(player.initial_capital))}",
            'current_profit_formatted': f"{int(round(player.total_value - player.initial_capital))}",
        }

class WaitForInstruction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

def _calculate_final_payoff_info(player: Player) -> Dict[str, Any]:
    """計算最終報酬資訊"""
    if player.round_number != C.NUM_ROUNDS:
        return None
    
    # 獲取選中的回合
    selected_round = player.field_maybe_none('selected_round')
    if selected_round is None:
        selected_round = random.randint(1, C.NUM_ROUNDS)
        player.selected_round = selected_round
    
    selected_round_player = player.in_round(selected_round)
    
    # 計算選中回合的資料
    personal_value = (selected_round_player.field_maybe_none('personal_item_value') or 
                     selected_round_player.subsession.item_market_price)
    item_value = selected_round_player.current_items * personal_value
    total_value = selected_round_player.current_cash + item_value
    profit = total_value - selected_round_player.initial_capital
    
    return {
        'selected_round': selected_round,
        'cash': selected_round_player.current_cash,
        'items': selected_round_player.current_items,
        'item_value': item_value,
        'total_value': total_value,
        'profit': profit,
        'profit_formatted': f"{int(round(profit))}",
        'total_value_formatted': f"{int(round(total_value))}",
        'final_cash_formatted': f"{int(round(selected_round_player.current_cash))}",
        'initial_capital_formatted': f"{int(round(selected_round_player.initial_capital))}",
        'item_count': selected_round_player.current_items,
        'personal_item_value_formatted': f"{int(round(personal_value))}",
        'item_value_formatted': f"{int(round(item_value))}",
    }

page_sequence = [Introduction, ReadyWaitPage, TradingMarket, ResultsWaitPage, Results, WaitForInstruction]
