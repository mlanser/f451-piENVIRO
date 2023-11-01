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

# FONT_SIZE_SM = 10           # Small font size
# FONT_SIZE_MD = 16           # Medium font size
# FONT_SIZE_LG = 20           # Large font size

ROTATE_90 = 90              # Rotate 90 degrees    

MAX_LEN_CPU_TEMPS = 5       # Max number of CPU temps

# DISPL_TOP_X = 2             # X/Y ccordinate of top-left corner for LCD content
# DISPL_TOP_Y = 2
# DISPL_TOP_BAR = 25          # Height (in px) of top bar

# DEF_LCD_OFFSET_X = 1        # Default horizontal offset for LCD
# DEF_LCD_OFFSET_Y = 1        # Default vertical offseet for LCD 

DEF_DELAY = 59              # Default delay between uploads
DEF_WAIT = 1                # Default delay between sensor reads
DEF_THROTTLE = 120          # Default additional delay on 'ThrottlingError'

# DEF_ROTATION = 0
# DEF_SLEEP = 600

DEF_ID_PREFIX = "raspi-"    # Default prefix for ID string

DEF_TEMP_COMP_FACTOR = 1    # Default compensation factor for temperature

# LOG_NOTSET = 0
# LOG_DEBUG = 10
# LOG_INFO = 20
# LOG_WARNING = 30
# LOG_ERROR = 40
# LOG_CRITICAL = 50

# LOG_LVL_OFF = -1
# LOG_LVL_MIN = -1
# LOG_LVL_MAX = 100

# STATUS_SUCCESS = "success"
# STATUS_FAILURE = "failure"

# STATUS_ON = "on"
# STATUS_OFF = "off"
# STATUS_TRUE = "true"
# STATUS_FALSE = "false"
STATUS_YES = "yes"
STATUS_NO = "no"
STATUS_UNKNOWN = "unknown"


# =========================================================
#    K E Y W O R D S   F O R   C O N F I G   F I L E S
# =========================================================
# KWD_AIO_USER = "AIO_USERNAME"
# KWD_AIO_KEY = "AIO_KEY"
# KWD_ROTATION = "ROTATION"
# KWD_DISPLAY = "DISPLAY"
# KWD_PROGRESS = "PROGRESS"
# KWD_SLEEP = "SLEEP"
# KWD_LOG_LEVEL = "LOGLVL"
# KWD_LOG_FILE = "LOGFILE"

KWD_TEMP_COMP = "TEMP_COMP"
KWD_MAX_LEN_CPU_TEMPS = "CPU_TEMPS"

KWD_DELAY = "DELAY"
KWD_WAIT = "WAIT"
KWD_THROTTLE = "THROTTLE"
KWD_FEED_TEMPS = "FEED_TEMPS"
KWD_FEED_PRESS = "FEED_PRESS"
KWD_FEED_HUMID = "FEED_HUMID"

KWD_DATA_TEMPS = "temperature"
KWD_DATA_PRESS = "pressure"
KWD_DATA_HUMID = "humidity"
# KWD_DATA_P2 = "P2"
# KWD_DATA_P1 = "P1"


# =========================================================
#    C O N S T A N T S   F O R   E N V I R O N   D A T A
# =========================================================
# RGB color palette for values on combo/text screen
# COLOR_PALETTE = [
#     RGB_BLUE,       # Dangerously Low
#     RGB_CYAN,       # Low
#     RGB_GREEN,      # Normal
#     RGB_YELLOW,     # High
#     RGB_RED         # Dangerously High
# ]         

# Min/max display modes.
IDX_ALL   = 0       # Display all data
IDX_TEMP  = 1
IDX_PRESS = 2
IDX_HUMID = 3
IDX_LIGHT = 4
IDX_OXID  = 5
IDX_REDUC = 6
IDX_NH3   = 7
IDX_PM1   = 8
IDX_PM25  = 9
IDX_PM10  = 10

MIN_DISPL = IDX_ALL     # Cannot be smaller than smallest IDX_xx value     
MAX_DISPL = IDX_PM10    # Cannot be larger than largest IDX_xx value 
