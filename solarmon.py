#!/usr/bin/env python3

import time
import os
import requests
import logging
import linecache


from logging.handlers import TimedRotatingFileHandler
from configparser import RawConfigParser
from influxdb import InfluxDBClient
from pymodbus.client import ModbusSerialClient as ModbusClient
#from pymodbus.client.sync import ModbusSerialClient as ModbusClient

from growatt import Growatt
from greenbono_socket import Greenbono
from automation import Automation

logHandler = TimedRotatingFileHandler("solarmon.log",when="midnight")
logFormatter = logging.Formatter('%(asctime)s %(message)s')
logHandler.setFormatter( logFormatter )
log = logging.getLogger('solarmon')
log.addHandler( logHandler )
log.setLevel( logging.INFO )

def merge(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result



def logException():
	exc_type, exc_obj, tb = sys.exc_info()
	f = tb.tb_frame
	lineno = tb.tb_lineno
	filename = f.f_code.co_filename
	linecache.checkcache(filename)
	line = linecache.getline(filename, lineno, f.f_globals)
	log.error('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))

deviceGrowatt = None
deviceGreenbono = None
myAutomation = None

settings = RawConfigParser()
settings.read(os.path.dirname(os.path.realpath(__file__)) + '/solarmon.cfg')

interval = settings.getint('query', 'interval', fallback=5)
error_interval = settings.getint('query', 'error_interval', fallback=60)

myAutomation = Automation()

# InfluxDB Clients
if (settings.get('influx', 'host', fallback=None)):
    db_name = settings.get('influx', 'db_name', fallback='inverter')
    log.debug('Setting up InfluxDB Client... ')
    influx = InfluxDBClient(host=settings.get('influx', 'host', fallback='localhost'),
                        port=settings.getint('influx', 'port', fallback=8086),
                        username=settings.get('influx', 'username', fallback=None),
                        password=settings.get('influx', 'password', fallback=None),
                        database=db_name)
    influx.create_database(db_name)
    log.debug('Done.')


if (settings.get('growatt', 'port', fallback=None)):
    log.debug('Setting up Modbus Connection... ')
    port = settings.get('growatt', 'port', fallback='/dev/ttyUSB0')
    modbusClient = ModbusClient(method='rtu', port=port, baudrate=9600, stopbits=1, parity='N', bytesize=8, timeout=1)
    modbusClient.connect()

    if modbusClient is None:
        log.info('Cant create Modbus client!')
    else:
        unit = int(settings.get('growatt', 'unit', fallback=1))
        measurementName = settings.get('influx', 'measurement', fallback='inverter')
        deviceGrowatt = Growatt(modbusClient, 'growatt', unit)
        log.info('Done.')
        deviceGrowatt.print_info()

if (settings.get('greenbono', 'host', fallback=None)):
    log.info('Setting up Greenbono Configuration... ')
    host = settings.get('greenbono', 'host', fallback=None)
    port = settings.get('greenbono', 'port', fallback=6770)
    ratio = settings.get('greenbono', 'voltage_ratio', fallback=1)
    deviceGreenbono = Greenbono(host, port, ratio)
    log.info('Done.')

if (settings.get('prometheus', 'postUri', fallback=None)):
    log.info('Setting up Prometheus Connection... ' )
    postUri = settings.get('prometheus', 'postUri', fallback=None)
    token = "Bearer " + settings.get('prometheus', 'token', fallback=None)
    prometheus = {
        'postUri': postUri,
        'token': token
    }
    log.info('Done.')

while True:
    online = False
    metrics = None
    metrics1 = {}
    metrics2 = {}
    metrics3 = {}

    try:
        now = time.time()
        if (deviceGrowatt):
            metrics1 = deviceGrowatt.read()
            log.debug('Inverter Growatt: data captured')


        if (deviceGreenbono):
            metrics2 = deviceGreenbono.read()
            log.debug('Watrouter Greenbono: data captured')

        if (metrics2 is not None):
            metrics = merge(metrics2, metrics1)
        else:
            metrics = metrics1
            log.error("Cant read data from Greenbono")

        if metrics is None:
            continue

        # Mark that at least one device is online so we should save collected data
        online = True

        metrics3 = myAutomation.count(metrics)
        if metrics3 is not None:
           metrics = merge(metrics, metrics3)


        #if (settings.get('influx', 'host', fallback=None)):
        if (influx):
            points = [{
                'time': int(now),
                'measurement': measurementName,
                "fields": metrics
            }]
            if not influx.write_points(points, time_precision='s'):
                log.error("Failed to write to InfluxDB!")
            #else:
                log.debug("InfluxDB update successfully")


        if (prometheus):
            # Prometheus data format:  metric_name,label=abc teplota=35.1,vlhkost=79
            prom_data = ''
            for key, value in metrics.items():
                if type(value) == str:    # Prometheus does not accept non-numeric values!
                    value = '"' + value + '"'
                prom_data += ',' + str(key) + "=" + str(value)
            prom_data = 'g ' + prom_data[1:]
            # g is name of metric
            # in grafana will be "g" prefix of variables

            log.info(str(prom_data))
            token = prometheus['token']
            uri = prometheus['postUri']
            retCode = requests.post(uri, data=str(prom_data), headers={
                            "Content-Type": "application/json", "Authorization": token}, timeout=2.50)

            if ('204' in str(retCode)):
                log.debug('Prometheus Return code: ' + str(retCode) + ' (204 is OK)')  # je zajimave, ze return 204 je OK :-)
            else:
                log.error('Prometheus Return code: ' + str(retCode) )  # je zajimave, ze return 204 je OK :-)
          
    except Exception as err:
        log.error('Exception in Solarmon flow')
        logException()
        log.error('Error: ' + str(err))

    if online:
        time.sleep(interval)
    else:
        time.sleep(error_interval)

