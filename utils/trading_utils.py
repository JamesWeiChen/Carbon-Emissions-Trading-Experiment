"""
交易工具庫：包含交易市場相關的共用函數
"""
from otree.api import *
import json
import time
from typing import Dict, List, Any, Tuple, Optional

class TradingError(Exception):
    """交易錯誤的基礎類別"""
    pass

class InsufficientResourcesError(TradingError):
    """資源不足錯誤"""
    pass

class InvalidOrderError(TradingError):
    """無效訂單錯誤"""
    pass

class DuplicateOrderError(TradingError):
    """重複訂單錯誤"""
    pass

def update_price_history(
    subsession: BaseSubsession, 
    trade_price: float, 
    event: str = 'trade'
) -> List[Dict[str, Any]]:
    """
    更新價格歷史記錄
    
    Args:
        subsession: 子會話物件
        trade_price: 交易價格
        event: 事件類型
        
    Returns:
        更新後的價格歷史列表
    """
    try:
        price_history = json.loads(subsession.price_history)
    except json.JSONDecodeError:
        price_history = []
    
    # 計算時間戳
    timestamp = _calculate_timestamp(subsession)
    
    # 獲取市場價格
    market_price = _get_market_price(subsession)
    
    # 創建價格記錄
    price_record = {
        'timestamp': timestamp,
        'price': float(trade_price),
        'event': event,
        'market_price': float(market_price),
        'round': subsession.round_number
    }
    
    price_history.append(price_record)
    subsession.price_history = json.dumps(price_history)
    
    return price_history

def _calculate_timestamp(subsession: BaseSubsession) -> str:
    """計算時間戳（格式：MM:SS）"""
    current_time = int(time.time())
    if hasattr(subsession, 'start_time') and subsession.start_time:
        elapsed_seconds = current_time - subsession.start_time
    else:
        elapsed_seconds = 0
    
    minutes = elapsed_seconds // 60
    seconds = elapsed_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def _get_market_price(subsession: BaseSubsession) -> Currency:
    """獲取市場價格"""
    return getattr(subsession, 'market_price', None) or getattr(subsession, 'item_market_price', 0)

def record_trade(
    group: BaseGroup, 
    buyer_id: int, 
    seller_id: int, 
    price: float, 
    quantity: int
) -> List[Dict[str, Any]]:
    """
    記錄交易
    
    Args:
        group: 組別物件
        buyer_id: 買方ID
        seller_id: 賣方ID
        price: 交易價格
        quantity: 交易數量
        
    Returns:
        更新後的交易歷史列表
    """
    try:
        trade_history = json.loads(group.trade_history)
    except json.JSONDecodeError:
        trade_history = []
    
    # 創建交易記錄
    trade_record = {
        'timestamp': _calculate_timestamp(group.subsession),
        'buyer_id': int(buyer_id),
        'seller_id': int(seller_id),
        'price': float(price),
        'quantity': int(quantity)
    }
    
    trade_history.append(trade_record)
    group.trade_history = json.dumps(trade_history)
    
    print(f"記錄交易: 買方{buyer_id} <- 賣方{seller_id}, 價格{price}, 數量{quantity}")
    return trade_history

def cancel_player_orders(group: BaseGroup, player_id: int, order_type: str) -> None:
    """
    取消玩家的所有指定類型訂單
    
    Args:
        group: 組別物件
        player_id: 玩家ID
        order_type: 訂單類型 ('buy' 或 'sell')
    """
    if order_type not in ['buy', 'sell']:
        print(f"無效的訂單類型: {order_type}")
        return
    
    try:
        # 獲取訂單列表
        orders_field = f"{order_type}_orders"
        orders = json.loads(getattr(group, orders_field))
        
        # 過濾掉該玩家的訂單
        old_count = len([o for o in orders if int(o[0]) == player_id])
        orders = [o for o in orders if int(o[0]) != player_id]
        
        # 更新訂單列表
        setattr(group, orders_field, json.dumps(orders))
        
        if old_count > 0:
            print(f"已自動取消玩家 {player_id} 的 {old_count} 筆{order_type}單")
    except json.JSONDecodeError:
        print(f"解析{order_type}單列表時發生錯誤")
    except Exception as e:
        print(f"取消訂單時發生錯誤: {e}")


def parse_orders(group: BaseGroup) -> Tuple[List[List], List[List]]:
    """
    解析買賣訂單
    
    Args:
        group: 組別物件
        
    Returns:
        (買單列表, 賣單列表)
    """
    try:
        buy_orders = json.loads(group.buy_orders)
    except (json.JSONDecodeError, AttributeError):
        buy_orders = []
        group.buy_orders = json.dumps(buy_orders)
    
    try:
        sell_orders = json.loads(group.sell_orders)
    except (json.JSONDecodeError, AttributeError):
        sell_orders = []
        group.sell_orders = json.dumps(sell_orders)
    
    return buy_orders, sell_orders

def save_orders(group: BaseGroup, buy_orders: List[List], sell_orders: List[List]) -> None:
    """儲存買賣訂單"""
    group.buy_orders = json.dumps(buy_orders)
    group.sell_orders = json.dumps(sell_orders)

def check_duplicate_order(
    orders: List[List],
    price: int,
    quantity: int
) -> bool:
    """
    檢查是否存在重複訂單（任何玩家的相同價格和數量）
    
    Args:
        orders: 訂單列表
        price: 價格
        quantity: 數量
        
    Returns:
        True 如果存在重複訂單，False 否則
    """
    for order in orders:
        if (float(order[1]) == price and 
            int(order[2]) == quantity):
            return True
    return False

def validate_order(
    player: BasePlayer, 
    direction: str, 
    price: int, 
    quantity: int,
    item_name: str = "物品"
) -> None:
    """
    驗證訂單有效性
    
    Args:
        player: 玩家物件
        direction: 'buy' 或 'sell'
        price: 價格
        quantity: 數量
        item_name: 物品名稱
        
    Raises:
        InvalidOrderError: 訂單無效
        InsufficientResourcesError: 資源不足
    """
    if price <= 0 or quantity <= 0:
        raise InvalidOrderError("價格和數量必須大於0")
    
    if direction == 'sell':
        # 檢查賣單數量不超過持有量
        if hasattr(player, 'current_items') and quantity > player.current_items:
            raise InsufficientResourcesError(
                f'單次賣單數量不能超過持有的{item_name}！'
                f'您要賣出 {quantity} 個{item_name}，但您只有 {player.current_items} 個{item_name}'
            )
        elif hasattr(player, 'current_permits') and quantity > player.current_permits:
            raise InsufficientResourcesError(
                f'單次賣單數量不能超過持有的{item_name}！'
                f'您要賣出 {quantity} 個{item_name}，但您只有 {player.current_permits} 個{item_name}'
            )

def find_matching_orders(
    orders: List[List], 
    player_id: int, 
    price: float, 
    quantity: int,
    is_buy_order: bool
) -> List[Tuple[int, List]]:
    """
    尋找匹配的訂單
    
    Args:
        orders: 訂單列表
        player_id: 當前玩家ID
        price: 價格
        quantity: 數量
        is_buy_order: 是否為買單
        
    Returns:
        匹配的訂單列表 [(索引, 訂單)]
    """
    matching_orders = []
    
    for i, order in enumerate(orders):
        order_player_id = int(order[0])
        order_price = float(order[1])
        order_quantity = int(order[2])
        
        # 排除自己的訂單
        if order_player_id == player_id:
            continue
        
        # 檢查價格匹配
        if is_buy_order:
            # 買單：尋找價格不高於出價的賣單
            if order_price <= price and order_quantity == quantity:
                matching_orders.append((i, order))
        else:
            # 賣單：尋找價格不低於要價的買單
            if order_price >= price and order_quantity == quantity:
                matching_orders.append((i, order))
    
    return matching_orders

def execute_trade(
    group: BaseGroup,
    buyer: BasePlayer,
    seller: BasePlayer,
    price: float,
    quantity: int,
    item_field: str = 'current_items'
) -> None:
    """
    執行交易
    
    Args:
        group: 組別物件
        buyer: 買方玩家
        seller: 賣方玩家
        price: 交易價格
        quantity: 交易數量
        item_field: 物品欄位名稱
    """
    # 確保價格為整數
    price = int(price)
    
    # 更新現金
    buyer.current_cash -= price * quantity
    seller.current_cash += price * quantity
    
    # 更新物品數量
    current_buyer_items = getattr(buyer, item_field)
    current_seller_items = getattr(seller, item_field)
    setattr(buyer, item_field, current_buyer_items + quantity)
    setattr(seller, item_field, current_seller_items - quantity)
    
    # 更新統計數據
    if hasattr(buyer, 'total_bought'):
        buyer.total_bought += quantity
        buyer.total_spent += price * quantity
    if hasattr(seller, 'total_sold'):
        seller.total_sold += quantity
        seller.total_earned += price * quantity
    
    # 記錄成交訂單到 subsession
    try:
        executed_trades = json.loads(group.subsession.executed_trades)
    except (json.JSONDecodeError, AttributeError):
        executed_trades = []
    
    # 計算時間戳（格式：MM:SS）
    current_time = int(time.time())
    if hasattr(group.subsession, 'start_time') and group.subsession.start_time:
        elapsed_seconds = current_time - group.subsession.start_time
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        timestamp = f"{minutes:02d}:{seconds:02d}"
    else:
        timestamp = "00:00"
    
    # 創建成交記錄
    executed_trade = {
        'timestamp': timestamp,  # MM:SS 格式
        'buyer_id': buyer.id_in_group,
        'seller_id': seller.id_in_group,
        'price': price,  # 已經轉換為整數
        'quantity': int(quantity)
    }
    
    executed_trades.append(executed_trade)
    group.subsession.executed_trades = json.dumps(executed_trades)
    
    print(f"成功交易: 買方{buyer.id_in_group} <- 賣方{seller.id_in_group}, "
          f"價格{price}, 數量{quantity}")

def process_new_order(
    player: BasePlayer,
    group: BaseGroup,
    direction: str,
    price: int,
    quantity: int,
    item_name: str = "物品",
    item_field: str = 'current_items'
) -> Dict[int, Dict[str, Any]]:
    """
    處理新訂單
    
    Args:
        player: 玩家物件
        group: 組別物件
        direction: 'buy' 或 'sell'
        price: 價格
        quantity: 數量
        item_name: 物品名稱
        item_field: 物品欄位名稱
        
    Returns:
        需要廣播給所有玩家的狀態更新
    """
    # 驗證訂單
    try:
        validate_order(player, direction, price, quantity, item_name)
    except TradingError as e:
        return {
            'type': 'fail',
            'notifications': {
                player.id_in_group: str(e)
            }
        }
    
    # 解析現有訂單
    buy_orders, sell_orders = parse_orders(group)
    
    # 檢查重複訂單
    if direction == 'buy':
        if check_duplicate_order(buy_orders, price, quantity):
            return {
                'type': 'fail',
                'notifications': {
                    player.id_in_group: f'市場上已有價格 {price} 且數量 {quantity} 的買單！'
                }
            }
    else:  # sell
        if check_duplicate_order(sell_orders, price, quantity):
            return {
                'type': 'fail',
                'notifications': {
                    player.id_in_group: f'市場上已有價格 {price} 且數量 {quantity} 的賣單！'
                }
            }
    
    # 移除：不再自動取消之前的同方向訂單，允許掛多個買單/賣單
    # cancel_player_orders(group, player.id_in_group, direction)
    
    # 尋找匹配的訂單
    if direction == 'buy':
        matching_orders = find_matching_orders(
            sell_orders, player.id_in_group, price, quantity, True
        )
        
        if matching_orders:
            # 找到最低價格的匹配賣單
            best_idx, best_order = min(matching_orders, key=lambda x: float(x[1][1]))
            seller_id = int(best_order[0])
            
            try:
                seller = group.get_player_by_id(seller_id)
                trade_price = int(float(best_order[1]))  # 確保交易價格為整數
                execute_trade(group, player, seller, trade_price, quantity, item_field)
                
                # 保留：交易成功時取消雙方其他訂單
                cancel_player_orders(group, player.id_in_group, 'buy')
                cancel_player_orders(group, seller_id, 'sell')
                
                # 從賣單列表移除已成交的訂單
                buy_orders, sell_orders = parse_orders(group)
                sell_orders = [o for o in sell_orders if not (
                    int(o[0]) == seller_id and 
                    float(o[1]) == float(best_order[1]) and 
                    int(o[2]) == int(best_order[2])
                )]
                save_orders(group, buy_orders, sell_orders)
                
                # 修改：添加自動交易成功通知，價格顯示為整數
                return {
                    'type': 'trade_executed', 
                    'update_all': True,
                    'notifications': {
                        player.id_in_group: f'交易成功：您以價格 {trade_price} 買入了 {quantity} 個{item_name}',
                        seller_id: f'交易成功：您以價格 {trade_price} 賣出了 {quantity} 個{item_name}'
                    }
                }
                
            except Exception as e:
                print(f"交易執行失敗: {e}")
                # 繼續添加訂單
        
        # 沒有匹配或執行失敗，添加新買單
        buy_orders.append([player.id_in_group, price, quantity])
        save_orders(group, buy_orders, sell_orders)
        
    else:  # sell
        matching_orders = find_matching_orders(
            buy_orders, player.id_in_group, price, quantity, False
        )
        
        if matching_orders:
            # 找到最高價格的匹配買單
            best_idx, best_order = max(matching_orders, key=lambda x: float(x[1][1]))
            buyer_id = int(best_order[0])
            
            try:
                buyer = group.get_player_by_id(buyer_id)
                trade_price = int(float(best_order[1]))  # 確保交易價格為整數
                execute_trade(group, buyer, player, trade_price, quantity, item_field)
                
                # 保留：交易成功時取消雙方其他訂單
                cancel_player_orders(group, buyer_id, 'buy')
                cancel_player_orders(group, player.id_in_group, 'sell')
                
                # 從買單列表移除已成交的訂單
                buy_orders, sell_orders = parse_orders(group)
                buy_orders = [o for o in buy_orders if not (
                    int(o[0]) == buyer_id and 
                    float(o[1]) == float(best_order[1]) and 
                    int(o[2]) == int(best_order[2])
                )]
                save_orders(group, buy_orders, sell_orders)
                
                # 修改：添加自動交易成功通知，價格顯示為整數
                return {
                    'type': 'trade_executed', 
                    'update_all': True,
                    'notifications': {
                        player.id_in_group: f'交易成功：您以價格 {trade_price} 賣出了 {quantity} 個{item_name}',
                        buyer_id: f'交易成功：您以價格 {trade_price} 買入了 {quantity} 個{item_name}'
                    }
                }
                
            except Exception as e:
                print(f"交易執行失敗: {e}")
                # 繼續添加訂單
        
        # 沒有匹配或執行失敗，添加新賣單
        sell_orders.append([player.id_in_group, price, quantity])
        save_orders(group, buy_orders, sell_orders)
    
    print(f"成功添加{direction}單: 玩家{player.id_in_group}, 價格{price}, 數量{quantity}")
    return {'type': 'order_added', 'update_all': True}

def process_accept_offer(
    player: BasePlayer,
    group: BaseGroup,
    offer_type: str,
    target_id: int,
    price: float,
    quantity: int,
    item_name: str = "物品",
    item_field: str = 'current_items'
) -> Dict[int, Dict[str, Any]]:
    """
    處理接受訂單
    
    Args:
        player: 玩家物件
        group: 組別物件
        offer_type: 'buy' 或 'sell'
        target_id: 目標玩家ID
        price: 價格
        quantity: 數量
        item_name: 物品名稱
        item_field: 物品欄位名稱
        
    Returns:
        需要廣播給所有玩家的狀態更新
    """
    if target_id == player.id_in_group:
        return {
            'type': 'fail',
            'notifications': {
                player.id_in_group: '不能接受自己的訂單'
            }
        }
    
    # 確保價格為整數
    price = int(price)
    
    try:
        if offer_type == 'sell':
            # 接受賣單（玩家是買方）
            seller = group.get_player_by_id(target_id)
            execute_trade(group, player, seller, price, quantity, item_field)
            
            # 保留：交易成功時取消雙方其他訂單
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
            
            return {
                'type': 'trade_executed',
                'update_all': True,
                'notifications': {
                    player.id_in_group: f'交易成功：您以價格 {price} 買入了 {quantity} 個{item_name}',
                    target_id: f'交易成功：您以價格 {price} 賣出了 {quantity} 個{item_name}'
                }
            }
            
        else:  # offer_type == 'buy'
            # 接受買單（玩家是賣方）
            # 先驗證賣方有足夠的物品
            current_items = getattr(player, item_field)
            if current_items < quantity:
                return {
                    'type': 'fail',
                    'notifications': {
                        player.id_in_group: f'您的{item_name}不足'
                    }
                }
            
            buyer = group.get_player_by_id(target_id)
            execute_trade(group, buyer, player, price, quantity, item_field)
            
            # 保留：交易成功時取消雙方其他訂單
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
            
            return {
                'type': 'trade_executed',
                'update_all': True,
                'notifications': {
                    player.id_in_group: f'交易成功：您以價格 {price} 賣出了 {quantity} 個{item_name}',
                    target_id: f'交易成功：您以價格 {price} 買入了 {quantity} 個{item_name}'
                }
            }
            
    except Exception as e:
        print(f"接受訂單失敗: {e}")
        return {
            'type': 'fail',
            'notifications': {
                player.id_in_group: '交易失敗：找不到交易對象'
            }
        }

def calculate_locked_resources(
    player: BasePlayer, 
    buy_orders: List[List], 
    sell_orders: List[List]
) -> Tuple[float, int]:
    """
    計算已鎖定的資源
    
    Args:
        player: 玩家物件
        buy_orders: 買單列表
        sell_orders: 賣單列表
        
    Returns:
        (鎖定的現金, 鎖定的物品數量)
    """
    player_id = player.id_in_group
    
    # 買單邏輯改為無限制掛單，不再鎖定現金
    locked_cash = 0
    # locked_cash = sum(
    #     float(order[1]) * int(order[2])
    #     for order in buy_orders
    #     if int(order[0]) == player_id
    # )
    
    # 計算鎖定的物品（賣單）
    locked_items = sum(
        int(order[2])
        for order in sell_orders
        if int(order[0]) == player_id
    )
    
    return locked_cash, locked_items

def filter_top_orders_for_display(orders: List[List], max_per_quantity: int = 3) -> List[List]:
    """
    為顯示過濾訂單，每個數量級別保留最好的幾筆
    
    Args:
        orders: 訂單列表 [[player_id, price, quantity], ...]
        max_per_quantity: 每個數量級別最多保留幾筆
        
    Returns:
        過濾後的訂單列表
    """
    if not orders:
        return []
    
    # 按數量分組
    quantity_groups = {}
    for order in orders:
        quantity = int(order[2])
        if quantity not in quantity_groups:
            quantity_groups[quantity] = []
        quantity_groups[quantity].append(order)
    
    # 對每個數量組排序並取前N筆
    filtered_orders = []
    for quantity, group in quantity_groups.items():
        # 排序：買單按價格降序（高價優先），賣單按價格升序（低價優先）
        # 這裡假設是買單，如果是賣單需要調整排序方向
        sorted_group = sorted(group, key=lambda x: float(x[1]), reverse=True)
        # 取前max_per_quantity筆
        filtered_orders.extend(sorted_group[:max_per_quantity])
    
    return filtered_orders

def filter_top_buy_orders_for_display(buy_orders: List[List], max_per_quantity: int = 3) -> List[List]:
    """
    為顯示過濾買單，每個數量級別保留價格最高的幾筆
    """
    if not buy_orders:
        return []
    
    # 按數量分組
    quantity_groups = {}
    for order in buy_orders:
        quantity = int(order[2])
        if quantity not in quantity_groups:
            quantity_groups[quantity] = []
        quantity_groups[quantity].append(order)
    
    # 對每個數量組按價格降序排序並取前N筆
    filtered_orders = []
    for quantity, group in quantity_groups.items():
        # 買單：價格高的優先
        sorted_group = sorted(group, key=lambda x: float(x[1]), reverse=True)
        filtered_orders.extend(sorted_group[:max_per_quantity])
    
    # 按價格降序排序最終結果
    return sorted(filtered_orders, key=lambda x: float(x[1]), reverse=True)

def filter_top_sell_orders_for_display(sell_orders: List[List], max_per_quantity: int = 3) -> List[List]:
    """
    為顯示過濾賣單，每個數量級別保留價格最低的幾筆
    """
    if not sell_orders:
        return []
    
    # 按數量分組
    quantity_groups = {}
    for order in sell_orders:
        quantity = int(order[2])
        if quantity not in quantity_groups:
            quantity_groups[quantity] = []
        quantity_groups[quantity].append(order)
    
    # 對每個數量組按價格升序排序並取前N筆
    filtered_orders = []
    for quantity, group in quantity_groups.items():
        # 賣單：價格低的優先
        sorted_group = sorted(group, key=lambda x: float(x[1]))
        filtered_orders.extend(sorted_group[:max_per_quantity])
    
    # 按價格升序排序最終結果
    return sorted(filtered_orders, key=lambda x: float(x[1]))

def record_submitted_offer(player, direction, price, quantity):
    """記錄提交的訂單（共用）"""
    try:
        submitted_offers = json.loads(player.submitted_offers)
    except Exception:
        submitted_offers = []
    
    # 計算時間戳（格式：MM:SS）
    current_time = int(time.time())
    start_time = getattr(getattr(player, 'subsession', None), 'start_time', None)
    if start_time:
        elapsed_seconds = current_time - start_time
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        timestamp = f"{minutes:02d}:{seconds:02d}"
    else:
        timestamp = "00:00"
    
    submitted_offers.append({
        'timestamp': timestamp,
        'direction': direction,
        'price': price,
        'quantity': quantity
    })
    player.submitted_offers = json.dumps(submitted_offers)

def cancel_specific_order(group, player_id, direction, price, quantity):
    """取消特定訂單（共用）"""
    def _parse_orders(orders_str):
        try:
            return json.loads(orders_str)
        except Exception:
            return []
    buy_orders = _parse_orders(group.buy_orders)
    sell_orders = _parse_orders(group.sell_orders)
    
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
    
    group.buy_orders = json.dumps(buy_orders)
    group.sell_orders = json.dumps(sell_orders)


class CommonReadyWaitPage(WaitPage):
    wait_for_all_groups = True

    @staticmethod
    def after_all_players_arrive(subsession):
        # 只在 start_time 尚未設定時才設定
        if subsession.field_maybe_none('start_time') is None:
            subsession.start_time = int(time.time() + 2)
            print(f"所有人準備就緒，start_time 設為 {subsession.start_time}")