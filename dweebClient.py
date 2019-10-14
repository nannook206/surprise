#!/usr/bin/python3

import asyncio
import json
import logging
import pprint
import queue
import urllib.request
import websockets


ET232ModeCodes = {
    'off': 0,
    'waves': 1,
    'intense': 2,
    'random': 3,
    'audio-soft': 4,
    'audio-loud': 5,
    'audio-waves': 6,
    'user': 7,
    'hi-freq': 8,
    'climb': 9,
    'throb': 10,
    'combo': 11,
    'thrust': 12,
    'thump': 13,
    'ramp': 14,
    'stroke': 15,
}

ET232ModeNames = ['off',        'waves',      'intense',     'random',
                  'audio-soft', 'audio-loud', 'audio-waves', 'user',
                  'hi-freq',    'climb',      'throb',       'combo',
                  'thrust',     'thump',      'ramp',        'stroke']


class dweebClient():

    def __init__(self, dweebQ, max_a, max_b,
                       webUrl='http://localhost:31280/devices',
                       WSUrl='ws://localhost:31280/devices',
                       test=False):
        logging.info('creating dweebClient class instance')
        if not test:
            logger = logging.getLogger('websockets')
            logger.setLevel(logging.INFO)
            logger.addHandler(logging.StreamHandler())

        self.queue = dweebQ
        self.webUrl = webUrl
        self.WSUrl = WSUrl
        with urllib.request.urlopen(webUrl) as response:
            html = response.read()
            self.devices = json.loads(html.decode("utf-8"))
        dev = self.findDevice('ET 232')
        self.devix = dev['devix']
        logging.error('dweebClient init: devix = %s', dev['devix'])

        self.hard_max_a = max_a
        self.hard_max_b = max_b
        logging.error('hardcoded max_a %d, max_b %d' % (max_a, max_b))
        self.max_a = max_a
        self.max_b = max_b
        self.setLevelsFromState(dev['state'])
        self.seqNr = 1
        logging.error('dweebClient class instance created')

    def setLevelsFromState(self, state):
        '''
        This is a typical JSON state response.  We'll receive its a parsed dict.
        {"devix":6,"avail":"remote","mode":2,"status":"ready","level_a":27,"level_b":38,"ma":-31,"batt":0}'
        '''
        logging.debug('Current state: %s' % state)
        level_a = int(state['level_a'])
        level_b = int(state['level_b'])
        if level_a <= self.hard_max_a:
            self.max_a = level_a
        if level_b <= self.hard_max_b:
            self.max_b = level_b
        logging.error('setting levels: max_a %d, max_b %d' % 
                      (self.max_a, self.max_b))
        self.norm_a = self.max_a - 4
        self.norm_b = self.max_b - 7
        self.low_a = self.max_a - 7
        self.low_b = self.max_b - 14

    def start(self):
        logging.error('dweebClient start')
        try:
            asyncio.get_event_loop().run_until_complete(self.run())
        except RuntimeError as e:
            logging.error(e)
            asyncio.new_event_loop().run_until_complete(self.run())
        
    async def run(self):
        logging.error('dweebClient run')
        try:
            async with websockets.connect(self.WSUrl) as websocket:
                logging.error('websocket: %s', websocket)
                await self.producer_handler(websocket)
            logging.error('dweebClient run past websockets.connect')
        except Exception as e:
            logging.error('websocket open failed.  already in use?')
            logging.error(e)
        logging.error('dweebClient run completed')

    class NoDeviceFound(Exception):
        pass

    def findDevice(self, device):
        for dev in self.devices:
            if dev['name'] == device:
                return dev
        logging.fatal('No %s found in device list' % device)
        raise self.NoDeviceFound

    def invalidValue(self, cmd, value):
        if cmd == 'set_level_a':
            if value < 0 or value > self.max_a:
                logging.error('Invalid A level %d: max is %d' % (value, self.max_a))
                return True
        if cmd == 'set_level_b':
            if value < 0 or value > self.max_b:
                logging.error('Invalid B level %d: max is %d' % (value, self.max_b))
                return True
        if cmd == 'set_mode':
            if value < 0 or value > 15:
                logging.error('Invalid mode: %d' % value)
                return True
        if cmd == 'set_ma':
            if value < -50 or value > 50:
                logging.error('Invalid mode: %d' % value)
                return True
        return False

    async def producer_handler(self, ws):
        while True:
            logging.info('---- producer_handler called: qsize %d ----' % self.queue.qsize())
            command = self.queue.get(block=True)
            logging.info('---- processing %s' % command)
            await self.processCommand(ws, command)

    async def processCommand(self, ws, command):
        if command == None:
            logging.error('Commands finished.')
            return
        else:
            logging.info('processing %s' % command)
            cmd = command['cmd']
            if cmd == 'reserve':
                resp = await self.sendAndReceive(ws, cmd)
                logging.error(resp)
                self.setLevelsFromState(json.loads(resp))
                await asyncio.sleep(1.0)
            elif cmd == 'release':
                #resp = await self.sendAndReceive(ws, cmd)
                #logging.error(resp)
                #await asyncio.sleep(3.0)
                pass
            elif cmd == 'on_low':
                await self.setValue(ws, 'set_level_a', self.low_a)
                await self.setValue(ws, 'set_level_b', self.low_b)
            elif cmd == 'on' or cmd == 'on_norm':
                await self.setValue(ws, 'set_level_a', self.norm_a)
                await self.setValue(ws, 'set_level_b', self.norm_b)
            elif cmd == 'on_max':
                await self.setValue(ws, 'set_level_a', self.max_a)
                await self.setValue(ws, 'set_level_b', self.max_b)
            elif cmd == 'off':
                await self.setValue(ws, 'set_level_a', 0)
                await self.setValue(ws, 'set_level_b', 0)
            elif cmd[0:3] == 'set':
                value = command['value']
                if self.invalidValue(cmd, value):
                    return
                await self.setValue(ws, cmd, value)
            else:
                logging.error('Unknown command: %s' % cmd)

    async def setValue(self, ws, event, value):
        cmd = {'event': event, 'value': value}
        logging.error('setValue: cmd: %s' % cmd)
        await self.sendCommand(ws, cmd)
        await asyncio.sleep(0.1)

    async def sendAndReceive(self, ws, event):
        cmd = {'event': event}
        await self.sendCommand(ws, cmd)
        resp = await ws.recv()
        return(resp)

    async def sendCommand(self, ws, cmd):
        cmd['seqNr'] = self.seqNr
        self.seqNr += 1
        cmd['devix'] = self.devix
        commandStr = json.dumps(cmd)
        logging.info('Request: %s' % commandStr)
        await asyncio.sleep(1.0)
        await ws.send(commandStr)

testCommands = [
    {'cmd': 'reserve'},
    {'cmd': 'off'},
    {'cmd': 'on'},
    {'cmd': 'set_ma', 'value': -17},
    {'cmd': 'set_mode', 'value': ET232ModeCodes['ramp']},
    {'cmd': 'set_level_a', 'value': 20},
    {'cmd': 'set_level_b', 'value': 20},
    {'cmd': 'set_mode', 'value': ET232ModeCodes['waves']},
    {'cmd': 'set_level_b', 'value': 2323},
    {'cmd': 'set_mode', 'value': ET232ModeCodes['intense']},
    {'cmd': 'off'},
    {'cmd': 'release'},
    {'cmd': 'reserve'},
    {'cmd': 'set_mode', 'value': 42},
    {'cmd': 'set_level_a', 'value': 30},
    {'cmd': 'set_level_b', 'value': 30},
    {'cmd': 'set_mode', 'value': ET232ModeCodes['thrust']},
    {'cmd': 'on_max'},
    {'cmd': 'set_mode', 'value': ET232ModeCodes['intense']},
    {'cmd': 'release'},
]

def enqueueCommands(dweebQ):
    #cmdIndex = 0
    #while cmdIndex < len(testCommands):
    for command in testCommands:
        #command = dweebQ.put(testCommands[cmdIndex])
        print('enqueing: %s' % command)
        dweebQ.put(command)
        #cmdIndex += 1

#async def runTest():
def runTest():
    print('runTest')
    dweebQ = queue.Queue()
    enqueueCommands(dweebQ)
    dweeb = dweebClient(dweebQ, max_a=27, max_b=40, test=True)
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(dweeb.devices)
    dweeb.start()
    # await dweeb.run()


if __name__ == "__main__":
    print('running tests')
    logging.basicConfig(level=logging.DEBUG)
    runTest()
    # asyncio.get_event_loop().run_until_complete(runTest())
    print('done running tests')
