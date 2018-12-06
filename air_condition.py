import os
import time
from device_config import DeviceConfig

IR_REPEATS = 3
LOW_HEAT   = 10
TEMP_MIN   = 16
TEMP_MAX   = 30

class AirCondition:
    def __init__(self, device_config):
        if device_config.is_simulated:
            self.hardware = False
        else:
            self.hardware = True
        self.currentTemp = 0

    # Return a valid version of temp
    def validate_temp(self, temp):
        # Valid entries are 10, 16-30
        if temp != LOW_HEAT:
            temp = max(TEMP_MIN, min(temp, TEMP_MAX))
        return temp
        
    # Set the temperature of the AC unit (if changed)
    # Uses irsend/lirc
    def set_temp(self, temp):
        temp = self.validate_temp(temp)
        if temp != self.currentTemp:
            self.currentTemp = temp

            if temp == LOW_HEAT:
                ircode = "LOW_HEAT_10"
            else:
                ircode = "HEAT_HIGH_{}".format(temp)

            if self.hardware:
                for i in range(IR_REPEATS):
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
	