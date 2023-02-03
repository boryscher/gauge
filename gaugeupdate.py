#!/usr/bin/env python3

import pymysql
import datetime
import configparser

from utilities.utils import updateGauge, calculate_gauge
from sshtunnel import SSHTunnelForwarder

# Database / Gauge Config
config = configparser.ConfigParser()
config.read('config.ini')
gauge = 1
GPIO = [14, 15, 23, 24]

# Query New Data - Ping
with SSHTunnelForwarder(
        (config['mysql']['ssh_host'], int(config['mysql']['ssh_port'])),
        ssh_username=config['mysql']['ssh_user'],
        ssh_password=config['mysql']['ssh_pass'],
        remote_bind_address=(config['mysql']['MySQL_hostname'], int(config['mysql']['sql_port']))) as tunnel:
    conn = pymysql.connect(host='127.0.0.1', user=config['mysql']['sql_username'],
                           passwd=config['mysql']['sql_password'], db=config['mysql']['sql_main_database'],
                           port=tunnel.local_bind_port)
    cur = conn.cursor()
    cur.execute("SELECT val_1 FROM data_current WHERE data_source='4';")
    new_value = float(cur.fetchall()[0][0])
    cur.execute("SELECT * FROM gauges.gauge_location WHERE gauge = 1  ORDER by idgauge_location DESC LIMIT 1;")
    loc_result = cur.fetchone()
    if loc_result:
        current_location = loc_result[4]
        current_percent = loc_result[2]
        old_value = int(loc_result[6])
    else:
        current_location = 0
        current_percent = 0
        old_value = 0
    cur.execute("SELECT * FROM gauges.gauge_details WHERE gauge = 1  ORDER by gaugeid DESC LIMIT 1;")
    gauge_details = cur.fetchone()
    total_steps = gauge_details[2]
    max_degree = gauge_details[3]
    min_degree = gauge_details[4]
    max_value = gauge_details[5]
    min_value = gauge_details[6]
    max_steps = total_steps * max_degree / 360
    min_steps = gauge_details[8]

    current_value, current_degree, degree_to_move, value_to_move, previous_degree, movement, new_percent, current_step \
        = calculate_gauge(new_value, old_value, max_degree, min_value, max_value, max_steps)

    # Update Gauge Location
    if old_value != new_value:
        updateGauge(GPIO, movement)


    # save current location
    sql = "INSERT INTO gauge_location (gauge,percent,movement,location,datetime,raw_value,logic) VALUES ga(%s,%s,%s,%s,%s,%s,%s)"
    val = (gauge, new_percent, movement, current_step, datetime.datetime.now(), new_value, '1')
    cur.execute(sql, val)
    cur.commit()
    conn.close()

