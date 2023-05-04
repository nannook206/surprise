#!/usr/bin/env python

# WS server that sends messages at random intervals

import asyncio
import logging
import queue
import sys
import websockets

class wsHandler():
    def __init__(self, surprise, queue, listenAddr="0.0.0.0", port=8889):
        self.surprise = surprise
        self.queue = queue
        self.listenAddr = listenAddr
        self.port = port
        self.lastmsg = {'field': '?', 'value': ''}

    def getStatus(self):
        (status, interval, elapsed, total) = self.surprise.timerStatus()
        if status[0:4] == 'Idle' or status == 'Waiting':
            return status
        else:
            return ('%s %d/%ds,  %ds total' %
                    (status, elapsed, interval, total))

    def start(self):
        async def process(websocket, path):
            while True:
                try:
                    msg = self.queue.get(timeout=0.5)
                except queue.Empty:
                    msg = self.lastmsg
                # logging.debug('wsHandler: processing %s' % msg)
                try:
                    await websocket.send('timer:%s' % self.getStatus())
                    await websocket.send('%s:%s' % (msg['field'], msg['value']))
                except websockets.exceptions.ConnectionClosed:
                    logging.info('Connection closed.')
                    return
                self.lastmsg = msg

        asyncio.set_event_loop(asyncio.new_event_loop())
        start_server = websockets.serve(process, self.listenAddr, self.port)
        logging.info('wsHandler listening on %s:%s' % (self.listenAddr, self.port))

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()


def main(argv):
    def mock_surprise():
        def timerStatus():
            return ('SomeState', 100, 42, 200)


    print('creating wsHandler')
    q = queue.Queue()
    handler = wsHandler(surprise=mock_surprise, queue=q)
    handler.start()

if __name__ == "__main__":
    main(sys.argv)
