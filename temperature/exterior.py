# %%
import re
import time
import os
import ast
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from datetime import timedelta

"""
This script scrapes and returns temperature in Paris for Parc Montsouris from MeteoCiel
website. See https://www.meteociel.fr/temps-reel/obs_villes.php?code2=7156&jour2=18&mois2=4&annee2=2020
"""


def parse_day(date):
    """
    Given a date returns a dict of datetime, temperature.
    See format url https://www.meteociel.fr/temps-reel/obs_villes.php?code2=7156&jour2=1&mois2=0&annee2=2019
    """
    url = 'https://www.meteociel.fr/temps-reel/'\
          'obs_villes.php?code2=7156&'\
          'jour2={day}&mois2={month}&annee2={year}'\
          .format(day=date.day, month=date.month - 1, year=date.year)

    print('fetching temperature for date {d}'.format(d=date))

    r = requests.get(url)
    text = r.text
    soup = BeautifulSoup(text, 'html.parser')
    table = soup.find('table', {'bordercolor': '#C0C8FE',
                                'bgcolor': '#EBFAF7'})
    data = []
    # number of rows in table. Some dates do not have all hours (e.g: July 9th, 2019)
    n_rows = len(table.find_all('tr')) - 1
    for row in range(1, n_rows):
        hour_raw = table.find_all('tr')[row].find_all('td')[0].text
        hour = int(re.split(' ', hour_raw)[0])
        datetime = date + timedelta(hours=hour)
        datetime = datetime.strftime('%Y-%m-%d %H:%M')

        temp_raw = table.find_all('tr')[row].find_all('td')[4].text
        # Some temperature data do not exist (e.g: May 18th, 2020 23h).
        if len(re.split(' ', temp_raw)) > 1:
            temp = float(re.split(' ', temp_raw)[0])
        else:
            temp = 'NA'

        data.append({'datetime': datetime,
                     'temp': temp})
    time.sleep(0.5)

    return data


def parse_day_at_6pm(date):
    """
    Given a date returns a dict of datetime, temperature only at 6pm.
    See format url https://www.meteociel.fr/temps-reel/obs_villes.php?code2=7156&jour2=1&mois2=0&annee2=2019
    """
    url = 'https://www.meteociel.fr/temps-reel/'\
          'obs_villes.php?code2=7156&'\
          'jour2={day}&mois2={month}&annee2={year}'\
          .format(day=date.day, month=date.month - 1, year=date.year)

    print('fetching temperature for date {d}'.format(d=date))

    r = requests.get(url)
    text = r.text
    soup = BeautifulSoup(text, 'html.parser')
    table = soup.find('table', {'bordercolor': '#C0C8FE',
                                'bgcolor': '#EBFAF7'})
    temp_raw = table.find_all('tr')[6].find_all('td')[4].text
    datetime = (date + timedelta(hours=18)).strftime('%Y-%m-%d %H:%M')
    if len(re.split(' ', temp_raw)) > 1:
        temp = float(re.split(' ', temp_raw)[0])
    else:
        temp = 'NA'
    temp_at_6pm = {'datetime': datetime,
                   'temp': temp}
    time.sleep(0.5)

    return temp_at_6pm


def write_file(date, list):
    date_file = date.strftime('%Y-%m-%d')
    with open('/Users/martindaniel/Documents/compans_data/temperature/export/daily_export/export_temp_{date}.txt'.format(date=date_file), 'w') as f:
        f.write(str(list))


def retrieve_temp_period(start_date, end_date, export=True, all_hours=True):
    """
    Request meteo ciel URL and retrieve
    temperature data between two YYYY-MM-DD dates
    """
    data = []
    dates = pd.date_range(start=start_date, end=end_date)
    if export == True:
        for d in dates:
            if check_file_exist('/Users/martindaniel/Documents/compans_data/temperature/export/daily_export',
                                d) == False:
                if all_hours == True:
                    result = parse_day(d)
                else:
                    result = parse_day_at_6pm(d)
                write_file(d, result)
                data.append(result)
    else:
        for d in dates:
            if all_hours == True:
                result = parse_day(d)
            else:
                result = parse_day_at_6pm(d)
            data.append(result)
    return data


def check_file_exist(path, date):
    path_folder = os.path.join(path)
    filelist = os.listdir(path_folder)
    filename = "export_temp_{date}.txt".format(date=date)
    if filename in filelist:
        print('file {filename} already exists'.format(filename=filename))
        return True
    else:
        return False


def read_export_files(path):
    """
    Iterate in a folder with exported txt files. Return a list.
    """
    data = []
    path_folder = os.path.join(path)
    for file in os.listdir(path_folder):
        if file.endswith('txt'):
            with open(os.path.join(path_folder, file), 'r') as f:
                l = ast.literal_eval(f.read())
                data.append(l)
    return data


def get_ext_df(path):
    """
    Read all txt files, return a Pandas DataFrame.
    """
    data = read_export_files(path)
    data = [item for sublist in data for item in sublist]
    df = pd.DataFrame(data)
    return df


def export_agg_df(path):
    """
    Read all txt files, return a Pandas DataFrame.
    """
    print('exporting to csv')
    df = get_ext_df(path)
    df.to_csv('temperature/export/tmp_ext_paris.csv')

# %%
