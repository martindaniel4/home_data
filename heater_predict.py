# %%
import pandas as pd
import plotly.express as px
import statsmodels.formula.api as smf
from temperature.exterior import get_ext_df
from kaya import set_dataframe_to_sheet

"""
Goal of this script is to predict the activity of the boiler
based on the interior and exterior temperature.

Our hope is that getting to an hourly resolution will help build
a more accurate energy model.
"""

PATH_TEMP = {'interior': 'netatmo/export/netatmo_temperature_2020-01-01_2022-01-23.csv',
             'exterior': 'temperature/export/daily_export'}
PATH_BOILER = "netatmo/export/netatmo_agg_boiler_data_boileron_2020-01-01_2022-01-15.csv"
TRAIN_MODEL_DATE_LIMIT = '2021-02-01'
DATE_NEW_ROOF = '2021-07-18'


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

    # Agregate to hourly resolution
    int_d = int.resample('H').mean().reset_index()
    ext_d = ext.resample('H').mean().reset_index()
    ext_d.rename(columns={'datetime': 'date',
                          'temp': 'temperature_ext'},
                 inplace=True)
    df = pd.merge(int_d, ext_d, on='date', how='left')
    df.dropna(inplace=True)
    return df


def read_boiler_data(path_boiler):
    """
    Read boiler data.
    """
    df = pd.read_csv(path_boiler)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # Agregate to hourly resolution
    df = df.resample('H').agg({'boileron': 'sum'}).reset_index()
    return df


def _season(x):
    """
    Seasonal function.
    """
    if x.month in [1, 2, 3, 10, 11, 12]:
        return 'winter'
    else:
        return 'summer'


def merge_temp_boiler(path_temp, path_boiler, season="winter"):
    """
    Merge boiler and gaz datasets.
    """
    temp = read_temperature(path_temp)
    boiler = read_boiler_data(path_boiler)

    df = pd.merge(temp, boiler, on='date', how='left')
    df.dropna(inplace=True)

    df['season'] = df['date'].apply(_season)
    if season == 'winter':
        df = df.query("season == 'winter'")

    return df


def export_to_gsheet(df, gsheet='boiler', worksheet='data'):
    """
    Export data to Google Sheets.
    We reformate date to be compatible with Google Sheets.
    """
    print(f'exporting {df.shape[0]} rows to {gsheet}/{worksheet}')
    df['date'] = df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    set_dataframe_to_sheet(df, gsheet, worksheet)


def build_energy_model(path_temp, path_boiler, season):
    """
    Build energy model.
    """
    df = merge_temp_boiler(path_temp, path_boiler, season)
    df = df.query("date < '{}'".format(TRAIN_MODEL_DATE_LIMIT))
    model = smf.ols(
        formula='boileron ~ temperature + temperature_ext', data=df)
    results = model.fit()
    print(results.summary())
    return results


def predict_on_set(PATH_TEMP, PATH_BOILER, season, type='test'):
    model = build_energy_model(PATH_TEMP, PATH_BOILER, season)
    df = merge_temp_boiler(PATH_TEMP, PATH_BOILER, season)
    if type == 'test':
        df = df.query("date > '{}'".format(DATE_NEW_ROOF))
    df['boileron_predicted'] = model.predict(
        df[['temperature', 'temperature_ext']])
    return df


def plot_prediction(PATH_TEMP, PATH_BOILER, season, type='test'):
    """
    Plot predicted energy.
    """
    df = predict_on_set(PATH_TEMP, PATH_BOILER, season, type)
    df.set_index('date', inplace=True)
    df_stack = df[['boileron', 'boileron_predicted']].stack().reset_index()
    df_stack.columns = ['date', 'type', 'value']
    fig = px.line(df_stack, x='date', y='value', color='type')
    fig.show()


# %%
df = merge_gaz_boiler(PATH_TEMP, PATH_BOILER)

# %%
