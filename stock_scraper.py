import requests
import re
import pymysql
import configparser
import datetime

from sshtunnel import SSHTunnelForwarder
from bs4 import BeautifulSoup

#DB Config
config = configparser.ConfigParser()
config.read('config.ini')

hdr = {'User-Agent': 'Mozilla/5.0'}
url = config['stock']['URL']
page = requests.get(url, headers=hdr)
data_source = 'Stock Scraper'
print(page.status_code)
soup = BeautifulSoup(page.text, 'html.parser')

company = soup.find('a', {'class': 'Fz(s) Ell Fw(600) C($linkColor)'}).text
price = soup.find('fin-streamer', {'class': 'Fz(s) Mt(4px) Mb(0px) Fw(b) D(ib)'}).text
change = soup.find('fin-streamer', {'data-field': 'regularMarketChangePercent'}).text
change = re.sub(r'[()]', '', change)
output = ', '.join((company, price, change))

change = change.rstrip("%")
change = float(change)

sql = "INSERT INTO data_archive (val_1,val_4,data_source,datetime,description) VALUES (%s,%s, %s, %s,%s)"
val = (change, output, '4', datetime.datetime.now(), data_source)
val_update = (float(change), '4', datetime.datetime.now(), data_source)
sql_update = f"""UPDATE data_current
                SET
                val_1 = %s,
                data_source = %s,
                datetime = %s,
                description = %s
                WHERE
                iddata = '4'"""

with SSHTunnelForwarder(
        (config['mysql']['ssh_host'], int(config['mysql']['ssh_port'])),
        ssh_username=config['mysql']['ssh_user'],
        ssh_password=config['mysql']['ssh_pass'],
        remote_bind_address=(config['mysql']['MySQL_hostname'], int(config['mysql']['sql_port']))) as tunnel:
    conn = pymysql.connect(host='127.0.0.1', user=config['mysql']['sql_username'],
            passwd=config['mysql']['sql_password'], db=config['mysql']['sql_main_database'],
            port=tunnel.local_bind_port)
    cur = conn.cursor()

    cur.execute(sql, val)
    conn.commit()
    cur.execute(sql_update, val_update)
    conn.commit()
    conn.close()
