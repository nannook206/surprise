'''
Surprise params file
'''
version = 'Surprise v4.1 (2020-04-29)'

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
MAX_SESSION_TIME = 120 * 60   # seconds

# Random number bounds
DELAY_MIN = 15   # must be less than following MAX values
START_SLEEP_MAX = 180
ESTIM_ON_MAX = 180
ESTIM_OFF_MAX = 120

ADD_ON_PERCENT = 25
ADD_OFF_PERCENT = 18
TEASE_PERCENT = 20

# multipliers for levels off of max value
MAX_PLUS_LEVEL = 1.1
NORMAL_LEVEL = 0.88
LOW_LEVEL = 0.73

# The maximum output value per channel we will allow the user to set
HARD_MAX_A = 105
HARD_MAX_B = 135

# Defines the set of On states to be chosen from at random.
# By changing the contents of this list, you can vary the frequency of various
# intensities being used.  Each mode change will randomly choose a new power level.
onCommand = ['on_low', 'on_low', 'on_norm', 'on_norm', 'on_max', 'on_max_plus']

'''
Defines which modes will be used.  Once we have more
devices, we will need to introduce device specific dicts.
The list is randomized before use and it then sequences through
the randomized list.  You can include entries more than once
and they will be used more frequently.  I omit modes that are
not useful or unintersting.  Tune as desired.
'''
USEFUL_ET232_MODES=['waves', 'intense', 'random', 'audio-soft',
                    'audio-waves', 'hi-freq', 'climb', 'throb',
                    'combo', 'thrust', 'thump', 'ramp', 'stroke',
                    'intense', 'random', 'throb', 'thrust', 'thrust', 'ramp']

# Port number for Surprise web interface
port = 8888

# Devices and other strings
#clickerDevice = '/dev/clicker'
clickerDevice = '/dev/input/event0'

# Estim Device handler: one of ('dweeb', 'buttshock')
estimHandler = 'buttshock'
# estimDevice (only used by buttshock handler)
estimDevice = '/dev/ttyUSB0'


announcePower = False
keepaliveInterval = 15*60
