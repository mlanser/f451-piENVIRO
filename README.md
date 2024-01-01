# Instructions for f451 Labs EnviroMon v1.0.3

## Overview

This application is designed for the *f451 Labs piENVIRO* device which is equipped with a [Pimoroni Enviro+ HAT](https://shop.pimoroni.com/products/enviro?variant=31155658457171) add-on. The main objective is to continously read environment data (e.g. temperature, barometric pressure, and humidity) from the Enviro+ sensors and then upload the data to the [Adafruit IO service](https://io.adafruit.com).

## Install

This application is not available on PyPi. However, you can still use `pip` to install the module directly from GitHub (see below).

### Dependencies

This module is dependent on the following libraries:

- [enviroplus-python](https://github.com/pimoroni/enviroplus-python/) — only install if you have a physical Enviro+ device
- [adafruit-io](https://pypi.org/project/adafruit-io/) — only install if you have an account with the Adafruit IO service

NOTE: You can run this app in demo mode on (almost) any device even without the Enviro+. It will then create random numbers and can send output to the `logger` when log level is `DEBUG` or when `--debug` flag is used.

### Installing from GitHub using `pip`

You can use `pip install` to install this module directly from GitHub as follows:

```bash
$ pip install 'f451-piENVIRO @ git+https://github.com/mlanser/f451-piENVIRO.git'
```

### What's with the name '*f451-piENVIRO*'

The original idea behind this repo was to hold all application running on a particalar Raspberry Pi device — piENVIRO — in my network. This device has a specific hardware configuration and general "purpose" (i.e. to read and process environment data).

So, if/when I add more applications to this device, they'll also be added to this repo and will show up as 'scripts' entry points in the `pyprojects.toml` file.

## How to use

### Running the application

The `enviromon` application is designed to run unsupervised, and it will collect and upload data until it is interrupted by some external event (e.g. keyboard interrupt, process `kill` command, etc.)

To launch this application from terminal:

```bash
$ nohup python -u enviromon.py > enviromon.out &
```

This command launches the `enviromon` application in the background. The application will keep running even after the terminal window is closed. Any output will be redirected to the `enviromon.out` file.

It's also possible to install this application via `pip` from GitHub, and one then can launch the application as follows:

```bash
$ nohup enviromon > enviromon.out &
```

### Interacting with the application

The `enviromon` application can read settings from both a `settings.toml` file and from CLI arguments:

```bash
# Use CLI arg '-h' to see available options
$ enviromon -h 

# Stop after 10 uploads
$ enviromon --uploads 10

# Show 'progress bar' regardless of setting in 'toml' file
$ enviromon --progress

# Show specific display mode (e.g. 'temperature') regardless 
# of setting in 'toml' file
$ enviromon --dmode temperature
```

The format of the `settings.toml` file is straight forward and this is also where you should store Adafruit IO credentials. The `settings.toml` file only supports numbers and strings. But you define most aspects of the applications here.

For example, if you change the `PROGRESS` setting to 1, then the Enviro+ LCD will display a progress bar indicating when the next (simulated) upload will happen.

There is also a 'sleep mode' which turns off the display automatically after a certain amount of time. You can also turn on/off the LED display by pushing/tapping the joystick button (down).

```toml
# File: settings.toml
...
PROGRESS = 1    # [0|1] - 1 = show upload progress bar on LED
SLEEP = 600     # Delay in seconds until screen is blanked
...
```

Please refer to the section "*Custom application settings in SETTINGS.TOML*" below for more information on available options in the `settings.toml` file.

The `enviromon` application can display live data both in the terminal and on the Enviro+ LCD. If you do no want to see any output in the termin (e.g. if you want to run the application in the background), the you can start the application with the `--noCLI` flag. Similarly, the `--noLED` flag prevents any output to the Enviro+ LCD.

This application offers 5 different display modes for the Enviro+ LCD:

- *temperature* — show realtime graph of current temperature data
- *pressure* — show realtime graph of current baromteric pressure data
- *humidity* — show realtime graph of current humidity data
- *all* — show latests data points as text in dual columns
- *sparkles* — show random pixels light up — looks great at night and lets you know the app is running 😉

You can switch between display modes by covering the Enviro+ light sensor for a fraction of a second. We're using the proximity data to trigger a switch and you can switch through all display modes.

Finally you can exit the application using the `ctrl-c` command. If you use the `--uploads N` commandline argument, then the application will stop after *N* (simulated) uploads.

## How to test

**NOTE: THIS IS STILL W.I.P - MORE/BETTER TEST TO COME**

The tests are written for [pytest](https://docs.pytest.org/en/7.1.x/contents.html) and we use markers to separate out tests that require the actual Enviro+ hardware. Some tests do not rely on the hardware to be present. However, those tests rely on the `pytest-mock` module to be present.

```bash
# Run all tests (except marked 'skip')
$ pytest

# Run tests with 'hardware' marker
$ pytest -m "hardware"

# Run tests without 'hardware' marker
$ pytest -m "not hardware"
```

## Custom application settings in SETTINGS.TOML

The 'settings.toml' file holds various custom application settings and secrets (e.g. Adafruit IO keys, etc.) and this file should **NOT** be included in 'git' commits.

It is recommended to copy the '*settings.example*' to '*settings.toml*' and then customize the values in '*settings.toml*' as nedeed for the specific device that the application is running on.

### Adafruit IO settings

- **AIO_USERNAME**: 'string' - Adafruit IO username
- **AIO_KEY**: 'string' - Adafruit IO key
- **AIO_UPLOAD**: 'string' - yes | force | no
  - "yes" - *upload if feed available*
  - "force" - *exit if feed invalid*
  - "no" - *do not upload data*

- **FEED_TEMPS**: 'string' - Adafruit IO feed key for 'temperature' feed
- **FEED_PRESS**: 'string' - Adafruit IO feed key for 'pressure' feed
- **FEED_HUMID**: 'string' - Adafruit IO feed key for 'humidity' feed

### Misc. Settings for Data Management

- **UNITS_TEMPS**: 'string' - temperature sensor reads in "C", but data can also be converted to other units for display and upload.
  - "C" - *Celsius*
  - "F" - *Fahrenheit - data will be converted from Celsius to Fahrenheit*
  - "K" - *Kelvin - data will be converted from Celsius to Kelvin*

  - *Example: "F" means temperature data will be converted from Celsius to Fahrenheit before it is uploaded or displayed.*

**NOTE:** THIS SETTING IS RESERVED FOR FUTURE USE

### Misc. Application Defaults

- **ROTATION**: 'int' - 0 | 90 | 180 | 270 degrees to turn LCD display
  - 90 | 270 - *top of LCD will point toward/away RPI HDMI and layout is 160x80*
  - 0 | 180 - *top of LCD will point away/toward RPI USB and layout is 80x160*

- **DISPLAY**: 'str'
  - 'name_of_display_mode' - *name of display mode with single data point (e.g. download speed, etc.) and scrolling bar graph*
  - 'all' - *displays all collected data as text in dual columns*
  - 'sparkles' - *default display is in 'sparkle' mode where data is collected and uploaded but not displayed*

- **DELAY**: 'int' - delay in seconds between uploads to Adafruit IO.
  - Smaller number means more freq uploads and higher data rate
- **WAIT**: 'int' - delay in seconds between sensor reads
- **THROTTLE**: 'int' - additional delay in seconds to be applied on Adafruit IO 'ThrottlingError'

- **PROGRESS**: 'string' - on | off
  - "on" - *show 'wait for upload' progress bar on LCD*
  - "off" - *do not show progress bar*

- **SLEEP**: 'int' - delay in seconds until LCD is blanked for "screen saver" mode

- **LOGLVL**: 'string' - debug | info | error
  - *Logging levels (see: [Python docs](https://docs.python.org/3/library/logging.html#logging-levels) for more info)*

- **LOGFILE**: 'string' - path and file name for log file
