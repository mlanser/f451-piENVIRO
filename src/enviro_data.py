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
TEMP_UNIT_C = "C"   # Celsius
TEMP_UNIT_F = "F"   # Fahrenheit
TEMP_UNIT_K = "K"   # Kelvin

# =========================================================
#                     M A I N   C L A S S
# =========================================================
class EnviroObject:
    """Data structure for environment data object.

    Attributes:
        data:   'dequeue' for data points
        unit:   'str' for data unit of measure (e.g. "C" for temperature)
        limits: 'list' of limit values
        label:  'str' for data object label (e .g. "Temperature")

    Methods:
        as_dict: return data attributes as 'dict'
    """
    def __init__(self, data, unit, limits, label):
        self.data = data
        self.unit = unit
        self.limits = limits
        self.label = label

    def as_dict(self):
        """Return data object as 'dict' with each attribute as key."""
        return {
            "data": self.data,
            "unit": self.unit,
            "limits": self.limits,
            "label": self.label.capitalize()
        }


class TemperatureObject(EnviroObject):
    """Data structure for environment data object.

    Attributes:
        data:   'dequeue' for data points
        unit:   'str' for data unit of measure (e.g. "C" for temperature)
        limits: 'list' of limit values
        label:  'str' for data object label (e .g. "Temperature")

    Methods:
        as_dict: return data attributes as 'dict'
    """
    def __init__(self, data, unit, limits, label):
        super().__init__(data, unit, limits, label)

    def as_dict(self, unit=TEMP_UNIT_C):
        """Return object as 'dict' with temp in C, F, or K
        
        Args:
            unit: if "C" then return temperature in Celsius
                  if "F"            -"-          in Fahrenheit
                  if "K"            -"-          in Kelvin
        """
        if unit == TEMP_UNIT_F:
            data = [self._convert_C2F(c) for c in self.data]
        elif unit == TEMP_UNIT_K:
            data = [self._convert_C2K(c) for c in self.data]
        else:
            data = self.data

        return {
            "data": data,
            "unit": self.unit,
            "limits": self.limits,
            "label": self.label.capitalize()
        }

    @staticmethod
    def _convert_C2F(celsius):
        """Convert Celsius to Fahrenheit"""
        return (celsius * 9 / 5) + 32.0

    @staticmethod
    def _convert_C2K(celsius):
        """Convert Celsius to Kelvin"""
        return float(celsius) + 273.15


class EnviroData:
    """Data structure for holding and managing sensor data.
    
    Create an empty full-size data structure that we use 
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
        as_list: returns a 'list' with data from each attribute as 'dict'
        convert_C2F: static (wrapper) method. Converts Celsius to Fahrenheit 
        convert_C2K: static (wrapper) method. Converts Celsius to Kelvin 
    """
    def __init__(self, defVal, maxLen):
        """Initialize data structurte.

        Args:
            defVal: default value to use when filling up the queues
            maxLen: max length of each queue

        Returns:
            'dict' - holds entiure data structure
        """
        self.temperature = TemperatureObject(
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

    def as_list(self, tempUnit=TEMP_UNIT_C):
        return [
            self.temperature.as_dict(tempUnit),
            self.pressure.as_dict(),
            self.humidity.as_dict(),
            self.light.as_dict(),
            self.oxidised.as_dict(),
            self.reduced.as_dict(),
            self.nh3.as_dict(),
            self.pm1.as_dict(),
            self.pm25.as_dict(),
            self.pm10.as_dict(),
        ]
    
    def convert_C2F(self, celsius):
        return self.temperature._convert_C2F(celsius)

    def convert_C2K(self, celsius):
        return self.temperature._convert_C2K(celsius)
