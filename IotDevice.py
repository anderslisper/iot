# Main file

from iotversion import *

import time
import datetime
import sys
import json
from device_config import DeviceConfig
from temp_reader   import Temperature
from air_condition import AirCondition
from weather       import Weather
from firebase      import Firebase
from azure         import Azure

DEFAULT_TELEMETRY       = 20*60   # 20 min
DEFAULT_TEMP            = 21      # deg C
TEMP_ALERT_LOW          = 7       # deg C
TEMP_ALERT_HIGH         = 28      # deg C

# Keys in state and telemetry
KEY_TELEMETRY_INTERVAL   = "telemetryInterval"
KEY_TEMPERATURE_SETPOINT = "tempSetPoint"
KEY_TEMPERATURE_CURRENT  = "tempCurrent"
KEY_TELEMETRY_ALERT      = "tempAlert"
KEY_TELEMETRY_TIME       = "utctime"
KEY_OUTDOOR_CONDITIONS   = "outdoor"
KEY_LOCATION             = "location"
KEY_UPDATE_TIME          = "updateTime"
KEY_SW                   = "software"
KEY_SW_VERSION           = "version"
KEY_SW_DATE              = "date"

class IotDevice:
    def __init__(self, device_config):
        self.device_config = device_config
        self.new_interval_set    = False
        self.reported_temp_alert = False
        self.got_twin_state_after_boot = False

        self.desired = { 
            KEY_TELEMETRY_INTERVAL:   DEFAULT_TELEMETRY,
            KEY_TEMPERATURE_SETPOINT: DEFAULT_TEMP,
        }

        self.weather      = Weather()
        self.airCondition = AirCondition(device_config)
        self.temperature  = Temperature(device_config)
        
        if device_config.cloud == "firebase":
            self.hub = Firebase(self, device_config)
        elif device_config.cloud == "azure":
            self.hub = Azure(self, device_config)
        else:
            raise Exception("Supported cloud services are 'azure' and 'firebase'. Update 'device_config.json'.")

    # Callback when the device twin stored in cloud has been updated
    def device_twin_update(self, desired):
        self.got_twin_state_after_boot = True

        self.desired = desired
        self.desired[KEY_TEMPERATURE_SETPOINT] = self.airCondition.validate_temp(self.desired[KEY_TEMPERATURE_SETPOINT])
        print ( "New desired state received: %s" % json.dumps(self.desired, indent=4) )
        try:
            # Report new state to HUB
            self.update_reported_state()
            # Set AC temp
            self.airCondition.set_temp(self.desired[KEY_TEMPERATURE_SETPOINT])
        except Exception as e:
            print(e)
        self.new_interval_set = True

    # Send current state to HUB
    def update_reported_state(self):
        reported = {}
        reported[KEY_SW]              = SOFTWARE_DICT
        reported[KEY_UPDATE_TIME]     = datetime.datetime.now().isoformat()
        reported[KEY_TELEMETRY_ALERT] = self.reported_temp_alert
        for key in [KEY_LOCATION, KEY_TELEMETRY_INTERVAL, KEY_TEMPERATURE_SETPOINT]:
            try:
                reported[key] = self.desired[key]
            except KeyError:
                print("State set from HUB lack key '%s'" % key)
        # Report new state to HUB
        self.hub.update_reported_state(reported)
    
    # Sleep for t seconds while every <device_config.temp_sampling> seconds...
    # - checking for temp alerts
    # - kicking hub connection
    # - checking if telemetryInterval has been updated
    def my_sleep(self, t):
        if t is None:
            t = 60
        expire = time.monotonic() + (t-2)
        while (time.monotonic() < expire):
            self.hub.kick()
            time.sleep(device_config.temp_sampling)
            temp_c, temp_a = self.temperature.get()
            alert = (temp_a < TEMP_ALERT_LOW) or (temp_a > TEMP_ALERT_HIGH)
            if alert != self.reported_temp_alert:
                break
            if self.new_interval_set:
                self.new_interval_set = False
                break

    # Main loop
    def main_loop(self):
        print ( "Starting IoT Device with ID '{}'".format(self.device_config.deviceid) )
        try:
            while True:
                if self.got_twin_state_after_boot:
                    temp_c, temp_a = self.temperature.get()
                    tempCurrent = temp_a # Reporting average temp

                    telemetry = {}
                    try:
                        telemetry[KEY_TEMPERATURE_SETPOINT] = self.desired[KEY_TEMPERATURE_SETPOINT]
                    except:
                        # No temperature set point
                        pass
                    telemetry[KEY_TEMPERATURE_CURRENT] = tempCurrent

                    current_alert = self.reported_temp_alert
                    self.reported_temp_alert = (temp_a < TEMP_ALERT_LOW) or (temp_a > TEMP_ALERT_HIGH)
                    if current_alert != self.reported_temp_alert:
                        self.update_reported_state()
                        
                    telemetry[KEY_TELEMETRY_ALERT] = self.reported_temp_alert
                    telemetry[KEY_TELEMETRY_TIME]  = datetime.datetime.now().isoformat()   
                    
                    weather = self.weather.get()
                    if weather is not None:
                        telemetry[KEY_OUTDOOR_CONDITIONS] = weather
                    
                    print ( "Send telemetry: %s" % json.dumps(telemetry,indent=4) )
                    self.hub.post_telemetry(telemetry)
                    
                    sys.stdout.flush()

                try:
                    self.my_sleep(self.desired[KEY_TELEMETRY_INTERVAL])
                except Exception as e:
                    print("Device {} has no configured device twin defined".format(self.device_config.deviceid))
                    print("Use e.g. iot_hub_twin_sample.py to create new device twin")
                    print(e)
                    raise KeyboardInterrupt

        except KeyboardInterrupt:
            print ( "IoTHubClient sample stopped" )


# Main program
device_config = DeviceConfig()
if device_config.logfile is not None:
    sys.stdout = open(device_config.logfile, "w")
iotDevice = IotDevice(device_config)
iotDevice.main_loop()
    