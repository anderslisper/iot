import os
import glob
import time
import random
import platform
from datetime import datetime
from device_config import DeviceConfig

# Read a DS1820 temp sensor
class Temperature:

    def __init__(self, device_config):
        self.temp_readings = [21]
        self.AVERAGE_INTERVAL = 120 #device_config.temp_average
        self.temp_sampling = device_config.temp_sampling
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

    def set_filter_time(self, filter_time):
        try:
            self.AVERAGE_INTERVAL = int(filter_time / self.temp_sampling)
        except Exception as e:
            print(e)
            self.AVERAGE_INTERVAL = 120
        if len(self.temp_readings) > self.AVERAGE_INTERVAL:
            del self.temp_readings[self.AVERAGE_INTERVAL:]
            
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

            i = 50
            while lines[0].strip()[-3:] != 'YES':
                time.sleep(0.2)
                lines = self.read_temp_raw()
                i -= 1
                if i == 0:
                    break

            if i > 0:
                equals_pos = lines[1].find('t=')
                if equals_pos != -1:
                    temp_string = lines[1][equals_pos+2:]
                    temp_c = float(temp_string) / 1000.0
            else:
                print("Could not read temperature @ {}".format(datetime.now()))
                temp_c = self.temp_readings[-1]

        else:
            # Simulating a temp around 21 deg C
            temp_c = 21 + (random.random() * 3) - 1.5

        self.temp_readings.append(temp_c)
        if len(self.temp_readings) > self.AVERAGE_INTERVAL:
            self.temp_readings = self.temp_readings[1:]

        temp_readings_sorted = sorted(self.temp_readings)
        temp_m = temp_readings_sorted[0]
        if len(temp_readings_sorted) > 3:
            temp_m = temp_readings_sorted[3]
        
        temp_c = round(temp_c, 1)
        temp_m = round(temp_m, 1)

        return temp_c, temp_m

if __name__ == '__main__':
    device_config = DeviceConfig()
    reader = Temperature(device_config)
    for i in range(100):
        temp_c, temp_m = reader.get()
        print("read: {}, min: {}".format(temp_c, temp_m))
        time.sleep(0.1)
	