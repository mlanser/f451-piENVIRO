# Instructions for f451-piENVIRO

## Custom application settings in SETTINGS.TOML

The 'settings.toml' file holds various custom application settings and secrets (e.g. Adafruit IO keys, etc.) and this file should **NOT** be included in 'git' commits.

It is recommended to copy the '*settings.example*' to '*settings.toml*' and then customize the values in '*settings.toml*' as nedeed for the specific device that the application is running on.

### Adafruit IO settings

- AIO_USERNAME: 'string' with Adafruit IO username
- AIO_KEY: 'string' with Adafruit IO key
- AIO_UPLOAD: 'string' - yes | force | no
    - "yes" - upload if feed available
    - "force" - exit if feed invalid
    - "no" - do not upload data

- FEED_TEMPS: 'string' with Adafruit IO feed key for 'temperature' feed
- FEED_PRESS: 'string' with Adafruit IO feed key for 'pressure' feed
- FEED_HUMID: 'string' with Adafruit IO feed key for 'humidity' feed

### Misc. Settings for Data Management

- UNITS_TEMPS: 'string' with sep. units for logging, display, and upload. The three units are separated with '|' (pipe) char.
    - "C" - Celsius
    - "F" - Fahrenheit
    - "K" - Kelvin

    - Example: "C|F|C" means log temperature in Celsius, display on LCD in Fahrenheit, and upload to Adafruit IO in Celsius

### Misc. Application Defaults

- ROTATION: 'int' - 0 | 90 | 180 | 270 degrees to turn LCD display
    - 90 | 270 - top of LCD will point toward/away RPI HDMI and layout is 160x80
    - 0 | 180 - top of LCD will point away/toward RPI USB and layout is 80x160

- DISPLAY: 'int' - 0..10
    - 0..9 - display modes with single data point (e.g. temperature, etc.) and scrolling line graph and color bars.
    - 10 - display mode showing all data ponits in all text in 2 columns

- DELAY: 'int' - delay in seconds between uploads to Adafruit IO.
    - Smaller number means more freq uploads and higher data rate
- WAIT: 'int' - delay in seconds between sensor reads
- THROTTLE: 'int' - additional delay in seconds to be applied on Adafruit IO 'ThottlingError'

- PROGRESS: 'string' - on | off
    - "on": show 'wait for upload' progress bar on LCD
    - "off": do not show progress bar

- SLEEP: 'int' - delay in seconds until LCD is blanked for "screen saver" mode ;-)

- LOGLVL: 'string' - debug | info | error
    - Logging levels (see: [Python docs](https://docs.python.org/3/library/logging.html#logging-levels) for more info)

- LOGFILE: 'string' - path and file name for log file
