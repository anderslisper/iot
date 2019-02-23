#!/bin/bash
cd /home/anders/gundbyniot
# Get latest 
git pull
# Run application
/usr/bin/python3 IotDevice.py&
