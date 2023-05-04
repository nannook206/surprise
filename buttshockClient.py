#!/usr/bin/python3
'''
buttshock-py client interface an ErosTek ET232
'''

import asyncio
import fcntl
import json
import logging
import params
from playSound import playSound
import queue
import random
import SurpriseClient
import sys
import threading
from time import sleep

sys.path.insert(0, "/home/pi/git/buttshock-py/")

import buttshock.et232


def modeCode(name):
    return SurpriseClient.ModeCodes[name]

ModeNames = ['throb',      'climb',      'audio-loud',  'audio-waves',
             'combo',      'hi-freq',    'audio-soft',  'user',
             'thump',      'ramp',       'intense',     'waves',
             'thrust',     'stroke',     'random',      'off']

def modeName(code):
    global ModeNames
    return ModeNames[code]


class deviceHandler(SurpriseClient.genericDeviceHandler):


    def __init__(self, deviceQ, max_a=params.HARD_MAX_A, max_b=params.HARD_MAX_B,
                       port='/dev/ttyUSB0',
                       test=False):
        logging.info('creating buttshock deviceHandler instance')

        super(deviceHandler, self).__init__(deviceQ, max_a, max_b, test)

        self.ma_low = 0
        self.ma_high = 255
        self.port = port
        self.et232 = self.connect()
        self.setLevelsFromDevice()

        logging.info('buttshock deviceClient instance created')

    def connect(self):
        # Lock the serial port while we use it, wait a few seconds
        connected = False
        attempt = 0
        while True:
            try:
                et232 = buttshock.et232.ET232SerialSync(self.port, debug=self.test)
            except Exception as e:
                logging.error(e)
                sleep(0.2)
                continue
            if et232.port.isOpen():
                fcntl.flock(et232.port.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                connected = True

            if (not connected):
                logging.error("Connect Failed")
                continue

            logging.info("[+] device opened")
            try:
                et232.perform_handshake()
                logging.info("[+] connected")
                playSound('connected')
                break
            except Exception as e:
                logging.error(e)
                et232.close()
                if (attempt % 10) == 0:
                    playSound('device_connection_problem')
                sleep(5)
            attempt += 1

        # reset overides if present
        et232.write(0xa4, [0])

        logging.info('Mode: %s, MA %d, chA %d, chB %d, D3 timer %d' % (
          modeName(et232.read(0xa3)), et232.read(0x89),
          et232.read(0x8c), et232.read(0x88), et232.read(0xd3)))
        return et232

    def reconnect(self):
        self.et232.close()
        self.et232 = self.connect()

    def setLevelsFromDevice(self):
        level_a = self.et232.read(0x8c)
        level_b = self.et232.read(0x88)
        logging.info('Current (minimum) levels: chA %d, chB %d' % (level_a, level_b))
        self.setLevels(level_a, level_b, fromUser=False)

    async def processCommand(self, command):
        if command == None:
            logging.info('Commands finished.')
            return
        else:
            logging.info('processing %s' % command)
            cmd = command['cmd']
            if cmd == 'reserve':
                # enable overrides for MA, chA, chB
                self.et232.write(0xa4, [0x13])
            elif cmd == 'release':
                # disable overrides for MA, chA, chB
                self.et232.write(0xa4, [0x00])
            elif cmd == 'on_low':
                self.et232.write(0x8c, [self.low_a])
                self.et232.write(0x88, [self.low_b])
            elif cmd == 'on' or cmd == 'on_norm':
                self.et232.write(0x8c, [self.norm_a])
                self.et232.write(0x88, [self.norm_b])
            elif cmd == 'on_max':
                self.et232.write(0x8c, [self.max_a])
                self.et232.write(0x88, [self.max_b])
            elif cmd == 'on_max_plus':
                self.et232.write(0x8c, [self.max_plus_a])
                self.et232.write(0x88, [self.max_plus_b])
            elif cmd == 'on_max_a':
                self.et232.write(0x8c, [self.max_a])
                self.et232.write(0x88, [0])
            elif cmd == 'on_max_b':
                self.et232.write(0x8c, [0])
                self.et232.write(0x88, [self.max_b])
            elif cmd == 'adjust_ab':
                if (self.adjustLevels(2 * command['a'], 2 * command['b']) and
                    command['activate']):
                    if command['a'] != 0:
                        self.et232.write(0x8c, [self.max_a])
                    if command['b'] != 0:
                        self.et232.write(0x88, [self.max_b])
            elif cmd == 'set_minimum':
                value = command['value']
                self.setMinimum(zero=value)
                logging.info('setting levels: max_a_min %d, max_b_min %d' % 
                              (self.max_a_min, self.max_b_min))
            elif cmd == 'set_levels_from_device':
                self.setLevelsFromDevice()
            elif cmd == 'off':
                self.et232.write(0x8c, [0])
                self.et232.write(0x88, [0])
            elif cmd == 'set_ma':
                value = command['value']
                if self.invalidValue(cmd, value):
                    return
                self.et232.write(0x89, [value])
            elif cmd == 'set_mode':
                value = command['value']
                if self.invalidValue(cmd, value):
                    return
                self.et232.write(0xa3, [modeCode(value)])
                # Reset time timer every time we change mode
                self.et232.write(0xd3, [0])
            elif cmd == 'set_level_a':
                value = command['value']
                if self.invalidValue(cmd, value):
                    return
                self.et232.write(0x8c, [value])
            elif cmd == 'set_level_b':
                value = command['value']
                if self.invalidValue(cmd, value):
                    return
                self.et232.write(0x88, [value])
            else:
                logging.error('Unknown command: %s' % cmd)


if __name__ == "__main__":
    print('running tests')
    logging.basicConfig(level=logging.DEBUG)
    device = deviceHandler(deviceQ=queue.Queue(), max_a=105, max_b=135, test=True)
    SurpriseClient.runTest(device)
    # asyncio.get_event_loop().run_until_complete(runTest())
    print('done running tests')
