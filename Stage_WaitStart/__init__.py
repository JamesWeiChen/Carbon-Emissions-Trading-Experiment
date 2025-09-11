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


class Consent(Page):
    form_model = None

    @staticmethod
    def vars_for_template(player: Player):
        return {}


class WaitStart(Page):
    form_model = None

page_sequence = [Consent, WaitStart]
