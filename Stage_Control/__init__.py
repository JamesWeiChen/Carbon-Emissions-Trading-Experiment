from otree.api import *
import random
import math
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.shared_utils import (
    initialize_player_roles, 
    calculate_control_payoffs,
    get_production_template_vars,
    calculate_final_payoff_info
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
    market_price = models.CurrencyField()

def creating_session(subsession):
    # 讓所有參與者都進入同一組
    # 這樣可以確保所有人都在相同的實驗環境中，便於統計和比較
    subsession.set_group_matrix([subsession.get_players()])

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    marginal_cost_coefficient = models.IntegerField()
    carbon_emission_per_unit = models.FloatField()
    is_dominant = models.BooleanField()
    market_price = models.CurrencyField()
    production = models.IntegerField(min=0, max=C.MAX_PRODUCTION)
    revenue = models.CurrencyField()
    total_cost = models.FloatField()
    net_profit = models.FloatField()
    initial_capital = models.CurrencyField()
    current_cash = models.CurrencyField()
    final_cash = models.CurrencyField()
    max_production = models.IntegerField()
    selected_round = models.IntegerField()

def initialize_roles(subsession: Subsession):
    initialize_player_roles(subsession, initial_capital=C.INITIAL_CAPITAL)

class Introduction(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player):
        return dict(
            treatment='control',
            treatment_text=config.get_treatment_name('control'),
            num_rounds=C.NUM_ROUNDS,
        )

class ReadyWaitPage(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = initialize_roles

class ProductionDecision(Page):
    form_model = 'player'
    form_fields = ['production']

    @staticmethod
    def error_message(player, values):
        pass

    @staticmethod
    def vars_for_template(player):
        return get_production_template_vars(player, treatment='control')

    @staticmethod
    def before_next_page(player, timeout_happened):
        pass

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = calculate_control_payoffs

class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        if player.field_maybe_none('total_cost') is not None:
            production_cost = player.total_cost
        else:
            from utils.shared_utils import calculate_production_cost
            production_cost = calculate_production_cost(player, player.production)
        
        total_emissions = player.production * player.carbon_emission_per_unit
        
        group_emissions = 0
        for p in player.group.get_players():
            p_emissions = p.production * p.carbon_emission_per_unit
            group_emissions += p_emissions
        
        final_payoff_info = calculate_final_payoff_info(player)
        
        is_last_round = player.round_number == C.NUM_ROUNDS
        remaining_rounds = C.NUM_ROUNDS - player.round_number
        progress_percentage = (player.round_number / C.NUM_ROUNDS) * 100
        
        return dict(
            production=player.production,
            market_price=player.market_price,
            revenue=player.revenue,
            production_cost=production_cost,
            net_profit=player.net_profit,
            final_cash=player.final_cash,
            current_round=player.round_number,
            total_rounds=C.NUM_ROUNDS,
            carbon_emission_per_unit=player.carbon_emission_per_unit,
            total_emissions=total_emissions,
            group_emissions=group_emissions,
            marginal_cost_coefficient=player.marginal_cost_coefficient,
            production_cost_formatted=f"{int(round(production_cost))}",
            revenue_formatted=f"{int(round(float(player.revenue)))}",
            net_profit_formatted=f"{int(round(player.net_profit))}",
            total_emissions_formatted=f"{int(round(total_emissions))}",
            group_emissions_formatted=f"{int(round(group_emissions))}",
            final_payoff_info=final_payoff_info,
            treatment='control',
            treatment_text=config.get_treatment_name('control'),
            is_last_round=is_last_round,
            remaining_rounds=remaining_rounds,
            progress_percentage=progress_percentage,
        )

page_sequence = [Introduction, ReadyWaitPage, ProductionDecision, ResultsWaitPage, Results]