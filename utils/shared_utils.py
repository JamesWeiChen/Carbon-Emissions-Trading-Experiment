"""
共享工具庫：包含各階段重複使用的函數和邏輯
"""
from otree.api import *
import random
import json
import time
import math
import sys
import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from configs.config import config, ConfigConstants

CommonConstants = ConfigConstants

def get_parameter_set_for_round(session: Any, round_number: int) -> Dict[str, Any]:
    """
    根據 session 與 round number，決定本回合使用哪一組參數。

    - 第一次呼叫時會在 session.vars 儲存隨機順序
    - 從 config.parameter_sets 中挑出該回合對應的參數組合

    Args:
        session: oTree session 物件
        round_number: 當前回合數（從 1 開始）

    Returns:
        Dict[str, Any]: 對應本回合的參數設定
    """
    all_sets = config.parameter_sets
    num_sets = len(all_sets)

    if 'parameter_order' not in session.vars:
        session.vars['parameter_order'] = random.sample(range(num_sets), num_sets)

    order = session.vars['parameter_order']
    if round_number < 1 or round_number > len(order):
        raise ValueError(f"Invalid round_number {round_number}: must be between 1 and {len(order)}")

    param_index = order[round_number - 1]
    return all_sets[param_index]

def initialize_player_roles(subsession: BaseSubsession, initial_capital: Currency) -> None:
    """
    初始化玩家角色分配
    
    Args:
        subsession: oTree 子會話物件
        initial_capital: 初始資金
    """
    players = subsession.get_players()
    num_players = len(players)
    print(f"初始化 {num_players} 個玩家的角色...")
    
    # 使用新的配置方式獲取主導廠商數量
    num_dominant = min(config.dominant_firm_count, num_players)
    
    # 生成角色分配列表
    roles = _generate_role_assignments(num_players, num_dominant)
    
    print(f"角色分配: {num_dominant} 個 dominant 廠商, {num_players - num_dominant} 個 non-dominant 廠商")
    print(f"角色列表: {roles}")
    print(f"測試模式: {'是' if config.test_mode else '否'}")
    
    # 為每個玩家設置屬性
    for i, player in enumerate(players):
        _assign_player_attributes(player, roles[i], initial_capital)
        _print_player_info(player)

def _generate_role_assignments(num_players: int, num_dominant: int) -> List[bool]:
    """生成角色分配列表"""
    if config.ensure_player1_dominant:
        # 測試模式：確保1號玩家為主導廠商
        roles = [True] + [False] * (num_players - 1)
        
        if num_dominant > 1:
            non_dominant_indices = list(range(1, num_players))
            additional_dominant = random.sample(
                non_dominant_indices, 
                min(num_dominant - 1, len(non_dominant_indices))
            )
            for idx in additional_dominant:
                roles[idx] = True
    else:
        roles = [True] * num_dominant + [False] * (num_players - num_dominant)
        # 隨機分配主導廠商
        if config.random_dominant_firm_each_round:
            random.shuffle(roles)
        
    return roles

def _assign_player_attributes(player: BasePlayer, is_dominant: bool, initial_capital: Currency):
    ss = player.subsession

    player.is_dominant = is_dominant
    player.marginal_cost_coefficient = ss.dominant_mc if is_dominant else ss.non_dominant_mc
    player.carbon_emission_per_unit = (
        config.dominant_emission_per_unit if is_dominant else config.non_dominant_emission_per_unit
    )
    player.max_production = (
        config.dominant_max_production if is_dominant else config.non_dominant_max_production
    )
    player.initial_capital = initial_capital
    player.current_cash = initial_capital
    player.market_price = ss.market_price
    player.disturbance_values = _calculate_disturbance_values(player)

def _generate_market_price() -> Currency:
    """生成市場價格"""
    base_prices = config.get('general.market_price_random_draw.base_prices', [25, 30, 35, 40])
    variations = config.get('general.market_price_random_draw.variations', [-2, -1, 1, 2])
    min_price = config.get('general.market_price_random_draw.min_price', 1)
    
    base_price = random.choice(base_prices)
    variation = random.choice(variations)
    return max(base_price + variation, min_price)

def _print_player_info(player: BasePlayer) -> None:
    """列印玩家資訊"""
    print(f"玩家 {player.id_in_group}: {'Dominant' if player.is_dominant else 'Non-dominant'}, "
          f"MC={player.marginal_cost_coefficient}, Emission={player.carbon_emission_per_unit}, "
          f"MaxProd={player.max_production}, Price={player.market_price}")

def calculate_production_cost(player: BasePlayer, production_quantity: int) -> float:
    """
    計算生產成本（包含隨機擾動）
    
    Args:
        player: 玩家物件
        production_quantity: 生產數量
        
    Returns:
        總生產成本
    """
    if production_quantity <= 0:
        return 0.0
    
    total_cost = 0.0

    disturbance_vector = np.array(json.loads(player.disturbance_values))
    
    a = player.marginal_cost_coefficient
    q = np.arange(1, production_quantity + 1)
    dist = disturbance_vector[:production_quantity]  # 預先計算好、已四捨五入的 vector

    total_cost = float(np.sum(a * q + dist))
    total_cost = round(total_cost, 2)
    
    return total_cost

def calculate_control_payoffs(group: BaseGroup) -> None:
    """計算控制組的收益"""
    for player in group.get_players():
        _calculate_player_payoff(player, tax_rate=0)

def calculate_carbon_tax_payoffs(group: BaseGroup) -> None:
    """計算碳稅組的收益"""
    tax_rate = group.subsession.tax_rate
    for player in group.get_players():
        _calculate_player_payoff(player, tax_rate=tax_rate)

def _calculate_player_payoff(player: BasePlayer, tax_rate: Currency = 0) -> None:
    """計算單個玩家的收益"""
    if player.production is None:
        player.production = 0
    
    # 計算成本和收入
    cost = calculate_production_cost(player, player.production)
    revenue = player.production * player.market_price
    
    # 計算碳稅（如果適用）
    if tax_rate > 0:
        emissions = player.production * player.carbon_emission_per_unit
        tax = emissions * tax_rate
        player.carbon_tax_paid = float(tax)
    else:
        tax = 0
    
    # 計算利潤
    profit = revenue - cost - tax
    
    # 更新玩家屬性
    player.revenue = revenue
    player.total_cost = float(cost)
    player.net_profit = float(profit)
    player.final_cash = player.current_cash + profit
    player.payoff = profit

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

def calculate_final_payoff_info(
    player: BasePlayer, 
    cost_calculator_func: Optional[callable] = None,
    additional_info_func: Optional[callable] = None
) -> Optional[Dict[str, Any]]:
    """
    計算最終報酬資訊
    
    Args:
        player: 玩家物件
        cost_calculator_func: 自定義成本計算函數
        additional_info_func: 額外資訊函數
        
    Returns:
        最終報酬資訊字典，如果不是最後一輪則返回 None
    """
    if player.round_number != config.num_rounds:
        return None
    
    # 選擇隨機回合
    selected_round = _get_or_set_selected_round(player)
    player.selected_round = selected_round
    selected_round_player = player.in_round(selected_round)
    
    # 計算選中回合的數據
    cost = selected_round_player.total_cost
    revenue = selected_round_player.production * selected_round_player.market_price
    profit = revenue - cost
    emissions = selected_round_player.production * selected_round_player.carbon_emission_per_unit
    
    # 計算組別總排放
    group_emissions = _calculate_group_emissions(selected_round_player)

    if additional_info_func:
        additional_info = additional_info_func(selected_round_player)
        tax = selected_round_player.carbon_tax_paid
        profit = profit - tax
    
    # 構建報酬資訊
    final_payoff_info = {
        'selected_round': selected_round,
        'production': selected_round_player.production,
        'market_price': selected_round_player.market_price,
        'revenue': revenue,
        'cost': cost,
        'profit': profit,
        'emissions': emissions,
        'group_emissions': group_emissions,
        'profit_formatted': f"{int(round(profit))}",
        'cost_formatted': f"{int(round(cost))}",
        'revenue_formatted': f"{int(round(revenue))}",
        'emissions_formatted': f"{int(round(emissions))}",
        'group_emissions_formatted': f"{int(round(group_emissions))}"
    }
    
    # 添加額外資訊
    if additional_info_func:
        final_payoff_info.update(additional_info)
    
    return final_payoff_info

def _get_or_set_selected_round(player: BasePlayer) -> int:
    if "selected_round" not in player.session.vars:
        player.session.vars["selected_round"] = random.randint(1, config.num_rounds)
    return player.session.vars["selected_round"]

def _calculate_cost_for_round(player: BasePlayer, cost_calculator_func: Optional[callable]) -> float:
    """計算指定回合的成本"""
    if cost_calculator_func:
        return cost_calculator_func(player)
    else:
        return calculate_production_cost(player, player.production)

def _calculate_group_emissions(player: BasePlayer) -> float:
    """計算組別總排放量"""
    group_emissions = 0
    for p in player.group.get_players():
        p_in_round = p.in_round(player.round_number)
        p_emissions = p_in_round.production * p_in_round.carbon_emission_per_unit
        group_emissions += p_emissions
    return group_emissions

def get_production_template_vars(
    player: BasePlayer, 
    treatment: str,
    additional_vars: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    獲取生產決策頁面的模板變數
    
    Args:
        player: 玩家物件
        treatment: 處理組別名稱
        additional_vars: 額外的模板變數
        
    Returns:
        模板變數字典
    """
    # 構建基本變數
    base_vars = {
        'max_production': player.max_production,
        'marginal_cost_coefficient': int(player.marginal_cost_coefficient),
        'carbon_emission_per_unit': player.carbon_emission_per_unit,
        'market_price': player.market_price,
        'current_cash': int(player.current_cash),
        'treatment': treatment,
        'treatment_text': config.get_treatment_name(treatment),
        'unit_income': int(player.market_price),
        'disturbance_values': json.loads(player.disturbance_values),
    }
    
    # 合併額外變數
    if additional_vars:
        base_vars.update(additional_vars)
    
    return base_vars

def _calculate_disturbance_values(player: BasePlayer) -> np.ndarray:
    """
    依據 player 產生已四捨五入（至 2 位小數）的 NumPy 擾動向量
    """
    # seed = player.id_in_group * 1000 + player.round_number
    # rng = np.random.default_rng(seed)
    rng = np.random.default_rng()  # 改成無種子，讓每次都隨機
    disturbance_range = config.random_disturbance_range
    disturbance_vector = np.round(rng.uniform(*disturbance_range, size=player.max_production), 2)
    disturbance_values = json.dumps(disturbance_vector.tolist())

    return disturbance_values


def generate_production_cost_table(player: BasePlayer) -> List[float]:
    """
    使用向量方式計算每單位的邊際成本，返回已 round 過的 list。
    邊際成本 = 擾動值 + 線性成本 a*q
    """
    a = player.marginal_cost_coefficient
    q_array = np.arange(1, player.max_production + 1)
    marginal_cost_vector = player.disturbance_vector + a * q_array

    #random.seed()  # 重置種子
    return marginal_cost_vector.tolist()
