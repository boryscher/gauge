import requests
import re
import pymysql
import configparser
import datetime
import time

from sshtunnel import SSHTunnelForwarder
from bs4 import BeautifulSoup

# DB Config
config = configparser.ConfigParser()
config.read('config.ini')

hdr = {'User-Agent': 'Mozilla/5.0'}
url = config['stock']['URL']
page = requests.get(url, headers=hdr)

print(page.status_code)
soup = BeautifulSoup(page.text, 'html.parser')

company = soup.find('a', {'class': 'Fz(s) Ell Fw(600) C($linkColor)'}).text
price = soup.find('fin-streamer', {'class': 'Fz(s) Mt(4px) Mb(0px) Fw(b) D(ib)'}).text
change = soup.find('fin-streamer', {'data-field': 'regularMarketChangePercent'}).text
change = re.sub(r'[()]', '', change)
output = ', '.join((company, price, change))

change = change.rstrip("%")
change = float(change)

sql = "INSERT INTO data_archive (val_1, val_4, data_source, datetime, description) VALUES (%s, %s, %s, %s, %s)"
val = (change, output, '4', datetime.datetime.now(), 'Stock Scraper')
val_update = (float(change), datetime.datetime.now(), 'Stock Scraper', 'New')
sql_update = f"""UPDATE data_current
                SET
                val_1 = %s,                
                datetime = %s,
                description = %s,
                upd=%s
                WHERE
                data_source = 4"""

cycle_time = datetime.datetime.now() + datetime.timedelta(seconds=float(config['cycle_length']['cycle_length']))
while datetime.datetime.now() < cycle_time:
    with SSHTunnelForwarder(
            (config['mysql']['ssh_host'], int(config['mysql']['ssh_port'])),
            ssh_username=config['mysql']['ssh_user'],
            ssh_password=config['mysql']['ssh_pass'],
            remote_bind_address=(config['mysql']['MySQL_hostname'], int(config['mysql']['sql_port']))) as tunnel:
        conn = pymysql.connect(host='127.0.0.1', user=config['mysql']['sql_username'],
                               passwd=config['mysql']['sql_password'], db=config['mysql']['sql_main_database'],
                               port=tunnel.local_bind_port)
        cur = conn.cursor()
        cur.execute("SELECT val_1 FROM data_current WHERE data_source = 4")
        existing_record = cur.fetchone()
        if not existing_record:
            sql_new = "INSERT INTO data_current (val_1, datetime, description, upd, data_source) VALUES " \
                      "(%s, %s, %s, %s, %s)"
            val_new = (float(change), datetime.datetime.now(), 'Stock_scraper', 'New', 4)
            cur.execute(sql_new, val_new)
            conn.commit()
            old_value = None
        else:
            old_value = float(existing_record[0])
        if old_value == change:
            conn.close()
            continue
        cur.execute(sql, val)
        conn.commit()
        cur.execute(sql_update, val_update)
        conn.commit()
        conn.close()
    time.sleep(60)
