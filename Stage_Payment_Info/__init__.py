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
    real_emission = models.FloatField()

class Player(BasePlayer):

    total_payment = models.IntegerField()
    # === 基本資料 ===
    name = models.StringField(label="您的名字")
    school = models.StringField(
        label="您的學校",
        choices=[
            ('國立臺灣大學', '國立臺灣大學'),
            ('國立政治大學', '國立政治大學'),
            ('國立臺北大學', '國立臺北大學'),
            ('國立臺灣師範大學', '國立臺灣師範大學'),
            ('國立臺北教育大學', '國立臺北教育大學'),
            ('國立臺灣科技大學', '國立臺灣科技大學'),
        ],
        widget=widgets.Dropdown,
        initial='國立臺灣大學',
    )
    student_id = models.StringField(label="您的學號")
    id_number = models.StringField(label="您的身份證字號")
    address = models.StringField(label="您的戶籍地址（含鄰里，需與身分證一致）")
    is_foreign = models.StringField(
        label="您是否為外籍生？",
        choices=[('是', '是'), ('否', '否')],
        widget=widgets.RadioSelect
    )
    arc = models.StringField(label="居留證號碼", blank=True)
    passport = models.StringField(label="護照號碼", blank=True)
    nation = models.StringField(label="國籍", blank=True)
    stay = models.StringField(
        label="是否在台滿 183 天",
        choices=[('是', '是'), ('否', '否')],
        widget=widgets.RadioSelect,
        blank=True
    )

    @staticmethod
    def calculate_payment_info(player):
        participant = player.participant
        session = player.session
        
        # 報酬來自 control 與 carbon 兩部分
        control = participant.vars.get("control_summary", {})
        tax = participant.vars.get("carbon_tax_summary", {})
        trade = participant.vars.get("carbon_trade_summary", {})
        
        total_profit = control.get("profit", cu(50)) + tax.get("profit", cu(60)) + trade.get("profit", cu(70))
        total_emission = control.get("emission", 12) + tax.get("emission", 11) + trade.get("emission", 13)
        total_group_emission = control.get("group_emission", 50) + tax.get("group_emission", 30) + trade.get("group_emission", 80)
        real_emission = total_group_emission * session.config.get("carbon_real_world_rate", 0.1)

        # 使用 cu() 包裝，才能使用 oTree 的貨幣轉換方法
        real_payoff = cu(total_profit).to_real_world_currency(session)
        participation_fee = session.config.get("participation_fee", 0)
        total_payment = int(round(real_payoff + participation_fee))

        return {
            'control': control,
            'tax': tax,
            'trade': trade,
            'total_profit': total_profit,
            'total_emission': total_emission,
            'total_group_emission': total_group_emission,
            'real_emission': real_emission,
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
            control_profit=info['control'].get("profit", cu(50)),
            tax_profit=info['tax'].get("profit", cu(60)),
            trade_profit=info['trade'].get("profit", cu(70)),
            total_profit=info['total_profit'],
            total_profit_formatted=f"{info['total_profit']:,.0f} 法幣",
            total_emission_formatted=f"{info['total_emission']:.0f} 單位碳排",
            total_group_emission_formatted=f"{info['total_group_emission']:.0f} 單位碳排",
            real_emission_formatted=f"{info['real_emission']:.0f} 公噸 CO₂e",
            real_payoff_formatted=f"{info['real_payoff']:,.0f} 元",
            participation_fee=int(info['participation_fee']),
            total_payment_formatted=f"{info['total_payment']:,.0f} 元",
            completion_code=Constants.completion_code
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        info = Player.calculate_payment_info(player)
        player.payoff = cu(info['total_profit'])  # 必須是 cu() 才會統計進 payoff
        player.total_payment = info['total_payment']
        player.group.real_emission = info['real_emission']

class BasicInfo(Page):
    form_model = 'player'
    form_fields = [
        'name',
        'school',
        'student_id',
        'id_number',
        'address',
        'is_foreign',
        'arc',
        'passport',
        'nation',
        'stay'
    ]

    @staticmethod
    def error_message(player: Player, values):
        if len(values['student_id']) != 9:
            return '學號長度不正確'
        if not values['student_id'][0].isalpha():
            return '學號第 1 碼應為英文字母'
        if not values['student_id'][1:2].isnumeric():
            return '學號格式不正確'
        if not values['student_id'][4:8].isnumeric():
            return '學號格式不正確'
        if len(values['id_number']) != 10:
            return '身份證字號長度不正確'
        if not values['id_number'][0].isalpha():
            return '身份證字號第 1 碼應為英文字母'
        if not values['id_number'][1:9].isnumeric():
            return '身份證字號格式不正確'
        if values['is_foreign'] == '是':
            if not values['arc']:
                return '請填寫居留證號碼'
            if not values['passport']:
                return '請填寫護照號碼'
            if not values['nation']:
                return '請填寫國籍'
            if not values['stay']:
                return '請選擇是否在台滿 183 天'

class WaitForInstruction(Page):
    pass

page_sequence = [PaymentInfo, BasicInfo, WaitForInstruction]
