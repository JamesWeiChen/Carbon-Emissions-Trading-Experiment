from otree.api import *
import random
import json
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.shared_utils import (
    update_price_history,
    record_trade,
    cancel_player_orders
)
from configs.config import config

doc = config.get_stage_description('muda')

class C(BaseConstants):
    NAME_IN_URL = config.get_stage_name_in_url('muda')
    PLAYERS_PER_GROUP = config.players_per_group
    NUM_ROUNDS = config.num_rounds
    TRADING_TIME = config.muda_trading_time
    INITIAL_CAPITAL = config.get_stage_initial_capital('muda')
    # 交易物品的名稱（可自定義）
    ITEM_NAME = config.muda_item_name
    # 控制是否每輪重置現金
    RESET_CASH_EACH_ROUND = config.muda_reset_cash_each_round

class Subsession(BaseSubsession):
    item_market_price = models.CurrencyField()
    price_history = models.LongStringField(initial='[]')
    start_time = models.IntegerField()  # 新增：記錄開始時間

def creating_session(subsession: Subsession):
    # 讓所有人進入同一組
    subsession.set_group_matrix([subsession.get_players()])
    # 設置開始時間
    subsession.start_time = int(time.time())
    
    # 設定一個參考價格（用於記錄和顯示）
    reference_price = random.choice(config.muda_item_price_options)
    subsession.item_market_price = reference_price
    print(f"第{subsession.round_number}輪 - MUDA參考碳權價格: {reference_price}")
    
    # 其他初始化代碼...
    for p in subsession.get_players():
        if C.RESET_CASH_EACH_ROUND or p.round_number == 1:
            p.current_cash = C.INITIAL_CAPITAL
        else:
            p.current_cash = p.in_round(p.round_number - 1).final_cash
        
        p.initial_capital = p.current_cash
        p.current_items = random.randint(3, 8)
        
        # 給每個玩家設定不同的碳權價值，創造交易動機
        player_item_value = random.choice(config.muda_item_price_options)
        p.personal_item_value = player_item_value
        print(f"玩家 {p.id_in_group} 的碳權價值: {player_item_value} (持有數量: {p.current_items})")

class Group(BaseGroup):
    buy_orders = models.LongStringField(initial='[]')
    sell_orders = models.LongStringField(initial='[]')
    # 交易歷史記錄
    trade_history = models.LongStringField(initial='[]')

class Player(BasePlayer):
    # 交易相關欄位
    buy_quantity = models.IntegerField(min=0)
    buy_price = models.FloatField(min=0)
    sell_quantity = models.IntegerField(min=0)
    sell_price = models.FloatField(min=0)
    
    # 其他現有欄位
    cash = models.CurrencyField()
    items = models.IntegerField()
    initial_capital = models.CurrencyField()
    final_cash = models.CurrencyField()
    current_cash = models.CurrencyField()
    current_items = models.IntegerField()  # 持有的物品數量
    personal_item_value = models.CurrencyField()  # 個人的碳權價值
    # 交易相關統計
    total_bought = models.IntegerField(default=0)  # 累計購買數量
    total_sold = models.IntegerField(default=0)    # 累計賣出數量
    total_spent = models.CurrencyField(default=0)  # 累計購買支出
    total_earned = models.CurrencyField(default=0) # 累計賣出收入
    # 結算相關
    item_value = models.CurrencyField()  # 持有物品價值
    total_value = models.CurrencyField()  # 總資產價值（現金+物品）
    # 新增：記錄所有提交的掛單
    submitted_offers = models.LongStringField(initial='[]')
    # 新增：隨機選中的回合用於最終報酬
    selected_round = models.IntegerField()

def initialize_roles(subsession: Subsession):
    for p in subsession.get_players():
        # 根據設置決定初始現金來源
        if C.RESET_CASH_EACH_ROUND or p.round_number == 1:
            p.current_cash = C.INITIAL_CAPITAL
        else:
            p.current_cash = p.in_round(p.round_number - 1).final_cash
        
        # 記錄初始資金，無論來源
        p.initial_capital = p.current_cash
        
        # 每個玩家隨機開始持有一些物品
        p.current_items = random.randint(3, 8)
        
        # 給每個玩家設定不同的碳權價值（強制設定，即使已存在）
        player_item_value = random.choice(config.muda_item_price_options)
        p.personal_item_value = player_item_value
        print(f"玩家 {p.id_in_group} 的碳權價值: {player_item_value} (持有數量: {p.current_items})")
        
        # 為每個玩家設置selected_round
        if p.round_number == 1:
            # 在第一輪隨機選擇一個回合用於最終報酬
            p.selected_round = random.randint(1, config.num_rounds)
        else:
            # 在後續回合中保持與第一輪相同的selected_round
            p.selected_round = p.in_round(1).selected_round

def set_payoffs(group: BaseGroup):
    for p in group.get_players():
        # 安全訪問個人碳權價值，如果為None則使用市場價格
        personal_value = p.field_maybe_none('personal_item_value') or p.subsession.item_market_price
        
        # 計算持有物品的價值（使用個人價值）
        p.item_value = p.current_items * personal_value
        
        # 計算總資產價值（現金+物品）
        p.total_value = p.current_cash + p.item_value
        
        # 記錄最終現金
        p.final_cash = p.current_cash
        
        # 計算利潤：總資產減去初始資金
        profit = p.total_value - p.initial_capital
        
        # 設置本輪實際收益為利潤
        p.payoff = profit

class Introduction(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player):
        return dict(
            num_rounds=C.NUM_ROUNDS,
            item_name=C.ITEM_NAME,
            initial_capital=C.INITIAL_CAPITAL,
        )

class ReadyWaitPage(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = initialize_roles

class TradingMarket(Page):
    form_model = 'player'
    form_fields = ['buy_quantity', 'buy_price', 'sell_quantity', 'sell_price']
    timeout_seconds = C.TRADING_TIME

    @staticmethod
    def vars_for_template(player):
        # 安全訪問個人碳權價值，如果為None則使用市場價格作為預設值
        personal_value = player.field_maybe_none('personal_item_value') or player.subsession.item_market_price
        total_item_value = player.current_items * personal_value
        
        return dict(
            cash=int(player.current_cash),
            items=player.current_items,
            timeout_seconds=TradingMarket.timeout_seconds,
            player_id=player.id_in_group,
            item_name=C.ITEM_NAME,
            market_price=int(player.subsession.item_market_price),
            personal_item_value=int(personal_value),  # 個人碳權價值
            total_item_value=int(total_item_value),  # 總碳權價值
            start_time=player.subsession.start_time,
        )

    @staticmethod
    def live_method(player, data):
        # 當頁面首次載入時，返回所有玩家的市場狀態以確保信息同步
        if data is None:
            return {p.id_in_group: TradingMarket.market_state(p) for p in player.group.get_players()}
            
        group = player.group
        
        # 添加更強健的錯誤處理和日誌記錄
        try:
            buy = json.loads(group.buy_orders)
            sell = json.loads(group.sell_orders)
            print(f"成功載入訂單數據: 買單{len(buy)}筆, 賣單{len(sell)}筆")
        except json.JSONDecodeError as e:
            print(f"JSON 解析錯誤: {e}, 重置訂單列表")
            buy = []
            sell = []
            group.buy_orders = json.dumps(buy)
            group.sell_orders = json.dumps(sell)
        except Exception as e:
            print(f"載入訂單時發生未預期錯誤: {e}")
            buy = []
            sell = []
            group.buy_orders = json.dumps(buy)
            group.sell_orders = json.dumps(sell)

        # 處理新買單
        if data.get('type') == 'place_order' and data.get('direction') == 'buy':
            pr = int(data.get('price', 0))
            qt = int(data.get('quantity', 0))
            
            if pr > 0 and qt > 0:
                print(f"玩家 {player.id_in_group} 提交買單: 價格={pr}, 數量={qt}")
                
                # 自動取消之前的買單
                cancel_player_orders(group, player.id_in_group, 'buy')
                
                # 檢查是否有匹配的賣單
                matching_sells = [(i, s) for i, s in enumerate(sell) 
                                if int(s[0]) != player.id_in_group and float(s[1]) <= pr and int(s[2]) >= qt]
                
                if matching_sells:
                    # 找到最低價格的匹配賣單
                    best_idx, best_sell = min(matching_sells, key=lambda x: float(x[1][1]))
                    seller_id, sell_price, sell_qty = int(best_sell[0]), float(best_sell[1]), int(best_sell[2])
                    
                    if qt <= sell_qty:
                        try:
                            seller = group.get_player_by_id(seller_id)
                            actual_price = sell_price
                            player.current_cash -= actual_price * qt
                            seller.current_cash += actual_price * qt
                            player.current_items += qt
                            seller.current_items -= qt
                            
                            # 更新統計
                            player.total_bought += qt
                            player.total_spent += actual_price * qt
                            seller.total_sold += qt
                            seller.total_earned += actual_price * qt
                            
                            print(f"成功撮合買單: 玩家{player.id_in_group}向玩家{seller_id}以價格{actual_price}買入{qt}個{C.ITEM_NAME}")
                            
                            # 記錄交易歷史
                            record_trade(group, player.id_in_group, seller_id, actual_price, qt)
                            
                            # 自動取消買家其他買單和賣家其他賣單
                            cancel_player_orders(group, player.id_in_group, 'buy')
                            cancel_player_orders(group, seller_id, 'sell')
                            
                            # 重新加載最新的買賣單列表
                            buy = json.loads(group.buy_orders)
                            sell = json.loads(group.sell_orders)
                            
                            # 從賣單清單移除交易完成的訂單
                            sell = [o for o in sell if not (int(o[0]) == seller_id and float(o[1]) == sell_price and int(o[2]) == sell_qty)]
                            group.sell_orders = json.dumps(sell)
                            
                            # 廣播更新
                            response = {p.id_in_group: TradingMarket.market_state(p) for p in group.get_players()}
                            return response
                            
                        except Exception as e:
                            print(f"交易執行失敗: {e}")
                            # 確保在異常情況下也返回適當的回應
                            return {player.id_in_group: {
                                'type': 'error', 
                                'message': '交易處理時發生錯誤，請重試',
                                **TradingMarket.market_state(player)
                            }}
                
                # 如果沒有匹配或執行失敗，添加新買單
                try:
                    buy.append([player.id_in_group, pr, qt])
                    group.buy_orders = json.dumps(buy)
                    print(f"成功添加買單: 玩家{player.id_in_group}, 價格{pr}, 數量{qt}")
                except Exception as e:
                    print(f"添加買單失敗: {e}")
                    return {player.id_in_group: {
                        'type': 'error', 
                        'message': '提交買單失敗，請重試',
                        **TradingMarket.market_state(player)
                    }}
                
                # 廣播更新
                try:
                    response = {p.id_in_group: TradingMarket.market_state(p) for p in group.get_players()}
                    return response
                except Exception as e:
                    print(f"廣播更新失敗: {e}")
                    return {player.id_in_group: {
                        'type': 'error', 
                        'message': '更新市場狀態失敗',
                        **TradingMarket.market_state(player)
                    }}

        # 處理新賣單
        elif data.get('type') == 'place_order' and data.get('direction') == 'sell':
            pr = int(data.get('price', 0))
            qt = int(data.get('quantity', 0))
            
            if pr > 0 and qt > 0:
                # 檢查單次賣單不超過持有量（允許同時掛多個賣單）
                if qt > player.current_items:
                    print(f"玩家 {player.id_in_group} 單次賣單數量超過持有量，掛單數量={qt}，持有{C.ITEM_NAME}={player.current_items}")
                    return {player.id_in_group: {
                        'type': 'fail',
                        'message': f'單次賣單數量不能超過持有的{C.ITEM_NAME}！您要賣出 {qt} 個{C.ITEM_NAME}，但您只有 {player.current_items} 個{C.ITEM_NAME}'
                    }}
                
                # 條件檢查通過，繼續處理賣單
                print(f"玩家 {player.id_in_group} 提交賣單: 價格={pr}, 數量={qt}")
                
                # 自動取消之前的賣單
                cancel_player_orders(group, player.id_in_group, 'sell')
                
                # 檢查是否有匹配的買單
                matching_buys = [(i, b) for i, b in enumerate(buy) 
                               if int(b[0]) != player.id_in_group and float(b[1]) >= pr and int(b[2]) >= qt]
                
                if matching_buys:
                    # 找到最高價格的匹配買單
                    best_idx, best_buy = max(matching_buys, key=lambda x: float(x[1][1]))
                    buyer_id, buy_price, buy_qty = int(best_buy[0]), float(best_buy[1]), int(best_buy[2])
                    
                    if qt <= buy_qty:
                        try:
                            buyer = group.get_player_by_id(buyer_id)
                            actual_price = buy_price
                            buyer.current_cash -= actual_price * qt
                            player.current_cash += actual_price * qt
                            buyer.current_items += qt
                            player.current_items -= qt
                            
                            # 更新統計
                            buyer.total_bought += qt
                            buyer.total_spent += actual_price * qt
                            player.total_sold += qt
                            player.total_earned += actual_price * qt
                            
                            print(f"成功撮合賣單: 玩家{player.id_in_group}向玩家{buyer_id}以價格{actual_price}賣出{qt}個{C.ITEM_NAME}")
                            
                            # 記錄交易歷史
                            record_trade(group, buyer_id, player.id_in_group, actual_price, qt)
                            
                            # 自動取消買家其他買單和賣家其他賣單
                            cancel_player_orders(group, buyer_id, 'buy')
                            cancel_player_orders(group, player.id_in_group, 'sell')
                            
                            # 重新加載最新的買賣單列表
                            buy = json.loads(group.buy_orders)
                            sell = json.loads(group.sell_orders)
                            
                            # 從買單清單移除交易完成的訂單
                            buy = [o for o in buy if not (int(o[0]) == buyer_id and float(o[1]) == buy_price and int(o[2]) == buy_qty)]
                            group.buy_orders = json.dumps(buy)
                            
                            # 廣播更新
                            response = {p.id_in_group: TradingMarket.market_state(p) for p in group.get_players()}
                            return response
                            
                        except Exception as e:
                            print(f"交易執行失敗: {e}")
                            # 確保在異常情況下也返回適當的回應
                            return {player.id_in_group: {
                                'type': 'error', 
                                'message': '交易處理時發生錯誤，請重試',
                                **TradingMarket.market_state(player)
                            }}
                
                # 如果沒有匹配或執行失敗，添加新賣單
                try:
                    sell.append([player.id_in_group, pr, qt])
                    group.sell_orders = json.dumps(sell)
                    print(f"成功添加賣單: 玩家{player.id_in_group}, 價格{pr}, 數量{qt}")
                except Exception as e:
                    print(f"添加賣單失敗: {e}")
                    return {player.id_in_group: {
                        'type': 'error', 
                        'message': '提交賣單失敗，請重試',
                        **TradingMarket.market_state(player)
                    }}
                
                # 廣播更新
                try:
                    response = {p.id_in_group: TradingMarket.market_state(p) for p in group.get_players()}
                    return response
                except Exception as e:
                    print(f"廣播更新失敗: {e}")
                    return {player.id_in_group: {
                        'type': 'error', 
                        'message': '更新市場狀態失敗',
                        **TradingMarket.market_state(player)
                    }}

        elif data.get('type') == 'accept_offer':
            ot = data.get('offer_type')  # 'buy' 或 'sell'
            # 修復參數名稱不一致的問題
            tid = int(data.get('target_id') or data.get('player_id'))
            pr = float(data.get('price'))
            qt = int(data.get('quantity'))
            
            print(f"玩家 {player.id_in_group} 接受{ot}單: 對象玩家={tid}, 價格={pr}, 數量={qt}")
            
            if ot == 'sell' and tid != player.id_in_group:
                # 移除現金檢查，允許負債購買
                # if player.current_cash >= pr * qt:
                try:
                    seller = group.get_player_by_id(tid)
                    player.current_cash -= pr * qt  # 允許現金變成負數
                    seller.current_cash += pr * qt
                    player.current_items += qt
                    seller.current_items -= qt
                    
                    # 更新統計
                    player.total_bought += qt
                    player.total_spent += pr * qt
                    seller.total_sold += qt
                    seller.total_earned += pr * qt
                    
                    print(f"接受賣單成功: 玩家{player.id_in_group}向玩家{tid}以價格{pr}買入{qt}個{C.ITEM_NAME}")
                    
                    # 記錄交易歷史
                    record_trade(group, player.id_in_group, tid, pr, qt)
                    
                    # 自動取消買家其他買單和賣家其他賣單
                    cancel_player_orders(group, player.id_in_group, 'buy')
                    cancel_player_orders(group, tid, 'sell')
                    
                    # 重新加載最新的買賣單列表
                    buy = json.loads(group.buy_orders)
                    sell = json.loads(group.sell_orders)
                    
                    sell = [o for o in sell if not (int(o[0]) == tid and float(o[1]) == pr and int(o[2]) == qt)]
                    group.sell_orders = json.dumps(sell)
                    
                    market_states = {}
                    for p in group.get_players():
                        state = TradingMarket.market_state(p)
                        if p.id_in_group == player.id_in_group:
                            state['notification'] = {
                                'type': 'success',
                                'message': f'交易成功：您以價格 {pr} 買入了 {qt} 個{C.ITEM_NAME}，總成本為 {pr * qt}。您的其他所有買單已自動取消。'
                            }
                        elif p.id_in_group == tid:
                            state['notification'] = {
                                'type': 'success',
                                'message': f'交易成功：您以價格 {pr} 賣出了 {qt} 個{C.ITEM_NAME}，總收入為 {pr * qt}。您的其他所有賣單已自動取消。'
                            }
                        market_states[p.id_in_group] = state
                    
                    return market_states
                except Exception as e:
                    print(f"接受賣單異常: {e}")
                    return {player.id_in_group: {'type': 'fail', 'message': '交易失敗：找不到賣家'}}
                    
            elif ot == 'buy' and tid != player.id_in_group:
                if player.current_items >= qt:
                    try:
                        buyer = group.get_player_by_id(tid)
                        player.current_cash += pr * qt
                        buyer.current_cash -= pr * qt
                        player.current_items -= qt
                        buyer.current_items += qt
                        
                        # 更新統計
                        buyer.total_bought += qt
                        buyer.total_spent += pr * qt
                        player.total_sold += qt
                        player.total_earned += pr * qt
                        
                        print(f"接受買單成功: 玩家{player.id_in_group}向玩家{tid}以價格{pr}賣出{qt}個{C.ITEM_NAME}")
                        
                        # 記錄交易歷史
                        record_trade(group, tid, player.id_in_group, pr, qt)
                        
                        # 自動取消買家其他買單和賣家其他賣單
                        cancel_player_orders(group, tid, 'buy')
                        cancel_player_orders(group, player.id_in_group, 'sell')
                        
                        # 重新加載最新的買賣單列表
                        buy = json.loads(group.buy_orders)
                        sell = json.loads(group.sell_orders)
                        
                        buy = [o for o in buy if not (int(o[0]) == tid and float(o[1]) == pr and int(o[2]) == qt)]
                        group.buy_orders = json.dumps(buy)
                        
                        market_states = {}
                        for p in group.get_players():
                            state = TradingMarket.market_state(p)
                            if p.id_in_group == player.id_in_group:
                                state['notification'] = {
                                    'type': 'success',
                                    'message': f'交易成功：您以價格 {pr} 賣出了 {qt} 個{C.ITEM_NAME}，總收入為 {pr * qt}。您的其他所有賣單已自動取消。'
                                }
                            elif p.id_in_group == tid:
                                state['notification'] = {
                                    'type': 'success',
                                    'message': f'交易成功：您以價格 {pr} 買入了 {qt} 個{C.ITEM_NAME}，總成本為 {pr * qt}。您的其他所有買單已自動取消。'
                                }
                            market_states[p.id_in_group] = state
                        
                        return market_states
                    except Exception as e:
                        print(f"接受買單異常: {e}")
                        return {player.id_in_group: {'type': 'fail', 'message': '交易失敗：找不到買家'}}
                else:
                    print(f"玩家 {player.id_in_group} 接受買單物品不足")
                    return {player.id_in_group: {'type': 'fail', 'message': f'{C.ITEM_NAME}不足'}}
            else:
                print(f"玩家 {player.id_in_group} 嘗試與自己交易")
                return {player.id_in_group: {'type': 'fail', 'message': '不能與自己交易'}}
            
            response = {p.id_in_group: TradingMarket.market_state(p) for p in group.get_players()}
            return response

        elif data.get('type') == 'cancel_offer':
            try:
                d = data.get('direction')
                pr = float(data.get('price', 0))
                qt = int(data.get('quantity', 0))
                
                print(f"玩家 {player.id_in_group} 取消{d}單: 價格={pr}, 數量={qt}")
                
                if d == 'buy':
                    buy = [o for o in buy if not (int(o[0]) == player.id_in_group and float(o[1]) == pr and int(o[2]) == qt)]
                    group.buy_orders = json.dumps(buy)
                    print(f"成功取消買單: 玩家{player.id_in_group}, 價格{pr}, 數量{qt}")
                else:
                    sell = [o for o in sell if not (int(o[0]) == player.id_in_group and float(o[1]) == pr and int(o[2]) == qt)]
                    group.sell_orders = json.dumps(sell)
                    print(f"成功取消賣單: 玩家{player.id_in_group}, 價格{pr}, 數量{qt}")
                    
                response = {p.id_in_group: TradingMarket.market_state(p) for p in group.get_players()}
                return response
            except Exception as e:
                print(f"取消訂單失敗: {e}")
                return {player.id_in_group: {
                    'type': 'error', 
                    'message': '取消訂單失敗，請重試',
                    **TradingMarket.market_state(player)
                }}
        
        elif data.get('type') == 'ping':
            try:
                response = {p.id_in_group: TradingMarket.market_state(p) for p in group.get_players()}
                return response
            except Exception as e:
                print(f"ping 處理失敗: {e}")
                return {player.id_in_group: {
                    'type': 'error', 
                    'message': '連接異常，正在重試...',
                    'cash': int(player.current_cash or 0),
                    'items': int(player.current_items or 0),
                    'buy_offers': [],
                    'sell_offers': [],
                    'my_buy_offers': [],
                    'my_sell_offers': [],
                    'trade_history': [],
                    'price_history': []
                }}
            
        # 預設回應處理
        try:
            response = {p.id_in_group: TradingMarket.market_state(p) for p in group.get_players()}
            return response
        except Exception as e:
            print(f"預設回應處理失敗: {e}")
            return {player.id_in_group: {
                'type': 'error', 
                'message': '系統異常，請重新整理頁面',
                'cash': int(player.current_cash or 0),
                'items': int(player.current_items or 0),
                'buy_offers': [],
                'sell_offers': [],
                'my_buy_offers': [],
                'my_sell_offers': [],
                'trade_history': [],
                'price_history': []
            }}

    @staticmethod
    def market_state(player):
        try:
            buy = json.loads(player.group.buy_orders)
            sell = json.loads(player.group.sell_orders)
        except Exception as e:
            print(f"market_state: 載入訂單失敗 {e}")
            buy = []
            sell = []
            # 重置損壞的數據
            try:
                player.group.buy_orders = json.dumps(buy)
                player.group.sell_orders = json.dumps(sell)
            except Exception as reset_error:
                print(f"market_state: 重置訂單失敗 {reset_error}")
            
        try:
            buy_sorted = sorted(buy, key=lambda x: (-float(x[1]), int(x[0])))
            sell_sorted = sorted(sell, key=lambda x: (float(x[1]), int(x[0])))
        except Exception as e:
            buy_sorted = []
            sell_sorted = []
        
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
        
        # 提取交易歷史
        try:
            trade_history = json.loads(player.group.trade_history)
            # 顯示全體玩家的交易記錄
            my_trades = trade_history  # 修改：顯示所有交易而不是個人交易
        except:
            my_trades = []
        
        # 提取價格歷史
        try:
            price_history = json.loads(player.subsession.price_history)
        except:
            price_history = []
        
        result = {
            'type': 'update',
            'cash': int(player.current_cash),
            'items': int(player.current_items),
            'my_buy_offers': my_buy_offers,
            'my_sell_offers': my_sell_offers,
            'buy_offers': public_buy_offers,
            'sell_offers': public_sell_offers,
            'trade_history': my_trades,
            'price_history': price_history,
            'item_name': C.ITEM_NAME,
            'market_price': int(player.subsession.item_market_price),
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
            player.current_items = max(player.current_items, 0)

    @staticmethod
    def js_vars(player):
        return {
            'start_time': player.group.subsession.start_time,
            'player_id': player.id_in_group,
            'timeout_seconds': C.TRADING_TIME
        }

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs

class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        # 計算全體玩家的物品總量
        group_items_total = 0
        for p in player.group.get_players():
            group_items_total += p.current_items
        
        # 計算本輪利潤
        current_profit = player.total_value - player.initial_capital
        
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
            
            # 安全訪問個人碳權價值
            selected_personal_value = selected_round_player.field_maybe_none('personal_item_value') or selected_round_player.subsession.item_market_price
            
            # 計算被選中回合的資產和利潤
            selected_item_value = selected_round_player.current_items * selected_personal_value
            selected_total_value = selected_round_player.current_cash + selected_item_value
            selected_profit = selected_total_value - selected_round_player.initial_capital
            
            # 確保所有值都是基本數據類型
            selected_round_int = int(selected_round)
            initial_capital_float = float(selected_round_player.initial_capital)
            final_cash_float = float(selected_round_player.current_cash)
            items_int = int(selected_round_player.current_items)
            item_value_float = float(selected_item_value)
            total_value_float = float(selected_total_value)
            profit_float = float(selected_profit)
            personal_value_float = float(selected_personal_value)  # 使用個人價值
            
            # 構建字典，確保沒有嵌套
            final_payoff_info = {}
            final_payoff_info['selected_round'] = selected_round_int
            final_payoff_info['initial_capital'] = initial_capital_float
            final_payoff_info['final_cash'] = final_cash_float
            final_payoff_info['item_count'] = items_int  # 改名避免衝突
            final_payoff_info['item_value'] = item_value_float
            final_payoff_info['total_value'] = total_value_float
            final_payoff_info['profit'] = profit_float
            final_payoff_info['personal_item_value'] = personal_value_float  # 修正：使用更明確的名稱
            final_payoff_info['market_price'] = personal_value_float  # 保持向後兼容
            final_payoff_info['profit_formatted'] = f"{int(round(profit_float))}"
            final_payoff_info['total_value_formatted'] = f"{int(round(total_value_float))}"
            final_payoff_info['item_value_formatted'] = f"{int(round(item_value_float))}"
            final_payoff_info['initial_capital_formatted'] = f"{int(round(initial_capital_float))}"
            final_payoff_info['final_cash_formatted'] = f"{int(round(final_cash_float))}"
            final_payoff_info['personal_item_value_formatted'] = f"{int(round(personal_value_float))}"  # 新增：格式化的個人價值
            
            # 調試輸出
            print(f"Debug - final_payoff_info type: {type(final_payoff_info)}")
            print(f"Debug - item_count value: {final_payoff_info['item_count']} (type: {type(final_payoff_info['item_count'])})")
            print(f"Debug - market_price value: {final_payoff_info['market_price']} (type: {type(final_payoff_info['market_price'])})")
        
        return dict(
            market_price=player.subsession.item_market_price,
            personal_item_value=player.field_maybe_none('personal_item_value') or player.subsession.item_market_price,  # 安全訪問個人碳權價值
            item_value=player.item_value,
            current_items=player.current_items,
            group_items_total=group_items_total,
            item_name=C.ITEM_NAME,
            remaining_rounds=C.NUM_ROUNDS - player.round_number,
            is_last_round=(player.round_number == C.NUM_ROUNDS),
            total_rounds=C.NUM_ROUNDS,
            progress_percentage=round((player.round_number / C.NUM_ROUNDS) * 100),
            # 新增：利潤相關資訊
            initial_capital=player.initial_capital,
            total_value=player.total_value,
            current_profit=current_profit,
            current_profit_formatted=f"{int(round(current_profit))}",
            total_value_formatted=f"{int(round(player.total_value))}",
            initial_capital_formatted=f"{int(round(player.initial_capital))}",
            final_payoff_info=final_payoff_info,  # 新增：最終報酬資訊
        )

page_sequence = [Introduction, ReadyWaitPage, TradingMarket, ResultsWaitPage, Results]