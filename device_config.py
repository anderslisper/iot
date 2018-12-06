import json
import re

class DeviceConfig:
    def __init__(self):
        with open('device_config.json') as f:
            config = json.load(f)

        self.is_simulated = config["is_simulated"]
        self.deviceid     = config["deviceid"]
        self.logfile      = config["logfile"]

        s = ""
        if self.is_simulated:
            s = "SIMULATED "
        if self.logfile:
            l = "with logging in " + self.logfile
        else:
            l = "with logging to stdout"
        print("Starting {}device {} {}".format(s, self.deviceid, l))
            
if __name__ == '__main__':
    device = DeviceConfig()

    print("Is simulated   = {}".format(device.is_simulated))
    print("Device ID      = {}".format(device.deviceid))
    print("Log file       = {}".format(device.logfile))
    