import os
import glob
import time
import random
import platform
from device_config import DeviceConfig

# Read a DS1820 temp sensor
class Temperature:

    def __init__(self, device_config):
        self.temp_readings = []
        self.AVERAGE_INTERVAL = device_config.temp_average
        if device_config.is_simulated:
            self.hardware = False
        else:
            self.hardware = True
            os.system('modprobe w1-gpio')
            os.system('modprobe w1-therm')
            try:
                base_dir = '/sys/bus/w1/devices/'
                device_folder = glob.glob(base_dir + '28*')[0]
                self.device_file = device_folder + '/w1_slave'
            except:
                self.hardware = False
                print("No temp sensor found. Simulating temp readings")

    # Read DS1820 output
    def read_temp_raw(self):
        lines = ""
        with open(self.device_file, 'r') as f:
            lines = f.readlines()
        return lines
        
    # Read temp and calculate a rolling average over AVERAGE_INTERVAL samples
    # return (currentTemp, averageTemp)
    def get(self):
        if self.hardware:
            lines = self.read_temp_raw()

            while lines[0].strip()[-3:] != 'YES':
                time.sleep(0.2)
                lines = self.read_temp_raw()

            equals_pos = lines[1].find('t=')
            if equals_pos != -1:
                temp_string = lines[1][equals_pos+2:]
                temp_c = float(temp_string) / 1000.0
        else:
            # Simulating a temp around 21 deg C
            temp_c = 21 + (random.random() * 3) - 1.5

        self.temp_readings.append(temp_c)
        if len(self.temp_readings) > self.AVERAGE_INTERVAL:
            self.temp_readings = self.temp_readings[1:]
        temp_a = sum(self.temp_readings)/float(len(self.temp_readings))

        #print(len(self.temp_readings))
        
        temp_c = round(temp_c, 1)
        temp_a = round(temp_a, 1)

        return temp_c, temp_a

if __name__ == '__main__':
    device_config = DeviceConfig()
    reader = Temperature(device_config)
    for i in range(100):
        temp_c, temp_a = reader.get()
        print("read: {}, aver: {}".format(temp_c, temp_a))
        time.sleep(0.1)
	