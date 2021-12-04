import altair as alt
import csv
import datetime as dt
import pandas as pd


# Prepare data


data_path = 'data\\data\\data_csv.csv'

column_date = []
column_index = []
column_dividend = []

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

        if not index_str or not dividend_str:
            continue

        column_date.append(pd.to_datetime(this_date))
        column_index.append(float(index_str))
        column_dividend.append(float(dividend_str))

data = pd.DataFrame({
    'date': column_date,
    'index': column_index,
    'dividend': column_dividend,
})


def calculate_average_compound_return_percent(data, start_from, years, fees_percent=0.07):

    balance = 1
    first_date = None
    prev_index = None

    for year_index in range(years + 1):

        data_index = start_from + year_index * 12
        row = data.iloc[data_index]

        this_date = row['date']
        index = row['index']
        dividend = row['dividend']

        if year_index == 0:
            first_date = this_date
            prev_index = index
            continue

        if this_date.month != first_date.month:
            raise Exception(f'Current month ({this_date}) is not the same as the first month ({first_date})')

        stocks = balance / prev_index
        my_dividend = stocks * dividend
        balance = (stocks * index) * (100 - fees_percent) / 100 + my_dividend

        prev_index = index

    return dict(first_date=first_date, return_percent=(balance ** (1 / years) - 1) * 100)


def gather_average_compount_returns(data, start_from, years):
    return pd.DataFrame(
        calculate_average_compound_return_percent(data, i, years)
        for i in range(((data.shape[0] - start_from) // 12 - years) * 12)
    )


#for years in (20, 25, 30):
#    returns = gather_average_compount_returns(data, 0, years)
#    returns.to_csv(f'returns_{years}y.csv')

charts = []

for years in (20, 25, 30):

    returns = pd.read_csv(f'returns_{years}y.csv')

    returns_chart = alt.Chart(returns) \
        .transform_joinaggregate(
            total_count='count(*)'
        ).transform_window(
            cumulative_count='count()',
            sort=[{'field': 'return_percent'}]
        ).transform_calculate(
            percent_with_lower_return='datum.cumulative_count / datum.total_count * 100'
        ).mark_line(
        ).encode(
            x=alt.X('return_percent:Q', title=f'Nominal average compound return if investing for {years}y, %'),
            y=alt.X('percent_with_lower_return:Q', title=f'Ratio of years with lower return, %'),
        )

    charts.append(returns_chart)

alt.hconcat(*charts).save('returns.html')
