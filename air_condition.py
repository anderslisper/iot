import os
import time
from device_config import DeviceConfig

class AirCondition:
    def __init__(self, device_config):
        if device_config.is_simulated:
            self.hardware = False
        else:
            self.hardware = True
        self.currentTemp = 0

    def validate_temp(self, temp):
        # Valid entries are 10, 16-30
        if temp != 10:
            temp = max(16, min(temp, 30))
        return temp
        
    def set_temp(self, temp):
        temp = self.validate_temp(temp)
        if temp != self.currentTemp:
            self.currentTemp = temp

            if temp != 10:
                ircode = "HEAT_HIGH_{}".format(temp)
            else:
                ircode = "LOW_HEAT_10"

            if self.hardware:
                for i in [1,2,3]:
                    os.system("irsend SEND_ONCE LG_AC {}".format(ircode))
                    time.sleep(1)

            print("Setting temperature to {} degC using IR code '{}'".format(temp, ircode))
        else:
            print("Temp is already set to {}. Not changed.".format(temp))
            
if __name__ == '__main__':
    device_config = DeviceConfig()
    ac = AirCondition(device_config)
    ac.set_temp(21)
    ac.set_temp(21)
    ac.set_temp(15)
    ac.set_temp(31)
    ac.set_temp(10)
	