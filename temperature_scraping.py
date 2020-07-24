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
          .format(day=date.day, month = date.month - 1, year=date.year)

    print('fetching date {d}'.format(d=date))

    r = requests.get(url)
    text = r.text
    soup = BeautifulSoup(text, 'html.parser')
    table = soup.find('table', {'bordercolor': '#C0C8FE', 
                                'bgcolor':'#EBFAF7'})
    data = []
    n_rows = len(table.find_all('tr')) - 1 #number of rows in table. Some dates do not have all hours (e.g: July 9th, 2019)
    for row in range(1, n_rows):
        hour_raw = table.find_all('tr')[row].find_all('td')[0].text
        hour = int(re.split(' ', hour_raw)[0])
        datetime = date + timedelta(hours=hour)
        datetime = datetime.strftime('%Y-%m-%d %H:%M')

        temp_raw = table.find_all('tr')[row].find_all('td')[4].text
        if len(re.split(' ', temp_raw)) > 1: #Some temperature data do not exist (e.g: May 18th, 2020 23h).
            temp = float(re.split(' ', temp_raw)[0])
        else:
            temp = 'NA'

        data.append({'datetime':datetime, 
                     'temp': temp})
    time.sleep(0.5)

    return data 

def write_file(date, list):
    date_file = date.strftime('%Y-%m-%d')
    with open('export/export_temp_{date}.txt'.format(date=date_file), 'w') as f:
        f.write(str(list))

def retrieve_temp_period(start_date, end_date):
    """
    Request meteo ciel URL and retrieve 
    temperature data between two YYYY-MM-DD dates
    """
    data = []
    dates = pd.date_range(start=start_date, end=end_date)

    for d in dates:
        result = parse_day(d)
        write_file(d, result)
        data.append(result)
    return data

def read_export_files(path):
    """
    Iterate in a folder with exported txt files. Return a list.
    """
    data = []
    path_folder = os.path.join(path)
    for file in os.listdir(path_folder):
        with open(os.path.join(path_folder, file), 'r') as f:
            l = ast.literal_eval(f.read())
            data.append(l)
    return data

def export_temp_df(path):
    """
    Read all txt files, return a Pandas DataFrame.
    """
    data = read_export_files(path)
    data = [item for sublist in data for item in sublist]
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(path, 'temp_all_paris.csv'))
    return df