# Main file

import json
import socket
import sys
import time
from datetime import datetime

from air_condition import AirCondition
from azure import Azure
from common import Common
from device_config import DeviceConfig
from firebase import Firebase
from iotversion import *
from temp_reader import Temperature
from weather import Weather

# When to report temp alerts
TEMP_ALERT_LOW  = 7
TEMP_ALERT_HIGH = 28

# Keys in state and telemetry
KEY_TELEMETRY_INTERVAL   = "telemetryInterval"
KEY_FALLBACK_DATE        = "fallbackDate"
KEY_FALLBACK_TEMP        = "fallbackTemp"
KEY_FALLBACK_ACTIVATED   = "fallbackActivated"
KEY_BOOT_TIME            = "bootTime"
KEY_TEMPERATURE_SETPOINT = "tempSetPoint"
KEY_TEMPERATURE_CURRENT  = "tempCurrent"
KEY_TELEMETRY_ALERT      = "tempAlert"
KEY_TELEMETRY_TIME       = "utctime"
KEY_OUTDOOR_CONDITIONS   = "outdoor"
KEY_UPDATE_TIME          = "updateTime"
KEY_SW                   = "software"
KEY_SW_VERSION           = "version"
KEY_SW_DATE              = "date"
KEY_IP_ADDRESS           = "ipAddress"

# These values are used as default if keys are lacking
DESIRED_STATE_TEMPLATE = { 
    KEY_TELEMETRY_INTERVAL:   20*60,   # 20 min
    KEY_TEMPERATURE_SETPOINT: 21,
    KEY_FALLBACK_DATE:        "2025-01-01",
    KEY_FALLBACK_TEMP:        21,
}

class IotDevice:
    def __init__(self, device_config):
        self.device_config = device_config
        self.reported_temp_alert = False
        self.fallback_activated = None
        self.boot_time = Common.getCurrentUTCTime()
        self.ip_address = self.getIpAddress()

        self.weather      = Weather()
        self.airCondition = AirCondition(device_config)
        self.temperature  = Temperature(device_config)
        
        if device_config.cloud == "firebase":
            self.hub = Firebase(self, device_config)
        elif device_config.cloud == "azure":
            self.hub = Azure(self, device_config)
        else:
            raise Exception("Supported cloud services are 'azure' and 'firebase'. Update 'device_config.json'.")

        try:
            with open('desired_state.json', 'r') as f:
                self.desired = json.load(f)                
        except Exception as e:
            print("Expection while reading saved desired state: " + str(e))
        self.wash_desired()

        self.set_fallback_date()

    def set_fallback_date(self):
        try:
            self.fallbackDateObject = datetime.strptime(self.desired[KEY_FALLBACK_DATE], "%Y-%m-%d")
            update_time = datetime.strptime(self.desired[KEY_UPDATE_TIME], "%Y-%m-%dT%H:%M:%S.%fZ")
            if self.fallbackDateObject < update_time:
                # Desired state updated since fallback, so ignore it
                self.fallbackDateObject = None
        except Exception as e:
            print(e.message)
            self.fallbackDateObject = None
            print("Fallback date format not YY-MM-DD " + self.desired[KEY_FALLBACK_DATE])

    def wash_desired(self):
        for key, val in DESIRED_STATE_TEMPLATE.items():
            if key not in self.desired:
                self.desired[key] = val
        self.desired[KEY_TEMPERATURE_SETPOINT] = self.airCondition.validate_temp(self.desired[KEY_TEMPERATURE_SETPOINT])
        self.desired[KEY_TELEMETRY_INTERVAL] = max(30, self.desired[KEY_TELEMETRY_INTERVAL])
        self.desired[KEY_TELEMETRY_INTERVAL] = min(3600, self.desired[KEY_TELEMETRY_INTERVAL])
        
    # Callback when the device twin stored in cloud has been updated
    def device_twin_update(self, desired):
        self.desired = desired
        self.wash_desired()

        print ( "New desired state received: %s" % json.dumps(self.desired, indent=4) )
        try:
            # Save new state to disk (to be read at boot)
            with open('desired_state.json', 'w') as f:
                json.dump(self.desired, f)                
            # Set new filter time
            self.temperature.set_filter_time(self.desired[KEY_TELEMETRY_INTERVAL])
            # Report new state to HUB
            self.update_reported_state()
            # Set AC temp
            self.airCondition.set_temp(self.desired[KEY_TEMPERATURE_SETPOINT])

            self.set_fallback_date()
        except Exception as e:
            print(e)

    # Send current state to HUB
    def update_reported_state(self):
        reported = {}
        reported[KEY_SW]              = SOFTWARE_DICT
        reported[KEY_UPDATE_TIME]     = Common.getCurrentUTCTime()
        reported[KEY_BOOT_TIME]       = self.boot_time
        reported[KEY_TELEMETRY_ALERT] = self.reported_temp_alert
        reported[KEY_IP_ADDRESS]      = self.ip_address
        if self.fallbackDateObject is None:
            reported[KEY_FALLBACK_ACTIVATED] = "Yes"
        else:
            reported[KEY_FALLBACK_ACTIVATED] = "No"
        for key in [KEY_TELEMETRY_INTERVAL, KEY_TEMPERATURE_SETPOINT]:
            try:
                reported[key] = self.desired[key]
            except KeyError:
                print("State set from HUB lack key '%s'" % key)
        # Report new state to HUB
        sent = self.hub.update_reported_state(reported)
    
    def get_temp_alert(self, temp):
        low_limit = TEMP_ALERT_LOW
        high_limit = TEMP_ALERT_HIGH
        if self.reported_temp_alert: # 1 degrees hysteresis
            low_limit += 1
            high_limit -= 1
        alert = (temp < low_limit) or (temp > high_limit)
        return alert

    # Sleep for t seconds while every <device_config.temp_sampling> seconds...
    # - checking for temp alerts
    # - kicking hub connection
    # - checking if telemetryInterval has been updated
    def telemetry_sleep(self):
        started_at = time.monotonic() - 2
        while (time.monotonic() < (started_at + self.desired[KEY_TELEMETRY_INTERVAL])):
            self.hub.kick()
            time.sleep(device_config.temp_sampling)
            temp_c, temp_m = self.temperature.get()
            alert = self.get_temp_alert(temp_m)
            if alert != self.reported_temp_alert:
                break

    def isTimeForFallback(self):
        if self.fallbackDateObject is None:
            return False
        seconds = (datetime.now() - self.fallbackDateObject).total_seconds()
        if seconds > 0:
            # 00:00:00 on fallback date has passed
            return True
        return False

    def getIpAddress(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    # Main loop
    def main_loop(self):
        print ( "Starting IoT Device with ID '{}'".format(self.device_config.deviceid) )
        self.hub.kick()
        while True:
            try:
                temp_c, temp_m = self.temperature.get()
                tempCurrent = temp_m # Reporting min temp

                telemetry = {}
                try:
                    telemetry[KEY_TEMPERATURE_SETPOINT] = self.desired[KEY_TEMPERATURE_SETPOINT]
                except:
                    # No temperature set point
                    pass
                telemetry[KEY_TEMPERATURE_CURRENT] = tempCurrent

                current_alert = self.reported_temp_alert
                self.reported_temp_alert = self.get_temp_alert(temp_m)
                if current_alert != self.reported_temp_alert:
                    self.update_reported_state()
                    
                telemetry[KEY_TELEMETRY_ALERT] = self.reported_temp_alert
                telemetry[KEY_TELEMETRY_TIME]  = Common.getCurrentUTCTime()  
                
                weather = self.weather.get()
                if weather is not None:
                    telemetry[KEY_OUTDOOR_CONDITIONS] = weather
                
                #print ( "Send telemetry: %s" % json.dumps(telemetry,indent=4) )
                sent = self.hub.post_telemetry(telemetry)
                
                if self.isTimeForFallback():
                    # Have passed automatic fallback time
                    # Set default AC temp
                    print("Fallback activated @ {}".format(datetime.now()))
                    self.desired[KEY_TEMPERATURE_SETPOINT] = self.desired[KEY_FALLBACK_TEMP]
                    self.airCondition.set_temp(self.desired[KEY_FALLBACK_TEMP])
                    self.fallbackDateObject = None
                
                sys.stdout.flush()

                try:
                    self.telemetry_sleep()
                except Exception as e:
                    print("Device '{}' has no configured device twin defined".format(self.device_config.deviceid))
                    if device_config.cloud == "firebase":
                        print("Use portal webpage to add the new device.")
                    else:
                        print("Use e.g. iot_hub_twin_sample.py to create the new device twin")
                    print(e)
                    raise KeyboardInterrupt

            except KeyboardInterrupt:
                print ( "IoTHubClient sample stopped by Ctrl-C" )
                break
                
            except Exception as e:
                print("Top level exception caught:")
                print(e)

# Main program
device_config = DeviceConfig()
if device_config.logfile is not None:
    sys.stdout = open(device_config.logfile, "a")
iotDevice = IotDevice(device_config)
iotDevice.main_loop()
    