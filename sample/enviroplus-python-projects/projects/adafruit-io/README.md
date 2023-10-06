# Enviro+ Adafruit IO

Uses Adafruit Blinka and BME280 libraries to publish sensor data to Adafruit IO

# Setup

- **Make sure you have the `enviroplus-python` library installed first**

- Install Adafruit_Blinka: `pip3 install Adafruit-Blinka`

- Install Adafruit_CircuitPython_BME280: `pip3 install adafruit-circuitpython-bme280`

- Clone this repo: `git clone https://gitlab.com/dedSyn4ps3/enviroplus-python-projects.git && cd enviroplus-dashboard`

- Create a free Adafruit IO account (if you don't have one), and follow instructions to obtain your AIO key and Username

- **Add credentials from previous step to the main application file `projects/adafruit-io/adafruit_io.py`**

- Run the app and watch data visualizations on your new dashboard!

# Important Note

For those new to using the enviroplus (or any other IoT devices), pay attention to the code in the main application file. It outlines the names of the feeds that will used to communicate with your Adafruit IO dashboard. **These names must match!**

For example, if you create a feed on your dashboard called "livingroom_temperature", you would want to change the line in the source file that says:

```python
temperature_feed = aio.feeds('temperature')
```

to instead read,

```python
temperature_feed = aio.feeds('livingroom_temperature')
```

If you are running the application as-is (after inputting your AIO KEY & USERNAME), you will see that your dashboard should show four new feeds created automatically as a result of the `try, except` block of code looking for the feeds to be present or not:

- temperature

- humidity

- pressure

- altitude

**As outlined above, you can create feeds with whatever names you want, just be sure to update the code and remove the `try, except` block to prevent new default feeds from being created.**
