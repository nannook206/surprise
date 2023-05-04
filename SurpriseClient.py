#!/usr/bin/python3
'''
generic deviceHandler class
'''

import asyncio
import fcntl
import json
import logging
import params
from playSound import playSound
import queue
import random
import sys
import threading


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


class genericDeviceHandler():


    class NoDeviceFound(Exception):
        pass


    def __init__(self, deviceQ, max_a=params.HARD_MAX_A, max_b=params.HARD_MAX_B,
                       test=False):
        self.queue = deviceQ
        self.test = test
        self.hard_max_a = max_a
        self.hard_max_b = max_b
        logging.info('hardcoded max_a %d, max_b %d' % (max_a, max_b))
        self.max_a = max_a
        self.max_b = max_b
        self.max_a_min = 0
        self.max_b_min = 0
        self.ma_low = 0
        self.ma_high = 255
        self.seqNr = 1

    def connect(self):
        raise(NotImplemented)

    def reconnect(self):
        raise(NotImplemented)

    def randomMA(self):
        return random.randint(self.ma_low, self.ma_high)

    def setMinimum(self, zero=False):
        if zero:
            self.max_a_min = 0
            self.max_b_min = 0
        else:
            self.max_a_min = self.max_a
            self.max_b_min = self.max_b

    def setLevelsFromDevice(self):
        raise(NotImplemented)

    def adjustLevels(self, delta_a, delta_b):
        return self.setLevels(self.max_a + delta_a, self.max_b + delta_b)

    def setLevels(self, max_a, max_b, fromUser=True):
        prev_max_a = self.max_a
        prev_max_b = self.max_b
        logging.info('requested levels: max_a %d, max_b %d' % 
                      (max_a, max_b))
        max_a = max(self.max_a_min, max_a)
        max_b = max(self.max_b_min, max_b)
        if max_a <= self.hard_max_a:
            self.max_a = max_a
        if max_b <= self.hard_max_b:
            self.max_b = max_b
        self.max_plus_a = min(int(self.max_a * params.MAX_PLUS_LEVEL), self.hard_max_a)
        self.max_plus_b = min(int(self.max_b * params.MAX_PLUS_LEVEL), self.hard_max_b)
        self.norm_a = int(self.max_a * params.NORMAL_LEVEL)

        self.norm_b = int(self.max_b * params.NORMAL_LEVEL)
        self.low_a = int(self.max_a * params.LOW_LEVEL)
        self.low_b = int(self.max_b * params.LOW_LEVEL)
        if prev_max_a != self.max_a:
            logging.info('setting levels A: %d, %d, %d, %d' % 
                         (self.low_a, self.norm_a, self.max_a, self.max_plus_a))
        if prev_max_b != self.max_b:
            logging.info('setting levels B: %d, %d, %d, %d' % 
                         (self.low_b, self.norm_b, self.max_b, self.max_plus_b))
        # If nothing changed, say 'sorry'.
        if prev_max_a == self.max_a and prev_max_b == self.max_b and fromUser:
            logging.info('sorry')
            playSound('sorry')
            return False
        return True

    def start(self):
        logging.info('deviceClient start')
        try:
            asyncio.get_event_loop().run_until_complete(self.run())
        except Exception as e:
            logging.error('deviceClient.start starting new event loop')
            asyncio.new_event_loop().run_until_complete(self.run())
        
    async def run(self):
        logging.info('deviceClient run')
        while True:
            logging.info('calling producer_handler')
            await self.producer_handler()
            logging.info('returned from producer_handler')

    async def drainQueue(self):
        logging.info('draining %d commands' % self.queue.qsize())
        while not self.queue.empty():
            _ = self.queue.get()
            self.queue.task_done()
        self.queue.put({'cmd': 'off'})

    async def producer_handler(self):
        while True:
            try:
                # logging.info('---- producer_handler called: qsize %d ----' % self.queue.qsize())
                command = self.queue.get()
                self.queue.task_done()
                await self.processCommand(command)
            except Exception as e:
                # TODO(me): need to reopen device at this point
                logging.info('device no longer open: %s' % e)
                self.reconnect()
                await self.drainQueue()

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
        raise(NotImplemented)


#
#  Everyting below here is for testing only.
#

def enqueueCommands(deviceQ, commands):
    #cmdIndex = 0
    #while cmdIndex < len(commands):
    for command in commands:
        #command = deviceQ.put(commands[cmdIndex])
        print('enqueing: %s' % command)
        deviceQ.put(command)
        #cmdIndex += 1

def runTest(device):
    def modeCode(name):
        global ModeCodes
        return ModeCodes[name]

    print('runTest')
    testCommands = [
        {'cmd': 'reserve'},
        {'cmd': 'off'},
        {'cmd': 'on'},
        {'cmd': 'set_ma', 'value': 17},
        {'cmd': 'set_mode', 'value': modeCode('ramp')},
        {'cmd': 'set_level_a', 'value': 20},
        {'cmd': 'set_level_b', 'value': 20},
        {'cmd': 'on_low'},
        {'cmd': 'set_level_a', 'value': 21},
        {'cmd': 'set_minimum_from_device'},
        {'cmd': 'adjust_ab', 'a': 1, 'b': 0, 'activate': True},
        {'cmd': 'set_minimum', 'value': False},
        {'cmd': 'adjust_ab', 'a': 0, 'b': -1, 'activate': True},
        {'cmd': 'set_minimum', 'value': True},
        {'cmd': 'adjust_ab', 'a': 0, 'b': -1, 'activate': True},
        {'cmd': 'set_mode', 'value': modeCode('waves')},
        {'cmd': 'on_norm'},
        {'cmd': 'on_max_plus'},
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
    enqueueCommands(device.queue, testCommands)

    device.start()


if __name__ == "__main__":
    print('running tests')
    logging.basicConfig(level=logging.DEBUG)
    device = genericDeviceHandler(queue.Queue())
    runTest(device)
    # asyncio.get_event_loop().run_until_complete(runTest())
    print('done running tests')
