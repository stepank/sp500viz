import math
import numpy_financial as npf

from datetime import datetime, timedelta
from typing import List, Optional

cash = 'cash'
sp500 = 'sp500'
vbmfx = 'vbmfx'
tb10y = 'tb10y'


class AssetConfig:

    fees_percent: float
    accumulate_dividens: bool

    def __init__(self, fees_percent: float, accumulate_dividens: bool):
        self.fees_percent = fees_percent
        self.accumulate_dividens = accumulate_dividens


class AssetConfigs(dict[str, AssetConfig]):

    def __init__(self, configs):
        configs[cash] = AssetConfig(0, accumulate_dividens=False)
        super().__init__(configs)


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

    def get_dividends(self, result: Optional[AssetResult]) -> float:
        raise NotImplementedError('pay_dividends')

    def get_value(self, this_date: datetime, result: Optional[AssetResult]) -> float:
        raise NotImplementedError('get_value')

    def get_maturity(self, this_date: datetime) -> Optional[float]:
        raise NotImplementedError('get_maturity')

    def buy(self, this_date: datetime, value: float, result: AssetResult) -> None:
        raise NotImplementedError('buy')

    def sell(self, this_date: datetime, value: float, result: AssetResult) -> None:
        raise NotImplementedError('sell')

    def pay_fees(self) -> None:
        raise NotImplementedError('sell')


class CashPosition(Position):

    count: float

    def __init__(self, count: float):
        self.count = count

    def get_dividends(self, result: Optional[AssetResult]) -> float:
        return 0.0

    def get_value(self, this_date: datetime, result: Optional[AssetResult]) -> float:
        return self.count

    def get_maturity(self, this_date: datetime) -> Optional[float]:
        return None

    def buy(self, this_date: datetime, value: float, result: AssetResult) -> None:
        assert value >= 0
        self.count += value

    def sell(self, this_date: datetime, value: float, result: AssetResult) -> None:
        assert value >= 0
        self.count -= value
        assert self.count >= -0.000001

    def pay_fees(self) -> None:
        pass


class EquityPosition(Position):

    count: float
    fees_percent: float

    def __init__(self, count: float, fees_percent: float):
        self.count = count
        self.fees_percent = fees_percent

    def get_dividends(self, result: Optional[AssetResult]) -> float:
        if not result or result.is_empty:
            assert not self.count
            return 0
        return self.count * result.dividends

    def get_value(self, this_date: datetime, result: Optional[AssetResult]) -> float:
        if not result or result.is_empty:
            assert not self.count
            return 0
        return self.count * result.price

    def get_maturity(self, this_date: datetime) -> Optional[float]:
        return None

    def buy(self, this_date: datetime, value: float, result: AssetResult) -> None:
        assert value >= 0
        self.count += value / result.price

    def sell(self, this_date: datetime, value: float, result: AssetResult) -> None:
        assert value >= 0
        self.count -= value / result.price
        assert self.count >= -0.000001

    def pay_fees(self) -> None:
        self.count *= (100 - self.fees_percent) / 100


class Bond:

    face_value: float
    rate_percet: float
    start_date: datetime
    marurity_date: datetime

    def __init__(self, face_value: float, rate_percent: float, start_date: datetime, time_to_maturity: timedelta) -> None:
        self.face_value = face_value
        self.start_date = start_date
        self.marurity_date = start_date + time_to_maturity
        self.time_to_maturity = time_to_maturity
        self.rate_percent = rate_percent

    def get_dividends(self) -> float:
        return self.face_value * self.rate_percent / 100

    def get_value(self, this_date: datetime, result: AssetResult) -> float:
        time_to_maturity = self.marurity_date - this_date
        return - npf.pv(
            result.dividends / 100,
            time_to_maturity.total_seconds() * 1.0 / 3600 / 24 / 365.25,
            self.face_value * self.rate_percent / 100,
            self.face_value)

    def is_matured(self, this_date: datetime) -> bool:
        return this_date >= self.marurity_date


class Tb10yPosition(Position):

    bonds: List[Bond]

    def __init__(self) -> None:
        self.bonds = []

    def get_dividends(self, result: Optional[AssetResult]) -> float:
        if not result or result.is_empty:
            assert not self.bonds
            return 0
        return sum(bond.get_dividends() for bond in self.bonds)

    def get_value(self, this_date: datetime, result: Optional[AssetResult]) -> float:
        if not result or result.is_empty:
            assert not self.bonds
            return 0
        return sum(bond.get_value(this_date, result) for bond in self.bonds)

    def get_maturity(self, this_date: datetime) -> Optional[float]:
        matured_bonds = [bond for bond in self.bonds if bond.is_matured(this_date)]
        for bond in matured_bonds:
            self.bonds.remove(bond)
        return sum(bond.face_value for bond in matured_bonds)

    def buy(self, this_date: datetime, value: float, result: AssetResult) -> None:
        assert value >= 0
        self.bonds.append(Bond(value, result.dividends, this_date, timedelta(days=365.25 * 10)))

    def sell(self, this_date: datetime, value: float, result: AssetResult) -> None:
        sold_value = 0.0
        while sold_value < value:
            first_bond = self.bonds[0]
            first_bond_value = first_bond.get_value(this_date, result)
            remaining_to_sell = value - sold_value
            if first_bond_value < remaining_to_sell:
                self.bonds.remove(first_bond)
                sold_value += first_bond_value
            else:
                first_bond.face_value *= (1 - remaining_to_sell / first_bond_value)
                sold_value += remaining_to_sell
                assert first_bond.get_value(this_date, result) + remaining_to_sell - first_bond_value < 0.000001

    def pay_fees(self) -> None:
        pass


class Portfolio(dict[str, Position]):


    def __init__(self, initial_balance: float, configs: AssetConfigs):
        self.init_position(cash, CashPosition(initial_balance))
        self.init_position(sp500, EquityPosition(0, configs[sp500].fees_percent))
        self.init_position(vbmfx, EquityPosition(0, configs[vbmfx].fees_percent))
        self.init_position(tb10y, Tb10yPosition())

    def _cash(self) -> float:
        return self[cash].get_value(None, None)  # type: ignore

    def _set_cash(self, value: float) -> None:
        self[cash].count = value  # type: ignore

    cash = property(_cash, _set_cash)

    def init_position(self, label: str, position: Position):
        self.setdefault(label, position)

    def buy(self, this_date: datetime, label: str, value: float, results: AssetResults):
        self[label].buy(this_date, value, results[label])
        self[cash].sell(this_date, value, results[cash])

    def sell(self, this_date: datetime, label: str, value: float, results: AssetResults):
        self[label].sell(this_date, value, results[label])
        self[cash].buy(this_date, value, results[cash])


class InvestmentStrategy:

    def start_investing(self, this_date: datetime, portfolio: Portfolio, results: AssetResults) -> None:
        pass

    def execute(self, this_date: datetime, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:
        raise NotImplementedError('execute')


class Sp500Strategy(InvestmentStrategy):

    def start_investing(self, this_date: datetime, portfolio: Portfolio, results: AssetResults) -> None:
        self.execute(this_date, 0, 100, portfolio, results)

    def execute(self, this_date: datetime, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:
        portfolio.buy(this_date, sp500, portfolio.cash, results)


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

    def start_investing(self, this_date: datetime, portfolio: Portfolio, results: AssetResults) -> None:

        if results[vbmfx].is_empty:
            self.sp500_strategy.start_investing(this_date, portfolio, results)
            return

        target_sp500_percent = self.get_target_sp500_percent(0, 100)
        portfolio.buy(this_date, sp500, portfolio.cash * target_sp500_percent / 100, results)
        portfolio.buy(this_date, vbmfx, portfolio.cash, results)

    def execute(self, this_date: datetime, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:

        if results[vbmfx].is_empty:
            self.sp500_strategy.execute(this_date, 0, 100, portfolio, results)
            return

        sp500_balance = portfolio[sp500].get_value(this_date, results[sp500])
        vbmfx_balance = portfolio[vbmfx].get_value(this_date, results[vbmfx])
        sp500_percent = sp500_balance / (sp500_balance + vbmfx_balance) * 100
        target_sp500_percent = self.get_target_sp500_percent(year_index, investment_years)
        if sp500_percent <= target_sp500_percent:
            portfolio.buy(this_date, sp500, portfolio.cash, results)
        else:
            portfolio.buy(this_date, vbmfx, portfolio.cash, results)


class Sp500AndTb10yStrategyWoSelling(InvestmentStrategy):

    def __init__(self, get_target_sp500_percent):
        self.get_target_sp500_percent = get_target_sp500_percent

    def start_investing(self, this_date: datetime, portfolio: Portfolio, results: AssetResults) -> None:
        target_sp500_percent = self.get_target_sp500_percent(0, 100)
        portfolio.buy(this_date, sp500, portfolio.cash * target_sp500_percent / 100, results)
        portfolio.buy(this_date, tb10y, portfolio.cash, results)

    def execute(self, this_date: datetime, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:
        sp500_balance = portfolio[sp500].get_value(this_date, results[sp500])
        tb10y_balance = portfolio[tb10y].get_value(this_date, results[tb10y])
        sp500_percent = sp500_balance / (sp500_balance + tb10y_balance) * 100
        target_sp500_percent = self.get_target_sp500_percent(year_index, investment_years)
        if sp500_percent <= target_sp500_percent:
            portfolio.buy(this_date, sp500, portfolio.cash, results)
        else:
            portfolio.buy(this_date, tb10y, portfolio.cash, results)


class Sp500AndVbmfxStrategyWithSelling(InvestmentStrategy):

    def __init__(self, get_target_sp500_percent):
        self.get_target_sp500_percent = get_target_sp500_percent
        self.sp500_strategy = Sp500Strategy()

    def start_investing(self, this_date: datetime, portfolio: Portfolio, results: AssetResults) -> None:

        if results[vbmfx].is_empty:
            self.sp500_strategy.start_investing(this_date, portfolio, results)
            return

        target_sp500_percent = self.get_target_sp500_percent(0, 100)
        portfolio.buy(this_date, sp500, portfolio.cash * target_sp500_percent / 100, results)
        portfolio.buy(this_date, vbmfx, portfolio.cash, results)

    def execute(self, this_date: datetime, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:

        if results[vbmfx].is_empty:
            self.sp500_strategy.execute(this_date, 0, 100, portfolio, results)
            return

        sp500_balance = portfolio[sp500].get_value(this_date, results[sp500])
        vbmfx_balance = portfolio[vbmfx].get_value(this_date, results[vbmfx])
        final_balance = sp500_balance + vbmfx_balance + portfolio.cash
        target_sp500_percent = self.get_target_sp500_percent(year_index, investment_years)
        target_sp500_balance = final_balance * target_sp500_percent / 100
        target_vbmfx_balance = final_balance - target_sp500_balance
        if target_sp500_balance <= sp500_balance:
            portfolio.buy(this_date, vbmfx, portfolio.cash, results)
            sell_amount = sp500_balance - target_sp500_balance
            portfolio.sell(this_date, sp500, sell_amount, results)
            portfolio.buy(this_date, vbmfx, sell_amount, results)
        elif target_vbmfx_balance <= vbmfx_balance:
            portfolio.buy(this_date, sp500, portfolio.cash, results)
            sell_amount = vbmfx_balance - target_vbmfx_balance
            portfolio.sell(this_date, vbmfx, sell_amount, results)
            portfolio.buy(this_date, sp500, sell_amount, results)
        else:
            portfolio.buy(this_date, vbmfx, target_vbmfx_balance - vbmfx_balance, results)
            portfolio.buy(this_date, sp500, target_sp500_balance - sp500_balance, results)


class Sp500AndTb10yStrategyWithSelling(InvestmentStrategy):

    def __init__(self, get_target_sp500_percent):
        self.get_target_sp500_percent = get_target_sp500_percent

    def start_investing(self, this_date: datetime, portfolio: Portfolio, results: AssetResults) -> None:
        target_sp500_percent = self.get_target_sp500_percent(0, 100)
        portfolio.buy(this_date, sp500, portfolio.cash * target_sp500_percent / 100, results)
        portfolio.buy(this_date, tb10y, portfolio.cash, results)

    def execute(self, this_date: datetime, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:
        sp500_balance = portfolio[sp500].get_value(this_date, results[sp500])
        tb10y_balance = portfolio[tb10y].get_value(this_date, results[tb10y])
        final_balance = sp500_balance + tb10y_balance + portfolio.cash
        target_sp500_percent = self.get_target_sp500_percent(year_index, investment_years)
        target_sp500_balance = final_balance * target_sp500_percent / 100
        target_tb10y_balance = final_balance - target_sp500_balance
        if target_sp500_balance <= sp500_balance:
            portfolio.buy(this_date, tb10y, portfolio.cash, results)
            sell_amount = sp500_balance - target_sp500_balance
            portfolio.sell(this_date, sp500, sell_amount, results)
            portfolio.buy(this_date, tb10y, sell_amount, results)
        elif target_tb10y_balance <= tb10y_balance:
            portfolio.buy(this_date, sp500, portfolio.cash, results)
            sell_amount = tb10y_balance - target_tb10y_balance
            portfolio.sell(this_date, tb10y, sell_amount, results)
            portfolio.buy(this_date, sp500, sell_amount, results)
        else:
            portfolio.buy(this_date, tb10y, target_tb10y_balance - tb10y_balance, results)
            portfolio.buy(this_date, sp500, target_sp500_balance - sp500_balance, results)


class FixedPercentStrategy(InvestmentStrategy):

    percent: float

    def __init__(self, percent) -> None:
        self.percent = percent

    def execute(self, this_date: datetime, year_index: int, investment_years: int, portfolio: Portfolio, results: AssetResults) -> None:
        portfolio.cash *= 1 + self.percent / 100
