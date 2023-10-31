"""Custom class for Enviro+ sensor data.

This class defines a data structure thaty can be used 
to manage all sensor data from the Enviro+ device. There
are also methods to support conversion between units, etc.

Dependencies:
    TBD
"""

from collections import deque

# =========================================================
#              M I S C .   C O N S T A N T S
# =========================================================
# IDX_TEMP  = 0
# IDX_PRESS = 1
# IDX_HUMID = 2
# IDX_LIGHT = 3
# IDX_OXID  = 4
# IDX_REDUC = 5
# IDX_NH3   = 6
# IDX_PM1   = 7
# IDX_PM25  = 8
# IDX_PM10  = 9


# =========================================================
#                     M A I N   C L A S S
# =========================================================
class EnviroObject:
    def __init__(self, data, unit, limits, label):
        self.data = data
        self.unit = unit
        self.limits = limits
        self.label = label

    def as_dict(self):
        return {
            "data": self.data,
            "unit": self.unit,
            "limits": self.limits,
            "label": self.label.capitalize()
        }


class EnviroData:
    """Data structure for holding and managing sensor data.
    
    Create an empty full-size data structujre that we use 
    in the app to collect a series of sensor data.

    NOTE: The 'limits' attribute stores a list of limits. You
            can define your own warning limits for your environment
            data as follows:

            Example limits explanation for temperature:
            [4,18,28,35] means:
            -273.15 ... 4     -> Dangerously Low
                  4 ... 18    -> Low
                 18 ... 28    -> Normal
                 28 ... 35    -> High
                 35 ... MAX   -> Dangerously High

    DISCLAIMER: The limits provided here are just examples and come
    with NO WARRANTY. The authors of this example code claim
    NO RESPONSIBILITY if reliance on the following values or this
    code in general leads to ANY DAMAGES or DEATH.

    Attributes:
        temperature:    temperature in C
        pressure:       barometric pressure in hPa
        humidity:       humidity in %
        light:          illumination in Lux
        oxidised:       gas value k0
        reduced:        gas value k0     
        nh3:            gas value k0
        pm1:            particle value in ug/m3
        pm25:           particle value in ug/m3
        pm10:           particle value in ug/m3

    Methods:
        TBD
    """
    def __init__(self, defVal, maxLen):
        """Initialize data structurte.

        Args:
            defVal: default value to use when filling up the queues
            maxLen: max length of each queue

        Returns:
            'dict' - holds entiure data structure
        """
        self.temperature = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "C",
            [4, 18, 25, 35],
            "Temperature"
        )
        self.pressure = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "hPa",
            [250, 650, 1013.25, 1015],
            "Pressure"
        )
        self.humidity = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "%",
            [20, 30, 60, 70],
            "Humidity"
        )
        self.light = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "Lux",
            [-1, -1, 30000, 100000],
            "Light"
        )
        self.oxidised = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "kO",
            [-1, -1, 40, 50],
            "Oxidized"
        )
        self.reduced = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "kO",
            [-1, -1, 450, 550],
            "Reduced"
        )
        self.nh3 = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "kO",
            [-1, -1, 200, 300],
            "NH3"
        )
        self.pm1 = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "ug/m3",
            [-1, -1, 50, 100],
            "PM1"
        )
        self.pm25 = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "ug/m3",
            [-1, -1, 50, 100],
            "PM25"
        )
        self.pm10 = EnviroObject(
            deque([defVal] * maxLen, maxlen=maxLen),
            "ug/m3",
            [-1, -1, 50, 100],
            "PM10"
        )
