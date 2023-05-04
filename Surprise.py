#!/usr/bin/env python3
'''
This is the module that does all the surprising behavior.  Lots of use
of the random module to provide a unique experience every time.

There are lots of parameters here that you may want to tweak (and yes
we should have a way to more easily set these without changing the code
and that will come in time.
'''

import asyncio
import logging
import params
from playSound import playSound
import buttshockClient as buttshock
import dweebClient as dweeb
import queue
import random
import sys
import threading
import time
import wsSurprise


def noop():
    return 0


class Surprise:
    def __init__(self, maxSession = params.MAX_SESSION_TIME, testMode=False,
                 modes=params.USEFUL_ET232_MODES):
        self.maxSession = maxSession
        self.sessionTime = 0
        self.onTime = 0
        self.offTime = 0
        self.idleOn = False
        self.state = 'Idle'
        self.stateStart = time.time()
        self.stateTime = 0
        self.timer = None
        self.failsafeTimer = None
        self.sessionTimer = None
        self.device = None
        self.locked = False
        self.testMode = testMode
        self.modes = modes
        self.queue = queue.Queue()
        self.wsQueue = queue.Queue()
        random.shuffle(self.modes)
        self.modeIndex = random.randint(0, len(self.modes)-1);
        logging.info('Surprise: maxSession %d, %d modes' % (maxSession, len(modes)))

        wsHandler = wsSurprise.wsHandler(surprise=self, queue=self.wsQueue)
        wsThread = threading.Thread(name='websocket', target=wsHandler.start)
        wsThread.start()
        logging.info('wsThread running')

        if params.estimHandler == 'buttshock':
            self.device = buttshock.deviceHandler(self.queue, port=params.estimDevice, test=True)
        elif params.estimHandler == 'dweeb':
            self.device = dweeb.deviceHandler(self.queue, port=params.estimDevice, test=True)

        self.queue.put({'cmd': 'release'})
        self.queue.put({'cmd': 'reserve'})
        self.queue.put({'cmd': 'off'})

        t = threading.Thread(name='deviceHandler', target=self.startDevice)
        t.start()

        self.keepAliveModeChange()

    def wsUpdate(self, field, text):
        self.wsQueue.put({'field': field, 'value': text})

    def startDevice(self):
        self.device.start()

    def getState(self):
        return self.state

    def timerStatus(self):
        now = time.time()
        timeInState = now - self.stateStart
        return (self.state, self.stateTime, timeInState, self.sessionTime)

    def delay(self, max, min=params.DELAY_MIN):
        secs = random.randint(min, max)
        return secs

    def setTimer(self, secs, function, state):
        logging.info('setTimer %s for %.1f' % (state, secs))
        if self.testMode is True:
            secs = secs / 100
        timer = threading.Timer(secs, function)
        if state:
            self.timer = timer
            self.state = state
            self.stateStart = time.time()
            self.stateTime = secs
        timer.start()

    def idle(self):
        '''Called once at service startup.  Announce service is started.
        '''
        playSound('ready')

    def startWait(self):
        self.state = 'Waiting'
        self.queue.put({'cmd': 'off'})
        if self.testMode:
            failsafeStart = 0.5
        else:
            failsafeStart = params.FAILSAFE_START
        logging.info('waiting for start button or %d seconds' % failsafeStart)
        self.failsafeTimer = threading.Timer(failsafeStart, self.turnOn)
        self.failsafeTimer.start()
        playSound('activated')

    def failsafeStart(self):
        logging.info('failsafe start')
        self.failsafeTimer = None
        if self.state == 'Waiting':
            self.startSurprise()

    def startSurprise(self):
        if self.failsafeTimer:
            self.failsafeTimer.cancel()
            self.filesafetimer = None
        random.shuffle(self.modes)
        self.sessionTimer = threading.Timer(self.maxSession, self.endSession)
        self.sessionTimer.start()
        secs = self.delay(params.START_SLEEP_MAX)
        self.offTime = secs
        self.onTime = 0
        self.setTimer(secs, self.turnOn, 'Starting')
        self.wsUpdate('status', 'Starting in %d secs' % secs)
        playSound('starting')

    def nextMode(self):
        mode = self.modes[self.modeIndex % len(self.modes)]
        self.modeIndex += 1
        return mode

    def keepAliveModeChange(self):
        ''' Change the mode every keepaliveInterval seconds
            to prevent ET232 auto shutdown if we are Idle
            or IdleOn.  The other states are transient.
            Staying in the same mode for too long (60 minutes?)
            will cause auto-shutdown of the device.
        '''
        logging.info('keepAliveModeChange (state %s)' % self.state)
        if self.state == 'Idle' or self.state == 'IdleOn':
            self.queueModeChange()
        self.setTimer(params.keepaliveInterval, self.keepAliveModeChange, None)

    def queueModeAndPowerChange(self):
        if self.state == 'On':
            newMode = self.queueModeChange()
            level = params.onCommand[random.randint(0, len(params.onCommand) - 1)]
            logging.info('Turning %s, %s' % (level, newMode))
            self.wsUpdate('status', '%s, %s' % (newMode, level))
            self.queue.put({'cmd': level})
            if params.announcePower is True:
                playSound(level)

    def queueModeChange(self):
        mode = self.nextMode()
        maValue = self.device.randomMA()
        self.queue.put({'cmd': 'set_ma', 'value': maValue})
        self.queue.put({'cmd': 'set_mode', 'value': mode})
        return '%s, MA %d' % (mode, maValue)

    def calculateTime(self, max, percentage):
        secs = self.delay(max)
        amounts = [secs]
        while random.randint(0, 100) < percentage:
            more = self.delay(max)
            secs += more
            amounts.append(more)
        if secs > 10 and random.randint(0, 100) < params.TEASE_PERCENT:
            logging.info('  teasing!')
            secs /= 10
        logging.debug('Interval %d seconds %s' % (secs, amounts))
        self.sessionTime += secs
        return secs

    def adjustLevels(self, delta):
        if self.idleOn == 'A':
            self.queue.put({'cmd': 'adjust_ab', 'a': delta, 'b': 0, 'activate': True})
        elif self.idleOn == 'B':
            self.queue.put({'cmd': 'adjust_ab', 'a': 0, 'b': delta, 'activate': True})
        else:  # 'AB' or while locked
            self.queue.put({'cmd': 'adjust_ab', 'a': delta, 'b': delta,
                            'activate': (self.state == 'On')})

    def turnOn(self):
        if self.sessionTime > self.maxSession:
            self.endSession()
            return

        secs = self.calculateTime(params.ESTIM_ON_MAX,
                                  params.ADD_ON_PERCENT)
        self.onTime += secs
        self.setTimer(secs, self.turnOff, 'On')
        t = 0
        while (secs - t) > 120:
            t = random.randint(max(60,t),secs-20)
            logging.info('scheduling mode/power change after %d' % t)
            self.setTimer(t, self.queueModeAndPowerChange, None)

        self.queueModeAndPowerChange()

    def reallyTurnOn(self):
        self.state = 'IdleOn'
        self.idleOn = True
        self.queueModeChange()
        self.wsUpdate('status', 'On Max')
        self.queue.put({'cmd': 'on_max'})

    def turnOff(self):
        if self.sessionTime > self.maxSession:
            self.endSession()
            return

        secs = self.calculateTime(params.ESTIM_OFF_MAX,
                                  params.ADD_OFF_PERCENT)
        self.offTime += secs
        self.setTimer(secs, self.turnOn, 'Off')
        logging.info('Turning off')
        self.queue.put({'cmd': 'off'})
        self.wsUpdate('status', 'Off')

    def reallyTurnOff(self):
        self.state = 'Idle'
        self.idleOn = False
        self.queue.put({'cmd': 'off'})
        self.wsUpdate('status', 'Off')

    def toggle(self):
        if self.state == 'Idle' or self.idleOn == 'AB':
            self.state = 'IdleOn'
            self.idleOn = 'A'
            logging.info('Turning on max a, %s' %self.queueModeChange())
            self.queue.put({'cmd': 'on_max_a'})
            self.wsUpdate('status', 'Max A')
            playSound('max-a')
        elif self.idleOn == 'A':
            self.idleOn = 'B'
            logging.info('Turning on max b')
            self.queue.put({'cmd': 'on_max_b'})
            self.wsUpdate('status', 'Max B')
            playSound('max-b')
        elif self.idleOn == 'B':
            self.idleOn = 'AB'
            logging.info('Turning on max a and b')
            self.queue.put({'cmd': 'on_max'})
            self.wsUpdate('status', 'Max A & B')
            playSound('a-and-b')
        else:
            logging.error('Bad state %s in toggle' % self.idleOn)

    def lock(self):
        logging.info('Locked.')
        self.locked = True
        playSound('locked')
        self.setMinimum()

    def setMinimum(self, zero=False):
        logging.info('setting minimums')
        # (set_minimum, True) resets minimum to 0
        self.queue.put({'cmd': 'set_minimum', 'value': zero})

    def setLevelsFromDevice(self, zero=False):
        logging.info('setting levels from device')
        playSound('levels_set_from_device')
        self.queue.put({'cmd': 'set_levels_from_device'})

    def endSession(self):
        self.state = 'Idle'
        if self.sessionTimer:
            self.sessionTimer.cancel()
            self.sessionTimer = None
        if self.failsafeTimer:
            self.failsafeTimer.cancel()
            self.failsafeTimer = None
        if self.timer:
            self.timer.cancel()
            self.timer = None

        self.queue.put({'cmd': 'off'})
        self.setMinimum(True)

        self.idleOn = False
        self.locked = False

        logging.info('--------------- Ending session ------------------')
        logging.info('On time %d, off time %d' % (self.onTime, self.offTime))
        self.sessionTime = 0
        self.onTime = 0
        self.offTime = 0
        playSound('reset')


def main(argv):
    logLevel = logging.DEBUG
    logger = logging.getLogger()
    logger.setLevel(logLevel)
    s = Surprise(maxSession=params.MAX_SESSION_TIME, testMode=True)
    t = threading.Thread(name='surprise', target=s.startWait)
    t.start()

if __name__ == "__main__":
    main(sys.argv)
