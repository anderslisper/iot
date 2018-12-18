import json
import re

class DeviceConfig:
    def __init__(self):
        with open('device_config.json') as f:
            config = json.load(f)

        self.is_simulated  = config["is_simulated"]
        self.deviceid      = config["deviceid"]
        self.logfile       = config["logfile"]
        self.cloud         = config["cloud"]
        self.temp_sampling = config["temp_sampling"] # in sec
        self.temp_average  = config["temp_average"]  # in no of intervals, e.g. TIME = temp_average * temp_sampling seconds

        s = ""
        if self.is_simulated:
            s = "SIMULATED "

        if self.logfile:
            l = self.logfile
        else:
            l = "stdout"

        print("Starting {}device {} with logging to {}".format(s, self.deviceid, l))
            
if __name__ == '__main__':
    device = DeviceConfig()

    print("Is simulated       = {}".format(device.is_simulated))
    print("Device ID          = {}".format(device.deviceid))
    print("Log file           = {}".format(device.logfile))
    print("Used cloud service = {}".format(device.cloud))   
    print("Temp sampling      = {} s".format(device.temp_sampling))
    print("Temp average       = {} intervals".format(device.temp_average))
    print("Temp average time  = {} s".format(device.temp_average * device.temp_sampling))