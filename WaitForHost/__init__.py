from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'WaitForHost'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession): pass
class Group(BaseGroup): pass
class Player(BasePlayer): pass


class WaitForInstruction(Page):
    timeout_seconds = None  # 無限等待，由主持人控制

    @staticmethod
    def is_displayed(player):
        return True

    @staticmethod
    def vars_for_template(player):
        return {
            'message': "請稍候，等待實驗者進行實驗說明。",
        }

page_sequence = [WaitForInstruction]
