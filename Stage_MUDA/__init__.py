from otree.api import *
import random
import json
import sys
import os
from typing import Dict, Any, List
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.trading_utils import *
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
    executed_trades = models.LongStringField(initial='[]')

def creating_session(subsession: Subsession) -> None:
    """創建會話時的初始化"""
    # 讓所有人進入同一組
    subsession.set_group_matrix([subsession.get_players()])

    # 為 MUDA 單獨抽取 selected_round（與其他 app 獨立）
    session_key = "selected_round__Stage_MUDA"
    if session_key not in subsession.session.vars:
        subsession.session.vars[session_key] = random.randint(1, C.NUM_ROUNDS)
        print(f"[MUDA] 本 app 的 selected_round 抽中第 {subsession.session.vars[session_key]} 輪")
    
    # 設定參考價格
    reference_price = random.choice(config.muda_item_price_options)
    subsession.item_market_price = reference_price
    print(f"第{subsession.round_number}輪 - MUDA參考碳權價格: {reference_price}")
    
    # 初始化玩家
    for p in subsession.get_players():
        p.selected_round = subsession.session.vars[session_key]
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
    initial_capital = models.CurrencyField()
    final_cash = models.CurrencyField()
    current_cash = models.CurrencyField()
    current_items = models.IntegerField()
    personal_item_value = models.CurrencyField()
    
    # 交易統計
    total_bought = models.IntegerField(default=0)
    total_sold = models.IntegerField(default=0)
    total_spent = models.CurrencyField(default=0)
    total_earned = models.CurrencyField(default=0)
    
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

class ReadyWaitPage(CommonReadyWaitPage):
    pass

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
        
        # 修復：統一處理 submit_offer
        if data.get('type') == 'submit_offer':
            direction = data.get('direction')
            price = int(data.get('price', 0))
            quantity = int(data.get('quantity', 0))
            
            # 記錄提交的訂單
            record_submitted_offer(player, direction, price, quantity)
            
            print(f"玩家 {player.id_in_group} 提交{direction}單: "
                  f"價格={price}, 數量={quantity}, "
                  f"現金={player.current_cash}, {C.ITEM_NAME}={player.current_items}")
            
            # 使用統一的 process_new_order 函數
            result = process_new_order(
                player, group, direction, price, quantity, 
                C.ITEM_NAME, 'current_items'
            )
            
            # 處理通知
            if result.get('notifications'):
                market_states = {}
                for p in group.get_players():
                    state = TradingMarket.market_state(p)
                    if p.id_in_group in result['notifications']:
                        # 根據 result.type 決定通知類型
                        notification_type = 'success'
                        if result.get('type') == 'fail':
                            notification_type = 'error'  # 前端會轉換為 danger
                        
                        state['notification'] = {
                            'type': notification_type,
                            'message': result['notifications'][p.id_in_group]
                        }
                    market_states[p.id_in_group] = state
                return market_states
            elif result.get('update_all'):
                return {p.id_in_group: TradingMarket.market_state(p) 
                        for p in group.get_players()}
            else:
                return result
        
        # 修復：統一處理 accept_offer，統一使用 player_id 參數
        elif data.get('type') == 'accept_offer':
            offer_type = data.get('offer_type')
            target_id = int(data.get('player_id', 0))  # 統一使用 player_id
            price = float(data.get('price'))
            quantity = int(data.get('quantity'))
            
            print(f"玩家 {player.id_in_group} 接受{offer_type}單: "
                  f"對象玩家={target_id}, 價格={price}, 數量={quantity}")
            
            # 使用統一的 process_accept_offer 函數
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
        
        # 修復：統一處理 cancel_offer
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
        
        # 修復：統一返回數據格式，使用 'update' 而不是 'market_update'
        return {
            'type': 'update',
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
