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
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from configs.config import config, ConfigConstants

CommonConstants = ConfigConstants
def initialize_player_roles(subsession, initial_capital):
    num_players = len(subsession.get_players())
    print(f"初始化 {num_players} 個玩家的角色...")
    
    # 使用新的配置方式獲取主導廠商數量
    num_dominant = config.dominant_firm_count
    
    # 確保主導廠商數量不超過總玩家數
    num_dominant = min(num_dominant, num_players)
    
    if config.ensure_player1_dominant:
        # 測試模式：確保1號玩家為主導廠商
        roles = [True] + [False] * (num_players - 1)
        
        if num_dominant > 1:
            non_dominant_indices = list(range(1, num_players))
            additional_dominant = random.sample(non_dominant_indices, min(num_dominant - 1, len(non_dominant_indices)))
            for idx in additional_dominant:
                roles[idx] = True
    else:
        # 正式模式：隨機分配主導廠商
        roles = [True] * num_dominant + [False] * (num_players - num_dominant)
        random.shuffle(roles)
    
    print(f"角色分配: {num_dominant} 個 dominant 廠商, {num_players - num_dominant} 個 non-dominant 廠商")
    print(f"角色列表: {roles}")
    print(f"測試模式: {'是' if config.test_mode else '否'}")
    
    for i, p in enumerate(subsession.get_players()):
        p.is_dominant = roles[i]
        p.marginal_cost_coefficient = random.randint(*config.dominant_mc_range) if p.is_dominant else random.randint(*config.non_dominant_mc_range)
        p.carbon_emission_per_unit = config.dominant_emission_per_unit if p.is_dominant else config.non_dominant_emission_per_unit
        p.max_production = config.dominant_max_production if p.is_dominant else config.non_dominant_max_production
        
        p.initial_capital = initial_capital
        p.current_cash = initial_capital
        
        # 使用新的隨機價格抽取機制
        base_prices = config.get('general.market_price_random_draw.base_prices', [25, 30, 35, 40])
        variations = config.get('general.market_price_random_draw.variations', [-2, -1, 1, 2])
        min_price = config.get('general.market_price_random_draw.min_price', 1)
        
        base_price = random.choice(base_prices)
        variation = random.choice(variations)
        market_price = max(base_price + variation, min_price)
        p.market_price = market_price
        
        print(f"玩家 {p.id_in_group}: {'Dominant' if p.is_dominant else 'Non-dominant'}, "
              f"MC={p.marginal_cost_coefficient}, Emission={p.carbon_emission_per_unit}, "
              f"MaxProd={p.max_production}, Price={p.market_price}")

def calculate_production_cost(player, production_quantity):
    if production_quantity <= 0:
        return 0.0
    
    random.seed(player.id_in_group * 1000 + player.round_number)
    
    total_cost = 0.0
    disturbance_range = config.random_disturbance_range
    
    for i in range(1, production_quantity + 1):
        unit_marginal_cost = player.marginal_cost_coefficient * i
        unit_disturbance = random.uniform(*disturbance_range)
        total_cost += unit_marginal_cost + unit_disturbance
    
    random.seed()
    return total_cost


def calculate_control_payoffs(group):
    for p in group.get_players():
        if p.production is None:
            p.production = 0
        
        cost = calculate_production_cost(p, p.production)
        revenue = p.production * p.market_price
        profit = revenue - cost
        
        p.revenue = revenue
        p.total_cost = float(cost)
        p.net_profit = float(profit)
        p.final_cash = p.current_cash + profit
        p.payoff = profit

def calculate_carbon_tax_payoffs(group):
    for p in group.get_players():
        if p.production is None:
            p.production = 0
        
        cost = calculate_production_cost(p, p.production)
        revenue = p.production * p.market_price
        emissions = p.production * p.carbon_emission_per_unit
        tax = emissions * p.subsession.tax_rate
        profit = revenue - cost - tax
        
        p.revenue = revenue
        p.total_cost = float(cost)
        p.carbon_tax_paid = float(tax)
        p.net_profit = float(profit)
        p.final_cash = p.current_cash + profit
        p.payoff = profit
def update_price_history(subsession, trade_price, event='trade'):
    try:
        price_history = json.loads(subsession.price_history)
    except json.JSONDecodeError:
        price_history = []
    
    current_time = int(time.time())
    if hasattr(subsession, 'start_time') and subsession.start_time:
        elapsed_seconds = current_time - subsession.start_time
    else:
        elapsed_seconds = 0
    
    minutes = elapsed_seconds // 60
    seconds = elapsed_seconds % 60
    
    market_price = getattr(subsession, 'market_price', None) or getattr(subsession, 'item_market_price', 0)
    
    price_record = {
        'timestamp': f"{minutes:02d}:{seconds:02d}",
        'price': float(trade_price),
        'event': event,
        'market_price': float(market_price),
        'round': subsession.round_number
    }
    
    price_history.append(price_record)
    subsession.price_history = json.dumps(price_history)
    
    return price_history

def record_trade(group, buyer_id, seller_id, price, quantity):
    try:
        trade_history = json.loads(group.trade_history)
    except:
        trade_history = []
    
    # 計算從交易開始經過的時間（秒）
    current_time = int(time.time())
    if hasattr(group.subsession, 'start_time') and group.subsession.start_time:
        elapsed_seconds = current_time - group.subsession.start_time
    else:
        elapsed_seconds = 0
    
    minutes = elapsed_seconds // 60
    seconds = elapsed_seconds % 60
    
    # 獲取市場價格
    market_price = getattr(group.subsession, 'market_price', None) or getattr(group.subsession, 'item_market_price', 0)
    
    trade_record = {
        'timestamp': f"{minutes:02d}:{seconds:02d}",  # 統一使用分:秒格式
        'buyer_id': int(buyer_id),
        'seller_id': int(seller_id),
        'price': float(price),  # 保持浮點數精度
        'quantity': int(quantity),
        'total_value': float(price) * int(quantity),
        'market_price': float(market_price)
    }
    
    trade_history.append(trade_record)
    group.trade_history = json.dumps(trade_history)
    
    print(f"記錄交易: 買方{buyer_id} <- 賣方{seller_id}, 價格{price}, 數量{quantity}")
    return trade_history

def cancel_player_orders(group, player_id, order_type):
    if order_type == 'buy':
        try:
            buy_orders = json.loads(group.buy_orders)
            old_count = len([o for o in buy_orders if int(o[0]) == player_id])
            buy_orders = [o for o in buy_orders if int(o[0]) != player_id]
            group.buy_orders = json.dumps(buy_orders)
            print(f"已自動取消玩家 {player_id} 的 {old_count} 筆買單")
        except json.JSONDecodeError:
            pass
    elif order_type == 'sell':
        try:
            sell_orders = json.loads(group.sell_orders)
            old_count = len([o for o in sell_orders if int(o[0]) == player_id])
            sell_orders = [o for o in sell_orders if int(o[0]) != player_id]
            group.sell_orders = json.dumps(sell_orders)
            print(f"已自動取消玩家 {player_id} 的 {old_count} 筆賣單")
        except json.JSONDecodeError:
            pass
def calculate_final_payoff_info(player, cost_calculator_func=None, additional_info_func=None):
    final_payoff_info = None
    if player.round_number == config.num_rounds:
        selected_round = player.field_maybe_none('selected_round')
        if selected_round is None:
            selected_round = random.randint(1, config.num_rounds)
            player.selected_round = selected_round
        
        selected_round_player = player.in_round(selected_round)
        
        if cost_calculator_func:
            selected_cost = cost_calculator_func(selected_round_player)
        else:
            selected_cost = calculate_production_cost(selected_round_player, selected_round_player.production)
        
        selected_revenue = selected_round_player.production * selected_round_player.market_price
        selected_profit = selected_revenue - selected_cost
        selected_emissions = selected_round_player.production * selected_round_player.carbon_emission_per_unit
        
        selected_round_group_emissions = 0
        for p in selected_round_player.group.get_players():
            p_in_selected_round = p.in_round(selected_round)
            p_emissions = p_in_selected_round.production * p_in_selected_round.carbon_emission_per_unit
            selected_round_group_emissions += p_emissions
        
        final_payoff_info = {
            'selected_round': selected_round,
            'production': selected_round_player.production,
            'market_price': selected_round_player.market_price,
            'revenue': selected_revenue,
            'cost': selected_cost,
            'profit': selected_profit,
            'emissions': selected_emissions,
            'group_emissions': selected_round_group_emissions,
            'profit_formatted': f"{int(round(selected_profit))}",
            'cost_formatted': f"{int(round(selected_cost))}",
            'revenue_formatted': f"{int(round(selected_revenue))}",
            'emissions_formatted': f"{int(round(selected_emissions))}",
            'group_emissions_formatted': f"{int(round(selected_round_group_emissions))}"
        }
        
        if additional_info_func:
            additional_info = additional_info_func(selected_round_player)
            final_payoff_info.update(additional_info)
    
    return final_payoff_info
def get_production_template_vars(player, treatment, additional_vars=None):
    random.seed(player.id_in_group * 1000 + player.round_number)
    disturbance_values = []
    disturbance_range = config.random_disturbance_range
    
    for q in range(1, player.max_production + 1):
        disturbance_values.append(round(random.uniform(*disturbance_range), 3))
    random.seed()
    
    base_vars = dict(
        max_production=player.max_production,
        marginal_cost_coefficient=int(player.marginal_cost_coefficient),
        carbon_emission_per_unit=player.carbon_emission_per_unit,
        market_price=player.market_price,
        current_cash=int(player.current_cash),
        treatment=treatment,
        treatment_text=config.get_treatment_name(treatment),
        unit_income=int(player.market_price),
        disturbance_values=disturbance_values,
    )
    
    if additional_vars:
        base_vars.update(additional_vars)
    
    return base_vars 