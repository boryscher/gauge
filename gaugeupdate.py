#!/usr/bin/env python3

import pymysql
import datetime
import configparser
import time

from utilities.utils import update_gauge, calculate_gauge
from sshtunnel import SSHTunnelForwarder

# Database / Gauge Config
config = configparser.ConfigParser()
config.read('config.ini')
GPIO = [14, 15, 23, 24]

sql_update = f"""UPDATE data_current
                SET
                upd = %s
                WHERE
                data_source = %s"""

# Query New Data - Ping
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
        cur.execute("SELECT val_1, data_source FROM data_current WHERE upd = 'New';")
        new_value = cur.fetchone()
        if not new_value:
            conn.close()
            continue
        new_value, data_source = new_value[0][0], new_value[0][1]
        val_update = ('Old', data_source)
        cur.execute(sql_update, val_update)
        conn.commit()
        cur.execute("SELECT * FROM gauges.gauge_location WHERE gauge = %s ORDER by idgauge_location DESC LIMIT 1;",
                    data_source)
        loc_result = cur.fetchone()
        if loc_result:
            current_location = loc_result[4]
            current_percent = loc_result[2]
            old_value = int(loc_result[6])
        else:
            current_location = 0
            current_percent = 0
            old_value = 0
        cur.execute("SELECT * FROM gauges.gauge_details WHERE gauge = %s ORDER by gaugeid DESC LIMIT 1;", data_source)
        gauge_details = cur.fetchone()
        total_steps = gauge_details[2]
        max_degree = gauge_details[3]
        min_degree = gauge_details[4]
        max_value = gauge_details[5]
        min_value = gauge_details[6]
        max_steps = total_steps * max_degree / 360
        min_steps = gauge_details[8]
        gauge = data_source

        current_value, current_degree, degree_to_move, value_to_move, previous_degree, movement, new_percent, \
            current_step = calculate_gauge(new_value, old_value, max_degree, min_value, max_value, max_steps)

        # Update Gauge Location
        if old_value != new_value:
            update_gauge(GPIO, movement)

        # save current location
        sql_new = "INSERT INTO gauge_location (gauge, percent, movement, location, datetime, raw_value, logic) " \
                  "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val_new = (gauge, new_percent, movement, current_step, datetime.datetime.now(), new_value, '1')
        cur.execute(sql_new, val_new)
        cur.commit()
        conn.close()
    time.sleep(60)
