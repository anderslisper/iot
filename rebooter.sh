#!/bin/bash
cd /home/anders/gundbyniot

touch rebooter_log.txt
tail -n 1000 rebooter_log.txt > rlog.tmp
mv -f rlog.tmp rebooter_log.txt
chmod 666 rebooter_log.txt

echo >> rebooter_log.txt
echo "STARTING APPLICATION" >> rebooter_log.txt
date >> rebooter_log.txt

# Avoid too fast rebooting if python fails below
sleep 120

# Run application
sudo -u anders /usr/bin/python3 firebase_rebooter.py

echo "REBOOTING" >> rebooter_log.txt
date >> rebooter_log.txt

reboot
