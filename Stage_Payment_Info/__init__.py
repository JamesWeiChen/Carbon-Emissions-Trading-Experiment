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
    pass


class Player(BasePlayer):
    pass


# PAGES
class PaymentInfo(Page):
    def vars_for_template(player: Player):
        participant = player.participant
        session = player.session
        treatment = session.config.get("treatment", "tax")  # 預設為 tax 組

        # 取出各組報酬資訊
        control = participant.vars.get("control_summary", {})
        carbon = {}
        if treatment == "trade":
            carbon = participant.vars.get("carbon_trade_summary", {})
        elif treatment == "tax":
            carbon = participant.vars.get("carbon_tax_summary", {})

        # 計算總實驗報酬（實驗幣）
        total_profit = control.get("profit", 0) + carbon.get("profit", 0)
        total_emission = control.get("emission", 0) + carbon.get("emission", 0)
        total_group_emission = control.get("group_emission", 0) + carbon.get("group_emission", 0)

        # 寫入 player.payoff（重要！讓 oTree 自動統計報酬）
        player.payoff = total_profit

        # 轉換為真錢
        real_payoff = player.payoff.to_real_world_currency(session)
        participation_fee = session.config.get("participation_fee", 0)
        total_payment = real_payoff + participation_fee

        return dict(
            control_profit=control.get("profit", 0),
            carbon_profit=carbon.get("profit", 0),
            total_profit=total_profit,
            total_profit_formatted=f"{total_profit:,.0f} 法幣",
            total_emission_formatted=f"{total_emission:.1f} 噸 CO₂",
            total_group_emission_formatted=f"{total_group_emission:.1f} 噸 CO₂",
            real_payoff_formatted=f"{real_payoff:,.0f} 元",
            participation_fee = int(player.session.config.get('participation_fee', 0)),
            total_payment_formatted=f"{total_payment:,.0f} 元",
            completion_code=Constants.completion_code
        )



page_sequence = [PaymentInfo, WaitForInstruction]
