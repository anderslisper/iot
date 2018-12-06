from device_config import DeviceConfig
import pyrebase
import json
import time
import datetime
import json

class Firebase:
    def __init__(self, application, device_config):
        self.application = application

        with open('firebase.json') as f:
            self.config = json.load(f)

        self.deviceid = device_config.deviceid
        self.hub = pyrebase.initialize_app(self.config['db_config'])
        self.FIREBASE_DEVICE_TWIN_POLL_TIME = 5*60 # Must be shorter than token lease time (1h)
        self.token_renewal_time = -10000
        self.desired_state = None
        self.login()

    # Keep cloud connection open
    def kick(self):
        print("FIREBASE: kick")
        elapsed = time.monotonic() - self.token_renewal_time
        if elapsed > self.FIREBASE_DEVICE_TWIN_POLL_TIME:
            self.read_state() # Implicit refresh_token

    # Post telemetry to cloud
    def post_telemetry(self, telemetry):
        print("FIREBASE: post_telemetry")
        self.refresh_token()
        user = self.user
        
        if user is not None:
            try:
                for key,obj in telemetry.copy().items():
                    if key[0] == "$":
                        telemetry[key[1:]] = telemetry.pop(key)
                
                # Get a reference to the database service
                db = self.hub.database()

                # Pass the user's idToken to the push method
                results = db.child(self.hub_root, 'telemetry').push(telemetry, user['idToken'])
                print("FIREBASE: Telemetry stored as hub id: {}".format(results["name"]))
            except Exception as e:
                print("FIREBASE: Post operation failed.")
                print(e)
        else:
            print("FIREBASE: Not logged in. No telemetry sent. @ {}".format(datetime.datetime.now()))

    # Read desired state from cloud
    def read_state(self, bank='desired'):
        print("FIREBASE: read_state")
        self.refresh_token()
        user = self.user
        new_state = None
        
        if user is not None:
            try:
                # Get a reference to the database service
                db = self.hub.database()

                new_state = dict(db.child(self.hub_root,'device_twin', bank).get(token=user['idToken']).val())
                #print(device_twin)
            except Exception as e:
                print("FIREBASE: read_desired_state operation failed.")
                print(e)
        else:
            print("Not logged in. Device twin not fetched at {}".format(datetime.datetime.now()))

        if new_state != self.desired_state and new_state != None:
            self.desired_state = new_state
            if self.application:
                self.application.device_twin_update(new_state)
        
    # Report current state to cloud
    def update_reported_state(self, device_twin, bank='reported'):
        print("FIREBASE: update_reported_state")
        self.refresh_token()
        user = self.user
        
        if user is not None:
            try:
                # Get a reference to the database service
                db = self.hub.database()

                db.child(self.hub_root, 'device_twin', bank).set(device_twin, user['idToken'])
            except Exception as e:
                print("FIREBASE: store_twin operation failed.")
                print(e)
        else:
            print("FIREBASE: Not logged in. No device twin stored. @ {}".format(datetime.datetime.now()))

        return device_twin

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
        print("FIREBASE: refresh_token")
        self.token_renewal_time = time.monotonic()    
        try:
            refresh = self.hub.auth().refresh(self.user['refreshToken'])
            self.user['refreshToken'] = refresh['refreshToken']
            self.user['idToken'] = refresh['idToken']
        except Exception as e:
            print("FIREBASE: Refresh token failed.")
            print(e)
            self.login()
            

if __name__ == '__main__':
    device_config = DeviceConfig()
    hub = Firebase(None, device_config)
    hub.deviceid = "test"
    
    test = {}
    test["$version"] = 17
    test["oj"] = {}
    test["oj"]["a"] = "Anders"
    test["oj"]["b"] = "Lisper"
    
    hub.post_telemetry(test)
    
    hub.update_reported_state(test, bank='desired')
    hub.read_state()   # Updates hub.desired_state
    print(hub.desired_state)
    print(hub.desired_state == test)
    
    hub.update_reported_state(test)
    hub.read_state(bank='reported')
    print(hub.desired_state)
    print(hub.desired_state == test)
    