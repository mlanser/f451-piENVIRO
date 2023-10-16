"""Global constants for f451 Labs piENVIRO application.

This module holds all global constants used within the components of 
the f451 Labs piENVIRO application. Some of the constants are used as 
keyword equivalents for attributes listed in the `settings.toml` file.
"""

# =========================================================
#              M I S C .   C O N S T A N T S
# =========================================================
DELIM_STD = "|"
DELIM_VAL = ":"
EMPTY_STR = ""

RGB_BLACK = (0, 0, 0)
RGB_WHITE = (255, 255, 255)
RGB_BLUE = (0, 0, 255)
RGB_CYAN = (0, 255, 255)
RGB_GREEN = (0, 255, 0)
RGB_YELLOW = (255, 255, 0)
RGB_RED = (255, 0, 0)

RGB_PROGRESS = (127, 0, 255) # Use for progressbar at bottom of LED

FONT_SIZE_SM = 10       # Small font size
FONT_SIZE_MD = 16       # Medium font size
FONT_SIZE_LG = 20       # Large font size

ROTATE_90 = 90          # Rotate 90 degrees    

MAX_LEN_CPU_TEMPS = 5   # Max number of CPU temps

DISPL_TOP_X = 2         # X/Y ccordinate of top-left corner for LCD content
DISPL_TOP_Y = 2
DISPL_TOP_BAR = 25      # Height (in px) of top bar

PROX_DEBOUNCE = 0.5     # Delay to debounce proximity sensor on 'tap'
PROX_LIMIT = 1500       # Threshold for proximity sensor to detect 'tap'

DEF_LCD_OFFSET_X = 1    # Default horizontal offset for LCD
DEF_LCD_OFFSET_Y = 1    # Default vertical offseet for LCD 

DEF_DELAY = 59          # Default delay between uploads
DEF_WAIT = 1            # Default delay between sensor reads
DEF_THROTTLE = 120      # Default additional delay on 'ThrottlingError'
DEF_ROTATION = 0
DEF_SLEEP = 600
DEF_ID_PREFIX = "raspi-"    # Default prefix for ID string
DEF_TEMP_COMP_FACTOR = 1    # Default compensation factor for temperature

LOG_CRITICAL = "CRITICAL"
LOG_DEBUG = "DEBUG"
LOG_ERROR = "ERROR"
LOG_INFO = "INFO"
LOG_NOTSET = "NOTSET"
LOG_OFF = "OFF"
LOG_WARNING = "WARNING"

LOG_LVL_OFF = -1
LOG_LVL_MIN = -1
LOG_LVL_MAX = 100

STATUS_SUCCESS = "success"
STATUS_FAILURE = "failure"

STATUS_ON = "on"
STATUS_OFF = "off"
STATUS_TRUE = "true"
STATUS_FALSE = "false"
STATUS_YES = "yes"
STATUS_NO = "no"


# =========================================================
#    K E Y W O R D S   F O R   C O N F I G   F I L E S
# =========================================================
KWD_AIO_USER = "AIO_USERNAME"
KWD_AIO_KEY = "AIO_KEY"
KWD_DELAY = "DELAY"
KWD_WAIT = "WAIT"
KWD_THROTTLE = "THROTTLE"
KWD_ROTATION = "ROTATION"
KWD_DISPLAY = "DISPLAY"
KWD_PROGRESS = "PROGRESS"
KWD_SLEEP = "SLEEP"
KWD_LOG_LEVEL = "LOGLVL"
KWD_LOG_FILE = "LOGFILE"

KWD_TEMP_COMP = "TEMP_COMP"

KWD_FEED_TEMPS = "FEED_TEMPS"
KWD_FEED_PRESS = "FEED_PRESS"
KWD_FEED_HUMID = "FEED_HUMID"

KWD_DATA_TEMPS = "temperature"
KWD_DATA_PRESS = "pressure"
KWD_DATA_HUMID = "humidity"
KWD_DATA_P2 = "P2"
KWD_DATA_P1 = "P1"

KWD_DISPL_TOP_X = "TOP_X"
KWD_DISPL_TOP_Y = "TOP_Y"
KWD_DISPL_TOP_BAR = "TOP_BAR"
KWD_MAX_LEN_CPU_TEMPS = "CPU_TEMPS"


# =========================================================
#    C O N S T A N T S   F O R   E N V I R O N   D A T A
# =========================================================


# RGB color palette for values on combo/text screen
COLOR_PALETTE = [
    RGB_BLUE,       # Dangerously Low
    RGB_CYAN,       # Low
    RGB_GREEN,      # Normal
    RGB_YELLOW,     # High
    RGB_RED         # Dangerously High
]         

# Min/max display modes. Must correspond to 'DATA_TYPES' list
DISPL_TEMPS = 0     # Temperature
DISPL_ALL = 10      # Display all data

MIN_DISPL = DISPL_TEMPS     
MAX_DISPL = DISPL_ALL

IDX_TEMP  = 0
IDX_PRESS = 1
IDX_HUMID = 2
IDX_LIGHT = 3
IDX_OXID  = 4
IDX_REDUC = 5
IDX_NH3   = 6
IDX_PM1   = 7
IDX_PM25  = 8
IDX_PM10  = 9


# List of environment data types
DATA_TYPES = [
    "temperature",          # 0
    "pressure",             # 1
    "humidity",             # 2
    "light",                # 3
    "oxidised",             # 4
    "reduced",              # 5
    "nh3",                  # 6
    "pm1",                  # 7
    "pm25",                 # 8
    "pm10"                  # 9
]

# List of environment data units
DATA_UNITS = [
    "C",
    "hPa",
    "%",
    "Lux",
    "kO",
    "kO",
    "kO",
    "ug/m3",
    "ug/m3",
    "ug/m3"
]

# Define your own warning limits for environment data
#
# The (data) limits definition follows the same order as 
# the 'DATA_TYPES' list.
#
# Example limits explanation for temperature:
# [4,18,28,35] means:
#  -273.15 ... 4     -> Dangerously Low
#        4 ... 18    -> Low
#       18 ... 28    -> Normal
#       28 ... 35    -> High
#       35 ... MAX   -> Dangerously High
#
# DISCLAIMER: The limits provided here are just examples and come
# with NO WARRANTY. The authors of this example code claim
# NO RESPONSIBILITY if reliance on the following values or this
# code in general leads to ANY DAMAGES or DEATH.
DATA_LIMITS = [
    [4, 18, 25, 35],
    [250, 650, 1013.25, 1015],
    [20, 30, 60, 70],
    [-1, -1, 30000, 100000],
    [-1, -1, 40, 50],
    [-1, -1, 450, 550],
    [-1, -1, 200, 300],
    [-1, -1, 50, 100],
    [-1, -1, 50, 100],
    [-1, -1, 50, 100]
]
