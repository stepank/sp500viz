# sp500viz

This project is an attempt to use historical SP500 data to simulate what happens to a portfolio fully allocated to an SP500 index fund.

**Note:** The project was created literally over one weekend by a person with no special education in finance or investment, so mb don't put to much faith in it. Still, if you notice any issues, please let me know. I'm really interested in this thing being somewhat accurate rather than not.

## Requirents

1. **Python**. Mine is of version 3.9.6, but it will likely work on at least some other 3.x versions too.
1. **Windows**. I'm fairly certain it's possible to make it run on Linux and Mac, but I haven't tried it.

## Bootstrap

Run `Bootstrap.ps1` to create a Python virtual environment in the root of the project and install all the dependencies there (see `requirements.txt`).

## Usage

Just run `run.ps1`. It will activate the virtual environment and run the simulation. See below for configuration options.

The simulation will do roughly the following. For every month starting from different dates, it will calculate the final balance adjusted to inflation for different configured portfolios allocated for the given number of years starting from that month.

The output is a greed of charts in the `returns.html` file. Each chart shows the likelihood (based on historical data) of reaching certain balance depending on how long the portfolio is kept invested. The axes are:
* X - final balance,
* Y - percent of starting years that had lower final balance.

The lines on the chart represent different investment strategies. Apart from others, there are "fixed percent" strategies, which are hypothetical investment strategies where you get certain stable nominal return rate. They are there for comparison with other real-world strategies. The default percentages are `0`, `2`, `4`, and `6%`. This can be configured in the `parameters.py` file (see below).

## Configuration

The simulation can be configured by adjusting parameters in the `parameters.py` file. The parameters are:

1. `initial_balance` is the initial lump sum investment. The default is `100`. The currency is always USD.
1. `annual_contributions` is how much you contribute every year year. All contirbutions are applied once per year. They are of the same size, but adjusted for inflation. To demonstrate what that means, consider the followign example. Suppose you set `annual_contributions` to `1000` and CPI in the beginning is `10`. If CPI later changes to let's say 12, the contributions for this later year will be `1000 / 10 * 12` or `1200`. The default is `20`.
1. `dividend_tax_rate_percent` is how much taxes you have to pay every year on the dividends. The default is `15%`.
1. `investment_years_options` is a list of options of the investment horizon. The simulation will be run for every option and the charts will include one column per option. The default is `[20, 25, 30]`, which means the simulation will be run for being invested for `20`, `25`, and `30` years.
1. `skip_time_percent_options` is a list of % of how much data from the beginning to not take into account for the simulation. The simulation will be run for every option and the charts will include one row per option. The default is `[0, 20, 40, 60, 80]`, which correspods to running the simulation starting from the following dates: Jan 1871, Jun 1900, Nov 1929, May 1959, Oct 1988.
1. `investment_strategies` is a list of investment strategies to compare.
1. `asset_configs` allows configuring properties of assets:
    - `fees_percent` is the fees of the fund or how much (in %) the fund charges per year.
    - `accumulate_dividens` determines how dividends are handled. If it is set to `True`, all dividens of this asset are re-invested in the asset itself. If the parameter is set to `False`, the dividens are paid as cash, which can then be used by investment strategies.


## Credits

The data for the simulation was taken from https://datahub.io/core/s-and-p-500. Whoever you are who created this data set, thank you!
