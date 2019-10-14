#!/usr/bin/env python3
'''
This is the module that does all the surprising behavior.  Lots of use
of the random module to provide a unique experience every time.

There are lots of parameters here that you may want to tweak (and yes
we should have a way to more easily set these without changing the code
and that will come in time.
'''

import asyncio
from dweebClient import dweebClient, ET232ModeNames
import logging
import params
import pprint
import queue
import random
import sys
import threading
import time


def noop():
    return 0


class Surprise:
    def __init__(self, maxSession = params.MAX_SESSION_TIME, testMode=False,
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
        logging.error('Surprise: maxSession %d, %d modes' % (maxSession, len(modes)))

        # Ensure the first command in the queue is a 'reserve'
        self.queue.put({'cmd': 'release'})
        self.queue.put({'cmd': 'reserve'})
        self.queue.put({'cmd': 'off'})
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
        dweeb = dweebClient(self.queue, max_a=35, max_b=50, test=True)
        #pp = pprint.PrettyPrinter(indent=4)
        #pp.pprint(dweeb.devices)
        dweeb.start()

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
        if state:
            self.state = state
            self.stateStart = time.time()
            self.stateTime = secs
        if self.testMode is True:
            secs = secs / 100
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
        if self.testMode:
            failsafeStart = 0.5
        else:
            failsafeStart = params.FAILSAFE_START
        logging.error('waiting for start button or %d seconds' % failsafeStart)
        self.failsafeTimer = threading.Timer(failsafeStart, self.turnOn)
        self.failsafeTimer.start()

    def failsafeStart(self):
        logging.error('failsafe start')
        self.failsafeTimer = None
        if self.state == 'Waiting':
            self.startSurprise()

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
        secs = self.delay(params.START_SLEEP_MAX)
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
        if not self.testMode:
            self.queueModeChange()
            self.setTimer(25*60, self.keepAliveModeChange, None)

    def queueModeAndPowerChange(self):
        newMode = self.queueModeChange()
        onCommand = ['on_low', 'on_low', 'on_norm', 'on_norm', 'on_max']
        index = random.randint(0, len(onCommand) - 1)
        logging.error('Turning %s, %s' % (onCommand[index], newMode))
        self.queue.put({'cmd': onCommand[index]})

    def queueModeChange(self):
        mode = self.nextMode()
        maValue = random.randint(-50, 50)
        self.queue.put({'cmd': 'set_mode', 'value': mode})
        self.queue.put({'cmd': 'set_ma', 'value': maValue})
        return 'Mode %s, MA %d' % (ET232ModeNames[mode], maValue)

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

        secs = self.calculateTime(params.ESTIM_OFF_MAX,
                                  params.ADD_OFF_PERCENT)
        self.offTime += secs
        self.setTimer(secs, self.turnOn, 'Off')
        logging.error('Turning off')
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
        # Was hoping to use this to grab knob values but it knocks the unit offline
        # self.queue.put({'cmd': 'release'})
        # self.queue.put({'cmd': 'reserve'})
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
    s = Surprise(maxSession=params.MAX_SESSION_TIME, testMode=True)
    t = threading.Thread(name='surprise', target=s.startWait)
    t.start()

if __name__ == "__main__":
    main(sys.argv)
