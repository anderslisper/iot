#!/bin/bash
cd /home/anders/gundbyniot

tail -n 1000 iot_log.txt > log.tmp
mv -f log.tmp iot_log.txt

echo >> iot_log.txt
echo "BOOTING APPLICATION" >> iot_log.txt
date >> iot_log.txt

# Wait for startup
sleep 120

# Get latest 
echo "Pulling from git" >> iot_log.txt
git pull >> iot_log.txt

# Run application
echo "STARTING APPLICATION" >> iot_log.txt
/usr/bin/python3 IotDevice.py&
