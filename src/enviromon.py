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

# ????????????????
import colorsys
from PIL import Image, ImageDraw, ImageFont
from fonts.ttf import RobotoMedium as UserFont
# ????????????????


# =========================================================
#          G L O B A L S   A N D   H E L P E R S
# =========================================================
#         - 0    1    2    3    4    5    6    7 -
EMPTY_Q = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
COLORS  = [const.RGB_BLUE, const.RGB_GREEN, const.RGB_YELLOW, const.RGB_RED]

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
def parse_environ_data(comp_temp, mod_press, raw_humid, raw_pm25, raw_pm10):
    """Parse environment data

    Parse data from BME280 and PMS5003 and return as dict
    """
    data = {}
    data[const.KWD_DATA_TEMPS] = "{:.2f}".format(comp_temp)
    data[const.KWD_DATA_PRESS] = "{:.2f}".format(mod_press)
    data[const.KWD_DATA_HUMID] = "{:.2f}".format(raw_humid)
    data[const.KWD_DATA_P2] = str(raw_pm25)
    data[const.KWD_DATA_P1] = str(raw_pm10)

    return data


# Saves the data to be used in the graphs later and prints to the log
def save_data(idx, data):
    variable = variables[idx]
    # Maintain length of list
    values_lcd[variable] = values_lcd[variable][1:] + [data]
    unit = units[idx]
    message = "{}: {:.1f} {}".format(variable[:4], data, unit)
    piEnviro.log_info(message)


# Displays data and text on the 0.96" LCD
def display_text(variable, data, unit):
    # Maintain length of list
    values_lcd[variable] = values_lcd[variable][1:] + [data]

    # Scale the values for the variable between 0 and 1
    vmin = min(values_lcd[variable])
    vmax = max(values_lcd[variable])
    colors = [(v - vmin + 1) / (vmax - vmin + 1)
            for v in values_lcd[variable]]
    
    # Format the variable name and value
    message = "{}: {:.1f} {}".format(variable[:4], data, unit)
    piEnviro.log_info(message)
    draw.rectangle((0, 0, piEnviro.widthLCD, piEnviro.heightLCD), const.RGB_WHITE)
    
    for i in range(len(colors)):
        # Convert the values to colors from red to blue
        colour = (1.0 - colors[i]) * 0.6
        r, g, b = [int(x * 255.0)
                for x in colorsys.hsv_to_rgb(colour, 1.0, 1.0)]
    
        # Draw a 1-pixel wide rectangle of colour
        draw.rectangle((i, top_pos, i + 1, piEnviro.heightLCD), (r, g, b))
    
        # Draw a line graph in black
        line_y = piEnviro.heightLCD - \
            (top_pos + (colors[i] * (piEnviro.heightLCD - top_pos))) + top_pos
        draw.rectangle((i, line_y, i + 1, line_y + 1), const.RGB_BLACK)
    
    # Write the text at the top in black
    draw.text((0, 0), message, font=font, fill=const.RGB_BLACK)
    piEnviro.LCD.display(img)


# Displays all the text on the 0.96" LCD
def display_everything():
    draw.rectangle((0, 0, piEnviro.widthLCD, piEnviro.heightLCD), const.RGB_BLACK)
    column_count = 2
    row_count = (len(variables) / column_count)
    for i in range(len(variables)):
        variable = variables[i]
        data_value = values_lcd[variable][-1]
        unit = units[i]
        x = const.DEF_LCD_OFFSET_X + ((piEnviro.widthLCD // column_count) * (i // row_count))
        y = const.DEF_LCD_OFFSET_Y + ((piEnviro.heightLCD / row_count) * (i % row_count))
        message = "{}: {:.1f} {}".format(variable[:4], data_value, unit)
        lim = limits[i]
        rgb = palette[0]
        for j in range(len(lim)):
            if data_value > lim[j]:
                rgb = palette[j + 1]
        draw.text((x, y), message, font=fontSM, fill=rgb)
    piEnviro.LCD.display(img)


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

    # Initialize core data queues
    # tempsQ = deque(EMPTY_Q, maxlen=const.LED_MAX_COL) # Temperature queue
    # pressQ = deque(EMPTY_Q, maxlen=const.LED_MAX_COL) # Pressure queue
    # humidQ = deque(EMPTY_Q, maxlen=const.LED_MAX_COL) # Humidity queue

    # Initialize device instance which includes the logger, 
    # Enviro+, and Adafruit IO client
    piEnviro = Device(config, appDir)

    # try:
    #     tempsFeed = piEnviro.get_feed_info(const.KWD_FEED_TEMPS)
    #     pressFeed = piEnviro.get_feed_info(const.KWD_FEED_PRESS)
    #     humidFeed = piEnviro.get_feed_info(const.KWD_FEED_HUMID)

    # except RequestError as e:
    #     piEnviro.log_error(f"Application terminated due to REQUEST ERROR: {e}")
    #     piEnviro.display_reset()
    #     sys.exit(1)

    # -- Main application loop --
    # Get core settings
    ioDelay = piEnviro.get_config(const.KWD_DELAY, const.DEF_DELAY)
    ioWait = piEnviro.get_config(const.KWD_WAIT, const.DEF_WAIT)
    ioThrottle = piEnviro.get_config(const.KWD_THROTTLE, const.DEF_THROTTLE)
    
    delayCounter = maxDelay = ioDelay       # Ensure that we upload first reading
    piEnviro.sleepCounter = piEnviro.displSleep   # Reset counter for screen blanking

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

    # Create a values dict to store the data
    variables = ["temperature",
                "pressure",
                "humidity",
                "light",
                "oxidised",
                "reduced",
                "nh3",
                "pm1",
                "pm25",
                "pm10"]
    units = ["C",
            "hPa",
            "%",
            "Lux",
            "kO",
            "kO",
            "kO",
            "ug/m3",
            "ug/m3",
            "ug/m3"]

    # Define your own warning limits
    # The limits definition follows the order of the variables array
    # Example limits explanation for temperature:
    # [4,18,28,35] means
    # [-273.15 .. 4] -> Dangerously Low
    # (4 .. 18]      -> Low
    # (18 .. 28]     -> Normal
    # (28 .. 35]     -> High
    # (35 .. MAX]    -> Dangerously High
    # DISCLAIMER: The limits provided here are just examples and come
    # with NO WARRANTY. The authors of this example code claim
    # NO RESPONSIBILITY if reliance on the following values or this
    # code in general leads to ANY DAMAGES or DEATH.
    limits = [[4, 18, 25, 35],
            [250, 650, 1013.25, 1015],
            [20, 30, 60, 70],
            [-1, -1, 30000, 100000],
            [-1, -1, 40, 50],
            [-1, -1, 450, 550],
            [-1, -1, 200, 300],
            [-1, -1, 50, 100],
            [-1, -1, 50, 100],
            [-1, -1, 50, 100]]

    # RGB palette for values on the combined screen
    palette = [
        const.RGB_BLUE,     # Dangerously Low
        const.RGB_CYAN,     # Low
        const.RGB_GREEN,    # Normal
        const.RGB_YELLOW,   # High
        const.RGB_RED       # Dangerously High
    ]         
    values_lcd = {}

    # Set up canvas and font
    img = Image.new('RGB', (piEnviro.widthLCD, piEnviro.heightLCD), color=const.RGB_BLACK)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(UserFont, const.FONT_SIZE_LG)
    fontSM = ImageFont.truetype(UserFont, const.FONT_SIZE_SM)
    message = ""

    # The position of the top bar
    top_pos = 25

    # Compensation factor for temperature
    comp_factor = 1

    # Added for state
    delay = 0.5  # Debounce the proximity tap
    mode = 0     # The starting mode
    last_page = 0
    light = 1

    for v in variables:
        values_lcd[v] = [1] * piEnviro.widthLCD

    # Text settings
    font = ImageFont.truetype(UserFont, const.FONT_SIZE_MD)
    cpu_temps = [piEnviro.get_CPU_temp()] * 5

    timeSinceUpdate = 0
    timeUpdate = time.time()
    cpu_temps_len = float(len(cpu_temps))

    # Main loop to read data, display, and send to Luftdaten
    counter = 0
    while not EXIT_NOW:
        counter += 1
        EXIT_NOW = (counter >= 200)
        try:
            timeCurrent = time.time()
            timeSinceUpdate = timeCurrent - timeUpdate

            # Calculate these things once, not twice
            cpu_temp = piEnviro.get_CPU_temp()

            # Smooth out with some averaging to decrease jitter
            cpu_temps = cpu_temps[1:] + [cpu_temp]
            avg_cpu_temp = sum(cpu_temps) / cpu_temps_len
            raw_temp = piEnviro.get_temperature()
            comp_temp = raw_temp - ((avg_cpu_temp - raw_temp) / comp_factor)

            raw_press = piEnviro.get_pressure()
            raw_humid = piEnviro.get_humidity()

            pm_values = piEnviro.get_particles()
            raw_pm25 = pm_values.pm_ug_per_m3(2.5)      # TO DO: fix magic number
            raw_pm10 = pm_values.pm_ug_per_m3(10)       # TO DO: fix magic number

            if timeSinceUpdate > 145:                 # TO DO: fix magic number
                values = parse_environ_data(comp_temp, raw_press*100,
                                    raw_humid, raw_pm25, raw_pm10)
                resp = upload_environ_data(values, piEnviro.get_ID(const.DEF_ID_PREFIX))
                timeUpdate = timeCurrent
                piEnviro.log_info(f"Upload Response: {const.STATUS_SUCCESS if resp else const.STATUS_FAILURE}")

            # Now comes the combined.py functionality:
            # If the proximity crosses the threshold, toggle the mode
            proximity = piEnviro.LTR559.get_proximity()
            if proximity > 1500 and timeCurrent - last_page > delay:
                mode = (mode + 1) % 11
                last_page = timeCurrent
            # One mode for each variable
            if mode == 0:
                # variable = "temperature"
                unit = "C"
                display_text(variables[mode], comp_temp, unit)

            if mode == 1:
                # variable = "pressure"
                unit = "hPa"
                display_text(variables[mode], raw_press, unit)

            if mode == 2:
                # variable = "humidity"
                unit = "%"
                display_text(variables[mode], raw_humid, unit)

            if mode == 3:
                # variable = "light"
                unit = "Lux"
                if proximity < 10:
                    data = piEnviro.LTR559.get_lux()
                else:
                    data = 1
                display_text(variables[mode], data, unit)

            if mode == 4:
                # variable = "oxidised"
                unit = "kO"
                data = piEnviro.GAS.read_all()
                data = data.oxidising / 1000
                display_text(variables[mode], data, unit)

            if mode == 5:
                # variable = "reduced"
                unit = "kO"
                data = piEnviro.GAS.read_all()
                data = data.reducing / 1000
                display_text(variables[mode], data, unit)

            if mode == 6:
                # variable = "nh3"
                unit = "kO"
                data = piEnviro.GAS.read_all()
                data = data.nh3 / 1000
                display_text(variables[mode], data, unit)

            if mode == 7:
                # variable = "pm1"
                unit = "ug/m3"
                data = float(pm_values.pm_ug_per_m3(1.0))
                display_text(variables[mode], data, unit)

            if mode == 8:
                # variable = "pm25"
                unit = "ug/m3"
                display_text(variables[mode], float(raw_pm25), unit)

            if mode == 9:
                # variable = "pm10"
                unit = "ug/m3"
                display_text(variables[mode], float(raw_pm10), unit)

            if mode == 10:
                # Everything on one screen
                save_data(0, comp_temp)
                save_data(1, raw_press)
                display_everything()

                save_data(2, raw_humid)
                if proximity < 10:
                    raw_data = piEnviro.LTR559.get_lux()
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
                save_data(7, float(pm_values.pm_ug_per_m3(1.0)))
                save_data(8, float(raw_pm25))
                save_data(9, float(raw_pm10))
                display_everything()
        except Exception as e:
            print(e)
            EXIT_NOW = True

    # A bit of clean-up before we exit
    piEnviro.log_info("-- END Data Logging --")
    piEnviro.display_reset()
