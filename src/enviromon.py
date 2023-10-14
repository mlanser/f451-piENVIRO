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
LOGFILE = "f451-piF451.log"
LOGNAME = "f451-piF451"


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
def parse_environ_data(temp, press, humid, pm25, pm10):
    """Parse environment data

    Parse data from BME280 and PMS5003 and return as dict
    """
    data = {}
    data[const.KWD_DATA_TEMPS] = "{:.2f}".format(temp)
    data[const.KWD_DATA_PRESS] = "{:.2f}".format(press)
    data[const.KWD_DATA_HUMID] = "{:.2f}".format(humid)
    data[const.KWD_DATA_P2] = str(pm25)
    data[const.KWD_DATA_P1] = str(pm10)

    return data


# Saves the data to be used in the graphs later and prints to the log
def save_data(idx, data):
    global dataSet

    type = const.DATA_TYPES[idx]

    # Maintain length of list
    dataSet[type] = dataSet[type][1:] + [data]
    unit = const.DATA_UNITS[idx]
    message = "{}: {:.1f} {}".format(type[:4], data, unit)
    piEnviro.log_info(message)


# Displays data and text on the 0.96" LCD
def display_text(type, data, unit):
    global dataSet

    # Maintain length of list
    dataSet[type] = dataSet[type][1:] + [data]

    piEnviro.display_as_graph(dataSet[type], type, unit)


# Displays all the text on the 0.96" LCD
def display_everything():
    global dataSet

    piEnviro.display_as_text(dataSet)


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

    cpuTempsQMaxLen = piEnviro.get_config(const.KWD_MAX_LEN_CPU_TEMPS, const.MAX_LEN_CPU_TEMPS)
    cpuTempsQ = deque([piEnviro.get_CPU_temp()] * cpuTempsQMaxLen, maxlen=cpuTempsQMaxLen)

    tempCompFactor = piEnviro.get_config(const.KWD_TEMP_COMP, const.DEF_TEMP_COMP_FACTOR)

    delayCounter = maxDelay = ioDelay       # Ensure that we upload first reading
    piEnviro.sleepCounter = piEnviro.displSleep   # Reset counter for screen blanking

    # Initialize core data queues
    # tempsQ = deque(EMPTY_Q, maxlen=const.LED_MAX_COL) # Temperature queue
    # pressQ = deque(EMPTY_Q, maxlen=const.LED_MAX_COL) # Pressure queue
    # humidQ = deque(EMPTY_Q, maxlen=const.LED_MAX_COL) # Humidity queue
    dataSet = {}
    for v in const.DATA_TYPES:
        dataSet[v] = [1] * piEnviro.widthLCD

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
    # Added for state
    delay = 0.5  # Debounce the proximity tap
    last_page = 0
    light = 1

    timeSinceUpdate = 0
    timeUpdate = time.time()

    # Main loop to read data, display, and send to Luftdaten
    counter = 0
    while not EXIT_NOW:
        counter += 1
        EXIT_NOW = (counter >= 200)
        try:
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

            if timeSinceUpdate > 145:                   # TO DO: fix magic number
                resp = upload_environ_data(
                    parse_environ_data(tempComp, pressRaw * 100, humidRaw, pm25Raw, pm10Raw), 
                    piEnviro.get_ID(const.DEF_ID_PREFIX)
                )
                timeUpdate = timeCurrent
                piEnviro.log_info(f"Upload Response: {const.STATUS_SUCCESS if resp else const.STATUS_FAILURE}")

            # If the proximity crosses the threshold, toggle the display mode
            proximity = piEnviro.get_proximity()

            if proximity > 1500 and timeCurrent - last_page > delay:
                piEnviro.displMode = (piEnviro.displMode + 1) % (const.MAX_DISPL + 1)
                last_page = timeCurrent

            # Check display mode. There's one mode for each data type
            if piEnviro.displMode == 0:     # type = "temperature"
                display_text(const.DATA_TYPES[piEnviro.displMode], tempComp, const.DATA_UNITS[piEnviro.displMode])

            elif piEnviro.displMode == 1:   # type = "pressure"
                display_text(const.DATA_TYPES[piEnviro.displMode], pressRaw, const.DATA_UNITS[piEnviro.displMode])

            elif piEnviro.displMode == 2:   # type = "humidity"
                display_text(const.DATA_TYPES[piEnviro.displMode], humidRaw, const.DATA_UNITS[piEnviro.displMode])

            elif piEnviro.displMode == 3:   # type = "light"
                if proximity < 10:
                    data = piEnviro.get_lux()
                else:
                    data = 1
                display_text(const.DATA_TYPES[piEnviro.displMode], data, const.DATA_UNITS[piEnviro.displMode])

            elif piEnviro.displMode == 4:   # type = "oxidized"
                data = piEnviro.GAS.read_all()
                data = data.oxidising / 1000
                display_text(const.DATA_TYPES[piEnviro.displMode], data, const.DATA_UNITS[piEnviro.displMode])

            elif piEnviro.displMode == 5:   # type = "reduced"
                data = piEnviro.GAS.read_all()
                data = data.reducing / 1000
                display_text(const.DATA_TYPES[piEnviro.displMode], data, const.DATA_UNITS[piEnviro.displMode])

            elif piEnviro.displMode == 6:   # type = "nh3"
                data = piEnviro.GAS.read_all()
                data = data.nh3 / 1000
                display_text(const.DATA_TYPES[piEnviro.displMode], data, const.DATA_UNITS[piEnviro.displMode])

            elif piEnviro.displMode == 7:   # type = "pm1"
                data = float(pmData.pm_ug_per_m3(1.0))
                display_text(const.DATA_TYPES[piEnviro.displMode], data, const.DATA_UNITS[piEnviro.displMode])

            elif piEnviro.displMode == 8:   # type = "pm25"
                display_text(const.DATA_TYPES[piEnviro.displMode], float(pm25Raw), const.DATA_UNITS[piEnviro.displMode])

            elif piEnviro.displMode == 9:   # type = "pm10"
                display_text(const.DATA_TYPES[piEnviro.displMode], float(pm10Raw), const.DATA_UNITS[piEnviro.displMode])

            else:                           # Display everything on one screen
                save_data(0, tempComp)
                save_data(1, pressRaw)
                display_everything()

                save_data(2, humidRaw)
                if proximity < 10:
                    raw_data = piEnviro.get_lux()
                else:
                    raw_data = 1
                save_data(3, raw_data)
                display_everything()

                gas_data = piEnviro.GAS.read_all()
                save_data(4, gas_data.oxidising / 1000)
                save_data(5, gas_data.reducing / 1000)
                save_data(6, gas_data.nh3 / 1000)
                display_everything()

                pms_data = None
                save_data(7, float(pmData.pm_ug_per_m3(1.0)))
                save_data(8, float(pm25Raw))
                save_data(9, float(pm10Raw))
                display_everything()

        except Exception as e:
            print(e)
            EXIT_NOW = True

    # A bit of clean-up before we exit
    piEnviro.log_info("-- END Data Logging --")
    piEnviro.display_reset()
    piEnviro.display_off()
