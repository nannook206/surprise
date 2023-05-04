# Surprise - A random personal experience

This program/service provide a randomized device activation
experience.  It has been integrated with
(buttshock.io, https://github.com/nannook206/buttshock-py) to provide
direct serial control of Estim devices and DeviceWeb (dweeb,
https://fetlife.com/groups/165887) which provides interfacing
logic and control to a wide variety of devices with a web and
websockets interface thanks to its creator.

The interface is two-fold:
* A web interface can be used, and its phone friendly albeit very
Web 1.0.
* A 4 button remote control (I use a presentation controller)

The basic states are:
* Idle - waiting to be activated, you cat toggle the device on
  and off in this mode.
* Activated - indicate that you are getting ready to start.  It also
  starts a failsafe time that will start the service in 15 minutes
* Started - service starts a random timer about 1-3 minutes after which it
  starts surprising you.

* Locked - in addition you can place the service in the Locked state which prevents resetting
(stopping) the service, or further on/off cycles

My clicker remote is set up as follows:

When Idle, Started:
* Up - Activate, then Start
* Left - Reset (go to Idle)
* Right - Cycle (Max_A -> Max_B -> Max_Both)
* Down - Lock

When in Max_A, Max_B, Max_Both:
* Up - Increase max intensity (about 1%)
* Left - Reset (go to Idle)
* Right - Cycle (Max_A -> Max_B -> Max_Both)
* Down - Decrease max intensity (about 1%)

When Locked:
* Up - Increase Max_A and Max_B (about 1%)
* Middle (if present) - lock max minimums (can only increase the minimum max)
* Down - Decrease Max_A and Max_B (about 1%)

So far we have successfully used this to control an Erostek
ET232 controller with very good success.

The software:
* runSurprise.py
Top level invocation module for Surprise.  It defines the basic flow
of page on the web server, sets up the clicker handlers, and handles
the core state machine and locking (in process()).
Defines which modes will be used:
* Surprise.py
This is the module that does all the surprising behavior.  Lots of use
of the random module to provide a unique experience every time.
* params.py
There are lots of parameters here that you may want to tweak (and yes
we should have a way to more easily set these without changing the code
and that will come in time.
```
FAILSAFE_START = 900
MAX_SESSION_TIME = 70 * 60  # 70 minutes

# Random number bounds
DELAY_MIN = 15   # must be less than following MAX values
START_SLEEP_MAX = 180
ESTIM_ON_MAX = 180
ESTIM_OFF_MAX = 120

ADD_ON_PERCENT = 30
ADD_OFF_PERCENT = 20
TEASE_PERCENT = 20
```
* Key Parameters from params.py
  - FAILSAFE_START
is the time from activating the application to when it starts
even if you are not ready (or lose access to the clicker...).
  - MAX_SESSION_TIME
is the maximum time for a session.  Surprise turns off and
returns to idle after this much time in seconds.
  - DELAY_MIN
minimum time for a delay (see the next three entries)
  - START_SLEEP_MAX
max amount of time to wait before starting the surprising experience (once STARTed)
  - ESTIM_ON_MAX
max amount of time in seconds for an ESTIMulating event
(but note it can be added to with additional random amounts, see code)
  - ESTIM_OFF_MAX
max amount for time in seconds for the off cycle (but this is also subject to addtions)
  - ADD_ON_PERCENT
likelihood that you will add an addtion amount of time to an ON cycle.  Repeats until it fails to add.
  - ADD_OFF_PERCENT
likelihood that you will add an addtion amount of time to an OFF cycle.  Repeats until it fails to add.
* buttshockClient.py
Class and methods to support talking directly to the Estim
device via the buttshock.io library.
* dweebClient.py
Class and methods to support talking to DeviceWeb service using
websockets.  Currently assumes that dweeb is running on the same
host and uses localhost to access it, but it could be on another
host.  Currently a code change but could be easily parameterized.
Its pretty specific to the ET232 but can be easily generalise to
other devices and I am welcome to adding additional device support
here.

* surprise.service
systemd configuration file to start Surprise daemon
* dweeb.service
systemd configuration file to start DeviceWeb (dweeb) daemon
* run_surprise
Called from system startup (e.g. systemd) to start the Surprise application
* run_dweeb
Called from system startup (e.g. systemd) to start the DeviceWeb (dweeb) application
* clicker.py
This class provide support for a button clicker device to actuate the
surprise applicaton remote (or while you a bit tied up...)
* pages.py
Simply defines the HTML pages used by the built in webserver.  Very Web 1.0.
dweebTest.py
Just a simple program to test the interface from my Python to dweeb.
Included in case it will help others with debugging other devices.

I try to provide a good amount of diagnosics from all the modules.  I play with output
of ./Surprise.py and grep to get an idea of what the parameters are going to do.

For testing, you should be able invoke individual modules for functional unit testing.
