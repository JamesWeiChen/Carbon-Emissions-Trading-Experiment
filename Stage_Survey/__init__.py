from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'survey'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):

    # === 背景資訊與控制變數 ===
    age = models.IntegerField(label='您的年齡為？', min=15, max=100)
    male = models.IntegerField(
        choices=[
            [1, '男'],
            [0, '女']
        ],
        label='您的性別為何？'
    )
    grade = models.StringField(
        choices=[
            ('U1', '大一'),
            ('U2', '大二'),
            ('U3', '大三'),
            ('U4', '大四（以上）'),
            ('M1', '碩一'),
            ('M2', '碩二'),
            ('M3', '碩三（以上）'),
            ('D', '博士班')
        ],
        label='您的年級為？'
    )
    major_econ_or_bz = models.IntegerField(
        label='您的主修／雙主修／輔系是否與「經濟或商管」相關？',
        choices=[[1, '是'], [0, '否']]
    )
    major_env = models.IntegerField(
        label='您的主修／雙主修／輔系是否與「環境科學」相關？',
        choices=[[1, '是'], [0, '否']]
    )

    has_intro_econ = models.IntegerField(
        label='您是否修過大一經濟學？（經濟學原理、個體經濟學原理等...）',
        choices=[[1, '是'], [0, '否']]
    )
    has_micro = models.IntegerField(
        label='您是否修過個體經濟學？（大二以上課程）',
        choices=[[1, '是'], [0, '否']]
    )
    has_env_econ = models.IntegerField(
        label='您是否修過環境經濟學？',
        choices=[[1, '是'], [0, '否']]
    )
    has_pub_econ = models.IntegerField(
        label='您是否修過公共經濟學？',
        choices=[[1, '是'], [0, '否']]
    )
    has_exp_econ = models.IntegerField(
        label='您是否修過實驗經濟學？',
        choices=[[1, '是'], [0, '否']]
    )

    # 價值觀與偏好
    main_goal = models.StringField(
        label='您決定生產量時主要考慮的目標是？',
        choices=['利潤最大化', '碳排最少', '綜合考慮利潤與碳排（多考慮利潤）', '綜合考慮利潤與碳排（多考慮碳排）']
    )

    respond_to_high_others = models.IntegerField(
        label='當您看到其他受試者碳排（生產）很多時，您通常會怎麼做？',
        choices=[
            [-2, '排放（生產）少很多'],
            [-1, '排放（生產）少一點'],
            [0, '不受影響，維持原策略'],
            [1, '排放（生產）多一點'],
            [2, '排放（生產）多很多']
        ],
        widget=widgets.RadioSelect
    )

    # carbon_tax 專屬題目
    carbon_tax_fairness = models.IntegerField(
        label='您認為第二階段的碳稅制度在「公平性」方面的表現',
        choices=[[1, '非常不公平'], [2, '不太公平'], [3, '普通'], [4, '公平'], [5, '非常公平']],
        widget=widgets.RadioSelect
    )
    carbon_tax_efficiency = models.IntegerField(
        label='您認為第二階段的碳稅制度在「經濟效率」方面的表現',
        choices=[[1, '非常沒效率'], [2, '沒效率'], [3, '普通'], [4, '有效率'], [5, '非常有效率']],
        widget=widgets.RadioSelect
    )
    carbon_tax_environment = models.IntegerField(
        label='您認為第二階段的碳稅制度在「減碳／改善環境」方面的效果',
        choices=[[1, '完全沒幫助'], [2, '幫助很小'], [3, '普通'], [4, '有幫助'], [5, '非常有效']],
        widget=widgets.RadioSelect
    )

    # carbon_trade 專屬題目
    carbon_trade_fairness = models.IntegerField(
        label='您認為第二階段的碳交易制度在「公平性」方面的表現',
        choices=[[1, '非常不公平'], [2, '不太公平'], [3, '普通'], [4, '公平'], [5, '非常公平']],
        widget=widgets.RadioSelect
    )
    carbon_trade_efficiency = models.IntegerField(
        label='您認為第二階段的碳交易制度在「經濟效率」方面的表現',
        choices=[[1, '非常沒效率'], [2, '沒效率'], [3, '普通'], [4, '有效率'], [5, '非常有效率']],
        widget=widgets.RadioSelect
    )
    carbon_trade_environment = models.IntegerField(
        label='您認為第二階段的碳交易制度在「減碳／改善環境」方面的效果',
        choices=[[1, '完全沒幫助'], [2, '幫助很小'], [3, '普通'], [4, '有幫助'], [5, '非常有效']],
        widget=widgets.RadioSelect
    )
    carbon_trade_mkt_power = models.IntegerField(
        label='若您是產量上限高的大廠商，您是否會嘗試壓低碳權的價格？',
        choices=[[1, '不會'], [2, '可能不會'], [3, '不確定'], [4, '可能會'], [5, '會']],
        widget=widgets.RadioSelect
    )

# === 頁面設定 ===
class Survey(Page):
    
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        return [
            'age', 'male', 'grade', 'major_econ_or_bz', 'major_env',
            'has_intro_econ', 'has_micro', 'has_env_econ', 'has_pub_econ', 'has_exp_econ',
            'main_goal', 'respond_to_high_others',
            'carbon_tax_fairness', 'carbon_tax_efficiency', 'carbon_tax_environment',
            'carbon_trade_fairness', 'carbon_trade_efficiency', 'carbon_trade_environment',
            'carbon_trade_mkt_power'
        ]

class ByePage(Page):
    def is_displayed(player):
        return True

page_sequence = [Survey, ByePage]
