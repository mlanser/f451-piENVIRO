"""Helper Module for applications on the f451 Labs piENVIRO device.

This module holds a few common helper functions that can be used across 
most/all applications designed for the f451 Labs piENVIRO device.
"""

import sys
from subprocess import check_output, STDOUT, DEVNULL
import constants as const

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


# =========================================================
#          G L O B A L S   A N D   H E L P E R S
# =========================================================
def load_settings(settingsFile):
    """Initialize TOML parser and load settings file

    Args:
        settingsFile: path object or string with filename

    Returns:
        'dict' with values from TOML file 
    """
    try:
        with open(settingsFile, mode="rb") as fp:
            settings = tomllib.load(fp)

    except (FileNotFoundError, tomllib.TOMLDecodeError):
        sys.exit(f"Missing or invalid file: '{settingsFile}'")      

    else:
        return settings


def get_RPI_serial_num():
    """Get Raspberry Pi serial number
    
    Based on code from Enviro+ example 'luftdaten_combined.py'

    Returns:
        'str' with RPI serial number or 'None' if we can't find it
    """
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line[0:6] == 'Serial':
                    return line.split(":")[1].strip()
    except OSError:
        return None


def get_RPI_ID(prefix="", suffix="", default="n/a"):
    """Get Raspberry Pi ID

    Returns a string with RPI ID (i.e. serial num with pre- and suffix).

    Args:
        prefix: optional prefix
        suffix: optional suffix
        default: optional default string to be returned if no serial num
    
    Returns:
        'str' with RPI ID
    """
    serialNum = get_RPI_serial_num()
    
    return f"{prefix}{serialNum}{suffix}" if serialNum else default


def check_wifi():
    """Check for Wi-Fi connection on Raspberry Pi

    Based on code from Enviro+ example 'luftdaten_combined.py'

    TODO: verify better way to do this

    Returns:
        'True' - wi-fi confirmed
        'False' - status unknown
    """
    try:
        result = check_output(['hostname', '-I'], stdout=DEVNULL, stderr=STDOUT)
    except:
        result = None

    return True if result is not None else False


def num_to_range(num, inMin, inMax, outMin, outMax):
    """Map value to range

    We use this function to map values (e.g. temp, etc.) against the Y-axis of 
    the SenseHat 8x8 LED display. This means that all values must be mapped 
    against a range of 0-7.

    Based on code found here: https://www.30secondsofcode.org/python/s/num-to-range/

    Args:
        num:
            Number to map against range
        inMin:
            Min value of range for numbers to be converted
        inMax:
            Max value of range for numbers to be converted
        outMin:
            Min value of target range
        outMax:
            Max value of target range

    Returns:
        'float'
    """
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


def convert_to_rgb(num, inMin, inMax, colors):
    """
    Map a value to RGB

    Based on reply found on StackOverflow by `martineau`: 

    See: https://stackoverflow.com/questions/20792445/calculate-rgb-value-for-a-range-of-values-to-create-heat-map

    Args:
        num:
            Number to convert/map to RGB
        inMin:
            Min value of range for numbers to be converted
        inMax:
            Max value of range for numbers to be converted
        colors:
            series of RGB colors delineating a series of adjacent 
            linear color gradients.

    Returns:
        'tuple' with RGB value
    """
    EPSILON = sys.float_info.epsilon    # Smallest possible difference

    # Determine where the given value falls proportionality within
    # the range from inMin->inMax and scale that fractional value
    # by the total number in the `colors` palette.
    i_f = float(num - inMin) / float(inMax - inMin) * (len(colors) - 1)

    # Determine the lower index of the pair of color indices this
    # value corresponds and its fractional distance between the lower
    # and the upper colors.
    i, f = int(i_f // 1), i_f % 1  # Split into whole & fractional parts.

    # Does it fall exactly on one of the color points?
    if f < EPSILON:
        return colors[i]
    
    # ... if not, then return a color linearly interpolated in the 
    # range between it and the following one.
    else:
        (r1, g1, b1), (r2, g2, b2) = colors[i], colors[i+1]
        return int(r1 + f * (r2 - r1)), int(g1 + f * (g2 - g1)), int(b1 + f * (b2 - b1))


def convert_to_bool(inVal):
    """Convert value to boolean.

    If value is a string, then we check against predefined string 
    constants. If value is an integer, then we return 'True' if value
    is greater than 0 (zero).

    For anything else we return a 'False'. 

    Args:
        inVal:
            Value to be converted to boolean.
    """
    if isinstance(inVal, int) or isinstance(inVal, float):
        return (abs(int(inVal)) > 0)
    elif isinstance(inVal, str):
        return (inVal.lower() in [const.STATUS_ON, const.STATUS_TRUE, const.STATUS_YES])
    else:
        return False
