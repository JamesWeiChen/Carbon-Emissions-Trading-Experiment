from otree.api import *


doc = """
Your app description
"""


class Constants(BaseConstants):
    name_in_url = 'payment_info'
    players_per_group = None
    num_rounds = 1
    completion_code = '273940'

    #定義乘數
    MULTIPLIER1 = 12
    MULTIPLIER2 = 5
    MULTIPLIER3 = 2


class Subsession(BaseSubsession):
    # def creating_session(self):
    #     for player in self.get_players():
    #         player.completion_code = Constants.completion_code
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    pass


# PAGES
class PaymentInfo(Page):
    def vars_for_template(player):
        participant = player.participant

        participant.SV_U_totalpayoff = (participant.SV_U_seq_payoff + participant.SV_U_sim_payoff)*14 + 100


page_sequence = [PaymentInfo]
