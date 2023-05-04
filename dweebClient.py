#!/usr/bin/python3
'''
Dweeb client interface for an ErosTek ET232
'''

import asyncio
import json
import logging
import pprint
import queue
import SurpriseClient
import threading
import urllib.request
import websockets


def modeCode(name):
    return SurpriseClient.ModeCodes[name]

ModeNames = ['off',        'waves',      'intense',     'random',
             'audio-soft', 'audio-loud', 'audio-waves', 'user',
             'hi-freq',    'climb',      'throb',       'combo',
             'thrust',     'thump',      'ramp',        'stroke']

def modeName(code):
    global ModeNames
    return ModeNames[code]


class deviceHandler(SurpriseClient.genericDeviceHandler):


    def __init__(self, deviceQ, max_a=40, max_b=50,
                       webUrl='http://localhost:31280/devices',
                       WSUrl='ws://localhost:31280/devices',
                       test=False):
        logging.info('creating dweeb deviceHandler instance')
        if not test:
            logger = logging.getLogger('websockets')
            logger.setLevel(logging.INFO)
            logger.addHandler(logging.StreamHandler())

        super(deviceHandler, self).__init__(deviceQ, max_a, max_b, test)

        self.ma_low = -50
        self.ma_high = 50
        self.webUrl = webUrl
        self.WSUrl = WSUrl
        with urllib.request.urlopen(webUrl) as response:
            html = response.read()
            self.devices = json.loads(html.decode("utf-8"))
            #pp = pprint.PrettyPrinter(indent=4)
            #pp.pprint(self.device.devices)
        dev = self.findDevice('ET 232')
        self.devix = dev['devix']
        logging.info('deviceClient init: devix = %s', dev['devix'])

        self.setLevelsFromState(dev['state'])

        logging.info('dweeb deviceClient instance created')

    def setLevelsFromState(self, state):
        '''
        This is a typical JSON state response.  We'll receive its a parsed dict.
        {"devix":6,"avail":"remote","mode":2,"status":"ready","level_a":27,"level_b":38,"ma":-31,"batt":0}'
        '''
        logging.info('Current state: %s' % state)
        level_a = int(state['level_a'])
        level_b = int(state['level_b'])
        self.setLevels(level_a, level_b, fromUser=False)

    async def run(self):
        logging.info('deviceClient run')
        #try:
        while True:
            async with websockets.connect(self.WSUrl) as websocket:
                logging.info('websocket: %s, %s' % (self.WSUrl, websocket))
                self.websocket = websocket

                logging.info('calling producer_handler')
                await self.producer_handler(websocket)
            logging.error('websocket: closing')
            while not ws.closed:
                await asyncio.sleep(1.0)
        #except Exception as e:
        #    logging.error('websocket open failed.  already in use?')
        #    logging.error(e)
        logging.error('deviceClient run completed')

    async def producer_handler(self, ws):
        while ws.open:
            # logging.info('---- producer_handler called: qsize %d ----' % self.queue.qsize())
            command = self.queue.get()
            self.queue.task_done()
            await self.processCommand(ws, command)
        logging.info('websocket no longer open')

    def findDevice(self, device):
        for dev in self.devices:
            if dev['name'] == device:
                return dev
        logging.fatal('No %s found in device list' % device)
        raise self.NoDeviceFound

    async def WSReader(self, ws):
        '''Stub routine for later.'''
        while True:
            message = await self.websocket.recv()
            logging.info('WSReader received: %s' % message)
            j = json.loads(message)
            if j is not None:
                await self.setLevelsFromState(j)

    async def processCommand(self, ws, command):
        if command == None:
            logging.error('Commands finished.')
            return
        else:
            logging.info('processing %s' % command)
            cmd = command['cmd']
            if cmd == 'reserve':
                #await self.sendCommandStr(ws, cmd)
                resp = await self.sendAndReceive(ws, cmd)
                logging.info(resp)
                self.setLevelsFromState(json.loads(resp))
                await asyncio.sleep(1.0)
            elif cmd == 'release':
                #resp = await self.sendAndReceive(ws, cmd)
                #logging.info(resp)
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
            elif cmd == 'on_max_a':
                await self.setValue(ws, 'set_level_a', self.max_a)
                await self.setValue(ws, 'set_level_b', 0)
            elif cmd == 'on_max_b':
                await self.setValue(ws, 'set_level_a', 0)
                await self.setValue(ws, 'set_level_b', self.max_b)
            elif cmd == 'adjust_ab':
                self.adjustLevels(2 * command['a'], 2 * command['b'])
                if command['activate']:
                    if command['a'] != 0:
                        await self.setValue(ws, 'set_level_a', self.max_a)
                    if command['b'] != 0:
                        await self.setValue(ws, 'set_level_b', self.max_b)
            elif cmd == 'set_minimum':
                value = command['value']
                self.setMinimum(zero=value)
                logging.info('setting levels: max_a_min %d, max_b_min %d' % 
                              (self.max_a_min, self.max_b_min))
            elif cmd == 'off':
                await self.setValue(ws, 'set_level_a', 0)
                await self.setValue(ws, 'set_level_b', 0)
            elif cmd == 'set_mode':
                value = command['value']
                if self.invalidValue(cmd, value):
                    return
                await self.setValue(ws, cmd, modeCode(value))
            elif cmd[0:3] == 'set':
                value = command['value']
                if self.invalidValue(cmd, value):
                    return
                await self.setValue(ws, cmd, value)
            else:
                logging.error('Unknown command: %s' % cmd)

    async def setValue(self, ws, event, value):
        cmd = {'event': event, 'value': value}
        logging.info('setValue: cmd: %s' % cmd)
        await self.sendCommand(ws, cmd)

    async def sendAndReceive(self, ws, event):
        cmd = {'event': event}
        await self.sendCommand(ws, cmd)
        resp = await ws.recv()
        return(resp)

    async def sendCommandStr(self, ws, event):
        cmd = {'event': event}
        await self.sendCommand(ws, cmd)

    async def sendCommand(self, ws, cmd):
        cmd['seqNr'] = self.seqNr
        self.seqNr += 1
        cmd['devix'] = self.devix
        commandStr = json.dumps(cmd)
        logging.info('Request: %s' % commandStr)
        await ws.send(commandStr)
        logging.info('Request: sent!')
        await asyncio.sleep(1.5)


def enqueueCommands(deviceQ, commands):
    for command in commands:
        print('enqueing: %s' % command)
        deviceQ.put(command)

#async def runTest():
def runTest():
    print('runTest')
    deviceQ = queue.Queue()
    device = deviceHandler(deviceQ, max_a=27, max_b=40, test=True)
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

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(device.devices)
    device.start()
    # await device.run()


if __name__ == "__main__":
    print('running tests')
    logging.basicConfig(level=logging.DEBUG)
    device = deviceHandler(deviceQ=queue.Queue(), max_a=35, max_b=50, test=True)
    SurpriseClient.runTest(device)
    # asyncio.get_event_loop().run_until_complete(runTest())
    print('done running tests')
