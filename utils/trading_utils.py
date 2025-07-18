"""
交易工具庫：包含交易市場相關的共用函數
"""
from otree.api import *
import json
import time
from typing import Dict, List, Any, Tuple, Optional
from .shared_utils import (
    update_price_history,
    record_trade,
    cancel_player_orders
)

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
    player_id: int,
    price: int,
    quantity: int
) -> bool:
    """
    檢查是否存在重複訂單
    
    Args:
        orders: 訂單列表
        player_id: 玩家ID
        price: 價格
        quantity: 數量
        
    Returns:
        True 如果存在重複訂單，False 否則
    """
    for order in orders:
        if (int(order[0]) == player_id and 
            float(order[1]) == price and 
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
            if order_price <= price and order_quantity >= quantity:
                matching_orders.append((i, order))
        else:
            # 賣單：尋找價格不低於要價的買單
            if order_price >= price and order_quantity >= quantity:
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
        'price': int(price),
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
        return {player.id_in_group: {
            'type': 'fail',
            'message': str(e)
        }}
    
    # 解析現有訂單
    buy_orders, sell_orders = parse_orders(group)
    
    # 檢查重複訂單
    if direction == 'buy':
        if check_duplicate_order(buy_orders, player.id_in_group, price, quantity):
            return {player.id_in_group: {
                'type': 'fail',
                'message': f'您已經掛了相同的買單！價格 {price}，數量 {quantity} 個{item_name}'
            }}
    else:  # sell
        if check_duplicate_order(sell_orders, player.id_in_group, price, quantity):
            return {player.id_in_group: {
                'type': 'fail',
                'message': f'您已經掛了相同的賣單！價格 {price}，數量 {quantity} 個{item_name}'
            }}
    
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
                execute_trade(group, player, seller, float(best_order[1]), quantity, item_field)
                
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
                
                # 返回更新狀態（需要調用者提供 market_state 函數）
                return {'type': 'trade_executed', 'update_all': True}
                
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
                execute_trade(group, buyer, player, float(best_order[1]), quantity, item_field)
                
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
                
                # 返回更新狀態
                return {'type': 'trade_executed', 'update_all': True}
                
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
        return {player.id_in_group: {
            'type': 'fail',
            'message': '不能接受自己的訂單'
        }}
    
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
                return {player.id_in_group: {
                    'type': 'fail',
                    'message': f'您的{item_name}不足'
                }}
            
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
        return {player.id_in_group: {
            'type': 'fail',
            'message': '交易失敗：找不到交易對象'
        }}

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
