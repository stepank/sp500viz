from invesment_strategies import *
from simulation import AssetConfigs, AssetConfig

investment_strategies = [
    (Sp500Strategy(), 'sp500'),
    (Sp500AndVbmfxStrategyWoSelling(fixed_target_sp500_percent(80)), 'sp500 & vbmfx 80/20 w/o selling'),
    (Sp500AndVbmfxStrategyWithSelling(fixed_target_sp500_percent(80)), 'sp500 & vbmfx 80/20 with selling, 0% capital gains tax'),
    (Sp500AndVbmfxStrategyWoSelling(linearly_changing_target_sp500_percent(100, 80)), 'sp500 & vbmfx 100/0 -> 80/20 w/o selling'),
    (Sp500AndVbmfxStrategyWithSelling(linearly_changing_target_sp500_percent(100, 80)), 'sp500 & vbmfx 100/0 -> 80/20 with selling, 0% capital gains tax'),
    (FixedPercentStrategy(0), 'cold cash only'),
    (FixedPercentStrategy(2), f'fixed 2%'),
    (FixedPercentStrategy(4), f'fixed 4%'),
    (FixedPercentStrategy(6), f'fixed 6%'),
]

parameters = dict(
    initial_balance=100,
    annual_contributions=20,
    dividend_tax_rate_percent=15,
    investment_years_options=[15, 20, 25, 30],
    skip_time_percent_options=[0, 20, 40, 60, 80],
    investment_strategies=investment_strategies,
    asset_configs=AssetConfigs({
        sp500: AssetConfig(fees_percent=0.07, accumulate_dividens=True),
        vbmfx: AssetConfig(fees_percent=0.07, accumulate_dividens=True),
    })
)
