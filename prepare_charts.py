import altair as alt
import csv
import datetime as dt
import pandas as pd


def get_data():

    data_path = 'data\\data\\data_csv.csv'

    column_date = []
    column_index = []
    column_dividend = []
    column_cpi = []

    with open(data_path, newline='', encoding='utf-8-sig') as csvfile:

        csvreader = csv.DictReader(csvfile)

        for row in csvreader:

            date_parts = row['Date'].split('-')
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
            column_index.append(float(index_str))
            column_dividend.append(float(dividend_str))
            column_cpi.append(float(cpi_str))

    return pd.DataFrame({
        'date': column_date,
        'index': column_index,
        'dividend': column_dividend,
        'cpi': column_cpi,
    })


def calculate_balance(data, skip_rows, investment_years, initial_balance, annual_contributions, fees_percent, tax_percent, investment_strategy):

    balance = initial_balance
    first_date = None
    prev_index = None
    prev_cpi = None

    for year_index in range(investment_years + 1):

        data_index = skip_rows + year_index * 12
        row = data.iloc[data_index]

        this_date = row['date']
        index = row['index']
        dividend = row['dividend']
        cpi = row['cpi']

        if year_index == 0:
            first_date = this_date
            prev_index = index
            prev_cpi = cpi
            continue

        if this_date.month != first_date.month:
            raise Exception(f'Current month ({this_date}) is not the same as the first month ({first_date})')

        balance = investment_strategy(
            balance, annual_contributions, fees_percent, tax_percent, prev_index, index, dividend, prev_cpi, cpi)

        prev_index = index
        prev_cpi = cpi

    return dict(first_date=first_date, final_balance=balance)


def gather_balances(
    data, investment_strategies, start_from, investment_years, initial_balance, annual_contributions, fees_percent, tax_percent):

    print(f'gathering balances for investment years {investment_years}')

    balances = []
    for investment_strategy, investment_strategy_label in investment_strategies:
        print(f'  processing strategy {investment_strategy_label}')
        for i in range(((data.shape[0] - start_from) // 12 - investment_years) * 12):
            balance_dict = calculate_balance(
                data, i, investment_years, initial_balance, annual_contributions, fees_percent, tax_percent, investment_strategy)
            balance_dict['investment_strategy'] = investment_strategy_label
            balances.append(balance_dict)

    return pd.DataFrame(balances)


def prepare_charts(
    investment_strategies,
    initial_balance=100, annual_contributions=20, fees_percent=0.07, tax_percent=15,
    investment_years_options=(20, 25, 30),
    skip_time_percent_options=(0, 20, 40, 60, 80)):

    data = get_data()

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
            balances = gather_balances(data, investment_strategies, 0, investment_years, initial_balance, annual_contributions, fees_percent, tax_percent)
            balances.to_csv(f'balance_{investment_years}y.csv')
            balances_all[investment_years] = balances
    else:
        for investment_years in investment_years_options:
            balances_all[investment_years] = \
                pd.read_csv(f'balance_{investment_years}y.csv').astype({'first_date': 'datetime64[ns]'})

    charts = []

    print('preparing charts')

    for start_date in start_date_options:

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
                        "datum.investment_strategy == 'boglehead'",
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
        )

    alt \
        .vconcat(*charts) \
        .properties(
            title=
                'Likelihood of getting particular final balance adjusted to inflation if investing for different number of years. '
                f'Initial balance is {initial_balance}, annual contributions are {annual_contributions}, fees are {fees_percent}%, tax rate is {tax_percent}%.'
        ) \
        .save('returns.html')


def boglehead_strategy(balance, annual_contributions, fees_percent, tax_percent, prev_index, index, dividend, prev_cpi, cpi):
    stocks_at_year_start = balance / prev_index
    stocks_at_year_end = stocks_at_year_start + annual_contributions / index
    my_dividend = stocks_at_year_end * dividend
    my_dividend_post_tax = my_dividend * (1 - tax_percent / 100)
    balance_not_adjusted_to_inflation = stocks_at_year_end * index * (100 - fees_percent) / 100 + my_dividend_post_tax
    return balance_not_adjusted_to_inflation * prev_cpi / cpi


def fixed_percent_strategy(percent):
    def strategy(balance, annual_contributions, fees_percent, tax_percent, prev_index, index, dividend, prev_cpi, cpi):
        balance += annual_contributions
        balance *= 1 + percent / 100
        return balance * prev_cpi / cpi
    return strategy


investment_strategies = [
    (boglehead_strategy, 'boglehead'),
    (fixed_percent_strategy(0), 'cold cash only'),
] + [
    (fixed_percent_strategy(p), f'stable {p}%') for p in (2, 4, 6)
]

prepare_charts(
    investment_strategies,
    initial_balance=100, annual_contributions=20, fees_percent=0.07, tax_percent=15
)
