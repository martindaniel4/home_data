# %%
import pandas as pd
import plotly.express as px
import statsmodels.formula.api as smf
from temperature.exterior import get_ext_df

PATH_TEMP = {'interior': 'netatmo/export/netatmo_temperature_2020-01-01_2022-01-23.csv',
             'exterior': 'temperature/export/daily_export'}
PATH_GAZ = "gaz/data/gaz_conso.csv"
DATE_NEW_ROOF = '2021-07-18'

heater = pd.read_csv(
    'netatmo/export/netatmo_agg_boiler_data_boileron_2020-01-01_2022-01-15.csv')
heater['date'] = pd.to_datetime(heater['date'])
heater.set_index('date', inplace=True)

# %%


def read_gaz(PATH_GAZ):
    """
    Read gaz data.
    """
    gaz = pd.read_csv(PATH_GAZ)
    gaz['date'] = pd.to_datetime(gaz['date'], format='%d/%m/%Y')
    # Smart meter only available from August 2020
    gaz = gaz.query("date > '2020-08-01'")
    return gaz


def read_temperature(path_temp):
    """
    Read temperature data.
    """
    int = pd.read_csv(path_temp['interior'])[['date', 'temperature']]
    int['date'] = pd.to_datetime(int['date'])
    ext = get_ext_df(path_temp['exterior'])
    ext['datetime'] = pd.to_datetime(ext['datetime'])
    int.set_index('date', inplace=True)
    ext.set_index('datetime', inplace=True)
    int_d = int.resample('D').mean().reset_index()
    ext_d = ext.resample('D').mean().reset_index()
    ext_d.rename(columns={'datetime': 'date',
                          'temp': 'temperature_ext'},
                 inplace=True)
    df = pd.merge(int_d, ext_d, on='date', how='left')
    return df


def stack_temperature(PATH_TEMP):
    """
    Stack temperature data.
    """
    df = read_temperature(PATH_TEMP)
    df.set_index('date', inplace=True)
    df = df.stack().reset_index()
    df.columns = ['date', 'type', 'value']
    return df


def _season(x):
    """
    Seasonal function.
    """
    if x.month in [1, 2, 3, 4, 10, 11, 12]:
        return 'winter'
    else:
        return 'summer'


def merge_gaz_temperature(PATH_GAZ, PATH_TEMP, season='winter'):
    """
    Merge gaz and temperature.
    """
    gaz = read_gaz(PATH_GAZ)
    temp = read_temperature(PATH_TEMP)
    df = pd.merge(gaz, temp, on='date', how='left')
    df['season'] = df['date'].apply(_season)
    if season == 'winter':
        df = df.query("season == 'winter'")
    return df


def build_energy_model(PATH_GAZ, PATH_TEMP, season):
    """
    Build energy model.
    """
    df = merge_gaz_temperature(PATH_GAZ, PATH_TEMP, season)
    df = df.query("date < '{}'".format(DATE_NEW_ROOF))
    model = smf.ols(formula='energy ~ temperature + temperature_ext', data=df)
    results = model.fit()
    print(results.summary())
    return results


def predict_on_set(PATH_GAZ, PATH_TEMP, season, type='test'):
    model = build_energy_model(PATH_GAZ, PATH_TEMP, season)
    df = merge_gaz_temperature(PATH_GAZ, PATH_TEMP, season)
    if type == 'test':
        df = df.query("date > '{}'".format(DATE_NEW_ROOF))
    df['energy_predicted'] = model.predict(
        df[['temperature', 'temperature_ext']])
    return df


def plot_prediction(PATH_GAZ, PATH_TEMP, season, type='test'):
    """
    Plot predicted energy.
    """
    df = predict_on_set(PATH_GAZ, PATH_TEMP, season, type)
    df.set_index('date', inplace=True)
    df_stack = df[['energy', 'energy_predicted']].stack().reset_index()
    df_stack.columns = ['date', 'type', 'value']
    fig = px.line(df_stack, x='date', y='value', color='type')
    fig.show()


def compute_energy_savings(PATH_GAZ, PATH_TEMP, season='winter', type='all'):
    """
    What's the difference between the energy consumption and the energy predicted?
    """
    df = predict_on_set(PATH_GAZ, PATH_TEMP, season, type)
    df['diff'] = df['energy'] - df['energy_predicted']
    savings_since_roof = df.query(
        "date > '{}'".format(DATE_NEW_ROOF))['diff'].sum()
    print("Savings since roof: {} kwh".format(savings_since_roof))
    df['month_year'] = df['date'].apply(lambda x: x.strftime('%m-%Y'))
    savings = df.groupby('month_year').agg({'diff': 'sum'}).reset_index()
    savings['date'] = pd.to_datetime(savings['month_year'], format="%m-%Y")
    savings.sort_values('date', inplace=True)
    return savings

    # %%


plot_prediction(PATH_GAZ, PATH_TEMP, season='winter', type='all')
# %%

# mod = smf.ols(formula='energy ~ boileron', data=merge_gaz_heater(heater, gaz))
# res = mod.fit()
# print(res.summary())
# # %%
# px.line(heater.resample('D').agg({'boileron': 'sum'}).reset_index(),
#         x='date',
#         y='boileron',
#         )

# # %%
# px.scatter(merge_gaz_heater(heater, gaz),
#            x='energy',
#            y='boileron',
#            hover_data=['date'])
# %%


def merge_gaz_heater(heater, gaz):
    """
    Merge boiler and gaz datasets.
    """
    heater_d = heater.resample('D').agg({'boileron': 'sum'}).reset_index()
    df = pd.merge(gaz, heater_d, on='date', how='left')
    return df


def stack_gaz_heater(heater, gaz):
    """
    Merge boiler and gaz datasets.
    """
    df = merge_gaz_heater(heater, gaz)
    df.set_index('date', inplace=True)
    df = df.stack().reset_index()
    df.columns = ['date', 'type', 'value']
    return df


def plot_gaz_heater(heater, gaz):
    """
    Plot gaz and heater.
    """
    df = stack_gaz_heater(heater, gaz)
    fig = px.bar(df, x='date', y='value', facet_row='type', color='type')
    fig.update_yaxes(matches=None)
    fig.show()

# %%
