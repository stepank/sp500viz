import math

class InvestmentStrategyState:

    def __init__(
        self,
        balance, annual_contributions,
        fees_percent, dividend_tax_rate_percent):
        self.requires_initialization = True
        self.balance = balance
        self.annual_contributions = annual_contributions
        self.fees_percent = fees_percent
        self.dividend_tax_rate_percent = dividend_tax_rate_percent
        self.sp500_count = 0
        self.vbmfx_count = 0
        self.prev_sp500_index = None
        self.sp500_index = None
        self.sp500_dividend = None
        self.prev_vbmfx_price = None
        self.vbmfx_price = None
        self.vbmfx_dividend = None


def sp500_strategy(state):

    if state.requires_initialization:
        state.sp500_count = state.balance / state.sp500_index
        return

    # dividend
    my_dividend = state.sp500_count * state.sp500_dividend
    my_dividend_post_tax = my_dividend * (1 - state.dividend_tax_rate_percent / 100)
    state.sp500_count += my_dividend_post_tax / state.sp500_index

    # fees
    state.sp500_count *= (100 - state.fees_percent) / 100

    # annual contributions
    state.sp500_count += state.annual_contributions / state.sp500_index

    state.balance = state.sp500_count * state.sp500_index


def sp500_and_bonds_strategy_wo_selling(target_equities_percent):
    def investment_strategy(state):

        if math.isnan(state.vbmfx_price) or math.isnan(state.vbmfx_dividend):
            sp500_strategy(state)
            return

        if state.requires_initialization:
            state.sp500_count = state.balance * target_equities_percent / 100 / state.sp500_index
            state.vbmfx_count = state.balance * (100 - target_equities_percent) / 100 / state.vbmfx_price
            return

        # dividend
        my_sp500_dividend = state.sp500_count * state.sp500_dividend
        my_sp500_dividend_post_tax = my_sp500_dividend * (1 - state.dividend_tax_rate_percent / 100)
        state.sp500_count += my_sp500_dividend_post_tax / state.sp500_index
        my_vbmfx_dividend = state.vbmfx_count * state.vbmfx_dividend
        my_vbmfx_dividend_post_tax = my_vbmfx_dividend * (1 - state.dividend_tax_rate_percent / 100)
        state.vbmfx_count += my_vbmfx_dividend_post_tax / state.sp500_index

        # fees
        state.sp500_count *= (100 - state.fees_percent) / 100
        state.vbmfx_count *= (100 - state.fees_percent) / 100

        # annual contributions
        sp500_balance = state.sp500_count * state.sp500_index
        vbmfx_balance = state.vbmfx_count * state.vbmfx_price
        equities_percent = sp500_balance / (sp500_balance + vbmfx_balance) * 100
        if equities_percent <= target_equities_percent:
            state.sp500_count += state.annual_contributions / state.sp500_index
        else:
            state.vbmfx_count += state.annual_contributions / state.vbmfx_price

        state.balance = state.sp500_count * state.sp500_index + state.vbmfx_count * state.vbmfx_price

    return investment_strategy


def sp500_and_bonds_strategy_with_selling(target_equities_percent):
    def investment_strategy(state):

        if math.isnan(state.vbmfx_price) or math.isnan(state.vbmfx_dividend):
            sp500_strategy(state)
            return

        if state.requires_initialization:
            state.sp500_count = state.balance * target_equities_percent / 100 / state.sp500_index
            state.vbmfx_count = state.balance * (100 - target_equities_percent) / 100 / state.vbmfx_price
            return

        # dividend
        my_sp500_dividend = state.sp500_count * state.sp500_dividend
        my_sp500_dividend_post_tax = my_sp500_dividend * (1 - state.dividend_tax_rate_percent / 100)
        state.sp500_count += my_sp500_dividend_post_tax / state.sp500_index
        my_vbmfx_dividend = state.vbmfx_count * state.vbmfx_dividend
        my_vbmfx_dividend_post_tax = my_vbmfx_dividend * (1 - state.dividend_tax_rate_percent / 100)
        state.vbmfx_count += my_vbmfx_dividend_post_tax / state.sp500_index

        # fees
        state.sp500_count *= (100 - state.fees_percent) / 100
        state.vbmfx_count *= (100 - state.fees_percent) / 100

        # annual contributions
        sp500_balance = state.sp500_count * state.sp500_index
        vbmfx_balance = state.vbmfx_count * state.vbmfx_price
        final_balance = sp500_balance + vbmfx_balance + state.annual_contributions
        target_sp500_balance = final_balance * target_equities_percent / 100
        target_vbmfx_balance = final_balance - target_sp500_balance

        if target_sp500_balance <= sp500_balance:
            state.vbmfx_count += state.annual_contributions / state.vbmfx_price
            sell_amount = sp500_balance - target_sp500_balance
            state.vbmfx_count += sell_amount / state.vbmfx_price
            state.sp500_count -= sell_amount / state.sp500_index
        elif target_vbmfx_balance <= vbmfx_balance:
            state.sp500_count += state.annual_contributions / state.sp500_index
            sell_amount = vbmfx_balance - target_vbmfx_balance
            state.sp500_count += sell_amount / state.sp500_index
            state.vbmfx_count -= sell_amount / state.vbmfx_price
        else:
            state.vbmfx_count += (target_vbmfx_balance - vbmfx_balance) / state.vbmfx_price
            state.sp500_count += (target_sp500_balance - sp500_balance) / state.sp500_index

        state.balance = state.sp500_count * state.sp500_index + state.vbmfx_count * state.vbmfx_price

        assert state.balance - final_balance < 0.000001

    return investment_strategy


def fixed_percent_strategy(percent):
    def strategy(state):
        if state.requires_initialization:
            return
        state.balance += state.annual_contributions
        state.balance *= 1 + percent / 100
    return strategy
