from otree.api import *
import random
import math
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.shared_utils import (
    initialize_player_roles, 
    calculate_carbon_tax_payoffs,
    get_production_template_vars,
    calculate_final_payoff_info,
    calculate_production_cost
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
    market_price = models.CurrencyField()
    tax_rate = models.CurrencyField()

def creating_session(subsession):
    # 讓所有參與者都進入同一組
    # 這樣可以確保所有人都在相同的實驗環境中，便於統計和比較
    subsession.set_group_matrix([subsession.get_players()])
    
    # 直接從稅率列表中隨機選擇一個
    tax_rates = config.carbon_tax_rates
    selected_tax_rate = random.choice(tax_rates)
    
    subsession.tax_rate = selected_tax_rate
    subsession.session.vars[f'tax_rate_round_{subsession.round_number}'] = selected_tax_rate
    
    print(f"第{subsession.round_number}輪 - 選中的稅率: {selected_tax_rate}")

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
    carbon_tax_paid = models.FloatField()
    net_profit = models.FloatField()
    initial_capital = models.CurrencyField()
    final_cash = models.CurrencyField()
    max_production = models.IntegerField()
    current_cash = models.CurrencyField()
    selected_round = models.IntegerField()

def initialize_roles(subsession: Subsession):
    initialize_player_roles(subsession, initial_capital=C.INITIAL_CAPITAL)

class Introduction(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player):
        tax_rate = player.session.vars.get(f'tax_rate_round_{player.round_number}', 0)
        
        return dict(
            treatment='carbon_tax',
            treatment_text=config.get_treatment_name('carbon_tax'),
            tax_rate=tax_rate,
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
        tax_rate = int(player.subsession.tax_rate)
        emissions_per_unit = player.carbon_emission_per_unit
        unit_tax = emissions_per_unit * tax_rate
        
        additional_vars = {
            'tax_rate': tax_rate,
            'unit_tax': unit_tax,
        }
        
        return get_production_template_vars(
            player, 
            treatment='carbon_tax',
            additional_vars=additional_vars
        )

    @staticmethod
    def before_next_page(player, timeout_happened):
        pass

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = calculate_carbon_tax_payoffs

class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        if player.field_maybe_none('total_cost') is not None:
            production_cost = player.total_cost
        else:
            production_cost = calculate_production_cost(player, player.production)
        
        if player.field_maybe_none('carbon_tax_paid') is not None:
            carbon_tax = player.carbon_tax_paid
        else:
            total_emissions = player.production * player.carbon_emission_per_unit
            carbon_tax = total_emissions * player.subsession.tax_rate
        
        total_emissions = player.production * player.carbon_emission_per_unit
        
        group_emissions = 0
        for p in player.group.get_players():
            p_emissions = p.production * p.carbon_emission_per_unit
            group_emissions += p_emissions
        
        def carbon_tax_cost_calculator(selected_player):
            base_cost = calculate_production_cost(selected_player, selected_player.production)
            emissions = selected_player.production * selected_player.carbon_emission_per_unit
            tax = emissions * selected_player.subsession.tax_rate
            return base_cost + tax
        
        def carbon_tax_additional_info(selected_player):
            emissions = selected_player.production * selected_player.carbon_emission_per_unit
            tax = emissions * selected_player.subsession.tax_rate
            return {
                'tax_rate': selected_player.subsession.tax_rate,
                'tax': tax,
                'tax_formatted': f"{int(round(tax))}"
            }
        
        final_payoff_info = calculate_final_payoff_info(player, carbon_tax_cost_calculator, carbon_tax_additional_info)
        
        is_last_round = player.round_number == C.NUM_ROUNDS
        remaining_rounds = C.NUM_ROUNDS - player.round_number
        progress_percentage = (player.round_number / C.NUM_ROUNDS) * 100
        
        return dict(
            production=player.production,
            market_price=player.market_price,
            revenue=player.revenue,
            production_cost=production_cost,
            carbon_tax_paid=carbon_tax,
            net_profit=player.net_profit,
            final_cash=player.final_cash,
            current_round=player.round_number,
            total_rounds=C.NUM_ROUNDS,
            carbon_emission_per_unit=player.carbon_emission_per_unit,
            total_emissions=total_emissions,
            group_emissions=group_emissions,
            tax_rate=player.subsession.tax_rate,
            marginal_cost_coefficient=player.marginal_cost_coefficient,
            production_cost_formatted=f"{int(round(production_cost))}",
            carbon_tax_formatted=f"{int(round(carbon_tax))}",
            revenue_formatted=f"{int(round(float(player.revenue)))}",
            net_profit_formatted=f"{int(round(player.net_profit))}",
            total_emissions_formatted=f"{int(round(total_emissions))}",
            group_emissions_formatted=f"{int(round(group_emissions))}",
            final_payoff_info=final_payoff_info,
            treatment='carbon_tax',
            treatment_text=config.get_treatment_name('carbon_tax'),
            is_last_round=is_last_round,
            remaining_rounds=remaining_rounds,
            progress_percentage=progress_percentage,
        )

page_sequence = [Introduction, ReadyWaitPage, ProductionDecision, ResultsWaitPage, Results]