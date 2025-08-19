from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'wait_start'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

class WaitStart(Page):
    # 顯示一個純訊息頁，無表單、無按鈕
    form_model = None

    @staticmethod
    def is_displayed(player: Player):
        return True

page_sequence = [WaitStart]