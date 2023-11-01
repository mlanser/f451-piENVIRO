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
from common import get_RPI_serial_num, get_RPI_ID, exit_now, check_wifi, EXIT_NOW
from enviro_data import EnviroData

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from f451_logger.logger import Logger as f451Logger
from f451_uploader.uploader import Uploader as f451Uploader
from f451_enviro.enviro import Enviro as f451Enviro, PROX_LIMIT, PROX_DEBOUNCE

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


# def process_environ_data(temp, press, humid, pm25, pm10):
#     """Process environment data

#     Process data from BME280 and PMS5003 and return as dict
#     """
#     data = {}

#     data[const.KWD_DATA_TEMPS] = "{:.2f}".format(temp)
#     data[const.KWD_DATA_PRESS] = "{:.2f}".format(press)
#     data[const.KWD_DATA_HUMID] = "{:.2f}".format(humid)
#     data[const.KWD_DATA_P2] = str(pm25)
#     data[const.KWD_DATA_P1] = str(pm10)

#     return data


# def upload_environ_data(values, id):
#     pm_values = dict(i for i in values.items() if i[0].startswith("P"))
#     temp_values = dict(i for i in values.items() if not i[0].startswith("P"))

#     pm_values_json = [{"value_type": key, "value": val}
#                     for key, val in pm_values.items()]
#     temp_values_json = [{"value_type": key, "value": val}
#                         for key, val in temp_values.items()]
#     # resp_1 = requests.post(
#     #     "https://api.luftdaten.info/v1/push-sensor-data/",
#     #     json={
#     #         "software_version": "enviro-plus 0.0.1",
#     #         "sensordatavalues": pm_values_json
#     #     },
#     #     headers={
#     #         "X-PIN": "1",
#     #         "X-Sensor": id,
#     #         "Content-Type": "application/json",
#     #         "cache-control": "no-cache"
#     #     }
#     # )

#     # resp_2 = requests.post(
#     #     "https://api.luftdaten.info/v1/push-sensor-data/",
#     #     json={
#     #         "software_version": "enviro-plus 0.0.1",
#     #         "sensordatavalues": temp_values_json
#     #     },
#     #     headers={
#     #         "X-PIN": "11",
#     #         "X-Sensor": id,
#     #         "Content-Type": "application/json",
#     #         "cache-control": "no-cache"
#     #     }
#     # )

#     # if resp_1.ok and resp_2.ok:
#     #     return True
#     # else:
#     #     return False
#     return True


async def upload_sensor_data(*args, **kwargs):
    """Send sensor data to cloud services.
    
    This help parses and send enviro data to Adafruit IO 
    and Arduino Cloud.

    NOTE: This function will upload specific environment 
          data using the following keywords:

          'temperature' - temperature data
          'pressure'    - barometric pressure
          'humidity'    - humidity

    Args:
        args:
            User can provide single 'dict' with data
        kwargs:
            User can provide individual data points as key-value pairs
    """
    # We combine 'args' and 'kwargs' to allow users to provide a 'dict' with
    # all data points and/or individual data points (which could override 
    # values in the 'dict').
    data = {**args[0], **kwargs} if args and type(args[0]) is dict else kwargs

    sendQ = []

    # Send temperature data ?
    if const.KWD_DATA_TEMPS in kwargs:
        sendQ.append(uploader.aio_send_data(tempsFeed.key, data.get(const.KWD_DATA_TEMPS)))

    # Send barometric pressure data ?
    if const.KWD_FEED_PRESS in kwargs:
        sendQ.append(uploader.aio_send_data(pressFeed.key, data.get(const.KWD_FEED_PRESS) * 100))

    # Send humidity data ?
    if const.KWD_DATA_HUMID in kwargs:
        sendQ.append(uploader.aio_send_data(humidFeed.key, data.get(const.KWD_DATA_HUMID)))

    # pm25 = pm25Raw,
    # pm10 = pm10Raw, 
    # deviceID = enviro.get_ID(const.DEF_ID_PREFIX)

    # await asyncio.gather(*sendQ)
    await asyncio.gather(
        uploader.aio_send_data(tempsFeed.key, 10),
        uploader.aio_send_data(pressFeed.key, 20),
        uploader.aio_send_data(humidFeed.key, 30)
    )


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
    uploadDelay = ioDelay
    tempCounter = 0

    while not EXIT_NOW:
        tempCounter += 1
        EXIT_NOW = (tempCounter >= 1000)

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
        if timeSinceUpdate > 600:
            try:
                asyncio.run(upload_sensor_data(
                    temperature = tempComp, 
                    pressure = pressRaw * 100, 
                    humidity = humidRaw, 
                    pm25 = pm25Raw,
                    pm10 = pm10Raw, 
                    deviceID = get_RPI_ID(const.DEF_ID_PREFIX)
                ))

            except RequestError as e:
                logger.log_error(f"Application terminated due to REQUEST ERROR: {e}")
                raise

            except ThrottlingError as e:
                # Keep increasing 'ioDelay' each time we get a 'ThrottlingError'
                uploadDelay += ioThrottle
                
            else:
                # Reset 'maxDelay' back to normal 'ioDelay' on successful upload
                uploadDelay = ioDelay
                logger.log_info(f"Uploaded: TEMP: {tempComp} - PRESS: {pressRaw * 100} - HUMID: {humidRaw}")

            finally:
                timeUpdate = timeCurrent

        # If proximity crosses threshold, toggle the display mode
        proximity = enviro.get_proximity()

        if proximity > PROX_LIMIT and (timeCurrent - displayUpdate) > PROX_DEBOUNCE:
            enviro.displMode = (enviro.displMode + 1) % (const.MAX_DISPL + 1)
            displayUpdate = timeCurrent

        # Check display mode. Each mode corresponds to a data type
        if enviro.displMode == const.IDX_TEMP:          # type = "temperature"
            enviroData.temperature.data.append(tempComp)
            enviro.display_as_graph(enviroData.temperature.as_dict())

        elif enviro.displMode == const.IDX_PRESS:       # type = "pressure"
            enviroData.pressure.data.append(pressRaw)
            enviro.display_as_graph(enviroData.pressure.as_dict())

        elif enviro.displMode == const.IDX_HUMID:       # type = "humidity"
            enviroData.humidity.data.append(humidRaw)
            enviro.display_as_graph(enviroData.humidity.as_dict())
                
        elif enviro.displMode == const.IDX_LIGHT:       # type = "light"
            data = enviro.get_lux() if (proximity < 10) else 1    # TO DO: fix magic number
            enviroData.light.data.append(data)
            enviro.display_as_graph(enviroData.light.as_dict())

        elif enviro.displMode == const.IDX_OXID:        # type = "oxidised"
            data = enviro.get_gas_data()
            enviroData.oxidised.data.append(data.oxidising / 1000)
            enviro.display_as_graph(enviroData.oxidised.as_dict())
                
        elif enviro.displMode == const.IDX_REDUC:       # type = "reduced"
            data = enviro.get_gas_data()
            enviroData.reduced.data.append(data.reducing / 1000)
            enviro.display_as_graph(enviroData.reduced.as_dict())

        elif enviro.displMode == const.IDX_NH3:         # type = "nh3"
            data = enviro.get_gas_data()
            enviroData.nh3.data.append(data.nh3 / 1000)
            enviro.display_as_graph(enviroData.nh3.as_dict())

        elif enviro.displMode == const.IDX_PM1:         # type = "pm1"
            enviroData.pm1.data.append(float(pmData.pm_ug_per_m3(1.0)))
            enviro.display_as_graph(enviroData.pm1.as_dict())

        elif enviro.displMode == const.IDX_PM25:        # type = "pm25"
            enviroData.pm25.data.append(float(pm25Raw))
            enviro.display_as_graph(enviroData.pm25.as_dict())

        elif enviro.displMode == const.IDX_PM10:        # type = "pm10"
            enviroData.pm10.data.append(float(pm10Raw))
            enviro.display_as_graph(enviroData.pm10.as_dict())

        else:                                           # Display everything on one screen
            enviroData.temperature.data.append(tempComp)
            enviroData.pressure.data.append(pressRaw)
            enviro.display_as_text(enviroData.as_list())

            enviroData.humidity.data.append(humidRaw)
            data = enviro.get_lux() if (proximity < 10) else 1    # TODO: fix magic numbers
            enviroData.light.data.append(data)
            enviro.display_as_text(enviroData.as_list())

            data = enviro.get_gas_data()
            enviroData.oxidised.data.append(data.oxidising / 1000)
            enviroData.reduced.data.append(data.reducing / 1000)
            enviroData.nh3.data.append(data.nh3 / 1000)
            enviro.display_as_text(enviroData.as_list())

            enviroData.pm1.data.append(float(pmData.pm_ug_per_m3(1.0)))
            enviroData.pm25.data.append(float(pm25Raw))
            enviroData.pm10.data.append(float(pm10Raw))
            enviro.display_as_text(enviroData.as_list())

    # A bit of clean-up before we exit
    logger.log_info("-- END Data Logging --")
    enviro.display_reset()
    enviro.display_off()
    # logger.debug(enviroData.as_list())
    # logger.debug(list(enviroData.__dict__.keys()))
    logger.debug(tempsFeed.key)
    logger.debug(pressFeed.key)
    logger.debug(humidFeed.key)

    print("Beep boop")
