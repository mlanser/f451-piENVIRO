"""Global constants for f451 Labs piENVIRO application.

This module holds all global constants used within the components of 
the f451 Labs piENVIRO application. Some of the constants are used as 
keyword equivalents for attributes listed in the `settings.toml` file.
"""

#fmt: off
# =========================================================
#              M I S C .   C O N S T A N T S
# =========================================================
DEF_FREQ = 600                  # Default delay between uploads in seconds
DEF_DELAY = 300                 # Default delay before first upload in seconds
DEF_WAIT = 1                    # Default delay between sensor reads
DEF_THROTTLE = 120              # Default additional delay on 'ThrottlingError'
DEF_ROUNDING = 2                # Default 'rounding' precision for uploaded data
#fmt: on


# =========================================================
#    K E Y W O R D S   F O R   C O N F I G   F I L E S
# =========================================================
KWD_FREQ = 'FREQ'
KWD_DELAY = 'DELAY'
KWD_WAIT = 'WAIT'
KWD_THROTTLE = 'THROTTLE'
KWD_ROUNDING = 'ROUNDING'

# -- Support for environment data --
KWD_FEED_TEMPS = 'FEED_TEMPS'
KWD_FEED_PRESS = 'FEED_PRESS'
KWD_FEED_HUMID = 'FEED_HUMID'

KWD_DATA_TEMPS = 'temperature'
KWD_DATA_PRESS = 'pressure'
KWD_DATA_HUMID = 'humidity'
# KWD_DATA_P2 = "P2"
# KWD_DATA_P1 = "P1"


# fmt: off
# =========================================================
#   C O N S T A N T S   F O R   D I S P L A Y   M O D E S
# =========================================================
DISPL_TEMPS = KWD_DATA_TEMPS    # Display download speed
DISPL_PRESS = KWD_DATA_PRESS    # Display upload speed
DISPL_HUMID = KWD_DATA_HUMID    # Display ping response time

DISPL_LIGHT = 'light'           # Display illumination
DISPL_OXID = 'oxidised'
DISPL_REDUC = 'reduced'
DISPL_NH3 = 'nh3'
DISPL_PM1 = 'pm1'
DISPL_PM25 = 'pm25'
DISPL_PM10 = 'pm10'
DISPL_ALL = 'all'               # Display all data as (dual-column) text
#fmt: on
