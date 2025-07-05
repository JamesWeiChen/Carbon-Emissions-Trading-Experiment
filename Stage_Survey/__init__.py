from otree.api import *

doc = """
Your app description
"""


class Constants(BaseConstants):
    name_in_url = 'Survey_U'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):

    name = models.StringField(label="您的名字")
    student_id = models.StringField(label="您的學號")
    id_number = models.StringField(label="您的身份證字號")
    address = models.StringField(label="您的戶籍地址 （ 鄰里也需要填，請確保每一字都與身分證上的地址完全一致 ）", )
    address_code = models.StringField(label="戶籍地址郵遞區號（3碼即可） ，若需查詢，填答表格下方網址為郵遞區號查詢網站。", )

    gender = models.IntegerField(
        choices=[[0, '女'], [1, '男'], ],
        label="1. 您的性別",
        widget=widgets.RadioSelect,
        required=True
    )

    age = models.IntegerField(label='2. 您的年齡是：', min=1, max=99, required=True)

    grade = models.IntegerField(
        choices=[['0', '大學部 1 年級'], ['1', '大學部 2 年級'], ['2', '大學部 3 年級'], ['3', '大學部 4 年級'], ['4', '大學部 5 年級以上'],
                 ['5', '碩士班學生'], ['6', '博士班學生'], ],
        label='3. 您的系級',
        widget=widgets.RadioSelect,
        required=True
    )

    principle = models.BooleanField(
        choices=[['True', '是'], ['False', '否']],
        label='4. 您是否修過大一經濟學（如：經濟學原理、個體經濟學原理與實習、總體經濟學原理與實習等...）？',
        widget=widgets.RadioSelect,
        required=True
    )

    principle_2 = models.BooleanField(
        choices=[['True', '是'], ['False', '否']],
        label='5. 您是否修過大二經濟學（如：個體經濟學一、個體經濟學二、總體經濟學一、總體經濟學二等...）？',
        widget=widgets.RadioSelect,
        required=True
    )

    theory = models.BooleanField(
        choices=[['True', '是'], ['False', '否']],
        label='6. 您是否修過碩博士班經濟學（如：個體經濟理論一、個體經濟理論二等...）？',
        widget=widgets.RadioSelect,
        required=True
    )

    game = models.BooleanField(
        label= "7. 您是否修過賽局相關課程，包含線上課程（如：賽局論、應用賽局理論、賽局實證分析等...）？",
        choices=[
            ['True', '是'], ['False', '否']],
        widget=widgets.RadioSelect,
        required=True
    )

    exp = models.BooleanField(
        label= "8. 您是否修過實驗經濟學相關課程，包含線上課程（如：實驗經濟學專題、行為賽局論等...）？",
        choices=[
            ['True', '是'], ['False', '否']],
        widget=widgets.RadioSelect,
        required=True
    )

    # Q9 = models.IntegerField(
    #     label='9. 在第一部份實驗中，當您是第一階段被選中的 4 人時，您採取什麼樣的選擇策略？',
    #     choices=[
    #         [0, '固定選擇報酬為 12 的選項 '],
    #         [1, '固定選擇報酬為 5 的選項 '],
    #         [2, '固定選擇報酬為 2 的選項 '],
    #         [3, '固定在報酬為 12 的選項與報酬為 5 的選項之間隨機選擇 '],
    #         [4, '固定在報酬為 12 的選項與報酬為 2 的選項之間隨機選擇 '],
    #         [5, '固定在報酬為 5 的選項與報酬為 2 的選項之間隨機選擇 '],
    #         [6, '在報酬為 12、5、2 的三個選項之間隨機選擇'],
    #         [7, '其他'], ],
    #     widget=widgets.RadioSelect, )
    # Q9_o = models.LongStringField(
    #     label='若選擇「其他」，請簡述您採取甚麼樣的選擇策略？',
    #     blank=True)

    #因為要能複選所以改用 Boolean 寫法
    # A5_1 = models.BooleanField(blank=True)
    # A5_2 = models.BooleanField(blank=True)
    # A5_3 = models.BooleanField(blank=True)
    # A5_4 = models.BooleanField(blank=True)
    # A5_5 = models.BooleanField(blank=True)
    # A5_6 = models.BooleanField(blank=True)
    # A5_7 = models.BooleanField(blank=True)

    Q9_1 = models.IntegerField(
        label="9-1. 在第一部份實驗中，當您是第二階段剩餘的 8 人且您看到報酬為 12 的選項是唯一最多人選擇時，您採取什麼樣的選擇策略？",
        choices=[
            [0, ' 選擇報酬為 12 的選項 '],
            [1, ' 選擇報酬為 5 的選項 '],
            [2, ' 選擇報酬為 2 的選項 '],
            [3, ' 其他 ']
        ],
        widget=widgets.RadioSelect, )
    Q9_1_o = models.LongStringField(
        label='若選擇「其他」，請簡述您採取甚麼樣的選擇策略？',
        blank=True)

    # A6_1 = models.BooleanField(blank=False)
    # A6_2 = models.BooleanField(blank=False)
    # A6_3 = models.BooleanField(blank=False)
    # A6_4 = models.BooleanField(blank=False)
    # A6_5 = models.BooleanField(blank=False)
    # A6_6 = models.BooleanField(blank=False)
    # A6_7 = models.BooleanField(blank=False)
    # A6_8 = models.BooleanField(blank=False)
    #

    Q9_2 = models.IntegerField(
        label="9-2. 在第一部份實驗中，當您是第二階段剩餘的 8 人且您看到報酬為 12 的選項與報酬為 5 的選項並列最多人選擇時，您採取什麼樣的選擇策略？",
        choices=[
            [0, ' 選擇報酬為 12 的選項 '],
            [1, ' 選擇報酬為 5 的選項 '],
            [2, ' 選擇報酬為 2 的選項 '],
            [3, ' 在報酬為 12 與 5 的選項之間隨機選擇 '],
            [4, ' 其他 ']
        ],
        widget=widgets.RadioSelect, )
    Q9_2_o = models.LongStringField(
        label='若選擇「其他」，請簡述您採取甚麼樣的選擇策略？',
        blank=True)

    Q9_3 = models.IntegerField(
        label="9-3. 在第一部份實驗中，當您是第二階段剩餘的 8 人且您看到報酬為 12 的選項與報酬為 2 的選項並列最多人選擇時，您採取什麼樣的選擇策略？",
        choices=[
            [0, ' 選擇報酬為 12 的選項 '],
            [1, ' 選擇報酬為 5 的選項 '],
            [2, ' 選擇報酬為 2 的選項 '],
            [3, ' 在報酬為 12 與 2 的選項之間隨機選擇 '],
            [4, ' 其他 ']
        ],
        widget=widgets.RadioSelect, )
    Q9_3_o = models.LongStringField(
        label='若選擇「其他」，請簡述您採取甚麼樣的選擇策略？',
        blank=True)

    # A7_1 = models.BooleanField(blank=False)
    # A7_2 = models.BooleanField(blank=False)
    # A7_3 = models.BooleanField(blank=False)
    # A7_4 = models.BooleanField(blank=False)
    # A7_5 = models.BooleanField(blank=False)
    # A7_6 = models.BooleanField(blank=False)
    # A7_7 = models.BooleanField(blank=False)
    # A7_8 = models.BooleanField(blank=False)
    # A7_9 = models.BooleanField(blank=False)
    # A7_10 = models.BooleanField(blank=False)
    # A7_11 = models.BooleanField(blank=False)
    # A7_12 = models.BooleanField(blank=False)

    # Q10_4 = models.IntegerField(
    #     label="10-4. 在第一部份實驗中，當您是第二階段剩餘的 8 人且您看到報酬為 12 的選項、報酬為 9 的選項、與報酬為 2 的選項，三個選項並列最多人選擇時，您採取什麼樣的選擇策略？",
    #     choices=[
    #         [0, ' 選擇報酬為 12 的選項 '],
    #         [1, ' 選擇報酬為 9 的選項 '],
    #         [2, ' 選擇報酬為 2 的選項 '],
    #         [3, ' 在報酬為 12、9、2 的三個選項之間隨機選擇 '],
    #         [4, ' 其他 ']
    #     ],
    #     widget=widgets.RadioSelect, )
    # Q10_4_o = models.LongStringField(
    #     label='若選擇「其他」，請簡述您採取甚麼樣的選擇策略？',
    #     blank=True)

    Q10 = models.IntegerField(
        label="10. 在第二部份實驗中，您採取什麼樣的選擇策略？",
        choices=[
            [0, ' 固定選擇報酬為 12 的選項 '],
            [1, ' 固定選擇報酬為 5 的選項 '],
            [2, ' 固定選擇報酬為 2 的選項 '],
            [3, ' 固定在報酬為 12 與報酬為 5 的選項之間隨機選擇 '],
            [4, ' 固定在報酬為 12 與報酬為 2 的選項之間隨機選擇 '],
            [5, ' 固定在報酬為 5 與報酬為 2 的選項之間隨機選擇 '],
            [6, ' 在報酬為 12、5、2 三個選項之間隨機選擇 '],
            [7, ' 其他 '], ],
        widget=widgets.RadioSelect, )
    Q10_o = models.LongStringField(
        label="若選擇「其他」，請簡述您會採取甚麼樣的選擇策略？",
        blank=True)


# PAGES
class Page1(Page):
    form_model = 'player'
    form_fields = ['gender', 'age', 'grade', 'principle', 'principle_2', 'theory', 'game', 'exp', ]


class Page2(Page):
    form_model = 'player'
    form_fields = ['Q9_1', 'Q9_1_o', 'Q9_2', 'Q9_2_o', 'Q9_3', 'Q9_3_o', 'Q10', 'Q10_o', ]


class BasicInfo(Page):
    form_model = 'player'
    form_fields = ['name', 'student_id', 'id_number', 'address', 'address_code']

    @staticmethod
    def error_message(player: Player, values):
        print('value is', values)
        if len(values['student_id']) != 9:
            return '學號長度不正確'
        elif not values['student_id'][0].isalpha():
            return '學號第 1 碼應為英文字母'
        elif not values['student_id'][1:2].isnumeric():
            return '學號格式不正確'
        elif not values['student_id'][4:8].isnumeric():
            return '學號格式不正確'

        if len(values['id_number']) != 10:
            return '身份證字號長度不正確'
        elif not values['id_number'][0].isalpha():
            return '身份證字號第 1 碼應為英文字母'
        elif not values['id_number'][1:9].isnumeric():
            return '身份證字號格式不正確'

        if len(values['address_code']) != 3:
            return '戶籍地址郵遞區號長度不正確'


class Bye(Page):
    pass


page_sequence = [BasicInfo, Page1, Page2, Bye]
