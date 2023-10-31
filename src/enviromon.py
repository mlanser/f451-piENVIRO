#!/usr/bin/env python3
"""f451 Labs piENVIRO Enviromon application.

This application is designed for the f451 Labs piENVIRO device which is also 
equipped with an Enviro+ add-on. The object is to continously read environment 
data (e.g. temperature, barometric pressure, and humidity from the Enviro+ 
sensors and then upload the data to the Adafruit IO service.

To launch this application from terminal:

    $ nohup python -u enviromon.py > enviromon.out &

This will start the application in the background and it will keep running 
even after terminal window is closed. Any output will be automatically redirected 
to the 'pienviro.out' file.

NOTE: This code is based on the 'luftdaten_combined.py' example from the Enviro+ Python
      example files. Main modifications include support for Adafruit.io, using Python 
      'deque' to manage data queues, moving device support to a separate class, etc.

      We also support additional display modes including a screen-saver mode, support 
      for 'settings.toml', and more.
"""

import time
import sys
import asyncio
import signal

from random import randint
from pathlib import Path
from collections import deque

import constants as const
from common import get_RPI_serial_num, exit_now, check_wifi, EXIT_NOW
from enviro_data import EnviroData

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from f451_logger.logger import Logger as f451Logger
from f451_uploader.uploader import Uploader as f451Uploader
from f451_enviro.enviro import Enviro as f451Enviro

from Adafruit_IO import RequestError, ThrottlingError


# =========================================================
#          G L O B A L S   A N D   H E L P E R S
# =========================================================
LOGLVL = "ERROR"
LOGFILE = "f451-piENVIRO.log"
LOGNAME = "f451-piENVIRO"


def debug_config_info():
    logger.log_debug("-- Config Settings --")
    logger.log_debug(f"DISPL ROT:   {enviro.displRotation}")
    logger.log_debug(f"DISPL MODE:  {enviro.displMode}")
    logger.log_debug(f"DISPL PROGR: {enviro.displProgress}")
    logger.log_debug(f"DISPL SLEEP: {enviro.displSleep}")
    logger.log_debug(f"SLEEP CNTR:  {enviro.displSleepCntr}")
    logger.log_debug(f"IO DEL:      {config.get(const.KWD_DELAY, const.DEF_DELAY)}")
    logger.log_debug(f"IO WAIT:     {config.get(const.KWD_WAIT, const.DEF_WAIT)}")
    logger.log_debug(f"IO THROTTLE: {config.get(const.KWD_THROTTLE, const.DEF_THROTTLE)}")

    # Display Raspberry Pi serial and Wi-Fi status
    logger.log_debug(f"Raspberry Pi serial: {get_RPI_serial_num()}")
    logger.log_debug(f"Wi-Fi: {(const.STATUS_YES if check_wifi() else const.STATUS_UNKNOWN)}")


# =========================================================
#              H E L P E R   F U N C T I O N S
# =========================================================
def process_environ_data(temp, press, humid, pm25, pm10):
    """Process environment data

    Process data from BME280 and PMS5003 and return as dict
    """
    data = {}

    data[const.KWD_DATA_TEMPS] = "{:.2f}".format(temp)
    data[const.KWD_DATA_PRESS] = "{:.2f}".format(press)
    data[const.KWD_DATA_HUMID] = "{:.2f}".format(humid)
    data[const.KWD_DATA_P2] = str(pm25)
    data[const.KWD_DATA_P1] = str(pm10)

    return data


def prep_data_row(inData, label=""):
    """??? WIP ???"""
    row = {
        "data": inData["data"],
        "unit": inData["unit"],
        "limits": inData["limits"],
        "label": label.capitalize()
    }

    return row

def prep_data_for_text_display(inData):
    """??? WIP ???"""
    data = []

    for key, item in inData.items():
        data.append(prep_data_row(item, key))

    return data


def save_data(idx, data, log=False):
    """Save environment data

    Save environment data so that it can be used 
    in graphs later and update log as needed
    """
    global enviroData

    type = const.DATA_TYPES[idx]
    enviroData[type]["data"].append(data)

    if log:
        logger.log_info("{}: {:.1f} {}".format(type[:4], data, enviroData[type]["unit"]))


def save_data_and_display_graph(type, data, log=False):
    """Save data and display graph

    This function saves data to global data set and then 
    displays data and corresponmding text on 0.96" LCD
    """
    global enviroData

    enviroData[type]["data"].append(data)
    enviro.display_as_graph(
        prep_data_row(enviroData[type]["data"], type)
    )

    if log:
        logger.log_info("{}: {:.1f} {}".format(type[:4], data, enviroData[type]["unit"]))


def upload_environ_data(values, id):
    pm_values = dict(i for i in values.items() if i[0].startswith("P"))
    temp_values = dict(i for i in values.items() if not i[0].startswith("P"))

    pm_values_json = [{"value_type": key, "value": val}
                    for key, val in pm_values.items()]
    temp_values_json = [{"value_type": key, "value": val}
                        for key, val in temp_values.items()]
    # resp_1 = requests.post(
    #     "https://api.luftdaten.info/v1/push-sensor-data/",
    #     json={
    #         "software_version": "enviro-plus 0.0.1",
    #         "sensordatavalues": pm_values_json
    #     },
    #     headers={
    #         "X-PIN": "1",
    #         "X-Sensor": id,
    #         "Content-Type": "application/json",
    #         "cache-control": "no-cache"
    #     }
    # )

    # resp_2 = requests.post(
    #     "https://api.luftdaten.info/v1/push-sensor-data/",
    #     json={
    #         "software_version": "enviro-plus 0.0.1",
    #         "sensordatavalues": temp_values_json
    #     },
    #     headers={
    #         "X-PIN": "11",
    #         "X-Sensor": id,
    #         "Content-Type": "application/json",
    #         "cache-control": "no-cache"
    #     }
    # )

    # if resp_1.ok and resp_2.ok:
    #     return True
    # else:
    #     return False
    return True


async def send_all_sensor_data(client, tempsData, pressData, humidData):
    """
    Send sensor data to Adafruit IO

    Args:
        client:
            We need full app context client
        tempsData:
            'dict' with 'temperature feed' key and temperature data point
        pressData:
            'dict' with 'pressure feed' key and pressure data point
        humidData:
            'dict' with 'humidity feed' key and humidity data point

    Raises:
        RequestError:
            When API request fails
        ThrottlingError:
            When exceeding Adafruit IO rate limit
    """
    pass
    # await asyncio.gather(
    #     client.send_sensor_data(tempsData),
    #     client.send_sensor_data(pressData),
    #     client.send_sensor_data(humidData)
    # )


# =========================================================
#      M A I N   F U N C T I O N    /   A C T I O N S
# =========================================================
if __name__ == '__main__':
    # Init signals
    signal.signal(signal.SIGINT, exit_now)
    signal.signal(signal.SIGTERM, exit_now)

    # Get app dir
    appDir = Path(__file__).parent

    # Initialize TOML parser and load 'settings.toml' file
    try:
        with open(appDir.joinpath("settings.toml"), mode="rb") as fp:
            config = tomllib.load(fp)
    except tomllib.TOMLDecodeError:
        sys.exit("Invalid 'settings.toml' file")      

    # Initialize logger and IO uploader
    logger = f451Logger(config)
    uploader = f451Uploader(config)

    # Initialize device instance which includes all sensors
    # an d LCD display on Enviro+
    enviro = f451Enviro(config)
    enviro.display_init()

    # enviroData = init_data_set(1, enviro.widthLCD)
    enviroData = EnviroData(1, 10)

    try:
        tempsFeed = uploader.aio_feed_info(config.get(const.KWD_FEED_TEMPS))
        pressFeed = uploader.aio_feed_info(config.get(const.KWD_FEED_PRESS))
        humidFeed = uploader.aio_feed_info(config.get(const.KWD_FEED_HUMID))

    except RequestError as e:
        logger.log_error(f"Application terminated due to REQUEST ERROR: {e}")
        enviro.display_reset()
        sys.exit(1)

    # Get core settings
    ioDelay = config.get(const.KWD_DELAY, const.DEF_DELAY)
    ioWait = config.get(const.KWD_WAIT, const.DEF_WAIT)
    ioThrottle = config.get(const.KWD_THROTTLE, const.DEF_THROTTLE)

    logData = False                         # Log all data
    delayCounter = maxDelay = ioDelay       # Ensure that we upload first reading

    # Initialize core data queues
    tempCompFactor = config.get(const.KWD_TEMP_COMP, const.DEF_TEMP_COMP_FACTOR)
    cpuTempsQMaxLen = config.get(const.KWD_MAX_LEN_CPU_TEMPS, const.MAX_LEN_CPU_TEMPS)
    cpuTempsQ = deque([enviro.get_CPU_temp(False)] * cpuTempsQMaxLen, maxlen=cpuTempsQMaxLen)

    # Log core info
    debug_config_info()
    logger.log_info("-- START Data Logging --")

    # # -- Main application loop --
    displayUpdate = 0
    timeSinceUpdate = 0
    timeUpdate = time.time()
    tempCounter = 0

    while not EXIT_NOW:
        tempCounter += 1
        EXIT_NOW = (tempCounter >= 10)

        timeCurrent = time.time()
        timeSinceUpdate = timeCurrent - timeUpdate

        # Get raw temp from sensor
        tempRaw = enviro.get_temperature()

        # Get current CPU temp, add to queue, and calculate new average
        #
        # NOTE: This feature relies on the 'vcgencmd' which is found on
        #       RPIs. If this is not run on a RPI (e.g. during testing),
        #       then we need to neutralize the 'cpuTemp' compensation. 
        cpuTempsQ.append(enviro.get_CPU_temp(False))
        cpuTempAvg = sum(cpuTempsQ) / float(cpuTempsQMaxLen)

        # Smooth out with some averaging to decrease jitter
        tempComp = tempRaw - ((cpuTempAvg - tempRaw) / tempCompFactor)

        pressRaw = enviro.get_pressure()
        humidRaw = enviro.get_humidity()

        pmData = enviro.get_particles()
        pm25Raw = pmData.pm_ug_per_m3(2.5)      # TO DO: fix magic number
        pm10Raw = pmData.pm_ug_per_m3(10)       # TO DO: fix magic number

        # Is it time to upload data?
        # if timeSinceUpdate > ioDelay:
        #     resp = upload_environ_data(
        #         process_environ_data(tempComp, pressRaw * 100, humidRaw, pm25Raw, pm10Raw), 
        #         enviro.get_ID(const.DEF_ID_PREFIX)
        #     )
        #     timeUpdate = timeCurrent
        #     logger.log_info(f"Upload Response: {const.STATUS_SUCCESS if resp else const.STATUS_FAILURE}")

        # If proximity crosses threshold, toggle the display mode
        proximity = enviro.get_proximity()

        if proximity > const.PROX_LIMIT and (timeCurrent - displayUpdate) > const.PROX_DEBOUNCE:
            enviro.displMode = (enviro.displMode + 1) % (const.MAX_DISPL + 1)
            displayUpdate = timeCurrent

        # Check display mode. Each mode corresponds to a data type
        if enviro.displMode == const.IDX_TEMP:        # type = "temperature"
            enviroData.temperature.data.append(tempComp)
            enviro.display_as_graph(enviroData.temperature.as_dict())
            if logData:
                logger.log_info("{}: {:.1f} {}".format(type[:4], tempComp, enviroData.temperature.unit))

    #     elif enviro.displMode == const.IDX_PRESS:     # type = "pressure"
    #         save_data_and_display_graph(
    #             const.DATA_TYPES[enviro.displMode], 
    #             pressRaw
    #         )

    #     elif enviro.displMode == const.IDX_HUMID:     # type = "humidity"
    #         save_data_and_display_graph(
    #             const.DATA_TYPES[enviro.displMode], 
    #             humidRaw
    #         )

    #     elif enviro.displMode == const.IDX_LIGHT:     # type = "light"
    #         data = enviro.get_lux() if (proximity < 10) else 1    # TO DO: fix magic number
    #         save_data_and_display_graph(
    #             const.DATA_TYPES[enviro.displMode], 
    #             data
    #         )

    #     elif enviro.displMode == const.IDX_OXID:      # type = "oxidised"
    #         data = enviro.get_gas_data()
    #         save_data_and_display_graph(
    #             const.DATA_TYPES[enviro.displMode], 
    #             data.oxidising / 1000
    #         )

    #     elif enviro.displMode == const.IDX_REDUC:     # type = "reduced"
    #         data = enviro.get_gas_data()
    #         save_data_and_display_graph(
    #             const.DATA_TYPES[enviro.displMode], 
    #             data.reducing / 1000
    #         )

    #     elif enviro.displMode == const.IDX_NH3:       # type = "nh3"
    #         data = enviro.get_gas_data()
    #         save_data_and_display_graph(
    #             const.DATA_TYPES[enviro.displMode], 
    #             data.nh3 / 1000
    #         )

    #     elif enviro.displMode == const.IDX_PM1:       # type = "pm1"
    #         save_data_and_display_graph(
    #             const.DATA_TYPES[enviro.displMode], 
    #             float(pmData.pm_ug_per_m3(1.0))
    #         )

    #     elif enviro.displMode == const.IDX_PM25:      # type = "pm25"
    #         save_data_and_display_graph(
    #             const.DATA_TYPES[enviro.displMode], 
    #             float(pm25Raw)
    #         )

    #     elif enviro.displMode == const.IDX_PM10:      # type = "pm10"
    #         save_data_and_display_graph(
    #             const.DATA_TYPES[enviro.displMode], 
    #             float(pm10Raw)
    #         )

    #     else:                           # Display everything on one screen
    #         save_data(const.IDX_TEMP, tempComp)
    #         save_data(const.IDX_PRESS, pressRaw)
    #         enviro.display_as_text(prep_data_for_text_display(enviroData))

    #         save_data(const.IDX_HUMID, humidRaw)
    #         data = enviro.get_lux() if (proximity < 10) else 1    # TO DO: fix magic number
    #         save_data(const.IDX_LIGHT, data)
    #         enviro.display_as_text(prep_data_for_text_display(enviroData))

    #         data = enviro.get_gas_data()
    #         save_data(const.IDX_OXID, data.oxidising / 1000)
    #         save_data(const.IDX_REDUC, data.reducing / 1000)
    #         save_data(const.IDX_NH3, data.nh3 / 1000)
    #         enviro.display_as_text(prep_data_for_text_display(enviroData))

    #         save_data(const.IDX_PM1, float(pmData.pm_ug_per_m3(1.0)))
    #         save_data(const.IDX_PM25, float(pm25Raw))
    #         save_data(const.IDX_PM10, float(pm10Raw))
    #         enviro.display_as_text(prep_data_for_text_display(enviroData))

    # A bit of clean-up before we exit
    logger.log_info("-- END Data Logging --")
    enviro.display_reset()
    enviro.display_off()
    logger.debug(dict(enviroData))
    print("Beep boop")
