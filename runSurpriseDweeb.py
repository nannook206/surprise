#!/usr/bin/python3
'''
Top level invocation module for Surprise.  It defines the basic flow
of page on the web server, sets up the clicker handlers, and handles
the core state machine and locking (in process()).
'''

import argparse
import clicker
import logging
import os
import pages
import params
from syslog_rfc5424_formatter import RFC5424Formatter
from SurpriseDweeb import Surprise
from threading import Thread
import time
import tornado.ioloop
import tornado.web


TEST_MODE = False

# Maps web page method to use for each state Surprise can be in.
Page = {
    'Idle': pages.idle,
    'Waiting': pages.waiting,
    'Starting': pages.status,
    'On': pages.status,
    'Off': pages.status,
}


class MyFileHandler(tornado.web.StaticFileHandler):
    def Xinitialize(self, path):
        self.dirname, self.filename = os.path.split(path)
        super(MyFileHandler, self).initialize(self.dirname)

    def Xparse_url_path(self, url_path):
        return os.path.basename('./' + url_path)


class MainHandler(tornado.web.RequestHandler):
    def initialize(self, processor):
        self.processor = processor

    def get(self):
        action = self.get_argument('action', None)
        state = self.processor(action)
        self.write(Page[state](surprise))


class Processor():
    def __init__(self, clicker):
        clicker.setUp(self.clickUp)
        clicker.setLeft(self.clickLeft)
        clicker.setRight(self.clickRight)
        clicker.setDown(self.clickDown)

    def clickUp(self, code):
        logging.error('clickUp')
        self.process('start')

    def clickLeft(self, code):
        logging.error('clickLeft')
        self.process('reset')

    def clickRight(self, code):
        logging.error('clickRight')
        self.process('toggle')

    def clickDown(self, code):
        logging.error('clickDown')
        self.process('lock')

    def process(self, action):
        state = surprise.getState()
        locked = surprise.locked
        logging.debug('process: arg: %s, state %s, locked %s' % (action, state, locked))
        if TEST_MODE == True:
            logging.error('process: arg: %s, state %s, locked %s' % (action, state, locked))
            logging.error('queue has %d commands pending' % surprise.queue.qsize())

        if action == 'lock':
            surprise.lock()
        elif state == 'Idle':
            if action == 'activate' or action == 'start':
                logging.error('activating surprise service')
                surprise.startWait()
            elif action == 'on' and not locked:
                surprise.reallyTurnOn()
            elif action == 'off' and not locked:
                surprise.reallyTurnOff()
            elif action == 'toggle' and not locked:
                surprise.toggle()
            elif action == 'reset':
                surprise.endSession()
        elif state == 'Waiting':
            if action == 'start':
                logging.error('starting surprise')
                surprise.startSurprise()
            elif action == 'reset' and not locked:
                logging.error('reseting surprise service')
                surprise.endSession()
        elif state == 'Starting' or state == 'On' or state == 'Off':
            if action == 'reset' and not locked:
                logging.error('reseting surprise service')
                surprise.endSession()
	    
        state = surprise.getState()
        logging.debug('state is %s' % state)
        time.sleep(0.5)   # Give time for beep to play.
        # print('process: state now %s, locked %s' % (state, surprise.locked))
        return(state)


def make_app(processor):
    return tornado.web.Application([
        (r"/(beep\.wav)", tornado.web.StaticFileHandler, {'path': './beep.wav'}),
        (r"/", MainHandler, dict(processor=processor)),
    ])


if __name__ == "__main__":
    logLevel = logging.ERROR

    parser = argparse.ArgumentParser()
    parser.add_argument('--maxSession', help='maximum time for session in minutes',
                        default=params.MAX_SESSION_TIME/60)
    parser.add_argument('--verbose', '-v', help='maximum time for session in minutes',
                        default=False)
    parser.add_argument('--test', '-t', help='enable test mode', default=False)
    args = parser.parse_args()
    maxSession = int(args.maxSession)*60
    if args.verbose:
        logLevel = logging.DEBUG
    if args.test:
        TEST_MODE=True
        logLevel=logging.INFO
    logger = logging.getLogger()
    logger.setLevel(logLevel)
    #syslog_handler = logging.handlers.SysLogHandler(address=('loghost', 514))
    syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
    syslog_handler.setLevel(logLevel)
    #syslog_handler.setFormatter(RFC5424Formatter())
    file_handler = logging.FileHandler(filename='/var/log/surprise.log')
    file_handler.setLevel(logLevel)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(syslog_handler)
    logger.addHandler(file_handler)

    logging.error('%s' % params.version)

    clicker = clicker.Clicker(params.clickerDevice)
    clickerThread = Thread(name='clicker', target=clicker.handler)

    surprise = Surprise(maxSession, testMode=TEST_MODE,
                        modes=params.USEFUL_ET232_MODES)
    surpriseThread = Thread(name='surprise', target=surprise.idle)

    surpriseThread.start()
    logging.error('SurpriseThread running')
    clickerThread.start()
    logging.error('clickerThread running')

    processor = Processor(clicker)

    app = make_app(processor.process)
    app.listen(params.port)
    logging.error('%s: listening on %d' % (params.version, params.port))
    tornado.ioloop.IOLoop.current().start()
