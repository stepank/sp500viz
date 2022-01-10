import math

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
    pass


class Position:

    count: float

    def __init__(self, count: float) -> None:
        self.count = count


class Portfolio(dict[str, Position]):

    def __init__(self, initial_balance: float):
        self.init_position(cash, initial_balance)

    def cash(self):
        return self[cash].count

    def set_cash(self, value: float):
        assert value >= -0.000001
        self[cash].count = value

    cash = property(cash, set_cash)

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

    def start_investing(self, portfolio: Portfolio, results: AssetResults):
        pass

    def execute(self, portfolio: Portfolio, results: AssetResults):
        raise NotImplementedError('execute')


class Sp500Strategy(InvestmentStrategy):

    def start_investing(self, portfolio: Portfolio, results: AssetResults):
        self.execute(portfolio, results)

    def execute(self, portfolio: Portfolio, results: AssetResults):
        portfolio.buy(sp500, portfolio.cash, results)


class Sp500AndVbmfxStrategyWoSelling(InvestmentStrategy):

    target_sp500_percent: float

    def __init__(self, target_sp500_percent: float):
        self.target_sp500_percent = target_sp500_percent
        self.sp500_strategy = Sp500Strategy()

    def start_investing(self, portfolio: Portfolio, results: AssetResults):

        if results[vbmfx].is_empty:
            self.sp500_strategy.start_investing(portfolio, results)
            portfolio.init_position(vbmfx)
            return

        portfolio.buy(sp500, portfolio.cash * self.target_sp500_percent / 100, results)
        portfolio.buy(vbmfx, portfolio.cash * (100 - self.target_sp500_percent) / 100, results)

    def execute(self, portfolio: Portfolio, results: AssetResults):

        if results[vbmfx].is_empty:
            self.sp500_strategy.execute(portfolio, results)
            return

        sp500_balance = portfolio[sp500].count * results[sp500].price
        vbmfx_balance = portfolio[vbmfx].count * results[vbmfx].price
        sp500_percent = sp500_balance / (sp500_balance + vbmfx_balance) * 100
        if sp500_percent <= self.target_sp500_percent:
            portfolio.buy(sp500, portfolio.cash, results)
        else:
            portfolio.buy(vbmfx, portfolio.cash, results)


class Sp500AndVbmfxStrategyWithSelling(InvestmentStrategy):

    target_sp500_percent: float

    def __init__(self, target_sp500_percent: float):
        self.target_sp500_percent = target_sp500_percent
        self.sp500_strategy = Sp500Strategy()

    def start_investing(self, portfolio: Portfolio, results: AssetResults):

        if results[vbmfx].is_empty:
            self.sp500_strategy.start_investing(portfolio, results)
            portfolio.init_position(vbmfx)
            return

        portfolio.buy(sp500, portfolio.cash * self.target_sp500_percent / 100, results)
        portfolio.buy(vbmfx, portfolio.cash * (100 - self.target_sp500_percent) / 100, results)

    def execute(self, portfolio: Portfolio, results: AssetResults):

        if results[vbmfx].is_empty:
            self.sp500_strategy.execute(portfolio, results)
            return

        sp500_balance = portfolio[sp500].count * results[sp500].price
        vbmfx_balance = portfolio[vbmfx].count * results[vbmfx].price
        final_balance = sp500_balance + vbmfx_balance + portfolio.cash
        target_sp500_balance = final_balance * self.target_sp500_percent / 100
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

    def execute(self, portfolio: Portfolio, results: AssetResults):
        portfolio.cash *= 1 + self.percent / 100
