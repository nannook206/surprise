#!/usr/bin/python3
#!/usr/local/bin/python3.7

import asyncio
import json
import pprint
import urllib.request
import websockets

import logging
logger = logging.getLogger('websockets')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

pp = pprint.PrettyPrinter(indent=4)

with urllib.request.urlopen('http://localhost:31280/devices') as response:
    html = response.read()

    print(html)

    devices = json.loads(html.decode("utf-8"))

    pp.pprint(devices)

print('trying to set a value')

modes = {
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
seqNr = 0
devix = 7

async def sendCommands():
    async with websockets.connect(
            'ws://controller1.local:31280/devices') as websocket:
        async def setValue(event, value):
            cmd = {'event': event, 'value': value}
            await sendCommand(cmd)

        async def sendAndReceive(event):
            cmd = {'event': event}
            await sendCommand(cmd)
            resp = await websocket.recv()
            print('Response: %s' % json.loads(resp))

        async def sendCommand(cmd):
            global seqNr, devix

            cmd['seqNr'] = seqNr
            seqNr += 1
            cmd['devix'] = devix
            commandStr = json.dumps(cmd)
            print('Request: %s' % commandStr)
            await asyncio.sleep(1.0)
            await websocket.send(commandStr)

        await sendAndReceive('reserve')
        await setValue('set_mode', modes['ramp'])
        await setValue('set_level_a', 20)
        await setValue('set_mode', modes['thrust'])
        await asyncio.sleep(4.0)
        await setValue('set_level_a', 19)
        await setValue('set_mode', modes['audio-soft'])
        await setValue('set_level_a', 18)
        await setValue('set_mode', modes['waves'])
        await sendAndReceive('release')
        await asyncio.sleep(3.0)
        await sendAndReceive('reserve')
        await setValue('set_mode', modes['random'])
        await setValue('set_level_a', 30)
        await setValue('set_level_b', 4)
        await setValue('set_mode', modes['waves'])
        await sendAndReceive('release')


asyncio.get_event_loop().run_until_complete(sendCommands())
