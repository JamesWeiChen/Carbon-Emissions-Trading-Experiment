from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'survey'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession): pass
class Group(BaseGroup): pass
class Player(BasePlayer):
    # 一、背景
    gender = models.StringField(
        choices=[('M', '男'), ('F', '女'), ('N', '非二元／不願透露')],
        label='你的性別為何？',
    )

    grade = models.StringField(
        choices=['大一', '大二', '大三', '大四', '研究所'],
        label='你的年級為？',
    )

    major = models.StringField(
        choices=[
            '經濟／商管類', '工程／自然科學', '社會科學（非商管）',
            '人文／藝術類', '其他'
        ],
        label='你主修的學門為？'
    )

    has_intro_econ = models.BooleanField(label='是否修過：初級經濟學？')
    has_env_econ = models.BooleanField(label='是否修過：環境經濟學？')
    has_pub_econ = models.BooleanField(label='是否修過：公共經濟學？')
    has_game_theory = models.BooleanField(label='是否修過：博弈論或策略互動相關課？')

    # 二、制度理解與偏好
    understand = models.IntegerField(
        label='你覺得自己對制度的理解程度為？',
        choices=[
            [1, '完全不了解'], [2, '略懂'], [3, '普通'], [4, '大致了解'], [5, '非常清楚']
        ],
        widget=widgets.RadioSelect
    )

    prefer_mechanism = models.StringField(
        choices=['碳稅制度', '碳交易制度', '兩者都差不多', '不知道'],
        label='你覺得哪一種制度較容易做出利潤最大化決策？',
    )

    real_world_choice = models.StringField(
        choices=['碳稅制度', '碳交易制度', '視產業而定', '沒意見'],
        label='若應用於現實，你偏好哪一種制度？',
    )

    # 三、行為
    consider_market_power = models.IntegerField(
        label='你是否考慮自己會影響市場價格？',
        choices=[[1, '完全沒考慮'], [2, '偶爾'], [3, '一半時間'], [4, '通常'], [5, '每輪都會']],
        widget=widgets.RadioSelect
    )

    adapt_to_others = models.IntegerField(
        label='你是否根據他人行為改變策略？',
        choices=[[1, '從未'], [2, '偶爾'], [3, '經常'], [4, '每輪都改']],
        widget=widgets.RadioSelect
    )

    attempt_manipulate = models.StringField(
        label='你是否曾試圖操控市場？',
        choices=['從未', '考慮但未實行', '偶爾嘗試', '經常嘗試'],
    )

    # 四、價值觀
    main_goal = models.StringField(
        label='你主要考慮的目標？',
        choices=['利潤最大化', '排放最少', '穩定策略', '觀望'],
    )

    free_rider_behavior = models.StringField(
        label='是否因他人高排放而也選擇高排？',
        choices=['從未', '偶爾', '經常', '每一輪都這樣']
    )

    altruism = models.StringField(
        label='若你減排無法影響總量，仍會減排嗎？',
        choices=['一定會', '視情況', '應該不會', '絕對不會']
    )

    # 五、公平與信任
    fairness = models.StringField(
        label='你覺得哪個制度比較公平？',
        choices=['碳稅制度', '碳交易制度', '都不公平', '不知道']
    )

    institutional_effect = models.IntegerField(
        label='你覺得制度對你行為的影響有多大？',
        choices=[
            [1, '幾乎沒有影響'],
            [2, '有些影響'],
            [3, '明顯影響'],
            [4, '決策完全受到制度影響']
        ],
        widget=widgets.RadioSelect
    )

    # 六、總體印象
    mechanism_complex = models.StringField(
        label='哪個制度讓市場比較混亂／難判斷？',
        choices=['碳稅制度', '碳交易制度', '都很清楚', '都很混亂']
    )

    better_for_emission = models.StringField(
        label='你覺得哪一制度比較有助於減少排放？',
        choices=['碳稅', '碳交易', '效果差不多', '不知道']
    )


class Survey(Page):
    form_model = 'player'
    form_fields = [
        # 背景
        'gender', 'grade', 'major',
        'has_intro_econ', 'has_env_econ', 'has_pub_econ', 'has_game_theory',
        # 理解
        'understand', 'prefer_mechanism', 'real_world_choice',
        # 行為
        'consider_market_power', 'adapt_to_others', 'attempt_manipulate',
        # 價值觀
        'main_goal', 'free_rider_behavior', 'altruism',
        # 公平與信任
        'fairness', 'institutional_effect',
        # 總結
        'mechanism_complex', 'better_for_emission'
    ]

page_sequence = [Survey]
