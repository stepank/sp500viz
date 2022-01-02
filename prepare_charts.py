import altair as alt
import csv
import datetime as dt
import json
import math
import os
import pandas as pd


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


class InvestmentStrategyState:

    def __init__(
        self,
        balance, annual_contributions,
        fees_percent, dividend_tax_rate_percent):
        self.requires_initialization = True
        self.balance = balance
        self.annual_contributions = annual_contributions
        self.fees_percent = fees_percent
        self.dividend_tax_rate_percent = dividend_tax_rate_percent
        self.sp500_count = 0
        self.vbmfx_count = 0
        self.prev_sp500_index = None
        self.sp500_index = None
        self.sp500_dividend = None
        self.prev_vbmfx_price = None
        self.vbmfx_price = None
        self.vbmfx_dividend = None


def calculate_balance(
    data, skip_rows, investment_years,
    initial_balance, annual_contributions,
    fees_percent, dividend_tax_rate_percent,
    investment_strategy):

    prev_cpi = None

    state = InvestmentStrategyState(
        initial_balance, annual_contributions,
        fees_percent, dividend_tax_rate_percent)

    for year_index in range(investment_years + 1):

        data_index = skip_rows + year_index * 12
        row = data.iloc[data_index]

        this_date = row['date']
        cpi = row['cpi']

        state.sp500_index = row['sp500_index']
        state.sp500_dividend = row['sp500_dividend']
        state.vbmfx_price = row['vbmfx_price']
        state.vbmfx_dividend = row['vbmfx_dividend']

        sp500_index = state.sp500_index
        vbmfx_price = state.vbmfx_price

        if year_index == 0:
            first_date = this_date

        if this_date.month != first_date.month:
            raise Exception(f'Current month ({this_date}) is not the same as the first month ({first_date})')

        investment_strategy(state)

        if year_index == 0:
            state.requires_initialization = False
        else:
            q = prev_cpi / cpi
            state.balance *= q
            state.sp500_count *= q
            state.vbmfx_count *= q

        prev_cpi = cpi
        state.prev_sp500_index = sp500_index
        state.prev_vbmfx_price = vbmfx_price

    return dict(first_date=first_date, final_balance=state.balance)


def gather_balances(
    data, investment_strategies, start_from, investment_years,
    initial_balance, annual_contributions,
    fees_percent, dividend_tax_rate_percent):

    print(f'gathering balances for investment years {investment_years}')

    balances = []
    for investment_strategy, investment_strategy_label in investment_strategies:
        print(f'  processing strategy {investment_strategy_label}')
        for i in range(((data.shape[0] - start_from) // 12 - investment_years) * 12):
            balance_dict = calculate_balance(
                data, i, investment_years,
                initial_balance, annual_contributions,
                fees_percent, dividend_tax_rate_percent,
                investment_strategy)
            balance_dict['investment_strategy'] = investment_strategy_label
            balances.append(balance_dict)

    return pd.DataFrame(balances)


def prepare_charts(
    investment_strategies,
    initial_balance, annual_contributions,
    fees_percent, dividend_tax_rate_percent,
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
                initial_balance, annual_contributions,
                fees_percent, dividend_tax_rate_percent)
            balances.to_csv(f'balance_{investment_years}y.csv')
            balances_all[investment_years] = balances
    else:
        for investment_years in investment_years_options:
            balances_all[investment_years] = \
                pd.read_csv(f'balance_{investment_years}y.csv').astype({'first_date': 'datetime64[ns]'})

    charts = []

    print('preparing charts')

    for start_date in start_date_options:

        print(f'  processing preparing charts {start_date}')

        row = []

        for investment_years in investment_years_options:

            balances_for_investment_years = balances_all[investment_years]
            balances_sliced = balances_for_investment_years[balances_for_investment_years['first_date'] > start_date]

            if balances_sliced.shape[0] == 0:
                continue

            color = alt.Color('investment_strategy', title='Investment strategy')

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
                    strokeWidth=alt.condition(
                        "datum.investment_strategy == 'sp500'",
                        alt.value(2),
                        alt.value(1)
                    ),
                    tooltip=['final_balance:Q', 'percent_of_years_with_lower_balance:Q', 'investment_strategy']
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
                f'fees are {fees_percent}%, dividend tax rate is {dividend_tax_rate_percent}%.'
        ) \
        .resolve_scale(x='shared') \
        .save('returns.html')


def sp500_strategy(state):

    if state.requires_initialization:
        state.sp500_count = state.balance / state.sp500_index
        return

    # dividend
    my_dividend = state.sp500_count * state.sp500_dividend
    my_dividend_post_tax = my_dividend * (1 - state.dividend_tax_rate_percent / 100)
    state.sp500_count += my_dividend_post_tax / state.sp500_index

    # fees
    state.sp500_count *= (100 - state.fees_percent) / 100

    # annual contributions
    state.sp500_count += state.annual_contributions / state.sp500_index

    state.balance = state.sp500_count * state.sp500_index


def sp500_and_bonds_strategy_wo_selling(target_equities_percent):
    def investment_strategy(state):

        if math.isnan(state.vbmfx_price) or math.isnan(state.vbmfx_dividend):
            sp500_strategy(state)
            return

        if state.requires_initialization:
            state.sp500_count = state.balance * target_equities_percent / 100 / state.sp500_index
            state.vbmfx_count = state.balance * (100 - target_equities_percent) / 100 / state.vbmfx_price
            return

        # dividend
        my_sp500_dividend = state.sp500_count * state.sp500_dividend
        my_sp500_dividend_post_tax = my_sp500_dividend * (1 - state.dividend_tax_rate_percent / 100)
        state.sp500_count += my_sp500_dividend_post_tax / state.sp500_index
        my_vbmfx_dividend = state.vbmfx_count * state.vbmfx_dividend
        my_vbmfx_dividend_post_tax = my_vbmfx_dividend * (1 - state.dividend_tax_rate_percent / 100)
        state.vbmfx_count += my_vbmfx_dividend_post_tax / state.sp500_index

        # fees
        state.sp500_count *= (100 - state.fees_percent) / 100
        state.vbmfx_count *= (100 - state.fees_percent) / 100

        # annual contributions
        sp500_balance = state.sp500_count * state.sp500_index
        vbmfx_balance = state.vbmfx_count * state.vbmfx_price
        equities_percent = sp500_balance / (sp500_balance + vbmfx_balance) * 100
        if equities_percent <= target_equities_percent:
            state.sp500_count += state.annual_contributions / state.sp500_index
        else:
            state.vbmfx_count += state.annual_contributions / state.vbmfx_price

        state.balance = state.sp500_count * state.sp500_index + state.vbmfx_count * state.vbmfx_price

    return investment_strategy


def sp500_and_bonds_strategy_with_selling(target_equities_percent):
    def investment_strategy(state):

        if math.isnan(state.vbmfx_price) or math.isnan(state.vbmfx_dividend):
            sp500_strategy(state)
            return

        if state.requires_initialization:
            state.sp500_count = state.balance * target_equities_percent / 100 / state.sp500_index
            state.vbmfx_count = state.balance * (100 - target_equities_percent) / 100 / state.vbmfx_price
            return

        # dividend
        my_sp500_dividend = state.sp500_count * state.sp500_dividend
        my_sp500_dividend_post_tax = my_sp500_dividend * (1 - state.dividend_tax_rate_percent / 100)
        state.sp500_count += my_sp500_dividend_post_tax / state.sp500_index
        my_vbmfx_dividend = state.vbmfx_count * state.vbmfx_dividend
        my_vbmfx_dividend_post_tax = my_vbmfx_dividend * (1 - state.dividend_tax_rate_percent / 100)
        state.vbmfx_count += my_vbmfx_dividend_post_tax / state.sp500_index

        # fees
        state.sp500_count *= (100 - state.fees_percent) / 100
        state.vbmfx_count *= (100 - state.fees_percent) / 100

        # annual contributions
        sp500_balance = state.sp500_count * state.sp500_index
        vbmfx_balance = state.vbmfx_count * state.vbmfx_price
        final_balance = sp500_balance + vbmfx_balance + state.annual_contributions
        target_sp500_balance = final_balance * target_equities_percent / 100
        target_vbmfx_balance = final_balance - target_sp500_balance

        if target_sp500_balance <= sp500_balance:
            state.vbmfx_count += state.annual_contributions / state.vbmfx_price
            sell_amount = sp500_balance - target_sp500_balance
            state.vbmfx_count += sell_amount / state.vbmfx_price
            state.sp500_count -= sell_amount / state.sp500_index
        elif target_vbmfx_balance <= vbmfx_balance:
            state.sp500_count += state.annual_contributions / state.sp500_index
            sell_amount = vbmfx_balance - target_vbmfx_balance
            state.sp500_count += sell_amount / state.sp500_index
            state.vbmfx_count -= sell_amount / state.vbmfx_price
        else:
            state.vbmfx_count += (target_vbmfx_balance - vbmfx_balance) / state.vbmfx_price
            state.sp500_count += (target_sp500_balance - sp500_balance) / state.sp500_index

        state.balance = state.sp500_count * state.sp500_index + state.vbmfx_count * state.vbmfx_price

        assert state.balance - final_balance < 0.000001

    return investment_strategy


def fixed_percent_strategy(percent):
    def strategy(state):
        if state.requires_initialization:
            return
        state.balance += state.annual_contributions
        state.balance *= 1 + percent / 100
    return strategy


investment_strategies = [
    (sp500_strategy, 'sp500'),
    (sp500_and_bonds_strategy_wo_selling(80), 'sp500 & bonds 80/20 w/o selling'),
    (sp500_and_bonds_strategy_with_selling(80), 'sp500 & bonds 80/20 with selling, 0% capital gains tax'),
    (fixed_percent_strategy(0), 'cold cash only'),
] + [
    (fixed_percent_strategy(p), f'fixed {p}%') for p in (2, 4, 6)
]

parameters=dict(
    initial_balance=100,
    annual_contributions=20,
    fees_percent=0.07,
    dividend_tax_rate_percent=15,
    investment_years_options=(20, 25, 30),
    skip_time_percent_options=(0, 20, 40, 60, 80)
)

external_parameters_file_name = 'parameters.json'
if os.path.exists(external_parameters_file_name):
    with open(external_parameters_file_name) as json_file:
        external_parameters = json.load(json_file)
        parameters.update(external_parameters)

prepare_charts(
    investment_strategies,
    **parameters
)
