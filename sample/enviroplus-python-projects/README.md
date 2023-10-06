# Enviro+ Python Projects

Designed for environmental monitoring, Enviro+ lets you measure air quality (pollutant gases and particulates), temperature, pressure, humidity, light, and noise level. Learn more - https://shop.pimoroni.com/products/enviro-plus

[![Python Versions](https://img.shields.io/pypi/pyversions/enviroplus.svg)](https://pypi.python.org/pypi/enviroplus)

# Goal of this Project

The hope is that this repository can be one more place for various example projects and code to be used with the Enviro & Enviro+ boards designed by Pimoroni. Their primary repository has several great example applications for users to learn from and apply to their own projects, and this repo looks to add more to the list!

<br>

![Enviro+](https://github.com/pimoroni/enviroplus-python/raw/master/Enviro-Plus-pHAT.jpg "Enviro+") 

<br>

##### Many of the examples here can also be modified and adapted to work with similar boards as well (at least those that utilize similar sensors i.e. BME280)

<br>

This repo is an effort to expand the original contribution I wrote for the Enviro+ that added functionality to publish sensor readings to a user's Adafruit IO dashboard. While the code for that project will serve as the first example listed here for users to learn from, **more code will be added soon!**

## Enviro Plus One-line Install

```bash
curl -sSL https://get.pimoroni.com/enviroplus | bash
```

### Install and configure dependencies from GitHub (Alternative)

* `git clone https://github.com/pimoroni/enviroplus-python`
* `cd enviroplus-python`
* `sudo ./install.sh`

**Note** Raspbian/Raspberry Pi OS Lite users may first need to install git: `sudo apt install git`


## Other User Projects

* Enviro Plus Dashboard - https://gitlab.com/dedSyn4ps3/enviroplus-dashboard
* enviro monitor - https://github.com/roscoe81/enviro-monitor
* enviroplus_exporter - https://github.com/tijmenvandenbrink/enviroplus_exporter - Prometheus exporter (with added support for Luftdaten and InfluxDB Cloud)
* homekit-enviroplus - https://github.com/sighmon/homekit-enviroplus - An Apple HomeKit accessory for the Pimoroni Enviro+
* go-enviroplus - https://github.com/rubiojr/go-enviroplus - Go modules to read Enviro+ sensors
* homebridge-enviroplus - https://github.com/mhawkshaw/homebridge-enviroplus
