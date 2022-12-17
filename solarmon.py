#!/usr/bin/env python3

import time
import os
import requests

from configparser import RawConfigParser
from influxdb import InfluxDBClient
from pymodbus.client import ModbusSerialClient as ModbusClient
#from pymodbus.client.sync import ModbusSerialClient as ModbusClient

from growatt import Growatt

settings = RawConfigParser()
settings.read(os.path.dirname(os.path.realpath(__file__)) + '/solarmon.cfg')

interval = settings.getint('query', 'interval', fallback=1)
offline_interval = settings.getint('query', 'offline_interval', fallback=60)
error_interval = settings.getint('query', 'error_interval', fallback=60)

db_name = settings.get('influx', 'db_name', fallback='inverter')
measurement = settings.get('influx', 'measurement', fallback='inverter')

# Clients
if (settings.get('influx', 'host', fallback=None)):
    print('Setup InfluxDB Client... ', end='')
    influx = InfluxDBClient(host=settings.get('influx', 'host', fallback='localhost'),
                        port=settings.getint('influx', 'port', fallback=8086),
                        username=settings.get(
                            'influx', 'username', fallback=None),
                        password=settings.get(
                            'influx', 'password', fallback=None),
                        database=db_name)
    influx.create_database(db_name)
    print('Done!')

print('Setup Serial Connection... ', end='')
port = settings.get('solarmon', 'port', fallback='/dev/ttyUSB0')
client = ModbusClient(method='rtu', port=port, baudrate=9600,
                      stopbits=1, parity='N', bytesize=8, timeout=1)
client.connect()
if client is None:
    print('client je null')

print('Done!')

print('Loading inverters... ')
inverters = []
for section in settings.sections():
    if not section.startswith('inverters.'):
        continue

    name = section[10:]
    unit = int(settings.get(section, 'unit'))
    measurement = settings.get(section, 'measurement')
    growatt = Growatt(client, name, unit)
    growatt.print_info()
    inverters.append({
        'error_sleep': 0,
        'growatt': growatt,
        'measurement': measurement
    })
print('Done!')

while True:
    online = False
    for inverter in inverters:
        # If this inverter errored then we wait a bit before trying again
        if inverter['error_sleep'] > 0:
            inverter['error_sleep'] -= interval
            continue

        growatt = inverter['growatt']
        try:
            now = time.time()
            info = growatt.read()

            if info is None:
                continue

            # Mark that at least one inverter is online so we should continue collecting data
            online = True

            points = [{
                'time': int(now),
                'measurement': inverter['measurement'],
                "fields": info
            }]

            print('Inverter ' + growatt.name + ': data captured')

            if (settings.get('influx', 'host', fallback=None)):
                if not influx.write_points(points, time_precision='s'):
                    print("Failed to write to InfluxDB!")
                else:
                    print("InfluxDB update successfully")

            postUri = settings.get('prometheus', 'postUri', fallback=None)
            if postUri:
                token = "Bearer " + settings.get('prometheus', 'token', fallback=None)

                # Prometheus data format:
                # metric_name,label=abc teplota=35.1,vlhkost=79
                prom_data = ''
                for key, value in info.items():
                    if type(value) == str:    # Prometheus does not accept non-numeric values!
                         value = '"' + value + '"'
                    prom_data += ',' + str(key) + "=" + str(value)
                prom_data = 'g ' + prom_data[1:]
                # g is name of metric
                # in grafana is "g" prefix of variables


                print(str(prom_data))
                retCode = requests.post(postUri, data=str(prom_data), headers={
                                "Content-Type": "application/json", "Authorization": token}, timeout=2.50)

                print('Prometheus Return code: ' + str(retCode) + ' (204 is OK)')  # je zajimave, ze return 204 je OK :-)
          
        except Exception as err:
            print('Exception, growatt name: ' + growatt.name)
            print('Chyba: ', end='')
            print(err)
            inverter['error_sleep'] = error_interval

    if online:
        time.sleep(interval)
    else:
        # If all the inverters are not online because no power is being generated then we sleep for 1 min
        time.sleep(offline_interval)
