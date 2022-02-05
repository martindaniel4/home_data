# %%
import pandas as pd
import plotly.express as px
import statsmodels.formula.api as smf
from temperature.exterior import get_ext_df
from kaya import set_dataframe_to_sheet, get_sheet_as_dataframe
from statsmodels.tools.eval_measures import rmse


PATH_TEMP = {'interior': 'netatmo/export/netatmo_temperature_2020-01-01_2022-01-23.csv',
             'exterior': 'temperature/export/daily_export'}
PATH_GAZ = "gaz/data/gaz_conso.csv"
DATE_NEW_ROOF = '2021-07-18'
TRAIN_MODEL_DATE_LIMIT = '2021-02-15'
SEASON = "winter"  # should we only keep winter months
WINTER_MONTH = [1, 2, 3, 10, 11, 12]
AGG_FUNC = {'energy': 'sum',
            'temperature_int': 'mean',
            'temperature_ext': 'mean'}
GSHEET = {'workbook': 'boiler',
          'sheet_occupied': 'occupied',
          'prediction_output': 'v2'}


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
    ext = ext[ext['temp'] != 'NA']
    ext['temp'] = ext['temp'].astype(float)
    int.set_index('date', inplace=True)
    ext.set_index('datetime', inplace=True)
    int_d = int.resample('D')\
               .agg({'temperature': AGG_FUNC['temperature_int']})\
               .reset_index()
    ext_d = ext.resample('D')\
               .agg({'temp': AGG_FUNC['temperature_ext']})\
               .reset_index()
    ext_d.rename(columns={'datetime': 'date',
                          'temp': 'temperature_ext'},
                 inplace=True)
    df = pd.merge(int_d, ext_d, on='date', how='left')
    return df


def stack_temperature():
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
    if x.month in WINTER_MONTH:
        return 'winter'
    else:
        return 'summer'


def merge_gaz_temperature():
    """
    Merge gaz and temperature.
    """
    gaz = read_gaz(PATH_GAZ)
    temp = read_temperature(PATH_TEMP)
    df = pd.merge(gaz, temp, on='date', how='left')
    df['season'] = df['date'].apply(_season)
    if SEASON == 'winter':
        df = df.query("season == 'winter'")
    return df


def build_feature_occupied():
    """
    For each date of the gaz_date temp
    returns whether the home was occupied or not.
    """
    df = merge_gaz_temperature()
    dates = pd.DataFrame(pd.date_range(
        df.date.min(), df.date.max()), columns=['date'])
    occupied = get_sheet_as_dataframe(
        GSHEET['workbook'], GSHEET['sheet_occupied'])
    occupied['date'] = \
        pd.to_datetime(occupied['date'],
                       format="%d/%m/%Y",
                       errors='coerce')
    data = pd.merge(dates, occupied, on='date', how='left')
    # O if away 1 if occupied
    data.occupied = data.occupied.fillna('1')
    return data[['date', 'occupied']]


def build_feature_set():
    """
    Feature set contains temperature and occupied.
    """
    df = merge_gaz_temperature()
    occupied = build_feature_occupied()
    df = pd.merge(df, occupied, on='date', how='left')
    df = df[['date', 'temperature', 'temperature_ext', 'occupied', 'energy']]
    # We can't have NaN in the feature set
    df.dropna(inplace=True)
    print(f'number of days in feature set: {df.shape[0]}')
    return df


def build_training_set():
    """
    Build the training set we will use for our model
    """
    df = build_feature_set()
    # Only keep the data from the training period
    df = df.query("date < '{}'".format(TRAIN_MODEL_DATE_LIMIT))
    print(f'number of days in training set: {df.shape[0]}')
    return df


def build_energy_model():
    """
    Build energy model.
    """
    df = build_training_set()
    model = smf.ols(
        formula='energy ~ temperature + temperature_ext + occupied', data=df)
    results = model.fit()
    print(results.summary())
    return results


def build_test_set():
    """
    Build the test set we will use for our model
    """
    df = build_feature_set()
    # Test set has to be after the model is trained and before new roof
    # now generate predictions
    df = df.query("date >= '{}'".format(TRAIN_MODEL_DATE_LIMIT))\
           .query("date < '{}'".format(DATE_NEW_ROOF))
    print(f'number of days in test set: {df.shape[0]}')
    return df


def compute_rmse_model():
    """
    Compute RMSE model on test set.
    """
    model = build_energy_model()
    # Build test set
    df = build_test_set()
    ypred = model.predict(df[['temperature', 'temperature_ext', 'occupied']])
    # calc rmse
    error = rmse(df['energy'], ypred)
    print(f'RMSE of the model is : {error}')


def run_prediction(range="all"):
    """
    Run prediction based on the energy model.
    If range is "all" we predict for the whole period (including the training set),
    otherwise we predict on the test set.
    """
    model = build_energy_model()
    if range == 'all':
        df = build_feature_set()
    elif range == 'test':
        df = build_test_set()
    else:
        print('range must be "all" or "test"')
        breakpoint()
    df['energy_predicted'] = model.predict(
        df[['temperature', 'temperature_ext', 'occupied']])
    error = rmse(df['energy'], df['energy_predicted'])
    print(f'RMSE on range {range} is : {error}')
    return df


def export_prediction_to_gsheet(range="all"):
    """
    Export data to Google Sheets.
    We reformate date to be compatible with Google Sheets.
    """
    df = run_prediction(range)
    print(
        f'exporting {df.shape[0]} rows to {GSHEET["workbook"]}/{GSHEET["prediction_output"]}')
    df['date'] = df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    set_dataframe_to_sheet(df, GSHEET["workbook"], GSHEET["prediction_output"])

# def stack_prediction_df():
#     df = build_test_set()
#     df.set_index('date', inplace=True)
#     df = df[['energy', 'energy_predicted']].stack().reset_index()
#     df.columns = ['date', 'type', 'value']
#     return df


# def plot_prediction():
#     """
#     Plot predicted energy.
#     """
#     df = stack_prediction_df()
#     fig = px.line(df, x='date', y='value', color='type')
#     fig.show()


# def compute_energy_savings():
#     """
#     What's the difference between the energy consumption and the energy predicted?
#     """
#     df = predict_on_set(PATH_GAZ, PATH_TEMP, season, type)
#     df['diff'] = df['energy'] - df['energy_predicted']
#     savings_since_roof = df.query(
#         "date > '{}'".format(DATE_NEW_ROOF))['diff'].sum()
#     print("Savings since roof: {} kwh".format(savings_since_roof))
#     df['month_year'] = df['date'].apply(lambda x: x.strftime('%m-%Y'))
#     savings = df.groupby('month_year').agg({'diff': 'sum'}).reset_index()
#     savings['date'] = pd.to_datetime(savings['month_year'], format="%m-%Y")
#     savings.sort_values('date', inplace=True)
#     return savings

    # %%
export_prediction_to_gsheet()
# build_feature_set(PATH_GAZ, PATH_TEMP, season='winter')
# plot_prediction(PATH_GAZ, PATH_TEMP, season='winter', type='all')
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
