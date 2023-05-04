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
from playSound import playSound
from Surprise import Surprise
from syslog_rfc5424_formatter import RFC5424Formatter
from threading import Thread
import time
import tornado.ioloop
import tornado.web


TEST_MODE = False

# Maps web page method to use for each state Surprise can be in.
Page = {
    'Idle': pages.idle,
    'IdleOn': pages.idle,
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
        clicker.setMiddle(self.clickMiddle)

    def clickUp(self, code):
        logging.info('clickUp')
        self.process('up')

    def clickLeft(self, code):
        logging.info('clickLeft')
        self.process('left')

    def clickRight(self, code):
        logging.info('clickRight')
        self.process('right')

    def clickDown(self, code):
        logging.info('clickDown')
        self.process('down')

    def clickMiddle(self, code):
        logging.info('clickMiddle')
        self.process('middle')

    def process(self, action):
        state = surprise.getState()
        locked = surprise.locked
        if TEST_MODE == True:
            logging.info('process: arg: %s, state %s, locked %s, queued %d' % (
                          action, state, locked, surprise.queue.qsize()))
        else:
            logging.debug('process: arg: %s, state %s, locked %s, queued %d' % (
                          action, state, locked, surprise.queue.qsize()))

        if state == 'Idle':
            if action == 'activate' or action == 'up':
                logging.info('===== activating surprise =====')
                surprise.startWait()
            elif action == 'off':
                surprise.reallyTurnOff()
            elif action == 'on' or action == 'right':
                surprise.toggle()
            elif action == 'middle':
                surprise.setLevelsFromDevice()
            elif action == 'reset' or action == 'left':
                surprise.endSession()
        elif state == 'IdleOn':
            if action == 'up':
                logging.info('increasing max')
                surprise.adjustLevels(1)
            elif action == 'down':
                logging.info('decreasing max')
                surprise.adjustLevels(-1)
            elif action == 'middle':
                playSound('new_minimum_set')
                surprise.setMinimum()
            elif action == 'on' or action == 'right':
                surprise.toggle()
            elif action == 'reset' or action == 'off' or action == 'left':
                surprise.endSession()
        elif state == 'Waiting':
            if action == 'start' or action == 'up':
                logging.info('===== starting surprise =====')
                surprise.startSurprise()
            elif (action == 'reset' or action == 'left') and not locked:
                logging.info('reseting surprise service')
                surprise.endSession()
            elif action == 'down':
                surprise.lock()
        elif state == 'Starting' or state == 'On' or state == 'Off':
            if not locked:
                if action == 'reset' or action == 'left':
                    logging.info('reseting surprise service')
                    surprise.endSession()
                elif action == 'down':
                    surprise.lock()
            else:
                if action == 'up':
                    logging.info('increasing max')
                    surprise.adjustLevels(1)
                elif action == 'down':
                    logging.info('decreasing max')
                    surprise.adjustLevels(-1)
                elif action == 'middle':
                    logging.info('setting minimum')
                    playSound('new_minimum_set')
                    surprise.setMinimum()
                elif action == 'left':
                    playSound('sorry')
	    
        state = surprise.getState()
        logging.debug('state is %s' % state)
        time.sleep(0.5)   # Give time for beep to play.
        return(state)


def make_app(processor):
    return tornado.web.Application([
        (r"/(beep\.wav)", tornado.web.StaticFileHandler, {'path': '.'}),
        (r"/", MainHandler, dict(processor=processor)),
    ])


if __name__ == "__main__":
    logLevel = logging.ERROR

    parser = argparse.ArgumentParser()
    parser.add_argument('--maxSession', help='maximum time for session in minutes',
                        type=int, default=params.MAX_SESSION_TIME/60)
    parser.add_argument('--verbose', '-v', help='debug level', type=int,
                        default=0)
    parser.add_argument('--test', '-t', help='enable test mode', default=False)
    args = parser.parse_args()
    maxSession = int(args.maxSession)*60
    if args.verbose > 1:
        logLevel = logging.DEBUG
    elif args.verbose == 1:
        logLevel = logging.INFO
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

    logging.info('%s ------------------------------------------' % params.version)

    clicker = clicker.Clicker(params.clickerDevice)
    clickerThread = Thread(name='clicker', target=clicker.handler)

    surprise = Surprise(maxSession, testMode=TEST_MODE,
                        modes=params.USEFUL_ET232_MODES)
    surpriseThread = Thread(name='surprise', target=surprise.idle)

    surpriseThread.start()
    logging.info('SurpriseThread running')
    clickerThread.start()
    logging.info('clickerThread running')

    processor = Processor(clicker)

    app = make_app(processor.process)
    app.listen(params.port)
    logging.info('%s: listening on %d' % (params.version, params.port))
    tornado.ioloop.IOLoop.current().start()
