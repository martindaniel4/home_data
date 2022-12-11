from __future__ import print_function
import os
import argparse
import pygazpar
import pandas as pd
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


def get_args():
    """
    Returns the arguments provided to the script.
    That only works in prod, not in dev.
    """
    if ENV == 'prod':
        parser = argparse.ArgumentParser()

        # Define the arguments that the script should accept
        parser.add_argument('-u', '--username', help='gazpar username')
        parser.add_argument('-p', '--password', help='gazpar password')
        parser.add_argument('-i', '--identifier', help='gazpar pce identifier')
        parser.add_argument('-sb', '--sendinblue', help='Sendinblue API key')
        parser.add_argument('-r', '--recipient', help='email of the recipient')

        # Parse the provided arguments
        args = parser.parse_args()
        return args

ENV = 'dev'
NDAYS = 500
if ENV == 'prod':
    RECIPIENT = [{'email': get_args().recipient}]
else:
    RECIPIENT = [{'email': ''}]

def connect_grdf_client():
    """
    Builds the client to connect to GRDF.
    """
    if ENV == 'dev':
        client = pygazpar.Client(username=os.environ['GAZPAR_EMAIL'],
                                password=os.environ['GAZPAR_PWD'],
                                pceIdentifier=os.environ['GAZPAR_IDENTIFIER'],
                                meterReadingFrequency=pygazpar.Frequency.DAILY,
                                lastNDays=NDAYS)
    else:
        args = get_args()
        client = pygazpar.Client(username=args.username,
                                password=args.password,
                                pceIdentifier=args.identifier,
                                meterReadingFrequency=pygazpar.Frequency.DAILY,
                                lastNDays=NDAYS)
    return client

def pull_gaz_consumption_data():
    """
    Pulls the gaz consumption data from GRDF.
    """
    client = connect_grdf_client()
    client.update()
    data = client.data()
    return pd.DataFrame(data)

def get_last_day():
    """
    Returns the last day of the gaz consumption data.
    That allows us to know how far the data has been updated.
    """
    df = pull_gaz_consumption_data()
    return pd.to_datetime(df['time_period'], format="%d/%m/%Y").max().strftime("%b %d, %Y")

def get_run_date():
    """
    Returns the date of the run.
    """
    return pd.to_datetime('today').strftime("%b %d, %Y")

def group_by_week():
    """
    Groups the gaz consumption data by week.
    """
    df = pull_gaz_consumption_data()
    df['date'] = \
        pd.to_datetime(df['time_period'], 
                       format='%d/%m/%Y')
    df['week_ending'] = \
        df.date.dt.to_period('W').dt.end_time.dt.date

    wf = df.groupby('week_ending')\
      .agg({'energy_kwh': 'sum'})\
      .sort_values('week_ending')
    wf['energy_last_year'] = \
        wf['energy_kwh'].shift(52)
    wf.reset_index(inplace=True)
    wf['date'] = pd.to_datetime(wf.week_ending)\
        .dt.strftime("%b %d")
    return wf

def build_html_weekly_table():
    """
    Builds the html body of the email.
    """
    df = group_by_week()
    df.rename(columns={'energy_kwh': 'this_year', 
                       'energy_last_year': 'last_year'}, 
              inplace=True)
    week_table_html = \
        df.tail(10)\
            .sort_values('week_ending', 
                            ascending=False)\
            [['date', 'this_year', 'last_year']]\
            .set_index('date')\
            .T.to_html(border=0)
    return week_table_html

def build_html_body():
    """
    Builds the html body of the email.
    """
    run_date = get_run_date()
    last_day = get_last_day()
    title = f"<h2>Home data, {run_date}</h2>"
    subtitle = f"<p>Data from GRDF updated until: {last_day}</p>"
    table = build_html_weekly_table()

    html_body = \
    f"""<html>
        <body>
            {title}
            {subtitle}
            <div>{table}</div>
        </body>
    </html>"""
    return html_body

def send_email():
    configuration = sib_api_v3_sdk.Configuration()
    if ENV == 'dev':
        configuration.api_key['api-key'] = os.environ['SENDINBLUE_API_KEY']
    else:
        args = get_args()
        configuration.api_key['api-key'] = args.sendinblue
    # send email
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = f"Home data, {get_run_date()}"
    sender = {"name":"Home Data","email":"homedata@martindaniel.co"}
    html_content = build_html_body()
    to = RECIPIENT
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(to=to, html_content=html_content, sender=sender, subject=subject)

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(api_response)
    except ApiException as e:
        print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)
