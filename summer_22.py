# %%

import pandas as pd
from temperature.utils import get_int_ext_temperature
from temperature.exterior import get_ext_df

# %%

PATH_TEMP = {'interior': 'netatmo/export/netatmo_temperature_2020-01-23_2022-06-25.csv',
             'exterior': 'export/daily_export'}
AGG_FUNC = {'energy': 'sum',
            'temperature_int': 'mean',
            'temperature_ext': 'mean'}


def read_temperature(path_temp):
    """
    Read temperature data.
    """
    int = pd.read_csv(path_temp['interior'])[['date', 'temperature']]
    int['date'] = pd.to_datetime(int['date'])
    ext = get_ext_df(path_temp['exterior'])
    ext['datetime'] = pd.to_datetime(ext['datetime'])
    ext = ext[ext['temp'] != 'NA']
    ext['temp'] = ext['temp'].astype(float)
    int.set_index('date', inplace=True)
    ext.set_index('datetime', inplace=True)
    int_d = int.resample('H')\
               .agg({'temperature': AGG_FUNC['temperature_int']})\
               .reset_index()
    ext_d = ext.resample('H')\
               .agg({'temp': AGG_FUNC['temperature_ext']})\
               .reset_index()
    ext_d.rename(columns={'datetime': 'date',
                          'temp': 'temperature_ext'},
                 inplace=True)
    df = pd.merge(int_d, ext_d, on='date', how='left')
    return df

# %%


df = read_temperature(PATH_TEMP)
df['diff'] = df['temperature'] - df['temperature_ext']

# What's the average difference on a daily level between ext and in for a month May - July at 4pm when exterior temp are above 30C?
df['hour'] = df.date.dt.hour
df['month'] = df.date.dt.month
print(df[df['month'].isin([5, 6, 7])]
      .query("hour == 16")
      .query("temperature_ext > 30")
      .query("date < '2021-07-18'")[['diff']].mean())

# %%
