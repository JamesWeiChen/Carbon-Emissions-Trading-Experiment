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
    consent = models.BooleanField(label="本人已閱讀並同意上述資訊與條款", blank=False)

class Consent(Page):
    form_model = 'player'
    form_fields = ['consent']

class WaitStart(Page):
    form_model = None

    @staticmethod
    def is_displayed(player: Player):
        # 僅在已同意時顯示
        return player.consent is True

page_sequence = [Consent, WaitStart]
