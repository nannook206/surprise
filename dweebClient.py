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
        self.max_a = max_a
        self.max_b = max_b
        self.norm_a = max_a - 3
        self.norm_b = max_b - 6
        self.low_a = max_a - 6
        self.low_b = max_b - 12
        self.seqNr = 1
        self.devix = self.findDevice('ET 232')
        logging.error('dweebClient class instance created')

    def start(self):
        logging.info('dweebClient start')
        try:
            asyncio.get_event_loop().run_until_complete(self.run())
        except RuntimeError as e:
            logging.error(e)
            asyncio.new_event_loop().run_until_complete(self.run())
        
    async def run(self):
        logging.info('dweebClient run')
        try:
            async with websockets.connect(self.WSUrl) as websocket:
                logging.info('websocket: %s', websocket)
                await self.producer_handler(websocket)
        except Exception as e:
            logging.error('websocket open failed.  already in use?')
            logging.error(e)

    class NoDeviceFound(Exception):
        pass

    def findDevice(self, device):
        for device in self.devices:
            if device['name'] == 'ET 232':
                return device['devix']
        logging.fatal('No ET 232 found in device list')
        raise NoDeviceFound

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
            await self.processCommand(ws, command)

    async def processCommand(self, ws, command):
        if command == None:
            logging.info('Commands finished.')
            return
        else:
            logging.info('processing %s' % command)
            cmd = command['cmd']
            if cmd == 'reserve' or cmd == 'release':
                resp = await self.sendAndReceive(ws, cmd)
                logging.info(resp)
                await asyncio.sleep(1.0)
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
    runTest()
    # asyncio.get_event_loop().run_until_complete(runTest())
    print('done running tests')
