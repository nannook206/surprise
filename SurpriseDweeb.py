#!/usr/bin/env python3
'''
This is the module that does all the surprising behavior.  Lots of use
of the random module to provide a unique experience every time.

There are lots of parameters here that you may want to tweak (and yes
we should have a way to more easily set these without changing the code
and that will come in time.
'''

import asyncio
from dweebClient import deviceHandler, modeName
import logging
import params
from playSound import playSound
import queue
import random
import sys
import threading
import time


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
        random.shuffle(self.modes)
        self.modeIndex = random.randint(0, len(self.modes)-1);
        logging.error('Surprise: maxSession %d, %d modes' % (maxSession, len(modes)))

        self.queue.put({'cmd': 'release'})
        self.queue.put({'cmd': 'reserve'})
        self.queue.put({'cmd': 'off'})
        t = threading.Thread(name='deviceHandler', target=self.startDevice)
        t.start()

        self.keepAliveModeChange()

    def startDevice(self):
        self.device = deviceHandler(self.queue, port=params.estimDevice, test=True)
        self.device.start()

    def getState(self):
        return self.state

    def timerStatus(self):
        now = time.time()
        timeInState = now - self.stateStart
        timeRemaining = float(self.stateTime) - timeInState
        logging.debug('%s for %dsec, %d remaining' % (
            self.state, self.stateTime, int(timeRemaining)))
        return (self.state, self.stateTime, timeRemaining, self.sessionTime)

    def delay(self, max, min=params.DELAY_MIN):
        secs = random.randint(min, max)
        return secs

    def setTimer(self, secs, function, state):
        logging.error('setTimer %s for %.1f' % (state, secs))
        timer = threading.Timer(secs, function)
        if state:
            self.timer = timer
            self.state = state
            self.stateStart = time.time()
            self.stateTime = secs
        if self.testMode is True:
            secs = secs / 100
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
        logging.error('waiting for start button or %d seconds' % failsafeStart)
        self.failsafeTimer = threading.Timer(failsafeStart, self.turnOn)
        self.failsafeTimer.start()
        playSound('activated')

    def failsafeStart(self):
        logging.error('failsafe start')
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
        playSound('starting')

    def nextMode(self):
        mode = self.modes[self.modeIndex % len(self.modes)]
        self.modeIndex += 1
        return mode

    def keepAliveModeChange(self):
        ''' Change the mode every keepaliveInterval seconds
            to prevent ET232 auto shutdown if we are Idle.
        '''
        logging.error('keepAliveModeChange (state %s)' % self.state)
        if self.state == 'Idle':
            self.queueModeChange()
        self.setTimer(params.keepaliveInterval, self.keepAliveModeChange, None)

    def queueModeAndPowerChange(self):
        if self.state == 'On':
            newMode = self.queueModeChange()
            onCommand = ['on_low', 'on_low', 'on_norm', 'on_norm', 'on_max']
            index = random.randint(0, len(onCommand) - 1)
            maValue = random.randint(-50, 50)
            self.queue.put({'cmd': 'set_ma', 'value': maValue})
            logging.error('Turning %s, %s, MA %d' % (onCommand[index], newMode, maValue))
            self.queue.put({'cmd': onCommand[index]})
            if params.announcePower is True:
                playSound(onCommand[index])

    def queueModeChange(self):
        mode = self.nextMode()
        self.queue.put({'cmd': 'set_mode', 'value': mode})
        return 'Mode %s' % ModeNames[mode]

    def calculateTime(self, max, percentage):
        secs = self.delay(max)
        amounts = [secs]
        while random.randint(0, 100) < percentage:
            more = self.delay(max)
            secs += more
            amounts.append(more)
        if secs > 10 and random.randint(0, 100) < params.TEASE_PERCENT:
            logging.error('  teasing!')
            secs /= 10
        logging.debug('Interval %d seconds %s' % (secs, amounts))
        self.sessionTime += secs
        return secs

    def adjustLevels(self, delta):
        if self.idleOn == 'A':
            self.queue.put({'cmd': 'adjust_a', 'value': delta})
        elif self.idleOn == 'B':
            self.queue.put({'cmd': 'adjust_b', 'value': delta})
        elif self.idleOn == 'AB':
            self.queue.put({'cmd': 'adjust_a', 'value': delta})
            self.queue.put({'cmd': 'adjust_b', 'value': delta})

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
            logging.error('scheduling mode/power change after %d' % t)
            self.setTimer(t, self.queueModeAndPowerChange, None)

        self.queueModeAndPowerChange()

    def reallyTurnOn(self):
        self.state = 'IdleOn'
        self.idleOn = True
        self.queueModeChange()
        self.queue.put({'cmd': 'on_max'})

    def turnOff(self):
        if self.sessionTime > self.maxSession:
            self.endSession()
            return

        secs = self.calculateTime(params.ESTIM_OFF_MAX,
                                  params.ADD_OFF_PERCENT)
        self.offTime += secs
        self.setTimer(secs, self.turnOn, 'Off')
        logging.error('Turning off')
        self.queue.put({'cmd': 'off'})

    def reallyTurnOff(self):
        self.state = 'Idle'
        self.idleOn = False
        self.queue.put({'cmd': 'off'})

    def toggle(self):
        if self.state == 'Idle' or self.idleOn == 'AB':
            logging.error('Turning on max a')
            self.state = 'IdleOn'
            self.idleOn = 'A'
            self.queueModeChange()
            self.queue.put({'cmd': 'on_max_a'})
            playSound('max-a')
        elif self.idleOn == 'A':
            logging.error('Turning on max b')
            self.idleOn = 'B'
            self.queue.put({'cmd': 'on_max_b'})
            playSound('max-b')
        elif self.idleOn == 'B':
            logging.error('Turning on max a and b')
            self.idleOn = 'AB'
            self.queue.put({'cmd': 'on_max'})
            playSound('a-and-b')
        else:
            logging.error('Bad state %s in toggle' % self.idleOn)

    def lock(self):
        logging.error('Locked.')
        self.locked = True
        playSound('locked')

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
        # Was hoping to use this to grab knob values but it knocks the unit offline
        # self.queue.put({'cmd': 'release'})
        # self.queue.put({'cmd': 'reserve'})

        self.idleOn = False
        self.locked = False

        logging.error('--------------- Ending session ------------------')
        logging.error('On time %d, off time %d' % (self.onTime, self.offTime))
        self.sessionTime = 0
        self.onTime = 0
        self.offTime = 0
        playSound('reset')


def main(argv):
    s = Surprise(maxSession=params.MAX_SESSION_TIME, testMode=True)
    t = threading.Thread(name='surprise', target=s.startWait)
    t.start()

if __name__ == "__main__":
    main(sys.argv)
