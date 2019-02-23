#!/bin/bash
cd /home/anders/gundbyniot

tail -n 1000 iot_log.txt > log.tmp
mv -f log.tmp iot_log.txt

echo "STARTING APPLICATION" >> iot_log.txt

# Get latest 
git pull >> iot_log.txt

# Run application
/usr/bin/python3 IotDevice.py&

