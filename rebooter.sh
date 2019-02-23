#!/bin/bash
cd /home/anders/gundbyniot

while [ ! -e "reboot.now" ]
do
	sleep 60
done

rm -f "reboot.now"
echo "Reboot now"
reboot
