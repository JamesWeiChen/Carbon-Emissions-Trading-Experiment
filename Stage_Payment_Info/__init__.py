from otree.api import *

doc = """
顯示最終報酬與排放資訊，並產生完成代碼與真實金額。
"""

class Constants(BaseConstants):
    name_in_url = 'payment_info'
    players_per_group = None
    num_rounds = 1
    completion_code = '273940'

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    total_payment = models.CurrencyField()

    @staticmethod
    def calculate_payment_info(player):
        participant = player.participant
        session = player.session
        treatment = session.config.get("treatment", "tax")

        control = participant.vars.get("control_summary", {})
        carbon = participant.vars.get(
            "carbon_trade_summary" if treatment == "trade" else "carbon_tax_summary", {}
        )

        total_profit = control.get("profit", 0) + carbon.get("profit", 0)
        total_emission = control.get("emission", 0) + carbon.get("emission", 0)
        total_group_emission = control.get("group_emission", 0) + carbon.get("group_emission", 0)

        real_payoff = total_profit.to_real_world_currency(session)
        participation_fee = session.config.get("participation_fee", 0)
        total_payment = real_payoff + participation_fee

        return {
            'control': control,
            'carbon': carbon,
            'total_profit': total_profit,
            'total_emission': total_emission,
            'total_group_emission': total_group_emission,
            'real_payoff': real_payoff,
            'participation_fee': participation_fee,
            'total_payment': total_payment,
        }

# PAGES
class PaymentInfo(Page):

    @staticmethod
    def vars_for_template(player: Player):
        info = Player.calculate_payment_info(player)

        return dict(
            control_profit=info['control'].get("profit", 0),
            carbon_profit=info['carbon'].get("profit", 0),
            total_profit=info['total_profit'],
            total_profit_formatted=f"{info['total_profit']:,.0f} 法幣",
            total_emission_formatted=f"{info['total_emission']:.1f} 單位碳排放",
            total_group_emission_formatted=f"{info['total_group_emission']:.1f} 單位碳排放",
            real_payoff_formatted=f"{info['real_payoff']:,.0f} 元",
            participation_fee=int(info['participation_fee']),
            total_payment_formatted=f"{info['total_payment']:,.0f} 元",
            completion_code=Constants.completion_code
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        info = player.calculate_payment_info(player)
        player.payoff = info['total_profit']
        player.total_payment = info['total_payment']

class WaitForInstruction(Page):
    pass

page_sequence = [PaymentInfo, WaitForInstruction]
