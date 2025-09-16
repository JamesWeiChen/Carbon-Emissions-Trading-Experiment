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

def get_parameter_set_for_round(
    session: Any,
    round_number: int,
    stage_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    根據 session 與 round number，決定本回合使用哪一組參數。

    - 第一次呼叫時會在 session.vars 儲存隨機順序
    - 從 config.parameter_sets 中挑出該回合對應的參數組合

    Args:
        session: oTree session 物件
        round_number: 當前回合數（從 1 開始）
        stage_key: 用於辨識不同階段的鍵值。若為 None，則所有階段共用同一順序。

    Returns:
        Dict[str, Any]: 對應本回合的參數設定
    """
    all_sets = config.parameter_sets
    num_sets = len(all_sets)

    # 每個 stage_key 單獨儲存一組隨機順序，避免不同階段使用相同排序
    stage_identifier = stage_key or 'default'
    parameter_orders = session.vars.setdefault('parameter_orders', {})

    if (
        stage_identifier not in parameter_orders
        or len(parameter_orders.get(stage_identifier, [])) != num_sets
    ):
        parameter_orders[stage_identifier] = random.sample(range(num_sets), num_sets)

    order = parameter_orders[stage_identifier]
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

def calculate_general_payoff(
    group: BaseGroup, 
    tax_rate: float = 0, 
    use_tax: bool = False,
    use_trading: bool = False
) -> None:
    """
    通用 payoff 計算，可處理控制組、碳稅組、碳交易組
    - use_trading: True 則 payoff = current_cash - initial_capital
    """
    for p in group.get_players():
        if p.production is None:
            p.production = 0

        # 計算生產成本
        cost = calculate_production_cost(p, p.production)
        revenue = p.production * p.market_price

        # 計算碳稅
        tax = 0
        if use_tax and tax_rate > 0:
            emissions = p.production * p.carbon_emission_per_unit
            tax = emissions * tax_rate
            p.carbon_tax_paid = float(tax)

        if use_trading:
            # 加上生產階段的收入/成本
            profit = (p.current_cash - p.initial_capital) + (revenue - cost - tax)
            p.final_cash = p.current_cash - cost + revenue
        else:
            # 控制組/碳稅組 payoff = 生產收入 - 成本 - 稅
            profit = revenue - cost - tax
            p.final_cash = p.current_cash + profit

        p.revenue = revenue
        p.total_cost = float(cost)
        p.net_profit = float(profit)
        p.payoff = profit

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
    
    # 選擇隨機回合（優先使用各子 app 先行設定在 Player 的欄位，其次使用「依 app 名稱」的 session key）
    selected_round = getattr(player, 'selected_round', None)
    if selected_round in (None, 0):
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
        'cost_formatted': f"{cost}",
        'revenue_formatted': f"{int(round(revenue))}",
        'emissions_formatted': f"{int(round(emissions))}",
        'group_emissions_formatted': f"{int(round(group_emissions))}"
    }
    
    # 添加額外資訊
    if additional_info_func:
        final_payoff_info.update(additional_info)
    
    return final_payoff_info

def _get_or_set_selected_round(player: BasePlayer) -> int:
    """
    依「子 app」各自抽取支付回合：
    - 使用 session.vars 中以 app 標籤區分的 key，例如：selected_round__Stage_Control
    - 預設回合數使用 config.num_rounds（此函式目前僅由控制組/碳稅組呼叫）
    """
    # 以 Player 所屬模組名稱推斷 app 標籤，例如 'Stage_Control.__init__' -> 'Stage_Control'
    module_name = getattr(player, '__module__', '')
    app_label = module_name.split('.')[0] if module_name else 'unknown_app'
    session_key = f"selected_round__{app_label}"

    if session_key not in player.session.vars:
        player.session.vars[session_key] = random.randint(1, config.num_rounds)
    return player.session.vars[session_key]

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
