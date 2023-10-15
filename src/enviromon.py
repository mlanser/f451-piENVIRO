#!/usr/bin/env python3
"""f451 Labs piENVIRO application.

This application is designed for the f451 Labs piENVIRO device which is also equipped with 
a Enviro+ add-on. The object is to continously read environment data (e.g. temperature, 
barometric pressure, and humidity from the Enviro+ sensors and then upload the data to 
the Adafruit IO service.

To launch this application from terminal:

    $ nohup python -u enviromon.py > enviromon.out &

This will start the application in the background and it will keep running even after 
terminal window is closed. Any output will be redirected to the 'pienviro.out' file.    
"""

import time
import sys
import asyncio
import signal

from collections import deque
from random import randint
from pathlib import Path

from Adafruit_IO import Client, MQTTClient, RequestError, ThrottlingError

import constants as const
from pienviro import Device
from common import exit_now, check_wifi, EXIT_NOW

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


# =========================================================
#          G L O B A L S   A N D   H E L P E R S
# =========================================================
LOGLVL = "ERROR"
LOGFILE = "f451-piENVIRO.log"
LOGNAME = "f451-piENVIRO"


def debug_config_info(dev):
    dev.log_debug("-- Config Settings --")
    dev.log_debug(f"DISPL ROT:   {dev.displRotation}")
    dev.log_debug(f"DISPL MODE:  {dev.displMode}")
    dev.log_debug(f"DISPL PROGR: {dev.displProgress}")
    dev.log_debug(f"DISPL SLEEP: {dev.displSleep}")
    dev.log_debug(f"SLEEP CNTR:  {dev.sleepCounter}")
    dev.log_debug(f"IO DEL:      {dev.get_config(const.KWD_DELAY, const.DEF_DELAY)}")
    dev.log_debug(f"IO WAIT:     {dev.get_config(const.KWD_WAIT, const.DEF_WAIT)}")
    dev.log_debug(f"IO THROTTLE: {dev.get_config(const.KWD_THROTTLE, const.DEF_THROTTLE)}")

    # Display Raspberry Pi serial and Wi-Fi status
    dev.log_debug(f"Raspberry Pi serial: {piEnviro.serialNum}")
    dev.log_debug(f"Wi-Fi: {(const.STATUS_YES if check_wifi() else const.STATUS_NO)}")


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


def save_data(idx, data, log=False):
    """Save environment data

    Save environment data so that it can be used 
    in graphs later and update log as needed
    """
    global environDataSet

    type = const.DATA_TYPES[idx]
    environDataSet[type].append(data)

    piEnviro.log(
        (const.LOG_INFO if log else const.LOG_DEBUG),
        "{}: {:.1f} {}".format(type[:4], data, const.DATA_UNITS[idx])
    )


def save_data_and_display_graph(type, data, unit):
    """Save data and display graph

    This function saves data to global data set and then 
    displays data and corresponmding text on 0.96" LCD
    """
    global environDataSet

    environDataSet[type].append(data)
    piEnviro.display_as_graph(environDataSet[type], type, unit)


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

    # Initialize device instance which includes the logger, 
    # Enviro+, and Adafruit IO client
    piEnviro = Device(config, appDir)
    piEnviro.display_init()

    # try:
    #     tempsFeed = piEnviro.get_feed_info(const.KWD_FEED_TEMPS)
    #     pressFeed = piEnviro.get_feed_info(const.KWD_FEED_PRESS)
    #     humidFeed = piEnviro.get_feed_info(const.KWD_FEED_HUMID)

    # except RequestError as e:
    #     piEnviro.log_error(f"Application terminated due to REQUEST ERROR: {e}")
    #     piEnviro.display_reset()
    #     sys.exit(1)

    # Get core settings
    ioDelay = piEnviro.get_config(const.KWD_DELAY, const.DEF_DELAY)
    ioWait = piEnviro.get_config(const.KWD_WAIT, const.DEF_WAIT)
    ioThrottle = piEnviro.get_config(const.KWD_THROTTLE, const.DEF_THROTTLE)

    tempCompFactor = piEnviro.get_config(const.KWD_TEMP_COMP, const.DEF_TEMP_COMP_FACTOR)

    delayCounter = maxDelay = ioDelay       # Ensure that we upload first reading
    piEnviro.sleepCounter = piEnviro.displSleep   # Reset counter for screen blanking

    # Initialize core data queues
    cpuTempsQMaxLen = piEnviro.get_config(const.KWD_MAX_LEN_CPU_TEMPS, const.MAX_LEN_CPU_TEMPS)
    cpuTempsQ = deque([piEnviro.get_CPU_temp()] * cpuTempsQMaxLen, maxlen=cpuTempsQMaxLen)

    environDataSet = {}
    for t in const.DATA_TYPES:
        environDataSet[t] = deque([1] * piEnviro.widthLCD, maxlen=piEnviro.widthLCD)

    # Log core info
    debug_config_info(piEnviro)
    piEnviro.log_info("-- START Data Logging --")

    #
    # vvvvvvvvvvvvvvvvvvvvvvvvvv ============================ vvvvvvvvvvvvvvvvvvvvv
    #
    print("""luftdaten_combined.py - This combines the functionality of luftdaten.py and combined.py
    ================================================================================================
    Luftdaten INFO
    Reads temperature, pressure, humidity,
    PM2.5, and PM10 from Enviro plus and sends data to Luftdaten,
    the citizen science air quality project.

    Note: you'll need to register with Luftdaten at:
    https://meine.luftdaten.info/ and enter your Raspberry Pi
    serial number that's displayed on the Enviro plus LCD along
    with the other details before the data appears on the
    Luftdaten map.

    Press Ctrl+C to exit!

    ========================================================================

    Combined INFO:
    Displays readings from all of Enviro plus' sensors

    Press Ctrl+C to exit!

    """)

    # -- Main application loop --
    displayUpdate = 0
    timeSinceUpdate = 0
    timeUpdate = time.time()
    counter = 0

    while not EXIT_NOW:
        counter += 1
        EXIT_NOW = (counter >= 200)

        timeCurrent = time.time()
        timeSinceUpdate = timeCurrent - timeUpdate

        # Get current CPU temp, add to queue, and calculate new average
        cpuTempsQ.append(piEnviro.get_CPU_temp())
        cpuTempAvg = sum(cpuTempsQ) / float(cpuTempsQMaxLen)

        # Smooth out with some averaging to decrease jitter
        tempRaw = piEnviro.get_temperature()
        tempComp = tempRaw - ((cpuTempAvg - tempRaw) / tempCompFactor)

        pressRaw = piEnviro.get_pressure()
        humidRaw = piEnviro.get_humidity()

        pmData = piEnviro.get_particles()
        pm25Raw = pmData.pm_ug_per_m3(2.5)      # TO DO: fix magic number
        pm10Raw = pmData.pm_ug_per_m3(10)       # TO DO: fix magic number

        # Is it time to upload data?
        if timeSinceUpdate > ioDelay:
            resp = upload_environ_data(
                process_environ_data(tempComp, pressRaw * 100, humidRaw, pm25Raw, pm10Raw), 
                piEnviro.get_ID(const.DEF_ID_PREFIX)
            )
            timeUpdate = timeCurrent
            piEnviro.log_info(f"Upload Response: {const.STATUS_SUCCESS if resp else const.STATUS_FAILURE}")

        # If proximity crosses threshold, toggle the display mode
        proximity = piEnviro.get_proximity()

        if proximity > const.PROX_LIMIT and (timeCurrent - displayUpdate) > const.PROX_DEBOUNCE:
            piEnviro.displMode = (piEnviro.displMode + 1) % (const.MAX_DISPL + 1)
            displayUpdate = timeCurrent

        # Check display mode. Each mode corresponds to a data type
        if piEnviro.displMode == const.IDX_TEMP:        # type = "temperature"
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                tempComp, 
                const.DATA_UNITS[piEnviro.displMode]
            )

        elif piEnviro.displMode == const.IDX_PRESS:     # type = "pressure"
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                pressRaw, 
                const.DATA_UNITS[piEnviro.displMode]
            )

        elif piEnviro.displMode == const.IDX_HUMID:     # type = "humidity"
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                humidRaw, 
                const.DATA_UNITS[piEnviro.displMode]
            )

        elif piEnviro.displMode == const.IDX_LIGHT:     # type = "light"
            data = piEnviro.get_lux() if (proximity < 10) else 1    # TO DO: fix magic number
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                data, 
                const.DATA_UNITS[piEnviro.displMode]
            )

        elif piEnviro.displMode == const.IDX_OXID:      # type = "oxidised"
            data = piEnviro.get_gas_data()
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                data.oxidising / 1000, 
                const.DATA_UNITS[piEnviro.displMode]
            )

        elif piEnviro.displMode == const.IDX_REDUC:     # type = "reduced"
            data = piEnviro.get_gas_data()
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                data.reducing / 1000, 
                const.DATA_UNITS[piEnviro.displMode]
            )

        elif piEnviro.displMode == const.IDX_NH3:       # type = "nh3"
            data = piEnviro.get_gas_data()
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                data.nh3 / 1000, 
                const.DATA_UNITS[piEnviro.displMode]
            )

        elif piEnviro.displMode == const.IDX_PM1:       # type = "pm1"
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                float(pmData.pm_ug_per_m3(1.0)), 
                const.DATA_UNITS[piEnviro.displMode]
            )

        elif piEnviro.displMode == const.IDX_PM25:      # type = "pm25"
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                float(pm25Raw), 
                const.DATA_UNITS[piEnviro.displMode]
            )

        elif piEnviro.displMode == const.IDX_PM10:      # type = "pm10"
            save_data_and_display_graph(
                const.DATA_TYPES[piEnviro.displMode], 
                float(pm10Raw), 
                const.DATA_UNITS[piEnviro.displMode]
            )

        else:                           # Display everything on one screen
            save_data(const.IDX_TEMP, tempComp)
            save_data(const.IDX_PRESS, pressRaw)
            piEnviro.display_as_text(environDataSet)

            save_data(const.IDX_HUMID, humidRaw)
            raw_data = piEnviro.get_lux() if (proximity < 10) else 1    # TO DO: fix magic number
            save_data(const.IDX_LIGHT, raw_data)
            piEnviro.display_as_text(environDataSet)

            gas_data = piEnviro.get_gas_data()
            save_data(4, gas_data.oxidising / 1000)
            save_data(5, gas_data.reducing / 1000)
            save_data(6, gas_data.nh3 / 1000)
            piEnviro.display_as_text(environDataSet)

            pms_data = None
            save_data(7, float(pmData.pm_ug_per_m3(1.0)))
            save_data(8, float(pm25Raw))
            save_data(9, float(pm10Raw))
            piEnviro.display_as_text(environDataSet)

    # A bit of clean-up before we exit
    piEnviro.log_info("-- END Data Logging --")
    piEnviro.display_reset()
    piEnviro.display_off()
