#!/usr/bin/python3
'''
Support for presentation "clicker" devices used for
Powerpoint and related presentation applications.

Specifically this supports the keyboard like imput that the
BYEASY USB Presenter Remote Control (or similar)
device provides through its USB interface.
(also BEBONCOOL RF 2.4GHz Wireless USB Presenter Remote Control but
it was flakey and disconnected unexpectly)

The button actions are eventually mapped to application actions.
The setXXXX methods are used to associate a button click with
a callback to effect an application action on a button press.
'''

from evdev import InputDevice, ecodes
import logging
import sys
from time import sleep

# Key mappings for original pointer
#UP = [48]
#LEFT = [104]
#RIGHT = [109]
#DOWN = [1, 42]

# Key mappings for ByEasy
UP = [1]
LEFT = [104]
RIGHT = [109]
DOWN = [48]
MIDDLE = [42]


def noop(code):
    print('Clicker code is %d' % code)

class Clicker():
    def __init__(self, device):
        self.device = device
        self.keytable = {
            48: noop, 
            104: noop,
            109: noop,
            42: noop,
            1:  noop,
        }

    def setUp(self, func):
        logging.info('set Up function')
        for i in UP:
            self.keytable[i] = func

    def setLeft(self, func):
        logging.info('set Left function')
        for i in LEFT:
            self.keytable[i] = func

    def setRight(self, func):
        logging.info('set Right function')
        for i in RIGHT:
            self.keytable[i] = func

    def setDown(self, func):
        logging.info('set Down function')
        for i in DOWN:
            self.keytable[i] = func

    def setMiddle(self, func):
        logging.info('set Middle function')
        self.setKeyFunction(MIDDLE, func)

    def setKeyFunction(self, keys, func):
        for i in keys:
            self.keytable[i] = func

    def handler(self, testing=False):
        logging.info('Clicker handler running')
        while True:
            while True:
                try:
                    if testing:
                        print("opening device %s" % self.device)
                    input = InputDevice(self.device)
                    break
                except Exception as e:
                    logging.error("clicker open failure: %s" % e)
                    if testing:
                        print("clicker open error - retrying: %s" % e)
                    sleep(5)

            try:
                for event in input.read_loop():
                    # trigger only on key down events
                    if event.type == ecodes.EV_KEY and event.value == 1:
                        if event.code in self.keytable:
                            self.keytable[event.code](event.code)
                        elif testing:
                            noop(event.code)
            except Exception as e:
                logging.error("clicker read failure: %s" % e)
                input.close()
                sleep(1)

def main(argv):
    device = '/dev/input/event0'
    if len(argv) > 1:
        device = argv[1]
    input = InputDevice(device)
    print("capabilities: %s" % input.capabilities(verbose=True))
    input.close()

    print('creating Clicker')
    clicker = Clicker(device)
    clicker.handler(testing=True)

if __name__ == "__main__":
    main(sys.argv)
