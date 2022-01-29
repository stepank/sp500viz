from invesment_strategies import *


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

        asset_results = AssetResults()

        portfolio = Portfolio(self.initial_balance, self.asset_configs)

        for year_index in range(investment_years + 1):

            data_index = skip_rows + year_index * 12
            row = data.iloc[data_index]

            this_date = row['date']
            cpi = row['cpi']

            asset_results = AssetResults(
                sp500=AssetResult(row['sp500_index'], row['sp500_dividend']),
                vbmfx=AssetResult(row['vbmfx_price'], row['vbmfx_dividend']),
                tb10y=AssetResult(100, row['bonds_10y_rate_percent'])
            )

            if year_index == 0:
                first_date = this_date
                first_cpi = cpi

            if this_date.month != first_date.month:
                raise Exception(f'Current month ({this_date}) is not the same as the first month ({first_date})')

            if year_index == 0:
                investment_strategy.start_investing(this_date, portfolio, asset_results)
            else:
                self._collect_dividends_and_pay_devidend_taxes(this_date, portfolio, asset_results)
                self._collect_maturity(this_date, portfolio)
                self._pay_all_fees(portfolio)
                portfolio.cash += self.annual_contributions * cpi / first_cpi
                investment_strategy.execute(this_date, year_index, investment_years, portfolio, asset_results)

        return dict(first_date=first_date, final_balance=self._summarize(this_date, portfolio, asset_results) * first_cpi / cpi)

    def _collect_dividends_and_pay_devidend_taxes(self, this_date: datetime, portfolio: Portfolio, results: AssetResults) -> None:
        for label, position in portfolio.items():
            result = results.get(label)
            dividends = position.get_dividends(result)
            dividends_post_tax = dividends * (100 - self.dividend_tax_rate_percent) / 100
            portfolio.cash += dividends_post_tax
            config = self.asset_configs[label]
            if config.accumulate_dividens:
                portfolio.buy(this_date, label, dividends_post_tax, results)

    def _collect_maturity(self, this_date: datetime, portfolio: Portfolio) -> None:
        for position in portfolio.values():
            maturity = position.get_maturity(this_date)
            if maturity:
                portfolio.cash += maturity

    def _pay_all_fees(self, portfolio: Portfolio) -> None:
        for position in portfolio.values():
            position.pay_fees()

    @staticmethod
    def _summarize(this_date: datetime, portfolio: Portfolio, results: AssetResults) -> float:
        balance = 0.0
        for label, position in portfolio.items():
            result = results.get(label)
            balance += position.get_value(this_date, result)
        return balance
