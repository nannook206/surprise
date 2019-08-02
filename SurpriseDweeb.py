#!/usr/bin/env python3

import asyncio
import logging
import pprint
import random
import sys
import time
import threading
import queue
from dweebClient import dweebClient, ET232ModeNames


FAILSAFE_START = 900
MAX_SESSION_TIME = 70 * 60  # 70 minutes

# Random number bounds
DELAY_MIN = 15   # must be less than following MAX values
START_SLEEP_MAX = 180
ESTIM_ON_MAX = 210
ESTIM_OFF_MAX = 150

ADD_ON_PERCENT = 30
ADD_OFF_PERCENT = 20
TEASE_PERCENT = 15


def noop():
    return 0


class Surprise:
    def __init__(self, maxSession = MAX_SESSION_TIME, testMode=False,
                 modes=[1, 2, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15]):
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
        self.locked = False
        self.testMode = testMode
        self.modes = modes
        self.queue = queue.Queue()
        random.shuffle(self.modes)
        self.modeIndex = random.randint(0, len(self.modes)-1);
        self.version = 'SurpriseDweeb v3.0 (maxSession %d)' % self.maxSession

        # Ensure the first command in the queue is a 'reserve'
        self.queue.put({'cmd': 'reserve'})
        t = threading.Thread(name='dweebClient', target=self.startDweeb)
        t.start()

        self.keepAliveModeChange()
        '''
        if testMode is True:
            automationhat.relay.one.on = noop
        automationhat.relay.one.off()
        if automationhat.is_automation_hat():
            automationhat.light.power.write(1)
        '''

    def startDweeb(self):
        dweeb = dweebClient(self.queue, max_a=23, max_b=45, test=True)
        #pp = pprint.PrettyPrinter(indent=4)
        #pp.pprint(dweeb.devices)
        dweeb.start()

    def getVersion(self):
        return self.version

    def getState(self):
        return self.state

    def timerStatus(self):
        now = time.time()
        timeInState = now - self.stateStart
        timeRemaining = float(self.stateTime) - timeInState
        logging.debug('%s for %dsec, %d remaining' % (
            self.state, self.stateTime, int(timeRemaining)))
        return (self.state, self.stateTime, timeRemaining, self.sessionTime)

    def delay(self, max, min=DELAY_MIN):
        secs = random.randint(min, max)
        return secs

    def setTimer(self, secs, function, state):
        logging.error('setTimer %s for %.1f' % (state, secs))
        if state:
            self.state = state
            self.stateStart = time.time()
            self.stateTime = secs
        if self.testMode is True:
            secs = 0.05
        self.timer = threading.Timer(secs, function)
        self.timer.start()

    def idle(self):
        pass

    def startWait(self):
        self.state = 'Waiting'
        self.queue.put({'cmd': 'off'})
        '''
        automationhat.relay.one.off()
        '''
        failsafeStart = time.clock() + FAILSAFE_START
        logging.error('waiting for start button or %d seconds' % failsafeStart)
        if self.testMode:
            failsafeStart = 0.5
        self.failsafeTimer = threading.Timer(failsafeStart, self.turnOn)
        self.failsafeTimer.start()

    def failsafeStart(self):
        logging.error('failsafe start')
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.turnOn()

    def startSurprise(self):
        if self.failsafeTimer:
            self.failsafeTimer.cancel()
            self.filesafetimer = None

        '''
        if automationhat.is_automation_hat():
            automationhat.light.comms.write(1)
        '''

        random.shuffle(self.modes)
        self.sessionTimer = threading.Timer(self.maxSession, self.endSession)
        self.sessionTimer.start()
        secs = self.delay(START_SLEEP_MAX)
        self.offTime = secs
        self.onTime = 0
        self.setTimer(secs, self.turnOn, 'Starting')

    def nextMode(self):
        mode = self.modes[self.modeIndex % len(self.modes)]
        self.modeIndex += 1
        return mode

    def keepAliveModeChange(self):
        ''' Change the mode every 25 minutes to prevent ET232 auto shutdown
        '''
        self.queueModeChange()
        self.setTimer(25*60, self.keepAliveModeChange, None)

    def queueModeAndPowerChange(self):
        self.queueModeChange()
        self.queueOn()

    def queueModeChange(self):
        mode = self.nextMode()
        maValue = random.randint(-50, 50)
        logging.error('Mode Change: %s, MA %d' % (ET232ModeNames[mode], maValue))
        self.queue.put({'cmd': 'set_mode', 'value': mode})
        self.queue.put({'cmd': 'set_ma', 'value': maValue})

    def queueOn(self):
        onCommand = ['on_low', 'on_low', 'on_norm', 'on_norm', 'on_max']
        index = random.randint(0, len(onCommand) - 1)
        logging.error('setting %s' % onCommand[index])
        self.queue.put({'cmd': onCommand[index]})

    def turnOn(self):
        if self.sessionTime > self.maxSession:
            self.endSession()
            return

        secs = self.delay(ESTIM_ON_MAX)
        while random.randint(0, 100) < ADD_ON_PERCENT:
            more = self.delay(ESTIM_ON_MAX)
            logging.error('... adding %d' % more)
            secs += more
        if secs > 10 and random.randint(0, 100) < TEASE_PERCENT:
            logging.error('  teasing!')
            secs /= 10
        self.sessionTime += secs
        self.onTime += secs
        self.setTimer(secs, self.turnOff, 'On')
        t = 0
        while (secs - t) > 120:
            t = random.randint(max(60,t),secs-20)
            logging.error('scheduling mode change after %d' % t)
            self.setTimer(t, self.queueModeAndPowerChange, None)

        self.queueModeAndPowerChange()
        '''
        automationhat.relay.one.on()
        '''

    def reallyTurnOn(self):
        self.idleOn = True
        self.queueModeChange()
        self.queue.put({'cmd': 'on_max'})
        '''
        automationhat.relay.one.on()
        '''

    def turnOff(self):
        if self.sessionTime > self.maxSession:
            self.endSession()
            return

        secs = self.delay(ESTIM_OFF_MAX)
        while random.randint(0, 100) < ADD_OFF_PERCENT:
            more = self.delay(ESTIM_OFF_MAX)
            logging.error('... adding %d' % more)
            secs += more
        if secs > 10 and random.randint(0, 100) < TEASE_PERCENT:
            logging.error('  teasing!')
            secs /= 10
        self.sessionTime += secs
        self.offTime += secs
        self.setTimer(secs, self.turnOn, 'Off')
        self.queue.put({'cmd': 'off'})
        '''
        automationhat.relay.one.off()
        '''

    def reallyTurnOff(self):
        self.idleOn = False
        self.queue.put({'cmd': 'off'})
        '''
        automationhat.relay.one.off()
        '''

    def toggle(self):
        if self.idleOn:
            self.reallyTurnOff()
        else:
            self.reallyTurnOn()

    def lock(self):
        logging.error('Locked.')
        self.locked = True

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
        '''
        automationhat.relay.one.off()
        if automationhat.is_automation_hat():
            automationhat.light.comms.write(0)
        '''

        self.idleOn = False
        self.locked = False

        logging.error('--------------- Ending session ------------------')
        logging.error('On time %d, off time %d' % (self.onTime, self.offTime))
        self.sessionTime = 0
        self.onTime = 0
        self.offTime = 0


def main(argv):
    s = Surprise(maxSession=4200, testMode=True)
    t = threading.Thread(name='surprise', target=s.startWait)
    t.start()

if __name__ == "__main__":
    main(sys.argv)
