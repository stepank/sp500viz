from invesment_strategies import *


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


class SimulationRunner:

    initial_balance: float
    annual_contributions: float
    dividend_tax_rate_percent: float
    asset_configs: AssetConfigs

    def __init__(self, initial_balance: float, annual_contributions: float, dividend_tax_rate_percent: float, asset_configs: AssetConfigs) -> None:
        self.initial_balance = initial_balance
        self.annual_contributions = annual_contributions
        self.dividend_tax_rate_percent = dividend_tax_rate_percent
        self.asset_configs = asset_configs

    def run_simulation(self, data, skip_rows: int, investment_years: int, investment_strategy: InvestmentStrategy):

        prev_cpi = None
        asset_results = AssetResults()

        portfolio = Portfolio(self.initial_balance)

        for year_index in range(investment_years + 1):

            data_index = skip_rows + year_index * 12
            row = data.iloc[data_index]

            this_date = row['date']
            cpi = row['cpi']

            asset_results = AssetResults(
                sp500=AssetResult(row['sp500_index'], row['sp500_dividend']),
                vbmfx=AssetResult(row['vbmfx_price'], row['vbmfx_dividend']),
            )

            if year_index == 0:
                first_date = this_date

            if this_date.month != first_date.month:
                raise Exception(f'Current month ({this_date}) is not the same as the first month ({first_date})')

            if year_index == 0:
                investment_strategy.start_investing(portfolio, asset_results)
            else:
                self._collect_dividends_and_pay_devidend_taxes(portfolio, asset_results)
                self._pay_all_fees(portfolio)
                portfolio.cash += self.annual_contributions
                investment_strategy.execute(year_index, investment_years, portfolio, asset_results)
                self._apply_inflation(portfolio, prev_cpi / cpi)

            prev_cpi = cpi

        return dict(first_date=first_date, final_balance=self._summarize(portfolio, asset_results))

    def _collect_dividends_and_pay_devidend_taxes(self, portfolio: Portfolio, results: AssetResults) -> None:

        for label, position in portfolio.items():
            result = results.get(label)
            if result and not result.is_empty:
                dividends = position.count * result.dividends
                dividends_post_tax = dividends * (100 - self.dividend_tax_rate_percent) / 100
                portfolio.cash += dividends_post_tax
                config = self.asset_configs[label]
                if config.accumulate_dividens:
                    portfolio.buy(label, dividends_post_tax, results)

    def _pay_all_fees(self, portfolio: Portfolio) -> None:
        for label, position in portfolio.items():
            position.count *= (100 - self.asset_configs[label].fees_percent) / 100

    def _apply_inflation(self, portfolio: Portfolio, inflation_q) -> None:
        for position in portfolio.values():
           position.count *= inflation_q

    @staticmethod
    def _summarize(portfolio: Portfolio, results: AssetResults) -> float:
        balance = 0.0
        for label, position in portfolio.items():
            result = results.get(label)
            if result and not result.is_empty:
                balance += position.count * result.price
        return balance
