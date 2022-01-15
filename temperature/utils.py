from datetime import datetime
from ..netatmo.netatmo import *
from temperature.exterior import *

""""
Utils functions to plot diff in temperature
"""


def get_int_ext_temperature(start_date, end_date):
    """
    From a start_date and a end_date, retrieve interior, exterior and diff temp.  
    """
    df_int = pull_temperature(start_date, end_date)
    df_int['datetime'] = df_int['date'].dt.floor('H')
    df_int.rename(columns={'temperature': 'temp_interior'},
                  inplace=True)
    df_int['datetime'] = df_int['datetime'].dt.floor(
        'H')  # To match at the hourly level

    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    tmp_ext = retrieve_temp_period(start, end)
    df_ext = pd.DataFrame([item for sublist in tmp_ext for item in sublist])
    df_ext.rename(columns={'temp': 'temp_exterior'},
                  inplace=True)
    df_ext['datetime'] = pd.to_datetime(df_ext['datetime'])

    df = pd.merge(df_int, df_ext, how='left')
    df['diff'] = df['temp_interior'] - df['temp_exterior']

    return df[['datetime', 'temp_interior', 'temp_exterior', 'diff']]


def plot_int_ext(start_date, end_date):

    df = get_int_ext_temperature(start_date, end_date)

    df_stack = df.set_index('datetime')\
                 .stack().reset_index()\
                 .rename(columns={'level_1': 'variable',
                                  0: 'value'})
    sns.set(rc={'figure.figsize': (20, 10)})
    ax = sns.lineplot(x="datetime", y='value', hue='variable', data=df_stack)
