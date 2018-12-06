import json
import re

class DeviceConfig:
    def __init__(self):
        with open('device_config.json') as f:
            config = json.load(f)

        self.connection_string = config["connection_string"]
        self.is_simulated      = config["is_simulated"]
        self.logfile           = config["logfile"]
        
        p = re.compile('HostName=(.*?);DeviceId=(.*?);SharedAccessKey=(.*)')
        m = p.match(self.connection_string)
        self.hostname = m.group(1)
        self.deviceid = m.group(2)
        self.sharedaccesskey = m.group(3)

        s = ""
        if self.is_simulated:
            s = "SIMULATED "
        print("Starting {}device {}".format(s, self.deviceid))
            
if __name__ == '__main__':
    device = DeviceConfig()

    print("Is simulated   = {}".format(device.is_simulated))
    print("Connection str = {}".format(device.connection_string))
    print("Host name      = {}".format(device.hostname))
    print("Device ID      = {}".format(device.deviceid))
    print("SharedAccessKey= {}".format(device.sharedaccesskey))
	