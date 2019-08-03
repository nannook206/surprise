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
import pprint
import random
import sys
import time
import threading
import queue
from dweebClient import dweebClient, ET232ModeNames


'''
These variable largely define the duration of the surprising events.
  FAILSAFE_START is the time from activating the application to when it starts
      even if you are not ready (or lose access to the clicker...).
  MAX_SESSION_TIME is the maximum time for a session.  Surprise turns off and
      returns to idle after this much time in seconds.
  DELAY_MIN minimum time for a delay (see the next three entries)
  START_SLEEP_MAX max amount of time to wait before starting the surprising
      experience (once STARTed)
  ESTIM_ON_MAX max amount of time in seconds for an ESTIMulating event
      (but note it can be added to with additional random amounts, see code)
  ESTIM_OFF_MAX max amount for time in seconds for the off cycle
      (but this is also subject to addtions)
  ADD_ON_PERCENT likelihood that you will add an addtion amount of time
      to an ON cycle.  Repeats until it fails to add.
  ADD_OFF_PERCENT likelihood that you will add an addtion amount of time
      to an OFF cycle.  Repeats until it fails to add.
'''
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
            failsafeStart = FAILSAFE_START
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
        if secs > 10 and random.randint(0, 100) < TEASE_PERCENT:
            logging.error('  teasing!')
            secs /= 10
        logging.debug('Interval %d seconds %s' % (secs, amounts))
        self.sessionTime += secs
        return secs

    def turnOn(self):
        if self.sessionTime > self.maxSession:
            self.endSession()
            return

        secs = self.calculateTime(ESTIM_ON_MAX, ADD_ON_PERCENT)
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

        secs = self.calculateTime(ESTIM_OFF_MAX, ADD_OFF_PERCENT)
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
