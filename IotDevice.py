# Main file

from iotversion import *

import time
import sys
import json
from datetime import datetime

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
KEY_FALLBACK_DATE        = "fallbackDate"
KEY_FALLBACK_TEMP        = "fallbackTemp"
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
        self.lastComm = time.time()
        self.fallback_executed = False

        try:
            with open('desired_state.json', 'r') as f:
                self.desired = data = json.load(f)                
        except Exception as e:
            print("Expection while reading saved desired state: " + str(e))
            self.desired = { 
                KEY_TELEMETRY_INTERVAL:   DEFAULT_TELEMETRY,
                KEY_TEMPERATURE_SETPOINT: DEFAULT_TEMP,
                KEY_FALLBACK_DATE:        "2025-01-01",
                KEY_FALLBACK_TEMP:        "21"
            }

        try:
            self.fallbackDateObject = datetime.strptime(self.desired[KEY_FALLBACK_DATE], "%Y-%m-%d")
        except:
            self.fallbackDateObject = datetime.strptime("2025-01-01", "%Y-%m-%d")
            print("Fallback date format not YY-MM-DD " + self.desired[KEY_FALLBACK_DATE])
            
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
            # Save new state to disk (to be read at boot)
            with open('desired_state.json', 'w') as f:
                json.dump(self.desired, f)                
            # Report new state to HUB
            self.update_reported_state()
            # Set AC temp
            self.airCondition.set_temp(self.desired[KEY_TEMPERATURE_SETPOINT])
            try:
                self.fallbackDateObject = datetime.strptime(self.desired[KEY_FALLBACK_DATE], "%Y-%m-%d")
            except:
                self.fallbackDateObject = datetime.strptime("2025-01-01", "%Y-%m-%d")
                print("Fallback date format not YY-MM-DD " + self.desired[KEY_FALLBACK_DATE])
        except Exception as e:
            print(e)
        self.new_interval_set = True
        self.fallback_executed = False

    # Send current state to HUB
    def update_reported_state(self):
        reported = {}
        reported[KEY_SW]              = SOFTWARE_DICT
        reported[KEY_UPDATE_TIME]     = datetime.now().isoformat()
        reported[KEY_TELEMETRY_ALERT] = self.reported_temp_alert
        for key in [KEY_LOCATION, KEY_TELEMETRY_INTERVAL, KEY_TEMPERATURE_SETPOINT]:
            try:
                reported[key] = self.desired[key]
            except KeyError:
                print("State set from HUB lack key '%s'" % key)
        # Report new state to HUB
        sent = self.hub.update_reported_state(reported)
        if sent:
            self.reportSuccessfulCommunication()
    
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

    def reportSuccessfulCommunication(self):
        self.lastComm = time.time()
        
    def isTimeForFallback(self):
        if time.time() - self.lastComm > 60: #*60:
            seconds = (datetime.now() - self.fallbackDateObject).total_seconds()
            #print(str(seconds) + " since fallback")
            if seconds > 0:
                # Passing into fallback date
                if not self.fallback_executed:
                    #print("Return true")
                    self.fallback_executed = True
                    return True
        else:
            #print("internet is still alive")
            pass

        return False
        
    # Main loop
    def main_loop(self):
        print ( "Starting IoT Device with ID '{}'".format(self.device_config.deviceid) )
        self.hub.kick()
        try:
            while True:
                if self.got_twin_state_after_boot or True:
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
                    telemetry[KEY_TELEMETRY_TIME]  = datetime.now().isoformat()   
                    
                    weather = self.weather.get()
                    if weather is not None:
                        telemetry[KEY_OUTDOOR_CONDITIONS] = weather
                    
                    #print ( "Send telemetry: %s" % json.dumps(telemetry,indent=4) )
                    sent = self.hub.post_telemetry(telemetry)
                    if sent:
                        self.reportSuccessfulCommunication()                        
                    
                    if self.isTimeForFallback():
                        # Have passed fallback time and has no internet. 
                        # Set default AC temp
                        self.airCondition.set_temp(self.desired[KEY_FALLBACK_TEMP])
                    
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
    