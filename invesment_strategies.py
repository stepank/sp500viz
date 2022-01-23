import math

from datetime import datetime, timedelta
from typing import Optional

cash = 'cash'
sp500 = 'sp500'
vbmfx = 'vbmfx'


class AssetResult:

    price: float
    dividends: float

    def __init__(self, price: float, dividends: float) -> None:
        self.price = price
        self.dividends = dividends

    @property
    def is_empty(self):
        return math.isnan(self.price) or math.isnan(self.dividends)


class AssetResults(dict[str, AssetResult]):

    def __init__(self, **kwargs) -> None:
        kwargs.update({cash: AssetResult(1, 0)})
        super().__init__(kwargs)


class Position:

    count: float

    def __init__(self, count: float) -> None:
        self.count = count

    def get_dividends(self, portfoliresult: AssetResult) -> float:
        raise NotImplementedError('pay_dividends')

    def get_value(self, result: AssetResult) -> float:
        raise NotImplementedError('get_value')

    def get_maturity(self, this_date: datetime) -> Optional[float]:
        raise NotImplementedError('get_maturity')


class EquityPosition(Position):

    def get_dividends(self, result: AssetResult) -> float:
        return self.count * result.dividends

    def get_value(self, result: AssetResult) -> float:
        return self.count * result.price

    def get_maturity(self, this_date: datetime) -> Optional[float]:
        return None


class BondPosition(Position):

    start_date: datetime
    marurity_date: datetime
    rate_percet: float

    def __init__(self, count: float, start_date: datetime, time_to_maturity: timedelta, rate_percent: float) -> None:
        super().__init__(count)
        self.start_date = start_date
        self.marurity_date = start_date + time_to_maturity
        self.time_to_maturity = time_to_maturity
        self.rate_percent = rate_percent

    def get_dividends(self, result: AssetResult) -> float:
        return self.count * self.rate_percent / 100

    def get_value(self, result: AssetResult) -> float:
        raise NotImplementedError('get_value')

    def get_maturity(self, this_date: datetime) -> Optional[float]:
        if this_date >= self.marurity_date:
            return self.count
        return None


class Portfolio(dict[str, Position]):

    def __init__(self, initial_balance: float):
        self.init_position(cash, initial_balance)

    def _cash(self) -> float:
        return self[cash].count

    def _set_cash(self, value: float) -> None:
        assert value >= -0.000001
        self[cash].count = value

    cash = property(_cash, _set_cash)

    def init_position(self, label, value=0):
        assert value >= 0
        self.setdefault(label, Position(value))

    def buy(self, label: str, value: float, results: AssetResults):
        assert value >= 0
        self.init_position(label)
        self[label].count += value / results[label].price
        self.cash -= value
        assert self.cash >= -0.000001

    def sell(self, label: str, value: float, results: AssetResults):
        assert value >= 0
        self[label].count -= value / results[label].price
        assert self[label].count >= -0.000001
        self.cash += value


class InvestmentStrategy:

    def start_investing(self, portfolio: Portfolio, results: AssetResults) -> None:
        pass

    def execute(self, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:
        raise NotImplementedError('execute')


class Sp500Strategy(InvestmentStrategy):

    def start_investing(self, portfolio: Portfolio, results: AssetResults) -> None:
        self.execute(0, 100, portfolio, results)

    def execute(self, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:
        portfolio.buy(sp500, portfolio.cash, results)


def fixed_target_sp500_percent(target_sp500_percent: float):
    def get_target_sp500_percent(year_index, investment_years):
        return target_sp500_percent
    return get_target_sp500_percent


def linearly_changing_target_sp500_percent(target_sp500_percent_start: float, target_sp500_percent_end: float):
    def get_target_sp500_percent(year_index, investment_years):
        return \
            target_sp500_percent_start \
            + (target_sp500_percent_end - target_sp500_percent_start) * (year_index / investment_years)
    return get_target_sp500_percent


class Sp500AndVbmfxStrategyWoSelling(InvestmentStrategy):

    def __init__(self, get_target_sp500_percent):
        self.get_target_sp500_percent = get_target_sp500_percent
        self.sp500_strategy = Sp500Strategy()

    def start_investing(self, portfolio: Portfolio, results: AssetResults) -> None:

        if results[vbmfx].is_empty:
            self.sp500_strategy.start_investing(portfolio, results)
            portfolio.init_position(vbmfx)
            return

        target_sp500_percent = self.get_target_sp500_percent(0, 100)
        portfolio.buy(sp500, portfolio.cash * target_sp500_percent / 100, results)
        portfolio.buy(vbmfx, portfolio.cash * (100 - target_sp500_percent) / 100, results)

    def execute(self, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:

        if results[vbmfx].is_empty:
            self.sp500_strategy.execute(0, 100, portfolio, results)
            return

        sp500_balance = portfolio[sp500].count * results[sp500].price
        vbmfx_balance = portfolio[vbmfx].count * results[vbmfx].price
        sp500_percent = sp500_balance / (sp500_balance + vbmfx_balance) * 100
        target_sp500_percent = self.get_target_sp500_percent(year_index, investment_years)
        if sp500_percent <= target_sp500_percent:
            portfolio.buy(sp500, portfolio.cash, results)
        else:
            portfolio.buy(vbmfx, portfolio.cash, results)


class Sp500AndVbmfxStrategyWithSelling(InvestmentStrategy):

    def __init__(self, get_target_sp500_percent):
        self.get_target_sp500_percent = get_target_sp500_percent
        self.sp500_strategy = Sp500Strategy()

    def start_investing(self, portfolio: Portfolio, results: AssetResults) -> None:

        if results[vbmfx].is_empty:
            self.sp500_strategy.start_investing(portfolio, results)
            portfolio.init_position(vbmfx)
            return

        target_sp500_percent = self.get_target_sp500_percent(0, 100)
        portfolio.buy(sp500, portfolio.cash * target_sp500_percent / 100, results)
        portfolio.buy(vbmfx, portfolio.cash * (100 - target_sp500_percent) / 100, results)

    def execute(self, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:

        if results[vbmfx].is_empty:
            self.sp500_strategy.execute(0, 100, portfolio, results)
            return

        sp500_balance = portfolio[sp500].count * results[sp500].price
        vbmfx_balance = portfolio[vbmfx].count * results[vbmfx].price
        final_balance = sp500_balance + vbmfx_balance + portfolio.cash
        target_sp500_percent = self.get_target_sp500_percent(year_index, investment_years)
        target_sp500_balance = final_balance * target_sp500_percent / 100
        target_vbmfx_balance = final_balance - target_sp500_balance
        if target_sp500_balance <= sp500_balance:
            portfolio.buy(vbmfx, portfolio.cash, results)
            sell_amount = sp500_balance - target_sp500_balance
            portfolio.sell(sp500, sell_amount, results)
            portfolio.buy(vbmfx, sell_amount, results)
        elif target_vbmfx_balance <= vbmfx_balance:
            portfolio.buy(sp500, portfolio.cash, results)
            sell_amount = vbmfx_balance - target_vbmfx_balance
            portfolio.sell(vbmfx, sell_amount, results)
            portfolio.buy(sp500, sell_amount, results)
        else:
            portfolio.buy(vbmfx, target_vbmfx_balance - vbmfx_balance, results)
            portfolio.buy(sp500, target_sp500_balance - sp500_balance, results)


class FixedPercentStrategy(InvestmentStrategy):

    percent: float

    def __init__(self, percent) -> None:
        self.percent = percent

    def execute(self, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:
        portfolio.cash *= 1 + self.percent / 100
