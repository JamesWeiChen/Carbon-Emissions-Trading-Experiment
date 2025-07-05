import survey as pages
from . import *
c = cu

class PlayerBot(Bot):
    def play_round(self):
        yield MyPage,dict(Q1=0)
    