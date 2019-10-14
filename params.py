'''
Surprise params file
'''
version = 'SurpriseDweeb v3.1 (2019-09-22)'

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
  TEASE_PERCENT percentage of time to dramatically shorten a timer to tease
      the user
'''
FAILSAFE_START = 900
MAX_SESSION_TIME = 90 * 60   # 90 minutes

# Random number bounds
DELAY_MIN = 15   # must be less than following MAX values
START_SLEEP_MAX = 180
ESTIM_ON_MAX = 210
ESTIM_OFF_MAX = 150

ADD_ON_PERCENT = 30
ADD_OFF_PERCENT = 20
TEASE_PERCENT = 15

'''
Defines which modes will be used.  Once we have more
devices, we will need to introduce device specific dicts.
The list is randomize berfore use and it then sequences through
the randomized list.  You can include entries more than once
and they will be used more frequently.  I omit modes that are
not useful or unintersting.  Tune as desired.
'''
USEFUL_ET232_MODES=[1, 2, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15,
                    2, 3, 10, 12, 14]

# Port number for Surprise web interface
port = 8888

# Devices and other strings
#clickerDevice = '/dev/clicker'
clickerDevice = '/dev/input/event0'
