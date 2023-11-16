"""Global constants for f451 Labs piENVIRO application.

This module holds all global constants used within the components of 
the f451 Labs piENVIRO application. Some of the constants are used as 
keyword equivalents for attributes listed in the `settings.toml` file.
"""

# =========================================================
#              M I S C .   C O N S T A N T S
# =========================================================
# DELIM_STD = "|"
# DELIM_VAL = ":"
# EMPTY_STR = ""

# RGB_BLACK = (0, 0, 0)
# RGB_WHITE = (255, 255, 255)
# RGB_BLUE = (0, 0, 255)
# RGB_CYAN = (0, 255, 255)
# RGB_GREEN = (0, 255, 0)
# RGB_YELLOW = (255, 255, 0)
# RGB_RED = (255, 0, 0)

# RGB_PROGRESS = (127, 0, 255) # Use for progressbar at bottom of LED

# ROTATE_90 = 90              # Rotate 90 degrees    

# DEF_UPLOADS = -1            # Number of uploads. If -1, then no limit.
DEF_FREQ = 600              # Default delay between uploads in seconds
DEF_DELAY = 300             # Default delay before first upload in seconds
DEF_WAIT = 1                # Default delay between sensor reads
DEF_THROTTLE = 120          # Default additional delay on 'ThrottlingError'
DEF_ROUNDING = 2            # Default 'rounding' precision for uploaded data

DEF_ID_PREFIX = "raspi-"    # Default prefix for ID string

# Tuning factor for compensation. Decrease this number to adjust the
# temperature down, and increase to adjust up
DEF_TEMP_COMP_FACTOR = 2.25
MAX_LEN_CPU_TEMPS = 5       # Max number of CPU temps

LOG_NOTSET = 0
LOG_DEBUG = 10
# LOG_INFO = 20
# LOG_WARNING = 30
# LOG_ERROR = 40
# LOG_CRITICAL = 50

STATUS_YES = "yes"
STATUS_NO = "no"
STATUS_UNKNOWN = "unknown"


# =========================================================
#    K E Y W O R D S   F O R   C O N F I G   F I L E S
# =========================================================
KWD_TEMP_COMP = "TEMP_COMP"
KWD_MAX_LEN_CPU_TEMPS = "CPU_TEMPS"

KWD_FREQ = "FREQ"
KWD_DELAY = "DELAY"
KWD_WAIT = "WAIT"
KWD_THROTTLE = "THROTTLE"
KWD_ROUNDING = "ROUNDING"
# KWD_UPLOADS = "UPLOADS"
KWD_FEED_TEMPS = "FEED_TEMPS"
KWD_FEED_PRESS = "FEED_PRESS"
KWD_FEED_HUMID = "FEED_HUMID"

KWD_DATA_TEMPS = "temperature"
KWD_DATA_PRESS = "pressure"
KWD_DATA_HUMID = "humidity"
# KWD_DATA_P2 = "P2"
# KWD_DATA_P1 = "P1"


# =========================================================
#   C O N S T A N T S   F O R   D I S P L A Y   M O D E S
# =========================================================
IDX_ALL   = 0           # Display all data
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
