from otree.api import *
import random
import math
import sys
import os
from typing import Dict, Any, Callable
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.shared_utils import (
    initialize_player_roles, 
    calculate_general_payoff,
    get_production_template_vars,
    calculate_final_payoff_info,
    get_parameter_set_for_round
)
from configs.config import config

doc = config.get_stage_description('carbon_tax')

class C(BaseConstants):
    NAME_IN_URL = config.get_stage_name_in_url('carbon_tax')
    PLAYERS_PER_GROUP = config.players_per_group
    NUM_ROUNDS = config.num_rounds
    TRADING_TIME = config.muda_trading_time
    INITIAL_CAPITAL = config.get_stage_initial_capital('carbon_tax')
    MAX_PRODUCTION = config.max_production
    TAX_RATE_OPTIONS = config.tax_rate_options

class Subsession(BaseSubsession):
    market_price = models.IntegerField()
    tax_rate = models.IntegerField()
    carbon_multiplier = models.FloatField()
    dominant_mc = models.IntegerField()
    non_dominant_mc = models.IntegerField()

def creating_session(subsession: Subsession) -> None:
    
    subsession.set_group_matrix([subsession.get_players()]) # 設定分組

    # 選擇報酬回合（僅第 1 輪）- 各子 app 獨立抽取
    session_key = "selected_round__Stage_CarbonTax"
    if session_key not in subsession.session.vars:
        subsession.session.vars[session_key] = random.randint(1, C.NUM_ROUNDS)
    
    param = get_parameter_set_for_round(
        subsession.session,
        subsession.round_number,
        stage_key='carbon_tax'
    ) # 抓參數組合

    subsession.market_price = param['market_price']
    subsession.tax_rate = param['tax_rate']
    subsession.carbon_multiplier = param['carbon_multiplier']
    subsession.dominant_mc = param['dominant_mc']
    subsession.non_dominant_mc = param['non_dominant_mc']

    initialize_roles(subsession)

    # 將 selected_round 指派給所有玩家（存到 Player 欄位）
    for player in subsession.get_players():
        player.selected_round = subsession.session.vars[session_key]

class Group(BaseGroup):
    emission = models.FloatField(initial=0)  # 記錄整個組的總排放量
    Q_soc = models.FloatField(initial=0)
    Q_mkt = models.FloatField(initial=0)
    Q_tax = models.FloatField(initial=0)
    Pi_soc = models.FloatField(initial=0)
    Pi_mkt = models.FloatField(initial=0)
    Pi_tax = models.FloatField(initial=0)
    E_soc = models.FloatField(initial=0)
    E_mkt = models.FloatField(initial=0)
    E_tax = models.FloatField(initial=0)

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
    carbon_tax_paid = models.FloatField()
    net_profit = models.FloatField()
    initial_capital = models.CurrencyField()
    current_cash = models.CurrencyField()
    final_cash = models.CurrencyField()

    # 碳排放記錄
    emission = models.FloatField(initial=0)  # 記錄實際產生的排放量

    # 基準情境與社會最適指標
    q_soc = models.IntegerField(initial=0)
    q_mkt = models.IntegerField(initial=0)
    q_tax = models.IntegerField(initial=0)
    pi_soc = models.FloatField(initial=0)
    pi_mkt = models.FloatField(initial=0)
    pi_tax = models.FloatField(initial=0)
    e_soc = models.FloatField(initial=0)
    e_mkt = models.FloatField(initial=0)
    e_tax = models.FloatField(initial=0)

    # 回合資訊
    selected_round = models.IntegerField()

def initialize_roles(subsession: Subsession) -> None:
    """初始化角色分配"""
    initialize_player_roles(subsession, initial_capital=C.INITIAL_CAPITAL)

#def before_next_round(subsession: Subsession):
#    """每一回合開始前重新分配 dominant firm 等角色"""
#    initialize_player_roles(subsession, initial_capital=C.INITIAL_CAPITAL)

class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player) -> bool:
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        tax_rate = player.session.vars.get(f'tax_rate_round_{player.round_number}', 0)
        
        return {
            'treatment': 'carbon_tax',
            'treatment_text': config.get_treatment_name('carbon_tax'),
            'tax_rate': tax_rate,
            'num_rounds': C.NUM_ROUNDS,
        }

class ReadyWaitPage(WaitPage):
    wait_for_all_groups = True
    # after_all_players_arrive = initialize_roles

class ProductionDecision(Page):
    form_model = 'player'
    form_fields = ['production']

    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        tax_rate = int(player.subsession.tax_rate)
        unit_tax = player.carbon_emission_per_unit * tax_rate
        
        additional_vars = {
            'tax_rate': tax_rate,
            'unit_tax': unit_tax,
        }
        
        return get_production_template_vars(
            player, 
            treatment='carbon_tax',
            additional_vars=additional_vars
        )         

class ResultsWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        # 先計算一般payoff
        calculate_general_payoff(group, tax_rate=group.subsession.tax_rate, use_tax=True)
        
        # 然後記錄每個player的實際排放量和組總排放量
        group_total_emission = 0
        for player in group.get_players():
            player.emission = player.production * player.carbon_emission_per_unit
            group_total_emission += player.emission
        
        # 記錄組總排放量
        group.emission = group_total_emission

class Results(Page):
    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        # 計算基本數據
        production_cost = player.total_cost
        carbon_tax = _get_carbon_tax(player)
        total_emissions = player.production * player.carbon_emission_per_unit
        group_emissions = _calculate_group_emissions(player)
        
        # 計算最終報酬資訊（包含碳稅）
        final_payoff_info = calculate_final_payoff_info(
            player, 
            _carbon_tax_cost_calculator, 
            _carbon_tax_additional_info
        )

        # 儲存數據以供 Payment Info 使用
        if final_payoff_info is not None:
            player.participant.vars["carbon_tax_summary"] = {
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
            'carbon_tax_paid': carbon_tax,
            'net_profit': player.net_profit,
            'final_cash': player.final_cash,
            
            # 回合資訊
            'current_round': player.round_number,
            'total_rounds': C.NUM_ROUNDS,
            'is_last_round': is_last_round,
            'remaining_rounds': remaining_rounds,
            'progress_percentage': progress_percentage,
            
            # 碳排放和稅務資訊
            'carbon_emission_per_unit': player.carbon_emission_per_unit,
            'total_emissions': total_emissions,
            'group_emissions': group_emissions,
            'tax_rate': player.subsession.tax_rate,
            'marginal_cost_coefficient': player.marginal_cost_coefficient,
            
            # 格式化數值
            'production_cost_formatted': f"{production_cost} 法幣",
            'carbon_tax_formatted': f"{int(round(carbon_tax))} 法幣",
            'revenue_formatted': f"{int(round(float(player.revenue)))}",
            'net_profit_formatted': f"{int(round(player.net_profit))} 法幣",
            'total_emissions_formatted': f"{int(round(total_emissions))}",
            'group_emissions_formatted': f"{int(round(group_emissions))}",
            
            # 最終報酬資訊
            'final_payoff_info': final_payoff_info,
            
            # 處理組別資訊
            'treatment': 'carbon_tax',
            'treatment_text': config.get_treatment_name('carbon_tax'),
        }

class WaitForInstruction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

def _get_carbon_tax(player: Player) -> float:
    """獲取碳稅金額"""
    if player.field_maybe_none('carbon_tax_paid') is not None:
        return player.carbon_tax_paid
    else:
        total_emissions = player.production * player.carbon_emission_per_unit
        return total_emissions * player.subsession.tax_rate

def _calculate_group_emissions(player: Player) -> float:
    """計算組別總排放量"""
    return sum(
        p.production * p.carbon_emission_per_unit 
        for p in player.group.get_players()
    )

def _carbon_tax_cost_calculator(selected_player: Player) -> float:
    """計算包含碳稅的總成本"""
    base_cost = selected_player.total_cost
    emissions = selected_player.production * selected_player.carbon_emission_per_unit
    tax = emissions * selected_player.subsession.tax_rate
    return base_cost + tax

def _carbon_tax_additional_info(selected_player: Player) -> Dict[str, Any]:
    """提供碳稅相關的額外資訊"""
    tax = selected_player.carbon_tax_paid
    return {
        'tax_rate': selected_player.subsession.tax_rate,
        'tax': tax,
        'tax_formatted': f"{int(round(tax))}"
    }

page_sequence = [Introduction, ReadyWaitPage, ProductionDecision, ResultsWaitPage, Results, WaitForInstruction]
