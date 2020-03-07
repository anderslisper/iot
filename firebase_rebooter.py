from device_config import DeviceConfig
import pyrebase
import json
import time
from datetime import datetime
import json
import os
import sys
import threading

class FirebaseRebooter:
    def __init__(self, device_config):
        with open('firebase.json') as f:
            self.config = json.load(f)

        self.deviceid = device_config.deviceid
        self.hub = pyrebase.initialize_app(self.config['db_config'])
        self.login()
        self.lock = threading.Lock()
        print("Running")

    def store_logs(self, name):
        storage = self.hub.storage()

        storage.child("iot_log.txt").put("iot_log.txt", self.user['idToken'])
        url = storage.child("iot_log.txt").get_url(self.user['idToken'])
        print("iot_log.txt URL: " + str(url))

        storage.child("rebooter_log.txt").put("rebooter_log.txt", self.user['idToken'])
        url = storage.child("rebooter_log.txt").get_url(self.user['idToken'])
        print("rebooter_log.txt URL: " + str(url))

    def run(self):
        retry = 60
        (self.org_state, self.org_getlogs) = self.read_reboot()
        while self.org_state == None:
            print("Reboot state fetch failed. Retrying in 10s")
            time.sleep(10)
            retry -= 1
            if (retry == 0):
                print("Max number of fails. Rebooting now.")
                sys.exit()
            (self.org_state, self.org_getlogs) = self.read_reboot()
        
        self.reboot = False
        self.getlogs = True
        self.kick = True
        self.missed_kicks = 0
        
        x = threading.Thread(target=self.reboot_poller, args=(1,), daemon=True)
        x.start()
        
        while True:
            time.sleep(10)
            with self.lock:
                if (self.reboot == True):
                    print("Reboot ordered")
                    break
                if (self.getlogs == True):
                    x = threading.Thread(target=self.store_logs, args=(1,), daemon=True)
                    x.start()
                    self.getlogs = False
                if (self.kick == True):
                    self.missed_kicks = 0
                    self.kick = False
                else:
                    self.missed_kicks += 1
                    print("Missed kick #" + str(self.missed_kicks))
                    if (self.missed_kicks > 10):
                        print("Max number of missed kicks. Rebooting")
                        break

    def reboot_poller(self, name):
        while True:
            time.sleep(10)
            (state, getlogs) = self.read_reboot()
            if state != None:
                #print("Org: " + self.org_state + ", new:" + state, " getlogs: " + self.org_getlogs + ", new: " + getlogs)
                with self.lock:
                    if getlogs != self.org_getlogs:
                        self.org_getlogs = getlogs
                        self.getlogs = True
                    if state == self.org_state:
                        self.kick = True
                    else:
                        self.reboot = True

    # Read reboot order from cloud
    def read_reboot(self):
        #print("FIREBASE: read_state")
        self.refresh_token()

        user = self.user
        reboot = None
        getlogs = None
        
        if user is not None:
            try:
                # Get a reference to the database service
                db = self.hub.database()
                
                reboot = db.child(self.hub_root, 'reboot').get(token=user['idToken']).val()
                getlogs = db.child(self.hub_root, 'getlog').get(token=user['idToken']).val()
                #print(new_state)
            except Exception as e:
                print("FIREBASE: read_reboot operation failed.")
                print(e)
        else:
            print("Not logged in. Reboot state not fetched at {}".format(datetime.now()))
        
        #print("Reboot: " + str(reboot))
        
        return (reboot, getlogs)

    # Login to Firebase
    def login(self):
        # Get a reference to the auth service
        print("FIREBASE login")
        try:
            user = self.hub.auth().sign_in_with_email_and_password(self.config['user'], self.config['password'])
            self.user = user
            self.hub_root = 'users' + '/' + user['localId'] + '/' + self.deviceid
        except Exception as e:
            self.user = None
            print("FIREBASE: Login failed.")
            print(e)

    # Refresh Firebase token to keep connection alive
    def refresh_token(self):
        #print("FIREBASE: refresh_token")
        try:
            refresh = self.hub.auth().refresh(self.user['refreshToken'])
            self.user['refreshToken'] = refresh['refreshToken']
            self.user['idToken'] = refresh['idToken']
        except Exception as e:
            print("FIREBASE: Refresh token failed.")
            print(e)
            self.login()
            

# Main program
device_config = DeviceConfig()
if device_config.logfile is not None:
    sys.stdout = open("rebooter_log.txt", "a")

try:
    hub = FirebaseRebooter(device_config)
    hub.run()
except Exception as e:
    print("Exception: " + str(e))