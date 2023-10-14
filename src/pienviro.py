"""f451 Labs piENVIRO Device Class.

The piENVIRO Device class includes support for hardware extensions (e.g. Enviro+, etc.),
core services (e.g. Adafruit IO, etc.), and utilities (e.g. logger, etc.).

The class wraps -- and extends as needed -- the methods and functions supported by 
underlying libraries, and also keeps track of core counters, flags, etc.

Dependencies:
 - Pimoroni Enviro+ library: https://github.com/pimoroni/enviroplus-python/  
"""

import time
import colorsys
import sys
import logging

from random import randint

from Adafruit_IO import Client, MQTTClient, RequestError, ThrottlingError

import constants as const
from common import convert_to_bool, convert_to_rgb, get_setting, num_to_range

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from fonts.ttf import RobotoMedium

from subprocess import PIPE, Popen

# Support for ST7735 LCD
try:
    import ST7735
except ImportError:
    from mocks.fake_device import FakeST7735 as ST7735

# Support for proximity sensor
try:
    try:
        # Transitional fix for breaking change in LTR559
        from ltr559 import LTR559
        ltr559 = LTR559()
    except ImportError:
        import ltr559
except ImportError:
    from mocks.fake_device import FakeLTR559 as ltr559

# Support SMBus
try:
    try:
        from smbus2 import SMBus
    except ImportError:
        from smbus import SMBus
except ImportError:
    from mocks.fake_device import FakeSMBus as SMBus

# Support temperature/pressure/humidity sensor
try:
    from bme280 import BME280
except ImportError:
    from mocks.fake_device import FakeBME280 as BME280

# Support air quality sensor
try:
    from pms5003 import PMS5003, ReadTimeoutError as pmsReadTimeoutError, SerialTimeoutError
except ImportError:
    from mocks.fake_device import FakePMS5003 as PMS5003, FakeReadTimeoutError as pmsReadTimeoutError, FakeSerialTimeoutError as SerialTimeoutError

# Support Enviro+ gas sensor
try:
    from enviroplus import gas
except ImportError:
    from mocks.fake_device import FakeEnviroPlus as gas


# =========================================================
#          G L O B A L S   A N D   H E L P E R S
# =========================================================
class Device:
    def __init__(self, config, appDir):
        """Initialize Enviro+ hardware and logger

        Args:
            config:
                Config values from 'settings.toml'
            appDir:
                Path object for app parent folder
        """
        self.config = config
        self.aio = Client(                                  # Adafruit Client
            get_setting(config, const.KWD_AIO_USER, ""), 
            get_setting(config, const.KWD_AIO_KEY, "")
        )
        self.logger = self._init_logger(config, appDir)     # Logger

        self.serialNum = self._get_serial_num()             # RaspberryPi serial number
        
        bus = SMBus(1)
        self._BME280 = BME280(i2c_dev=bus)                  # BME280 temperature, pressure, humidity sensor

        self._PMS5003 = PMS5003()                           # PMS5003 particulate sensor
        self.LTR559 = ltr559                                # Proximity sensor
        self.GAS = gas                                      # Enviro+

        # Initialize LCD and canvas
        self.LCD = self._init_LCD(config)                   # ST7735 0.96" 160x80 LCD

        self.displRotation = get_setting(config, const.KWD_ROTATION, const.DEF_ROTATION)
        self.displMode = get_setting(config, const.KWD_DISPLAY, const.DISPL_SPARKLE)
        self.displProgress = convert_to_bool(get_setting(config, const.KWD_PROGRESS, const.STATUS_ON))
        self.displSleep = get_setting(config, const.KWD_SLEEP, const.DEF_SLEEP)

        self.displTopX = get_setting(config, const.KWD_DISPL_TOP_X, const.DISPL_TOP_X)
        self.displTopY = get_setting(config, const.KWD_DISPL_TOP_Y, const.DISPL_TOP_Y)
        self.displTopBar = get_setting(config, const.KWD_DISPL_TOP_BAR, const.DISPL_TOP_BAR)

        self.displImg = None
        self.displDraw = None
        self.displFontLG = None
        self.displFontSM = None
        self.displData = {}

    @property
    def widthLCD(self):
        return self.LCD.width
    
    @property
    def heightLCD(self):
        return self.LCD.height

    def _init_logger(self, config, appDir):
        """Initialize Logger

        We always initialize the logger with a stream 
        handler. But file handler is only created if 
        a file name has been provided in settings.
        """
        logger = logging.getLogger("f451-piENVIRO")
        logFile = get_setting(config, const.KWD_LOG_FILE)
        logFileFP = appDir.parent.joinpath(logFile) if logFile else None
        logLvl = get_setting(config, const.KWD_LOG_LEVEL, const.LOG_INFO)

        logger.setLevel(logLvl)

        if logFileFP:
            fileHandler = logging.FileHandler(logFileFP)
            fileHandler.setLevel(logLvl)
            fileHandler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s"))
            logger.addHandler(fileHandler)

        streamHandler = logging.StreamHandler()
        streamHandler.setLevel(logLvl if logLvl == const.LOG_DEBUG else logging.ERROR)
        streamHandler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s"))
        logger.addHandler(streamHandler)

        return logger

    def _init_LCD(self, config):
        """Initialize LCD on Enviro+"""
        st7735 = ST7735.ST7735(
            port=0,
            cs=1,
            dc=9,
            backlight=12,
            rotation=get_setting(config, const.KWD_ROTATION, const.DEF_ROTATION),    # Set initial rotation,
            spi_speed_hz=10000000
        )
        st7735.begin()

        return st7735

    def _get_serial_num(self, default="n/a"):
        """Get Raspberry Pi serial number
        
        Based on code from Enviro+ example 'luftdaten_combined.py'
        """
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line[0:6] == 'Serial':
                        return line.split(":")[1].strip()
        except OSError:
            return default

    def get_ID(self, prefix="", suffix=""):
        return prefix + self.serialNum + suffix

    def get_CPU_temp(self):
        """Get CPU temp

        We use this for compensating temperature reads from BME280 sensor.

        Based on code from Enviro+ example 'luftdaten_combined.py'
        """
        process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE, universal_newlines=True)
        output, _error = process.communicate()
        return float(output[output.index('=') + 1:output.rindex("'")])

    def get_config(self, key, default=None):
        """Get a config value from settings
        
        This method rerieves value from settings (TOML), but can
        return a default value if key does not exist (i.e. settings 
        value has not been defined in TOML file.

        Args:
            key:
                'str' with name of settings key
            defaul:
                Default value

        Returns:
            Settings value        
        """
        return self.config[key] if key in self.config else default

    def get_feed_info(self, feedKwd, default=""):
        """Get Adafruit IO feed info

        Args:
            feedKwd:
                'str' with feed keyword to find in config/settings
        """
        feed = get_setting(self.config, feedKwd, default)
        try:
            info = self.aio.feeds(feed)

        except RequestError as e:
            self.logger.log(logging.ERROR, f"Failed to get feed info - ADAFRUIT REQUEST ERROR: {e}")
            raise
        
        return info

    def get_pressure(self):
        """Get air pressure data from BME280 sensor"""
        return self._BME280.get_pressure()

    def get_humidity(self):
        """Get humidity data from BME280 sensor"""
        return self._BME280.get_humidity()

    def get_temperature(self):
        """Get temperature data from BME280"""
        return self._BME280.get_temperature()

    def get_particles(self):
        """Get particle data from PMS5003"""
        try:
            data = self._PMS5003.read()

        except pmsReadTimeoutError:
            self._PMS5003.reset()
            data = self._PMS5003.read()

        return data

    def get_sensor_data(self):
        """
        Read sensor data and round values to 1 decimal place

        Returns:
            'tuple' with 1 data point from each of the SenseHat sensors
        """
        tempC = round(self.enviro.get_temperature(), 1)     # Temperature in C
        press = round(self.enviro.get_pressure(), 1)        # Presure in hPa
        humid = round(self.enviro.get_humidity(), 1)        # Humidity 

        return tempC, press, humid 

    def log(self, lvl, msg):
            """Wrapper of Logger.log()"""
            self.logger.log(lvl, msg)

    def log_error(self, msg):
            """Wrapper of Logger.error()"""
            self.logger.error(msg)

    def log_info(self, msg):
            """Wrapper of Logger.info()"""
            self.logger.info(msg)

    def log_debug(self, msg):
            """Wrapper of Logger.debug()"""
            self.logger.debug(msg)

    def display_init(self):
        self.displImg = Image.new('RGB', (self.LCD.width, self.LCD.height), color=const.RGB_BLACK)
        self.displDraw = ImageDraw.Draw(self.displImg)
        self.displFontLG = ImageFont.truetype(RobotoMedium, const.FONT_SIZE_LG)
        self.displFontSM = ImageFont.truetype(RobotoMedium, const.FONT_SIZE_SM)

    def display_on(self):
        self.LCD.display_on()

    def display_off(self):
        self.LCD.display_off()
        
    def display_blank(self):
        """Show clear/blank LED"""
        img = Image.new('RGB', (self.LCD.width, self.LCD.height), color=(0, 0, 0))
        # draw = ImageDraw.Draw(img)
        self.LCD.display(img)

    def display_reset(self):
        """Reset and clear LED"""
        self.display_init()

    def display_sparkle(self):
        """Show random sparkles on LED"""
        pass
        # x = randint(0, 7)
        # y = randint(0, 7)
        # r = randint(0, 255)
        # g = randint(0, 255)
        # b = randint(0, 255)

        # toggle = randint(0, 3)

        # if toggle != 0:
        #     self.enviro.set_pixel(x, y, r, g, b)
        # else:    
        #     self.enviro.clear()

    def display_as_graph(self, data, dataType, dataUnit):
        """Display graph and data point as text label
        
        This method will redraw the entire LCD

        Args:
            data:
                'list' with one value for each column of pixels on LCD
            dataType:
                'str' with data type name (e.g. 'temperature', etc.)
            dataUnit:
                'str' with data unit (e.g. 'C' for Celsius, etc.)
        """
        # Scale values in data set between 0 and 1
        vmin = min(data)
        vmax = max(data)
        colors = [(v - vmin + 1) / (vmax - vmin + 1) for v in data]
        
        # Format data type name and value
        message = "{}: {:.1f} {}".format(dataType[:4], data[-1], dataUnit)
        self.log_info(message)
        self.displDraw.rectangle((0, 0, self.LCD.width, self.LCD.height), const.RGB_WHITE)
        
        for i in range(len(colors)):
            # Convert the values to colors from red to blue
            color = (1.0 - colors[i]) * 0.6
            r, g, b = [int(x * 255.0)
                    for x in colorsys.hsv_to_rgb(color, 1.0, 1.0)]
        
            # Draw a 1-pixel wide rectangle of given color
            self.displDraw.rectangle((i, self.displTopBar, i + 1, self.LCD.height), (r, g, b))
        
            # Draw and overlay a line graph in black
            line_y = self.LCD.height - (self.displTopBar + (colors[i] * (self.LCD.height - self.displTopBar))) + self.displTopBar
            self.displDraw.rectangle((i, line_y, i + 1, line_y + 1), const.RGB_BLACK)
        
        # Write the text at the top in black
        self.displDraw.text((0, 0), message, font=self.displFontLG, fill=const.RGB_BLACK)
        self.LCD.display(self.displImg)
    
    def display_as_text(self, data):
        """Display graph and data point as text label
        
        This method will redraw the entire LCD

        Args:
            data:
                'list' with one value for each column of pixels on LCD
            dataType:
                'str' with data type name (e.g. 'temperature', etc.)
            dataUnit:
                'str' with data unit (e.g. 'C' for Celsius, etc.)
        """
        self.displDraw.rectangle((0, 0, self.LCD.width, self.LCD.height), const.RGB_BLACK)
        cols = 2
        rows = (len(const.DATA_TYPES) / cols)

        for i in range(len(const.DATA_TYPES)):
            type = const.DATA_TYPES[i]
            val = data[type][-1]
            unit = const.DATA_UNITS[i]
            
            x = const.DEF_LCD_OFFSET_X + ((self.LCD.width // cols) * (i // rows))
            y = const.DEF_LCD_OFFSET_Y + ((self.LCD.height / rows) * (i % rows))
            
            message = "{}: {:.1f} {}".format(type[:4], val, unit)
            
            lim = const.DATA_LIMITS[i]
            rgb = const.COLOR_PALETTE[0]

            for j in range(len(lim)):
                if val > lim[j]:
                    rgb = const.COLOR_PALETTE[j + 1]
            self.displDraw.text((x, y), message, font=self.displFontSM, fill=rgb)
        
        self.LCD.display(self.displImg)

    def display_progress(self, inVal, maxVal=100):
        """Update progressbar on bottom row of LED

        Args:
            inVal:
                Value to represent on progressbar
            maxVal:
                Max value so we can calculate percentage
        """
        pass
        # # Convert value to percentange and map against num pixels in a row
        # normalized = int(num_to_range(inVal / maxVal, 0.0, 1.0, 0.0, float(const.LED_MAX_COL)))
        
        # # Update LED bottom row
        # for x in range(0, normalized):
        #     self.enviro.set_pixel(x, const.LED_MAX_ROW - 1, const.RGB_PROGRESS)

    async def send_sensor_data(self, data):
        """Send sensor data to Adafruit IO

        Args:
            data:
                'dict' with feed key and data point

        Raises:
            RequestError:
                When API request fails
            ThrottlingError:
                When exceeding Adafruit IO rate limit
        """
        return (0, 0, 0)

        # try:
        #     self.aio.send_data(data["feed"].key, data["data"])
        # except RequestError as e:
        #     self.logger.log(logging.ERROR, f"Upload failed for {data['feed'].key} - REQUEST ERROR: {e}")
        #     raise RequestError
        # except ThrottlingError as e:
        #     self.logger.log(logging.ERROR, f"Upload failed for {data['feed'].key} - THROTTLING ERROR: {e}")
        #     raise ThrottlingError
