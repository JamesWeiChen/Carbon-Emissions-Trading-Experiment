from otree.api import *
import random
import math
import sys
import os
from typing import Dict, Any
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.shared_utils import (
    initialize_player_roles, 
    calculate_general_payoff,
    get_production_template_vars,
    calculate_final_payoff_info,
    get_parameter_set_for_round
)
from configs.config import config

doc = config.get_stage_description('control')

class C(BaseConstants):
    NAME_IN_URL = config.get_stage_name_in_url('control')
    PLAYERS_PER_GROUP = config.players_per_group
    NUM_ROUNDS = config.num_rounds
    TRADING_TIME = config.muda_trading_time
    INITIAL_CAPITAL = config.get_stage_initial_capital('control')
    MAX_PRODUCTION = config.max_production

class Subsession(BaseSubsession):
    # market_price = models.CurrencyField()
    market_price = models.IntegerField()
    tax_rate = models.IntegerField()
    carbon_multiplier = models.FloatField()
    dominant_mc = models.IntegerField()
    non_dominant_mc = models.IntegerField()

def creating_session(subsession: Subsession) -> None:
    
    subsession.set_group_matrix([subsession.get_players()]) # 設定分組

    # 選擇報酬回合（僅第 1 輪）
    if "selected_round" not in subsession.session.vars:
        subsession.session.vars["selected_round"] = random.randint(1, C.NUM_ROUNDS)
    
    param = get_parameter_set_for_round(subsession.session, subsession.round_number) # 抓參數組合

    subsession.market_price = param['market_price']
    subsession.tax_rate = param['tax_rate']
    subsession.carbon_multiplier = param['carbon_multiplier']
    subsession.dominant_mc = param['dominant_mc']
    subsession.non_dominant_mc = param['non_dominant_mc']

    initialize_roles(subsession)

    # 將 selected_round 指派給所有玩家
    for player in subsession.get_players():
        player.selected_round = subsession.session.vars["selected_round"]

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    # 企業特性
    is_dominant = models.BooleanField()
    marginal_cost_coefficient = models.IntegerField()
    carbon_emission_per_unit = models.FloatField()
    max_production = models.IntegerField()
    
    # 市場和生產
    market_price = models.CurrencyField()
    production = models.IntegerField(min=0, max=C.MAX_PRODUCTION)
    disturbance_values = models.LongStringField()
    
    # 財務相關
    revenue = models.CurrencyField()
    total_cost = models.FloatField()
    net_profit = models.FloatField()
    initial_capital = models.CurrencyField()
    current_cash = models.CurrencyField()
    final_cash = models.CurrencyField()
    
    # 新增：記錄生產成本表
    # production_cost_table = models.LongStringField(initial='[]')
    
    # 隨機選中的回合用於最終報酬
    selected_round = models.IntegerField()

def initialize_roles(subsession: Subsession) -> None:
    """初始化角色分配"""
    initialize_player_roles(subsession, initial_capital=C.INITIAL_CAPITAL)


class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player) -> bool:
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        return {
            'treatment': 'control',
            'treatment_text': config.get_treatment_name('control'),
            'num_rounds': C.NUM_ROUNDS,
        }

class ReadyWaitPage(WaitPage):
    wait_for_all_groups = True

class ProductionDecision(Page):
    form_model = 'player'
    form_fields = ['production']

    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        return get_production_template_vars(player, treatment='control')

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = lambda group: calculate_general_payoff(group)

class Results(Page):
    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        # 計算基本數據
        production_cost = player.total_cost
        total_emissions = player.production * player.carbon_emission_per_unit
        group_emissions = _calculate_group_emissions(player)
        
        # 計算最終報酬資訊
        final_payoff_info = calculate_final_payoff_info(player)

        # 給 Payment Info 用的資訊
        if final_payoff_info is not None:
            player.participant.vars["control_summary"] = {
                "profit": final_payoff_info["profit"],
                "emission": final_payoff_info["emissions"],
                "group_emission": final_payoff_info["group_emissions"]
            }

        # 計算進度資訊
        is_last_round = player.round_number == C.NUM_ROUNDS
        remaining_rounds = C.NUM_ROUNDS - player.round_number
        progress_percentage = (player.round_number / C.NUM_ROUNDS) * 100
        
        return {
            # 基本資訊
            'production': player.production,
            'market_price': player.market_price,
            'revenue': player.revenue,
            'production_cost': production_cost,
            'net_profit': player.net_profit,
            'final_cash': player.final_cash,
            
            # 回合資訊
            'current_round': player.round_number,
            'total_rounds': C.NUM_ROUNDS,
            'is_last_round': is_last_round,
            'remaining_rounds': remaining_rounds,
            'progress_percentage': progress_percentage,
            
            # 碳排放資訊
            'carbon_emission_per_unit': player.carbon_emission_per_unit,
            'total_emissions': total_emissions,
            'group_emissions': group_emissions,
            'marginal_cost_coefficient': player.marginal_cost_coefficient,
            
            # 格式化數值
            'production_cost_formatted': f"{int(round(production_cost))} 法幣",
            'revenue_formatted': f"{int(round(float(player.revenue)))}",
            'net_profit_formatted': f"{int(round(player.net_profit))} 法幣",
            'total_emissions_formatted': f"{int(round(total_emissions))}",
            'group_emissions_formatted': f"{int(round(group_emissions))}",
            
            # 最終報酬資訊
            'final_payoff_info': final_payoff_info,
            
            # 處理組別資訊
            'treatment': 'control',
            'treatment_text': config.get_treatment_name('control'),
        }

class WaitForInstruction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

def _calculate_group_emissions(player: Player) -> float:
    """計算組別總排放量"""
    group_emissions = 0
    for p in player.group.get_players():
        p_emissions = p.production * p.carbon_emission_per_unit
        group_emissions += p_emissions
    return group_emissions

page_sequence = [Introduction, ReadyWaitPage, ProductionDecision, ResultsWaitPage, Results, WaitForInstruction]
