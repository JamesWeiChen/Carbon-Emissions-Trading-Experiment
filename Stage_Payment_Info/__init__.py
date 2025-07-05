from otree.api import *

doc = """
顯示最終報酬與排放資訊，並產生完成代碼。
"""

class Constants(BaseConstants):
    name_in_url = 'payment_info'
    players_per_group = None
    num_rounds = 1
    completion_code = '273940'

    # 定義乘數（若需乘法運算）
    MULTIPLIER1 = 12
    MULTIPLIER2 = 5
    MULTIPLIER3 = 2


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    pass


# PAGES
class PaymentInfo(Page):
    def vars_for_template(player: Player):
        participant = player.participant
        treatment = player.session.config.get("treatment", "tax")  # 預設為 tax 組

        # 取出各組報酬資訊
        control = participant.vars.get("control_summary", {})
        carbon = {}
        if treatment == "trade":
            carbon = participant.vars.get("carbon_trade_summary", {})
        elif treatment == "tax":
            carbon = participant.vars.get("carbon_tax_summary", {})

        # 計算總報酬
        total_profit = control.get("profit", 0) + carbon.get("profit", 0)
        total_emission = control.get("emission", 0) + carbon.get("emission", 0)
        total_group_emission = control.get("group_emission", 0) + carbon.get("group_emission", 0)

        particpipant.profit = total_profit

        # 格式化後給 template 用
        return dict(
            control_profit=control.get("profit", 0),
            carbon_profit=carbon.get("profit", 0),
            total_profit=total_profit,
            total_profit_formatted=f"{total_profit:,.0f} 法幣",
            total_emission_formatted=f"{total_emission:.1f} 噸 CO₂",
            total_group_emission_formatted=f"{total_group_emission:.1f} 噸 CO₂"
        )

page_sequence = [PaymentInfo]
