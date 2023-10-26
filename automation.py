#!/usr/bin/env python3

import logging
log = logging.getLogger('solarmon')

import os
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
#------------------------------------------
# PIN stav LOW sepne relatko
PIN_NT = 12         # bojler na NT, LOW se spousti
PIN_BOJLER_ON = 16  # bojler ON
PIN_FUN = 18        # chladici ventilator
#------------------------------------------


class Automation:

    fun_last_state = 0

    def __init__(self):
        log.info('Init Automation')
        GPIO.setwarnings(False) # Ignore warning for now
        GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
        GPIO.setup(PIN_NT, GPIO.OUT)
        GPIO.setup(PIN_BOJLER_ON, GPIO.OUT)
        GPIO.setup(PIN_FUN, GPIO.OUT)
        #GPIO.setup(PIN_FUN, GPIO.LOW)


    def count(self, data):
        info = None

        vyroba  = data['Ppv']
        baterie = data['SOC']
        teplota = data['Temp']

        bojler = 0

        if ( ((teplota > 35) and (Automation.fun_last_state == 1)) or (teplota > 40)):
        #if ( teplota > 40):
            GPIO.setup(PIN_FUN, GPIO.LOW)
            Automation.fun_last_state = 1
        else:
            GPIO.setup(PIN_FUN, GPIO.HIGH)
            Automation.fun_last_state = 0

        if ((vyroba > 4000) or ((vyroba > 2000) and (baterie > 80))):
            bojler = 1

        if (((vyroba > 3000) and (vyroba > 95)) or ((vyroba > 5000) and (vyroba > 80))):
            bojler = 2
            GPIO.setup(PIN_NT, GPIO.LOW)
        else:
            GPIO.setup(PIN_NT, GPIO.HIGH)

        if (bojler > 0):
            GPIO.setup(PIN_BOJLER_ON, GPIO.LOW)
        else:
            GPIO.setup(PIN_BOJLER_ON, GPIO.HIGH)

        info = {
            'gbo_bojler': bojler,
            'fun': Automation.fun_last_state,
        }
        
        for key, value in info.items():
            log.debug('       ' + key + ': ' + str(value))

        return info

