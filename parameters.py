from invesment_strategies import *

investment_strategies = [
    (sp500_strategy, 'sp500'),
    (sp500_and_bonds_strategy_wo_selling(80), 'sp500 & bonds 80/20 w/o selling'),
    (sp500_and_bonds_strategy_with_selling(80), 'sp500 & bonds 80/20 with selling, 0% capital gains tax'),
    (fixed_percent_strategy(0), 'cold cash only'),
] + [
    (fixed_percent_strategy(p), f'fixed {p}%') for p in (2, 4, 6)
]


parameters = dict(
    initial_balance=100,
    annual_contributions=20,
    fees_percent=0.07,
    dividend_tax_rate_percent=15,
    investment_years_options=(20, 25, 30),
    skip_time_percent_options=(0, 20, 40, 60, 80),
    investment_strategies=investment_strategies,
)
