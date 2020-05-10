import os
import time
from device_config import DeviceConfig

IR_REPEATS = 3
AC_OFF     = 0
AC_ON      = 1
LOW_HEAT   = 10
TEMP_MIN   = 16
TEMP_MAX   = 30

class AirCondition:
    def __init__(self, device_config):
        if device_config.is_simulated:
            self.hardware = False
        else:
            self.hardware = True
        self.currentTemp = AC_ON
        self.send_ir_code(AC_ON)

    # Return a valid version of temp
    def validate_temp(self, temp):
        # Valid entries are 0, 10, 16-30
        if temp != LOW_HEAT and temp != AC_OFF:
            temp = max(TEMP_MIN, min(temp, TEMP_MAX))
        return temp

    # Set the temperature of the AC unit (if changed)
    # Uses irsend/lirc
    def set_temp(self, temp):
        temp = self.validate_temp(temp)
        if temp != self.currentTemp:
            if self.currentTemp == AC_OFF:
                self.send_ir_code(AC_ON)
                print("Switching system back on.")
                
            self.currentTemp = temp

            self.send_ir_code(temp)
            
            print("Setting temperature to {} degC".format(temp))
        else:
            print("Temp is already set to {}. Not changed.".format(temp))
            
    def send_ir_code(self, temp):
        if temp == AC_OFF:
            ircode = "AC_OFF"
        elif temp == AC_ON:
            ircode = "AC_ON"
        elif temp == LOW_HEAT:
            ircode = "LH_HIGH_10"
        else:
            ircode = "HEAT_HIGH_{}".format(temp)

        if self.hardware:
            for i in range(IR_REPEATS):
                os.system("irsend SEND_ONCE LG_AC {}".format(ircode))
                time.sleep(1)
    
if __name__ == '__main__':
    device_config = DeviceConfig()
    ac = AirCondition(device_config)
    ac.set_temp(21)
    ac.set_temp(21)
    ac.set_temp(15)
    ac.set_temp(31)
    ac.set_temp(10)
    ac.set_temp(0)
    ac.set_temp(1)
