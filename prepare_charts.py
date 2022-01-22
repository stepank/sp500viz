import altair as alt
import csv
import datetime as dt
import pandas as pd
import parameters

from simulation import AssetConfigs, SimulationRunner


def get_data():

    vbmfx_data_price_path = 'data\\bonds\\vbmfx_price.csv'
    vbmfx_prices = {}

    with open(vbmfx_data_price_path, newline='', encoding='utf-8-sig') as csvfile:

        csvreader = csv.DictReader(csvfile)

        for row in csvreader:

            date_parts = row['Date'].split('-')
            year = date_parts[0]
            month = date_parts[1]
            day = date_parts[2]

            price_str = row['Value']
            if not price_str:
                continue

            price = float(price_str)

            this_date = dt.date(year=int(year), month=int(month), day=1)
            this_date_str = this_date.strftime('%Y-%m-%d')
            vbmfx_prices.setdefault(this_date_str, price)

    vbmfx_data_div_yield_path = 'data\\bonds\\vbmfx_div_yield.csv'
    vbmfx_div_yields = {}

    with open(vbmfx_data_div_yield_path, newline='', encoding='utf-8-sig') as csvfile:

        csvreader = csv.DictReader(csvfile)

        for row in csvreader:

            date_parts = row['Date'].split('-')
            year = date_parts[0]
            month = date_parts[1]
            day = date_parts[2]

            price_str = row['Value']
            if not price_str:
                continue

            div_yield = float(price_str)

            this_date = dt.date(year=int(year), month=int(month), day=1)
            this_date_str = this_date.strftime('%Y-%m-%d')
            vbmfx_div_yields.setdefault(this_date_str, div_yield)

    sp500_data_path = 'data\\sp500\\data\\data_csv.csv'

    column_date = []
    column_cpi = []
    column_sp500_index = []
    column_sp500_dividend = []
    column_vbmfx_price = []
    column_vbmfx_dividend = []

    print('getting data')

    with open(sp500_data_path, newline='', encoding='utf-8-sig') as csvfile:

        csvreader = csv.DictReader(csvfile)

        for row in csvreader:

            this_date_str = row['Date']

            date_parts = this_date_str.split('-')
            year = date_parts[0]
            month = date_parts[1]
            day = date_parts[2]

            this_date = dt.date(year=int(year), month=int(month), day=int(day))

            index_str = row['SP500']
            dividend_str = row['Dividend']
            cpi_str = row['Consumer Price Index']

            if not index_str or not dividend_str or not cpi_str:
                continue

            column_date.append(pd.to_datetime(this_date))
            column_cpi.append(float(cpi_str))

            column_sp500_index.append(float(index_str))
            column_sp500_dividend.append(float(dividend_str))

            vbmfx_price = vbmfx_prices.get(this_date_str)
            vbmfx_rate = vbmfx_div_yields.get(this_date_str)
            column_vbmfx_price.append(vbmfx_price)
            if vbmfx_price and vbmfx_rate:
                column_vbmfx_dividend.append(vbmfx_price * vbmfx_rate / 100)
            else:
                column_vbmfx_dividend.append(None)

    return pd.DataFrame({
        'date': column_date,
        'cpi': column_cpi,
        'sp500_index': column_sp500_index,
        'sp500_dividend': column_sp500_dividend,
        'vbmfx_price': column_vbmfx_price,
        'vbmfx_dividend': column_vbmfx_dividend,
    })


def gather_balances(
    data, investment_strategies, start_from, investment_years,
    initial_balance: float, annual_contributions: float, dividend_tax_rate_percent: float, asset_configs: AssetConfigs):

    print(f'gathering balances for investment years {investment_years}')

    balances = []
    simulation_runner = SimulationRunner(initial_balance, annual_contributions, dividend_tax_rate_percent, asset_configs)
    for investment_strategy, investment_strategy_label in investment_strategies:
        print(f'  processing strategy {investment_strategy_label}')
        for i in range(((data.shape[0] - start_from) // 12 - investment_years) * 12):
            balance_dict = simulation_runner.run_simulation(data, i, investment_years, investment_strategy)
            balance_dict['investment_strategy'] = investment_strategy_label
            balances.append(balance_dict)

    return pd.DataFrame(balances)


def prepare_charts(
    investment_strategies,
    initial_balance: float, annual_contributions: float, dividend_tax_rate_percent: float, asset_configs: AssetConfigs,
    investment_years_options, skip_time_percent_options):

    data = get_data()
    data.to_csv(f'main_data.csv')

    length = data.shape[0]
    start_date_options = []
    for skip_time_percent in skip_time_percent_options:
        start_index = length * skip_time_percent // 100
        start_date = data.at[start_index, 'date']
        start_date_options.append(start_date)

    balances_all = {}

    write_data = True
    #write_data = False

    if write_data:
        for investment_years in investment_years_options:
            balances = gather_balances(
                data, investment_strategies, 0, investment_years,
                initial_balance, annual_contributions, dividend_tax_rate_percent, asset_configs)
            balances.to_csv(f'balance_{investment_years}y.csv')
            balances_all[investment_years] = balances
    else:
        for investment_years in investment_years_options:
            balances_all[investment_years] = \
                pd.read_csv(f'balance_{investment_years}y.csv').astype({'first_date': 'datetime64[ns]'})

    charts = []

    print('preparing charts')

    color = alt.Color('investment_strategy', title='Investment strategy')

    selection = alt.selection_multi(
        bind='legend',
        fields=['investment_strategy'])
    opacity = alt.condition(
        selection,
        alt.value(1),
        alt.value(0.15))

    for start_date in start_date_options:

        print(f'  processing preparing charts {start_date}')

        row = []

        for investment_years in investment_years_options:

            balances_for_investment_years = balances_all[investment_years]
            balances_sliced = balances_for_investment_years[balances_for_investment_years['first_date'] > start_date]

            if balances_sliced.shape[0] == 0:
                continue

            balance_chart = alt.Chart(balances_sliced) \
                .mark_line(
                    clip=True
                ).transform_joinaggregate(
                    total_count='count(*)',
                    groupby=['investment_strategy']
                ).transform_window(
                    cumulative_count='count()',
                    sort=[{'field': 'final_balance'}],
                    groupby=['investment_strategy']
                ).transform_calculate(
                    percent_of_years_with_lower_balance='datum.cumulative_count / datum.total_count * 100'
                ).encode(
                    x=alt.X(
                        'final_balance:Q',
                        title='Final balance',
                        scale=alt.Scale(type='log')
                    ),
                    y=alt.X(
                        'percent_of_years_with_lower_balance:Q',
                        title=f'% of years with lower final balance if investing for {investment_years}y',
                        scale=alt.Scale(domain=[0, 100])
                    ),
                    color=color,
                    opacity=opacity,
                    strokeWidth=alt.condition(
                        "datum.investment_strategy == 'sp500'",
                        alt.value(2),
                        alt.value(1)
                    ),
                    tooltip=['final_balance:Q', 'percent_of_years_with_lower_balance:Q', 'investment_strategy']
                ).add_selection(
                    selection
                ).properties(
                    width=1200
                )

            row.append(balance_chart)

        charts.append(
            alt
                .hconcat(*row)
                .properties(title=f'Data for analysis starting from {start_date}')
                .resolve_scale(x='shared')
        )

    alt \
        .vconcat(*charts) \
        .properties(
            title=
                'Likelihood of getting particular final balance adjusted to inflation if investing for different number of years. '
                f'Initial balance is {initial_balance}, annual contributions are {annual_contributions}, '
                f'dividend tax rate is {dividend_tax_rate_percent}%.'
        ) \
        .resolve_scale(x='shared') \
        .save('returns.html')


prepare_charts(
    **parameters.parameters
)
