# apps/WaitForHost/__init__.py
from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'WaitForHost'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession): pass
class Group(BaseGroup): pass
class Player(BasePlayer): pass

class InstructionWait(Page):
    timeout_seconds = None
    def is_displayed(player): return True

page_sequence = [WaitForInstruction]
