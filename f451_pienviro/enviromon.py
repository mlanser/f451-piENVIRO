#!/usr/bin/env python3
"""f451 Labs piENVIRO Enviromon application.

This application is designed for the f451 Labs piENVIRO device which is also 
equipped with an Enviro+ add-on. The main objective is to continously read 
environment data (e.g. temperature, barometric pressure, and humidity from 
the Enviro+ sensors and then upload the data to the Adafruit IO service.

To launch this application from terminal:

    $ nohup python -u enviromon.py > enviromon.out &

This will start the application in the background and it will keep running 
even after terminal window is closed. Any output will be automatically redirected 
to the 'enviromon.out' file.

It's also possible to install this application via 'pip' from Github and one 
can launch the application as follows:

    $ nohup enviromon > enviromon.out &

NOTE: Parts of this code is based on ideas found in the 'luftdaten_combined.py' example 
      from the Enviro+ Python example files. Main modifications include support for 
      Adafruit.io, using Python 'deque' to manage data queues, moving device support 
      to a separate class, etc.

      We also support additional display modes including a screen-saver mode, support 
      for 'settings.toml', and more. And finally, this app also has support for a 
      terminal UI (using the Rich library) with live data updates, sparklines graphs,
      and more.

Dependencies:
    - adafruit-io - only install if you have an account with Adafruit IO
"""

import time
import sys
import asyncio
import contextlib
import platform

from collections import deque
from datetime import datetime
from pathlib import Path

from . import constants as const

import f451_common.cli_ui as f451CLIUI
import f451_common.common as f451Common
import f451_common.logger as f451Logger
import f451_common.cloud as f451Cloud

import f451_enviro.enviro as f451Enviro
import f451_enviro.enviro_data as f451EnviroData

from rich.console import Console
from rich.live import Live

from Adafruit_IO import RequestError, ThrottlingError

# Install Rich 'traceback' and 'pprint' to
# make (debug) life is easier. Trust me!
from rich.pretty import pprint
from rich.traceback import install as install_rich_traceback

install_rich_traceback(show_locals=True)


# fmt: off
# =========================================================
#          G L O B A L S   A N D   H E L P E R S
# =========================================================
APP_VERSION = '1.0.1'
APP_NAME = 'f451 Labs - EnviroMon'
APP_NAME_SHORT = 'EnviroMon'
APP_LOG = 'f451-enviromon.log'      # Individual logs for devices with multiple apps
APP_SETTINGS = 'settings.toml'      # Standard for all f451 Labs projects

APP_MIN_SENSOR_READ_WAIT = 1        # Min wait in sec between sensor reads
APP_MIN_PROG_WAIT = 1               # Remaining min (loop) wait time to display prog bar
APP_WAIT_1SEC = 1
APP_MAX_DATA = 120                  # Max number of data points in the queue
APP_DELTA_FACTOR = 0.02             # Any change within X% is considered negligable
APP_TOPLBL_LEN = 5                  # Num chars of label to display in top bar

APP_DATA_TYPES = [
    const.KWD_DATA_TEMPS,           # 'temperature' in C
    const.KWD_DATA_PRESS,           # barometric 'pressure'
    const.KWD_DATA_HUMID            # 'humidity'
]

APP_DISPLAY_MODES = {
    f451Enviro.KWD_DISPLAY_MIN: const.MIN_DISPL,
    f451Enviro.KWD_DISPLAY_MAX: const.MAX_DISPL,
}

COLOR_LOGO = (255, 0, 0)

class AppRT(f451Common.Runtime):
    """Application runtime object.
    
    We use this object to store/manage configuration and any other variables
    required to run this application as object atrtribustes. This allows us to
    have fewer global variables.
    """
    def __init__(self, appName, appVersion, appNameShort=None, appLog=None, appSettings=None):
        super().__init__(
            appName, 
            appVersion, 
            appNameShort, 
            appLog, 
            appSettings,
            platform.node(),        # Get device 'hostname'
            Path(__file__).parent   # Find dir for this app
        )
        
    def init_runtime(self, cliArgs, data):
        """Initialize the 'runtime' variable
        
        We use an object to hold all core runtime values, flags, etc. 
        This makes it easier to send global values around the app as
        a single entitye rather than having to manage a series of 
        individual (global) values.

        Args:
            cliArgs: holds user-supplied values from ArgParse
            data: general data set (used to create CLI UI table rows, etc.)
        """
        # Load settings and initialize logger
        self.config = f451Common.load_settings(self.appDir.joinpath(self.appSettings))
        self.logger = f451Logger.Logger(self.config, LOGFILE=self.appLog)

        self.ioFreq = self.config.get(const.KWD_FREQ, const.DEF_FREQ)
        self.ioDelay = self.config.get(const.KWD_DELAY, const.DEF_DELAY)
        self.ioWait = max(self.config.get(const.KWD_WAIT, const.DEF_WAIT), APP_MIN_SENSOR_READ_WAIT)
        self.ioThrottle = self.config.get(const.KWD_THROTTLE, const.DEF_THROTTLE)
        self.ioRounding = self.config.get(const.KWD_ROUNDING, const.DEF_ROUNDING)
        self.ioUploadAndExit = False

        # Update log file or level?
        if cliArgs.debug:
            self.logLvl = f451Logger.LOG_DEBUG
            self.debugMode = True
        else:
            self.logLvl = self.config.get(f451Logger.KWD_LOG_LEVEL, f451Logger.LOG_NOTSET)
            self.debugMode = (self.logLvl == f451Logger.LOG_DEBUG)

        self.logger.set_log_level(self.logLvl)

        if cliArgs.log is not None:
            self.logger.set_log_file(appRT.logLvl, cliArgs.log)

        # Initialize various counters, etc.
        self.timeSinceUpdate = float(0)
        self.timeUpdate = time.time()
        self.displayUpdate = self.timeUpdate
        self.uploadDelay = self.ioDelay
        self.maxUploads = int(cliArgs.uploads)
        self.numUploads = 0
        self.loopWait = APP_WAIT_1SEC   # Wait time between main loop cycles

        self.tempCompFactor = self.config.get(f451Common.KWD_TEMP_COMP, f451Common.DEF_TEMP_COMP_FACTOR)
        self.cpuTempsQMaxLen = self.config.get(f451Common.KWD_MAX_LEN_CPU_TEMPS, f451Common.MAX_LEN_CPU_TEMPS)

        # If comp factor is 0 (zero), then do NOT compensate for CPU temp
        self.tempCompYN = self.tempCompFactor > 0

        # Initialize UI for terminal
        if cliArgs.noCLI:
            self.console = Console() # type: ignore
        else:
            UI = f451CLIUI.BaseUI()
            UI.initialize(
                self.appName,
                self.appNameShort,
                self.appVersion,
                f451CLIUI.prep_data(data.as_dict(), APP_DATA_TYPES, labelsOnly=True),
                not cliArgs.noCLI,
            )
            self.console = UI # type: ignore

    def init_CPU_temps(self):
        """Initialize a CPU temperature queue
        
        We use the data in this queue to calculate average CPU temps
        which we then can use to compensate temp reading from the Sense 
        HAT temp sensors.
        """
        return (
            deque(
                [self.sensors['Enviro'].get_CPU_temp(False)]
                * self.cpuTempsQMaxLen,
                maxlen=self.cpuTempsQMaxLen,
            )
            if self.tempCompYN
            else []
        )

    def debug(self, cli=None, data=None):
        """Print/log some basic debug info.
        
        Args:
            cli: CLI args
            data: app data
        """

        self.console.rule('Config Settings', style='grey', align='center')

        self.logger.log_debug(f"DISPL ROT:   {self.sensors['Enviro'].displRotation}")
        self.logger.log_debug(f"DISPL MODE:  {self.sensors['Enviro'].displMode}")
        self.logger.log_debug(f"DISPL PROGR: {self.sensors['Enviro'].displProgress}")
        self.logger.log_debug(f"SLEEP TIME:  {self.sensors['Enviro'].displSleepTime}")
        self.logger.log_debug(f"SLEEP MODE:  {self.sensors['Enviro'].displSleepMode}")

        self.logger.log_debug(f'IO DEL:      {self.ioDelay}')
        self.logger.log_debug(f'IO WAIT:     {self.ioWait}')
        self.logger.log_debug(f'IO THROTTLE: {self.ioThrottle}')

        # Display Raspberry Pi serial and Wi-Fi status
        self.logger.log_debug(
            f'Raspberry Pi serial: {f451Common.get_RPI_serial_num()}'
        )
        self.logger.log_debug(
            f'Wi-Fi: {(f451Common.STATUS_YES if f451Common.check_wifi() else f451Common.STATUS_UNKNOWN)}'
        )

        # List CLI args
        if cli:
            for key, val in vars(cli).items():
                self.logger.log_debug(f"CLI Arg '{key}': {val}")

        # List config settings
        self.console.rule('CONFIG', style='grey', align='center')  # type: ignore
        pprint(self.config, expand_all=True)

        if data:
            self.console.rule('APP DATA', style='grey', align='center')  # type: ignore
            pprint(data.as_dict(), expand_all=True)

        # Display nice border below everything
        self.console.rule(style='grey', align='center')  # type: ignore

    def show_summary(self, cli=None, data=None):
        """Display summary info
        
        We (usually) call this method to display summary info
        at the before we exit the application.

        Args:
            cli: CLI args
            data: app data
        """
        print()
        self.console.rule(f'{self.appName} (v{self.appVersion})', style='grey', align='center')  # type: ignore
        print(f'Work start:  {self.workStart:%a %b %-d, %Y at %-I:%M:%S %p}')
        print(f'Work end:    {(datetime.now()):%a %b %-d, %Y at %-I:%M:%S %p}')
        print(f'Num uploads: {self.numUploads}')

        # Show config info, etc. if in 'debug' mode
        if self.debugMode:
            self.debug(cli, data)

    def add_sensor(self, sensorName, sensorType, **kwargs):
        self.sensors[sensorName] = sensorType(self.config, **kwargs)
        return self.sensors[sensorName]

    def add_feed(self, feedName, feedService, feedKey):
        service = feedService(self.config)
        feed = service.feed_info(feedKey)

        self.feeds[feedName] = f451Cloud.AdafruitFeed(service, feed)

        return self.feeds[feedName]

    def update_action(self, cliUI, msg=None):
        """Wrapper to help streamline code"""
        if cliUI:
            self.console.update_action(msg) # type: ignore

    def update_progress(self, cliUI, prog=None, msg=None):
        """Wrapper to help streamline code"""
        if cliUI:
            self.console.update_progress(prog, msg) # type: ignore        

    def update_upload_status(self, cliUI, lastTime, lastStatus):
        """Wrapper to help streamline code"""
        if cliUI:
            self.console.update_upload_status(      # type: ignore
                lastTime, 
                lastStatus, 
                lastTime + self.uploadDelay, 
                self.numUploads, 
                self.maxUploads
            )

    def update_data(self, cliUI, data):
        """Wrapper to help streamline code"""
        if cliUI:
            self.console.update_data(data) # type: ignore

# Define app runtime object
appRT = AppRT(APP_NAME, APP_VERSION, APP_NAME_SHORT, APP_LOG, APP_SETTINGS)
# fmt: on


# =========================================================
#              H E L P E R   F U N C T I O N S
# =========================================================
async def upload_sensor_data(app, *args, **kwargs):
    """Send sensor data to cloud services.

    This helper function parses and sends enviro data to
    Adafruit IO and/or Arduino Cloud.

    NOTE: This function will upload specific environment
          data using the following keywords:

          'temperature' - temperature data
          'pressure'    - barometric pressure
          'humidity'    - humidity

    Args:
        app:    app: hook to app runtime object
        args:   user can provide single 'dict' with data
        kwargs: user can provide individual data points as key-value pairs
    """
    # We combine 'args' and 'kwargs' to allow users to provide a 'dict' with
    # all data points and/or individual data points (which could override
    # values in the 'dict').
    data = {**args[0], **kwargs} if args and isinstance(args[0], dict) else kwargs

    sendQ = []

    # Send temperature data?
    if data.get(const.KWD_DATA_TEMPS) is not None:
        sendQ.append(app.feeds[const.KWD_DATA_TEMPS].send_data(data.get(const.KWD_DATA_TEMPS)))  # type: ignore

    # Send barometric pressure data?
    if data.get(const.KWD_DATA_PRESS) is not None:
        sendQ.append(app.feeds[const.KWD_DATA_PRESS].send_data(data.get(const.KWD_DATA_PRESS)))  # type: ignore

    # Send humidity data?
    if data.get(const.KWD_DATA_HUMID) is not None:
        sendQ.append(app.feeds[const.KWD_DATA_HUMID].send_data(data.get(const.KWD_DATA_HUMID)))  # type: ignore

    # pm25 = pm25Raw,
    # pm10 = pm10Raw,
    # deviceID = SENSE_HAT.get_ID(DEF_ID_PREFIX)

    await asyncio.gather(*sendQ)


def update_data(data, raw):
    """Update data set with new sensor data"""
    data.temperature.data.append(raw['temperature'])
    data.pressure.data.append(raw['pressure'])
    data.humidity.data.append(raw['humidity'])

    data.light.data.append(raw['light'])
    data.oxidised.data.append(raw['gasData'].oxidising / 1000)
    data.reduced.data.append(raw['gasData'].reducing / 1000)
    data.nh3.data.append(raw['gasData'].nh3 / 1000)
    data.pm1.data.append(raw['pm1'])
    data.pm25.data.append(raw['pm25'])
    data.pm10.data.append(raw['pm10'])


def update_Enviro_LCD_display_mode(app, timeCurrent, proximity):
    if (
        proximity > f451Enviro.PROX_LIMIT
        and (timeCurrent - app.displayUpdate) > f451Enviro.PROX_DEBOUNCE
    ):
        # app.sensors['Enviro'].displMode = (app.sensors['Enviro'].displMode + 1) % (const.MAX_DISPL + 1)
        app.sensors['Enviro'].update_display_mode()
        app.sensors['Enviro'].update_sleep_mode(False)
        # app.displayUpdate = timeCurrent


def update_Enviro_LCD(enviro, data, colors=None):
    """Update Enviro+ LCD depending on display mode

    We check current display mode and then prep data as needed
    for display on LCD.

    Args:
        sense: hook to SenseHat object
        data: full data set where we'll grab a slice from the end
        colors: (optional) custom color map
    """

    def _minMax(data):
        """Create min/max based on all collecxted data

        This will smooth out some hard edges that may occur
        when the data slice is to short.
        """
        scrubbed = [i for i in data if i is not None]
        return (min(scrubbed), max(scrubbed)) if scrubbed else (0, 0)

    def _get_color_map(data, colors=None):
        return f451Common.get_tri_colors(colors, True) if all(data.limits) else None

    # Check display mode. Each mode corresponds to a data type
    # Show temperature?
    if enviro.displMode == const.DISPL_TEMP:
        minMax = _minMax(data.temperature.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.temperature.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show pressure?
    elif enviro.displMode == const.DISPL_PRESS:
        minMax = _minMax(data.pressure.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.pressure.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show humidity?
    elif enviro.displMode == const.DISPL_HUMID:
        minMax = _minMax(data.humidity.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.humidity.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show light?
    elif enviro.displMode == const.DISPL_LIGHT:
        minMax = _minMax(data.light.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.light.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show oxidised?
    elif enviro.displMode == const.DISPL_OXID:
        minMax = _minMax(data.oxidising.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.oxidising.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show reduced?
    elif enviro.displMode == const.DISPL_REDUC:
        minMax = _minMax(data.reducing.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.reducing.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show nh3?
    elif enviro.displMode == const.DISPL_NH3:
        minMax = _minMax(data.nh3.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.nh3.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show pm1?
    elif enviro.displMode == const.DISPL_PM1:
        minMax = _minMax(data.pm1.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.pm1.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show pm25?
    elif enviro.displMode == const.DISPL_PM25:
        minMax = _minMax(data.pm25.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.pm25.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show pm10?
    elif enviro.displMode == const.DISPL_PM10:
        minMax = _minMax(data.pm10.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.pm10.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show everything on one screen?
    elif enviro.displMode == const.DISPL_ALL:
        minMax = _minMax(data.rndpcnt.as_tuple().data)
        dataClean = f451Enviro.prep_data(data.rndpcnt.as_tuple())
        colorMap = _get_color_map(dataClean, colors)
        enviro.display_as_graph(dataClean, minMax, colorMap, APP_TOPLBL_LEN)

    # Show sparkles? :-)
    else:
        enviro.display_sparkle()


def init_cli_parser(appName, appVersion, setDefaults=True):
    """Initialize CLI (ArgParse) parser.

    Initialize the ArgParse parser with CLI 'arguments'
    and return new parser instance.

    Args:
        appName: 'str' with app name
        appVersion: 'str' with app version
        setDefaults: 'bool' flag indicates whether to set up default CLI args

    Returns:
        ArgParse parser instance
    """
    # fmt: off
    parser = f451Common.init_cli_parser(appName, appVersion, setDefaults)

    # Add app-specific CLI args
    parser.add_argument(
        '--noCLI',
        action='store_true',
        default=False,
        help='do not display output on CLI',
    )
    parser.add_argument(
        '--noLCD',
        action='store_true',
        default=False,
        help='do not display output on LCD',
    )
    parser.add_argument(
        '--progress',
        action='store_true',
        default=False,
        help='show upload progress bar on LCD',
    )
    parser.add_argument(
        '--uploads',
        action='store',
        type=int,
        default=-1,
        help='number of uploads before exiting',
    )

    return parser
    # fmt: on


def hurry_up_and_wait(app, cliUI=False):
    """Display wait messages and progress bars

    This function comes into play if we have longer wait times
    between sensor reads, etc. For example, we may want to read
    temperature sensors every second. But we may want to wait a
    minute or more to run internet speed tests.

    Args:
        app: hook to app runtime object
        cliUI: 'bool' indicating whether user wants full UI
    """
    if app.ioWait > APP_MIN_PROG_WAIT:
        app.update_progress(cliUI, None, 'Waiting for sensors')
        for i in range(app.ioWait):
            app.update_progress(cliUI, int(i / app.ioWait * 100))
            time.sleep(APP_WAIT_1SEC)
        app.update_action(cliUI, None)
    else:
        time.sleep(app.ioWait)

    # Update Sense HAT prog bar as needed with time remaining
    # until next data upload
    app.sensors['Enviro'].display_progress(app.timeSinceUpdate / app.uploadDelay)


def collect_data(app, data, cpuTempsQ, timeCurrent, cliUI=False):
    """Collect data from sensors.
    
    This is core of the application where we collect data from 
    one or more sensors, and then upload the data as needed.

    Args:
        app: application runtime object with config, counters, etc.
        data: main application data queue
        timeCurrent: time stamp from when loop started
        cliUI: 'bool' to indicate if we use full (console) UI

    Returns:
        'bool' if 'True' then we're done with all loops and we can exit app
    """
    exitApp = False

    # --- Get sensor data ---
    #
    app.update_action(cliUI, 'Reading sensors …')

    # Get raw temp from sensor
    tempRaw = tempComp = app.sensors['Enviro'].get_temperature()

    # Do we need to compensate for CPU temp?
    if app.tempCompYN:
        # Get current CPU temp, add to queue, and calculate new average
        #
        # NOTE: This feature relies on the 'vcgencmd' which is found on
        #       RPIs. If this is not run on a RPI (e.g. during testing),
        #       then we need to neutralize the 'cpuTemp' compensation.
        cpuTempsQ.append(app.sensors['Enviro'].get_CPU_temp(False))
        cpuTempAvg = sum(cpuTempsQ) / float(app.cpuTempsQMaxLen)

        # Smooth out with some averaging to decrease jitter
        tempComp = tempRaw - ((cpuTempAvg - tempRaw) / app.tempCompFactor)

    # Get barometric pressure and humidity data
    pressRaw = app.sensors['Enviro'].get_pressure()
    humidRaw = app.sensors['Enviro'].get_humidity()

    # Get illumination and proximity data.
    proximity = app.sensors['Enviro'].get_proximity()
    lux = app.sensors['Enviro'].get_lux() if (proximity < 10) else 1    # TODO: fix magic number

    # Get gas and particle data
    gasData = app.sensors['Enviro'].get_gas_data()
    try:
        pmData = app.sensors['Enviro'].get_particles()
        pm25Raw = pmData.pm_ug_per_m3(2.5)                              # TODO: fix magic number
        pm10Raw = pmData.pm_ug_per_m3(10)                               # TODO: fix magic number

    except f451Enviro.EnviroError as e:
        app.logger.log_error(f"Application terminated: {e}")
        sys.exit(1)
    #
    # -----------------------
    # fmt: on

    # Is it time to upload data?
    if app.timeSinceUpdate >= app.uploadDelay:
        try:
            asyncio.run(
                upload_sensor_data(
                    app,
                    {
                        const.KWD_DATA_TEMPS: round(tempComp, app.ioRounding),
                        const.KWD_DATA_PRESS: round(pressRaw, app.ioRounding),
                        const.KWD_DATA_HUMID: round(humidRaw, app.ioRounding),
                    },
                    pm25=round(pm25Raw, app.ioRounding),
                    pm10=round(pm10Raw, app.ioRounding),
                    deviceID=f451Common.get_RPI_ID(f451Common.DEF_ID_PREFIX),
                )
            )

        except RequestError as e:
            app.logger.log_error(f'Application terminated: {e}')
            sys.exit(1)

        except ThrottlingError as e:
            # Keep increasing 'ioDelay' each time we get a 'ThrottlingError'
            app.uploadDelay += app.ioThrottle
            app.logger.log_error(f'Throttling error: {e}')

        except KeyboardInterrupt:
            exitApp = True

        else:
            # Reset 'uploadDelay' back to normal 'ioFreq' on successful upload
            app.numUploads += 1
            app.uploadDelay = app.ioFreq
            exitApp = exitApp or app.ioUploadAndExit
            app.logger.log_info(
                f'Uploaded: TEMP: {round(tempComp, app.ioRounding)} - PRESS: {round(pressRaw, app.ioRounding)} - HUMID: {round(humidRaw, app.ioRounding)}'
            )
            app.update_upload_status(cliUI, timeCurrent, f451CLIUI.STATUS_OK)

        finally:
            app.timeUpdate = timeCurrent
            exitApp = (app.maxUploads > 0) and (app.numUploads >= app.maxUploads)
            app.update_action(cliUI, None)

    # Check 'proximity' value to determine when to toggle display mode
    update_Enviro_LCD_display_mode(app, timeCurrent, proximity)

    # Update data set and display to terminal as needed
    update_data(data, {
        'temperature': tempComp,
        'pressure': pressRaw,
        'humidity': humidRaw,
        'light': lux,
        'gasData': gasData,
        'pm1': float(pmData.pm_ug_per_m3(1.0)),
        'pm25': float(pm25Raw),
        'pm10': float(pm10Raw)
    })

    update_Enviro_LCD(app.sensors['Enviro'], data)
    app.update_data(
        cliUI, f451CLIUI.prep_data(data.as_dict(), APP_DATA_TYPES, APP_DELTA_FACTOR)
    )

    return exitApp


def main_loop(app, data, cliUI=False):
    """Main application loop.

    This is where most of the action happens. We continously collect
    data from our sensors, process it, display it, and upload it at
    certain intervals.

    Args:
        app: application runtime object with config, counters, etc.
        data: main application data queue
        cliUI: 'bool' to indicate if we use full (console) UI
    """
    # Do we need to compensate for CPU temps? If so, initialize a
    # CPU temp queue so that we have data to calculate averages.
    cpuTempsQ = appRT.init_CPU_temps()

    # Set 'wait' counter 'exit' flag and start the loop!
    exitApp = False
    waitForSensor = 0

    while not exitApp:
        try:
            # fmt: off
            timeCurrent = time.time()
            app.timeSinceUpdate = timeCurrent - app.timeUpdate
            app.sensors['Enviro'].update_sleep_mode(
                (timeCurrent - app.displayUpdate) > app.sensors['Enviro'].displSleepTime, # Time to sleep?
                # cliArgs.noLCD,                                                            # Force no LED?
                app.sensors['Enviro'].displSleepMode                                      # Already asleep?
            )
            # fmt: on

            # Update Sense HAT prog bar as needed
            app.sensors['Enviro'].display_progress(app.timeSinceUpdate / app.uploadDelay)

            # Do we need to wait for next sensor read?
            if waitForSensor > 0:
                app.update_progress(cliUI, int((1 - waitForSensor / app.ioWait) * 100))

            # ... or can we collect more 'specimen'? :-P
            else:
                app.update_action(cliUI, None)
                exitApp = collect_data(app, data, cpuTempsQ, timeCurrent, cliUI)
                waitForSensor = max(app.ioWait, APP_MIN_PROG_WAIT)
                if app.ioWait > APP_MIN_PROG_WAIT:
                    app.update_progress(cliUI, None, 'Waiting for speed test')

            # Update UI and SenseHAT LED as needed even when we're just waiting for 
            # next upload. This means that more sparkles are generated as well
            app.update_data(
                cliUI, f451CLIUI.prep_data(data.as_dict(), APP_DATA_TYPES, APP_DELTA_FACTOR)
            )
            update_Enviro_LCD(app.sensors['Enviro'], data)
            app.sensors['Enviro'].display_progress(app.timeSinceUpdate / app.uploadDelay)

        except KeyboardInterrupt:
            exitApp = True

        # Are we done?
        if not exitApp:
            time.sleep(app.loopWait)
            waitForSensor -= app.loopWait


# =========================================================
#      M A I N   F U N C T I O N    /   A C T I O N S
# =========================================================
def main(cliArgs=None):  # sourcery skip: extract-method
    """Main function.

    This function will goes through the setup and then runs the
    main application loop.

    NOTE:
     -  Application will exit with error level 1 if invalid Adafruit IO
        or Arduino Cloud feeds are provided

     -  Application will exit with error level 0 if either no arguments
        are entered via CLI, or if arguments '-V' or '--version' are used.
        No data will be uploaded will be sent in that case.

    Args:
        cliArgs:
            CLI arguments used to start application
    """
    global appRT

    # Parse CLI args and show 'help' and exit if no args
    cli = init_cli_parser(APP_NAME, APP_VERSION, True)
    cliArgs, _ = cli.parse_known_args(cliArgs)
    if not cliArgs and len(sys.argv) == 1:
        cli.print_help(sys.stdout)
        sys.exit(0)

    if cliArgs.version:
        print(f'{APP_NAME} (v{APP_VERSION})')
        sys.exit(0)

    # Get core settings and initialize core data queue
    appData = f451EnviroData.EnviroData(None, APP_MAX_DATA)
    appRT.init_runtime(cliArgs, appData)

    # Verify that feeds exist and initialize them
    try:
        appRT.add_feed(
            const.KWD_DATA_TEMPS,
            f451Cloud.AdafruitCloud,
            appRT.config.get(const.KWD_FEED_TEMPS, None),
        )
        appRT.add_feed(
            const.KWD_DATA_PRESS,
            f451Cloud.AdafruitCloud,
            appRT.config.get(const.KWD_FEED_PRESS, None),
        )
        appRT.add_feed(
            const.KWD_DATA_HUMID,
            f451Cloud.AdafruitCloud,
            appRT.config.get(const.KWD_FEED_HUMID, None),
        )

    except RequestError as e:
        appRT.logger.log_error(f'Application terminated due to REQUEST ERROR: {e}')
        sys.exit(1)

    try:
        # Initialize device instance which includes all sensors
        # and LED display on Sense HAT. Also initialize joystick
        # events and set 'sleep' and 'display' modes.
        appRT.add_sensor('Enviro', f451Enviro.Enviro)
        appRT.sensors['Enviro'].display_init(**APP_DISPLAY_MODES)
        appRT.sensors['Enviro'].update_sleep_mode(cliArgs.noLCD)
        appRT.sensors['Enviro'].displProgress = cliArgs.progress
        appRT.sensors['Enviro'].display_message(APP_NAME)

    except KeyboardInterrupt:
        appRT.sensors['Enviro'].display_reset()
        print(f'{APP_NAME} (v{APP_VERSION}) - Session terminated by user')
        sys.exit(0)

    # --- Main application loop ---
    #
    appRT.logger.log_info('-- START Data Logging --')

    with contextlib.suppress(KeyboardInterrupt):
        if cliArgs.noCLI:
            main_loop(appRT, appData)
        else:
            appRT.console.update_upload_next(appRT.timeUpdate + appRT.uploadDelay)  # type: ignore
            with Live(appRT.console.layout, screen=True, redirect_stderr=False):  # noqa: F841 # type: ignore
                main_loop(appRT, appData, True)

    appRT.logger.log_info('-- END Data Logging --')
    #
    # -----------------------------

    # A bit of clean-up before we exit
    appRT.sensors['Enviro'].display_reset()
    appRT.sensors['Enviro'].display_off()

    # Show session summary
    appRT.show_summary(cliArgs, appData)


# =========================================================
#            G L O B A L   C A T C H - A L L
# =========================================================
if __name__ == '__main__':
    main()  # pragma: no cover
