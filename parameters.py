from invesment_strategies import *
from simulation import AssetConfigs, AssetConfig

investment_strategies = [
    (Sp500Strategy(), 'sp500'),
    (Sp500AndTb10yStrategyWoSelling(fixed_target_sp500_percent(70)), 'sp500 & tb10y 70/30 w/o selling'),
    (Sp500AndVbmfxStrategyWoSelling(fixed_target_sp500_percent(70)), 'sp500 & vbmfx 70/30 w/o selling'),
    (Sp500AndTb10yStrategyWithSelling(fixed_target_sp500_percent(70)), 'sp500 & tb10y 70/30 with selling, 0% capital gains tax'),
    (Sp500AndVbmfxStrategyWithSelling(fixed_target_sp500_percent(70)), 'sp500 & vbmfx 70/30 with selling, 0% capital gains tax'),
    (Sp500AndTb10yStrategyWoSelling(linearly_changing_target_sp500_percent(100, 70)), 'sp500 & tb10y 100/0 -> 70/30 w/o selling'),
    (Sp500AndVbmfxStrategyWoSelling(linearly_changing_target_sp500_percent(100, 70)), 'sp500 & vbmfx 100/0 -> 70/30 w/o selling'),
    (Sp500AndTb10yStrategyWithSelling(linearly_changing_target_sp500_percent(100, 70)), 'sp500 & tb10y 100/0 -> 70/30 with selling, 0% capital gains tax'),
    (Sp500AndVbmfxStrategyWithSelling(linearly_changing_target_sp500_percent(100, 70)), 'sp500 & vbmfx 100/0 -> 70/30 with selling, 0% capital gains tax'),
    (FixedPercentStrategy(0), 'cash only'),
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
        sp500: AssetConfig(fees_percent=0.07, accumulate_dividens=False),
        vbmfx: AssetConfig(fees_percent=0.15, accumulate_dividens=False),
        tb10y: AssetConfig(fees_percent=0.0, accumulate_dividens=False),
    })
)
