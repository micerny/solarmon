#!/usr/bin/env python3
import socket
import sys

import logging
log = logging.getLogger('solarmon')

def read_int8(row, index):
    return row[index]

def read_int16inv(row, index):
    return (row[index+1] * 256) + row[index]

def read_int16(row, index):
    return (row[index] * 256) + row[index + 1]

def read_signed16(row, index):
        return (-1) * (row[index +1] -  row[index])

def read_float16(row, index, units=10):
    return float((row[index] << 16) + row[index + 1]) / units

class Greenbono:
    def __init__(self, host, port, ratio):
        self.host = str(host)
        self.port = int(port)
        self.ratio = float(ratio)

    def read(self):
        info = None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            log.debug('Connecting to: ' + self.host + ':' + str(self.port))
            s.connect((self.host, self.port))
            s.settimeout(10)

            #  dotaz:   unit 8bit, funkce 8bit, zacatek 16bit , pocet 16bit), CRC 16bit
            #  odpoved: 8x8bit , unit 8bit, funkce 8bit, delka 8bit , DATA  (delka * 2x8bit), CRC 16bit
            # CRC lze ziskat tady: https://crccalc.com/   (zvolit CRC-16/MODBUS a obratit poradi HEXa cisel)
            # pozor, v odpovedi byva vice dat, nez je pozadovano v requestu
            #bb = bytes.fromhex('010400000050F036')  # vsechny hodnoty (80 bytu (50 v hexa)) z funkce 4
            #bb = bytes.fromhex('010400000009300C')  # prvni hodnoty z funkce 4
            #bb = bytes.fromhex('010400000014F005')  # prvnich 0x14 hodnot z funkce 4
            bb = bytes.fromhex('01040000001531C5')  # prvnich 0x15 hodnot z funkce 4

            s.sendall(bb)

            # nejdriv prijde zpatky cely request
            d = s.recv(4096)
            # prvni blok dat
            d = s.recv(4096)
            #    print('Received1: ', end='')
            #    for byte in d:
            #        print('{:02x}'.format(byte), end=' ')
            #    print('')
    
            if len(d) < 4:
                log.error('Error 9');
                log.error('Received data in second buffer are to short.');
                return None
    
            # zjistim delku prijatych dat:
            delka_celkova = d[2]    # tato hodnota je jednobytova a to je zvlastni
            log.debug('Delka celkova: ' + str(delka_celkova))
            log.debug('Delka prijatych dat: ' + str(len(d)) + ' - 3 zpocatku')
            delka_prijato = len(d) - 3
            # na konci cekavam jeste 16b CRC ale protoze ho nekontroluju, tak to nezapocitavam

            loop = 1
            payload = d[-delka_prijato:]
            while (delka_prijato < delka_celkova):
                loop += 1
                d = s.recv(4096)
                delka_prijato += len(d)
                payload = payload + d;

            #print('DATA: ')
            #i = 0
            #for byte in payload:
            #    print('{:02x}'.format(byte), end=' ')
            #    i += 1
            #    if not (i % 2):
            #        print(' ', end='')
            #    if not (i % 10):
            #        print('')
            #print('')
        
            if (delka_prijato < 20):
                log.error('Error 10')
                log.error('Received payload is to short.');
                return None
                

            voltage = round(read_int16(payload, 16)*self.ratio, 1)
            current1 = read_signed16(payload, 8)/10
            current2 = read_signed16(payload, 10)/10
            current3 = read_signed16(payload, 12)/10
            nakup = 0
            prodej = 0
            if (current1 > 0):
                nakup = nakup + current1  
            else:
                prodej = prodej + current1

            if (current2 > 0):
                nakup = nakup + current2
            else:
                prodej = prodej + current2

            if (current3 > 0):
                nakup = nakup + current3
            else:
                prodej = prodej + current3

            info = {
                #'Vsurova':      read_int16(payload, 6),
                #'VsurovaInv':      read_int16inv(payload, 6),
                #'VkalibrovanaInv': read_int16inv(payload, 16),
                #'OutputPI':     read_int8(payload, 18),
                #'SamplesCnt':     read_int8(payload, 19),
                # proudy pro smer dovnitr funguji:
                #'I1Smer':     ((256-i1)/10) if (i1 != 0) else 0,
                'gbo_I_L1':     current1,
                'gbo_I_L2':     current2,
                'gbo_I_L3':     current3,
                #'gbo_I_suma':     read_signed16(payload, 14)/10, tohle je stejna hodnota jako I1
                #'gbo_I_suma_moje':     (current1 + current2 + current3),
                'gbo_Power': round(voltage * (current1 + current2 + current3), 1),
                'gbo_Voltage': voltage,
                'gbo_nakup':  round(voltage * nakup, 1),
                'gbo_prodej': round(voltage * prodej, 1),
                'gbo_bilance': round(nakup + prodej)
                #'PpropL-1':        read_int8(payload, 20),
                #'PpropH-1':        read_int8(payload, 21),
                #'PpropL-2':        read_int8(payload, 38),
                #'PpropH-2':        read_int8(payload, 39),
                #'PpropL-3':        read_int8(payload, 54),
                #'PpropH-3':        read_int8(payload, 55),
                #'PI_sumaL-1':      read_int8(payload, 22),
                #'PI_sumaH-1':      read_int8(payload, 23),
                #'PI_sumaL-2':      read_int8(payload, 40),
                #'PI_sumaH-2':      read_int8(payload, 41),
                #'PI_sumaL-3':      read_int8(payload, 56),
                #'PI_sumaH-3':      read_int8(payload, 57)

            }
        
#            print('Debug: ')
#            for key, value in info.items():
#                print('       ' + key + ': ' + str(value))

        return info

