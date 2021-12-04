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


def calculate_returns(data, skip_rows, investment_years, initial_balance, yearly_contributions, fees_percent, tax_percent):

    balance = initial_balance
    balance_no_investment = initial_balance
    balance_investment_1pct = initial_balance
    balance_investment_3pct = initial_balance
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
            prev_cpi = index
            continue

        if this_date.month != first_date.month:
            raise Exception(f'Current month ({this_date}) is not the same as the first month ({first_date})')

        stocks_at_year_start = balance / prev_index
        stocks_at_year_end = stocks_at_year_start + yearly_contributions / index
        my_dividend = stocks_at_year_end * dividend
        my_dividend_post_tax = my_dividend * (1 - tax_percent / 100)
        balance_not_adjusted_to_inflation = stocks_at_year_end * index * (100 - fees_percent) / 100 + my_dividend_post_tax
        balance = balance_not_adjusted_to_inflation * cpi / prev_cpi

        balance_no_investment += yearly_contributions
        balance_no_investment *= cpi / prev_cpi

        balance_investment_1pct += yearly_contributions
        balance_investment_1pct *= 1.01
        balance_investment_1pct *= cpi / prev_cpi

        balance_investment_3pct += yearly_contributions
        balance_investment_3pct *= 1.03
        balance_investment_3pct *= cpi / prev_cpi

        prev_index = index
        prev_cpi = cpi

    return dict(
        first_date=first_date,
        final_balance=balance,
        final_balance_no_investment=balance_no_investment,
        final_balance_investment_1pct=balance_investment_1pct,
        final_balance_investment_3pct=balance_investment_3pct,
    )


def gather_returns(data, start_from, investment_years, initial_balance, yearly_contributions, fees_percent, tax_percent):
    return pd.DataFrame(
        calculate_returns(data, i, investment_years, initial_balance, yearly_contributions, fees_percent, tax_percent)
        for i in range(((data.shape[0] - start_from) // 12 - investment_years) * 12)
    )


def prepare_charts(
    initial_balance=100, yearly_contributions=20, fees_percent=0.07, tax_percent=15,
    investment_years_options=(20, 25, 30), skip_time_percent_options=(0, 10, 20, 30, 40, 50, 60, 70, 80)):

    data = get_data()

    for investment_years in investment_years_options:
        returns = gather_returns(data, 0, investment_years, initial_balance, yearly_contributions, fees_percent, tax_percent)
        returns.to_csv(f'balance_{investment_years}y.csv')

    returns = {}

    for investment_years in investment_years_options:
        returns[investment_years] = pd.read_csv(f'balance_{investment_years}y.csv')

    length = returns[investment_years_options[0]].shape[0]

    charts = []

    for skip_time_percent in skip_time_percent_options:

        row = []

        for investment_years in investment_years_options:

            start = length * skip_time_percent // 100
            returns_sliced = returns[investment_years][start:]
            first_date = returns_sliced.at[start, 'first_date']

            balance_chart = None

            for color, field in [
                ('darkblue', 'final_balance'),
                ('red', 'final_balance_no_investment'),
                ('orange', 'final_balance_investment_1pct'),
                ('green', 'final_balance_investment_3pct')]:

                temp_chart = alt.Chart(returns_sliced) \
                    .mark_line(
                        clip=True,
                        color=color
                    ).transform_joinaggregate(
                        total_count='count(*)'
                    ).transform_window(
                        cumulative_count='count()',
                        sort=[{'field': field}]
                    ).transform_calculate(
                        percent_of_years_with_lower_balance='datum.cumulative_count / datum.total_count * 100'
                    ).encode(
                        x=alt.X(
                            field + ':Q',
                            title='Final balance',
                            scale=alt.Scale(type='log')
                        ),
                        y=alt.X(
                            'percent_of_years_with_lower_balance:Q',
                            title=f'% of years with lower final balance if investing for {investment_years}y',
                            scale=alt.Scale(domain=[0, 100])
                        ),
                        tooltip=[field + ':Q', 'percent_of_years_with_lower_balance:Q']
                    )

                if not balance_chart:
                    balance_chart = temp_chart
                else:
                    balance_chart += temp_chart

            row.append(balance_chart)

        charts.append(
            alt
                .hconcat(*row)
                .properties(title=f'Data for analysis starting from {first_date}')
        )

    alt \
        .vconcat(*charts) \
        .properties(
            title=
                'Likelihood of getting particular final balance if investing for different number of years. '
                f'Initial balance is {initial_balance}, yearly contributions are {yearly_contributions}, fees are {fees_percent}%, tax rate is {tax_percent}%.'
        ) \
        .save('returns.html')


prepare_charts()
