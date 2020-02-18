#!/usr/bin/python3
'''
buttshock-py client interface an ErosTek ET232
'''

import asyncio
import fcntl
import json
import logging
import pprint
import queue
import random
import sys
import threading
from time import sleep

sys.path.insert(0, "/home/pi/git/buttshock-py/")

import buttshock.et232


ModeCodes = {
    'throb': 0,
    'climb': 1,
    'audio-loud': 2,
    'audio-waves': 3,
    'combo': 4,
    'hi-freq': 5,
    'audio-soft': 6,
    'user': 7,
    'thump': 8,
    'ramp': 9,
    'intense': 10,
    'waves': 11,
    'thrust': 12,
    'stroke': 13,
    'random': 14,
    'off': 15,
}

def modeCode(name):
    global ModeCodes
    return ModeCodes[name]

ModeNames = ['throb',      'climb',      'audio-loud',  'audio-waves',
             'combo',      'hi-freq',    'audio-soft',  'user',
             'thump',      'ramp',       'intense',     'waves',
             'thrust',     'stroke',     'random',      'off']

def modeName(code):
    global ModeNames
    return ModeNames[code]


class deviceHandler():


    class NoDeviceFound(Exception):
        pass


    def __init__(self, deviceQ, max_a=105, max_b=135,
                       port='/dev/ttyUSB0',
                       test=False):
        logging.info('creating buttshock deviceHandler instance')

        self.queue = deviceQ
        self.port = port
        self.test = test
        
        self.et232 = self.connect()

        self.hard_max_a = max_a
        self.hard_max_b = max_b
        logging.error('hardcoded max_a %d, max_b %d' % (max_a, max_b))
        self.max_a = max_a
        self.max_b = max_b
        self.ma_low = 0
        self.ma_high = 255
        self.setLevelsFromDevice()
        self.seqNr = 1
        logging.error('deviceClient class instance created')

    def connect(self):
        # Lock the serial port while we use it, wait a few seconds
        connected = False
        for _ in range(60*5):
            try:
                et232 = buttshock.et232.ET232SerialSync(self.port, debug=self.test)
                if et232.port.isOpen():
                    fcntl.flock(et232.port.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    connected = True
            except Exception as e:
                print(e)
                et232.close()
                sleep(.2)
                continue

            if (not connected):
                print ("Connect Failed")
                continue

            print ("[+] connected")
            try:
                et232.perform_handshake()
                print ("[+] handshake ok")
                break
            except Exception as e:
                print(e)
                et232.close()
                sleep(1)

        # reset overides if present
        et232.write(0xa4, [0])

        print_modes(et232)
        return et232

    def randomMA(self):
        return random.randint(self.ma_low, self.ma_high)

    def setLevelsFromDevice(self):
        level_a = self.et232.read(0x8c)
        level_b = self.et232.read(0x88)
        logging.error('Current levels: chA %d, chB %d' % (level_a, level_b))
        self.setLevels(level_a, level_b)

    def adjustLevels(self, delta_a, delta_b):
        self.setLevels(self.max_a + delta_a, self.max_b + delta_b)

    def setLevels(self, max_a, max_b):
        logging.error('set levels: max_a %d, max_b %d' % 
                      (max_a, max_b))
        if max_a < 0:
            max_a = 0
        if max_b < 0:
            max_b = 0
        if max_a <= self.hard_max_a:
            self.max_a = max_a
        if max_b <= self.hard_max_b:
            self.max_b = max_b
        self.norm_a = int(self.max_a * 0.88)
        self.norm_b = int(self.max_b * 0.88)
        self.low_a = int(self.max_a * 0.73)
        self.low_b = int(self.max_b * 0.73)
        logging.error('setting levels: max_a %d, max_b %d' % 
                      (self.max_a, self.max_b))
        logging.error('setting levels: norm_a %d, norm_b %d' % 
                      (self.norm_a, self.norm_b))
        logging.error('setting levels: low_a %d, low_b %d' % 
                      (self.low_a, self.low_b))

    def start(self):
        logging.error('deviceClient start')
        try:
            asyncio.get_event_loop().run_until_complete(self.run())
        except RuntimeError as e:
            logging.error('deviceClient.start starting new event loop')
            asyncio.new_event_loop().run_until_complete(self.run())
        
    async def run(self):
        logging.error('deviceClient run')
        while True:
            logging.error('calling producer_handler')
            await self.producer_handler()
            logging.error('returned from producer_handler')

    async def producer_handler(self):
        while True:
            try:
                # logging.info('---- producer_handler called: qsize %d ----' % self.queue.qsize())
                command = self.queue.get()
                await self.processCommand(command)
            except Exception as e:
                # TODO(me): need to reopen device at this point
                logging.info('device no longer open: %s' % e)
                self.et232.close()
                self.et232 = self.connect()

    def invalidValue(self, cmd, value):
        if cmd == 'set_level_a':
            if value < 0 or value > self.max_a:
                logging.error('Invalid A level %d: max is %d' % (value, self.max_a))
                return True
        elif cmd == 'set_level_b':
            if value < 0 or value > self.max_b:
                logging.error('Invalid B level %d: max is %d' % (value, self.max_b))
                return True
        elif cmd == 'set_mode':
            if value not in ModeCodes:
                logging.error('Invalid mode: %d' % value)
                return True
        elif cmd == 'set_ma':
            if value < self.ma_low or value > self.ma_high:
                logging.error('Invalid mode: %d' % value)
                return True
        else:
            logging.error('Invalid command: %s' % cmd)
            return True
        return False

    async def processCommand(self, command):
        if command == None:
            logging.error('Commands finished.')
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
            elif cmd == 'on_max_a':
                self.et232.write(0x8c, [self.max_a])
                self.et232.write(0x88, [0])
            elif cmd == 'on_max_b':
                self.et232.write(0x8c, [0])
                self.et232.write(0x88, [self.max_b])
            elif cmd == 'adjust_a':
                value = command['value']
                self.adjustLevels(2*value, 0)
                self.et232.write(0x8c, [self.max_a])
            elif cmd == 'adjust_b':
                value = command['value']
                self.adjustLevels(0, 2*value)
                self.et232.write(0x88, [self.max_b])
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


def print_modes(et232):
    modes = {0x0b:"Waves",     0x0a:"Intense",   0x0e:"Random",
             0x06:"AudioSoft", 0x02:"AudioLoud", 0x03:"AudioWaves",
             0x07:"User",      0x05:"HiFreq",    0x01:"Climb",
             0x00:"Throb",     0x04:"Combo",     0x0c:"Thrust",
             0x08:"Thump",     0x09:"Ramp",      0x0d:"Stroke",
             0x0f:"Off",
            }

    print('Mode: %s, MA %d, chA %d, chB %d, D3 timer %d' % (
       modes[et232.read(0xa3)], et232.read(0x89),
       et232.read(0x8c), et232.read(0x88), et232.read(0xd3)))
    return

def enqueueCommands(deviceQ, commands):
    #cmdIndex = 0
    #while cmdIndex < len(commands):
    for command in commands:
        #command = deviceQ.put(commands[cmdIndex])
        print('enqueing: %s' % command)
        deviceQ.put(command)
        #cmdIndex += 1

def runTest():
    print('runTest')
    deviceQ = queue.Queue()
    device = deviceHandler(deviceQ, max_a=70, max_b=105, test=True)
    testCommands = [
        {'cmd': 'reserve'},
        {'cmd': 'off'},
        {'cmd': 'on'},
        {'cmd': 'set_ma', 'value': -17},
        {'cmd': 'set_mode', 'value': modeCode('ramp')},
        {'cmd': 'set_level_a', 'value': 20},
        {'cmd': 'set_level_b', 'value': 20},
        {'cmd': 'set_mode', 'value': modeCode('waves')},
        {'cmd': 'set_level_b', 'value': 2323},
        {'cmd': 'set_mode', 'value': modeCode('intense')},
        {'cmd': 'off'},
        {'cmd': 'release'},
        {'cmd': 'reserve'},
        {'cmd': 'set_mode', 'value': 42},
        {'cmd': 'set_level_a', 'value': 30},
        {'cmd': 'set_level_b', 'value': 30},
        {'cmd': 'set_mode', 'value': modeCode('thrust')},
        {'cmd': 'on_max'},
        {'cmd': 'set_mode', 'value': modeCode('intense')},
        {'cmd': 'release'},
    ]
    enqueueCommands(deviceQ, testCommands)

    device.start()


if __name__ == "__main__":
    print('running tests')
    logging.basicConfig(level=logging.DEBUG)
    runTest()
    # asyncio.get_event_loop().run_until_complete(runTest())
    print('done running tests')
