#!/usr/bin/python3
'''
Support for presentation "clicker" devices used for
Powerpoint and related presentation applications.

Specifically this support the keyboard like imput that the
BEBONCOOL RF 2.4GHz Wireless USB Presenter Remote Control (or similar)
device provides through its USB interface.

The button actions are eventually mapped to application actions.
The setXXXX methods are used to associate a button click with
a callback to effect an application action on a button press.
'''

from evdev import InputDevice, categorize, ecodes
import logging

UP = [48]
LEFT = [104]
RIGHT = [109]
DOWN = [1, 42]

def noop(code):
    print('Clicker code is %d' % code)

class Clicker():
    def __init__(self, device):
        self.device = InputDevice(device)
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

    def handler(self):
        logging.error('Clicker handler running')
        for event in self.device.read_loop():
            # trigger only on key down events
            if event.type == ecodes.EV_KEY and event.value == 1:
                if event.code in self.keytable:
                    self.keytable[event.code](event.code)


if __name__ == "__main__":
    clicker = Clicker("/dev/input/event0")
    clicker.handler()
