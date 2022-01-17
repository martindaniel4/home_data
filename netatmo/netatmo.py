# %%
import requests
import pandas as pd
import numpy as np
import os
from datetime import datetime

"""
Pull identification variables from Netatmo.
Those were added to my path.
"""

client_id = os.environ["NETATMO_CLIENT_ID"]
client_secret = os.environ["NETATMO_CLIENT_SECRET"]
email = os.environ['NETATMO_EMAIL']
pwd = os.environ['NETATMO_PWD']
relay_id = os.environ['NETATMO_RELAY_ID']
thermostat_id = os.environ['NETATMO_THERMOSTAT_ID']


def get_access_token(client_id, client_secret, email, pwd):
    """
    Authenticate, get access token.
    See https://dev.netatmo.com/apidocumentation/oauth
    """
    r = requests.post('https://api.netatmo.com/oauth2/token?',
                      data={'grant_type': 'password',
                            'client_id': client_id,
                            'client_secret': client_secret,
                            'username': email,
                            'password': pwd,
                            'scope': 'read_thermostat'})

    access_token = r.json()['access_token']
    return access_token


def get_home_features():
    """
    Get room, home id and device setup_date which is needed to retrieve temp data.
    See https://dev.netatmo.com/apidocumentation/security#gethomedata
    """
    access_token = get_access_token(client_id, client_secret, email, pwd)

    r = requests.get('https://api.netatmo.com/api/homesdata?',
                     headers={'Authorization': 'Bearer '+access_token})

    # I have only one home and one device, so using indice 0 below
    home_id = r.json()['body']['homes'][0]['id']
    room_id = r.json()['body']['homes'][0]['rooms'][0]['id']
    setup_date = r.json()['body']['homes'][0]['modules'][0]['setup_date']

    return {'home_id': home_id,
            'room_id': room_id,
            'setup_date': setup_date}


def split_dates(start_date, end_date):
    """
    The max limit of rows retrieved is 1024.
    1) Take the date difference between today and device setup.
    2) Create pair of dates timestamps that will be used in a loop
    if no start_date is provided, script returns start_date. If no end_date is provided
    script uses today as end_date.
    See https://dev.netatmo.com/apidocumentation/energy#getroommeasure
    """
    today_timestamp = datetime.now().timestamp()

    if start_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        setup_timestamp = get_home_features()['setup_date']
        start = datetime.utcfromtimestamp(setup_timestamp).strftime('%Y-%m-%d')

    if end_date:
        end = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end = datetime.now().strftime('%Y-%m-%d')

    end_of_day = datetime.strptime(end.strftime(
        '%Y-%m-%d') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    # We split dates using a step of 30D. Netatmo API returns 1024 rows max.
    # There is also a rate limit of 500 per hour and 50 requests every 10 seconds.
    list_dates = pd.date_range(start=start,
                               end=end,
                               freq='30D').to_pydatetime().tolist()

    df = pd.DataFrame(list_dates)
    # # Convert to timestamp
    df['begin'] = df[0].values.astype(np.int64) // 10 ** 9
    # # Using shift will empty last value. We then fill with today's timestamp.
    df['end'] = df['begin'].shift(-1,
                                  fill_value=end_of_day.timestamp())
    df = df.drop(0, axis=1)

    pair_dates = df.values.tolist()

    return pair_dates


def pull_temperature_from_list(list_dates):
    """
    From a given list of dates and homes features,
    retrieve temperature measures. Step is 30min.
    See https://dev.netatmo.com/apidocumentation/energy#getroommeasure
    """
    access_token = get_access_token(client_id, client_secret, email, pwd)
    features = get_home_features()
    r = requests.get('https://api.netatmo.com/api/getroommeasure',
                     headers={'Authorization': 'Bearer '+access_token},
                     params={'home_id': features['home_id'],
                             'room_id': features['room_id'],
                             'scale': '1hour',
                             'type': 'temperature',
                             'date_begin': list_dates[0],
                             'date_end': list_dates[1],
                             'optimize': False,
                             'real_time': False})

    print('pull temperature between {d1} and {d2}'.format(d1=list_dates[0],
                                                          d2=list_dates[1]))

    return r.json()['body']


def pull_temperature(start_date, end_date, export=False):
    """
    From the full list of temperature, iterate over each date.
    Return a DataFrame with date and temperature
    """
    range_dates = split_dates(start_date, end_date)

    data = {}

    for p in range_dates:
        t = pull_temperature_from_list(p)
        data.update(t)

    df = pd.DataFrame.from_dict(data,
                                orient='index').reset_index()

    df['date'] = pd.to_datetime(df['index'],
                                unit='s')

    df.rename(columns={0: 'temperature'},
              inplace=True)
    if export:
        # export Netatmo temperature to csv
        df.to_csv('netatmo_temperature_{start_date}_{end_date}.csv'.format(
            start_date=start_date, end_date=end_date))

    return df[['date', 'temperature']]


def pull_boiler_data_from_list(list_dates, metric):
    """
    Pull boiler data from Netatmo.
    """
    access_token = get_access_token(client_id, client_secret, email, pwd)
    r = requests.get('https://api.netatmo.com/api/getmeasure',
                     headers={'Authorization': 'Bearer '+access_token},
                     params={'device_id': relay_id,
                             'module_id': thermostat_id,
                             'scale': '1hour',
                             'type': metric,
                             'date_begin': list_dates[0],
                             'date_end': list_dates[1],
                             'optimize': False,
                             'real_time': False})
    print(f"pull boiler data between {list_dates[0]} and {list_dates[1]}")
    try:
        response = r.json()['body']
        return response
    except:
        print(f"error pulling boiler data for {list_dates}")


def pull_boiler_data(start_date, end_date, metric='boileron', export=False):
    """
    From the full list of temperature, iterate over each date.
    Return a DataFrame with date and temperature
    """
    range_dates = split_dates(start_date, end_date)

    data = {}

    for p in range_dates:
        t = pull_boiler_data_from_list(p, metric)
        data.update(t)

    df = pd.DataFrame.from_dict(data,
                                orient='index').reset_index()

    df['date'] = pd.to_datetime(df['index'],
                                unit='s')

    df.rename(columns={0: metric},
              inplace=True)
    if export:
        df.to_csv(
            f'export/netatmo_agg_boiler_data_{metric}_{start_date}_{end_date}.csv')

    return df[['date', metric]]


# %%
pull_temperature('2020-01-01', '2022-01-15', export=True)

# %%
