import time
import datetime
import requests
import json

class Weather:

    def __init__(self):
        self.WEATHER_UPDATE_INTERVAL = 60*60
        self.weather_request = "http://api.openweathermap.org/data/2.5/weather?lat=60.08&lon=17.9&units=metric&APPID=7887aae3408a6f84623247cc0aface84"
        self.last_fetched_at = -10000
        self.current = None
        
    def get(self):
        elapsed = time.monotonic() - self.last_fetched_at
        if elapsed > self.WEATHER_UPDATE_INTERVAL:
            self.last_fetched_at = time.monotonic()
            r = requests.get(self.weather_request)
            if r.status_code == 200:
                weather = r.json()
                self.current = {}
                self.current["fetched_utctime"] = datetime.datetime.now().isoformat() 
                self.current["temp"]            = weather["main"]["temp"]
                self.current["wind"]            = weather["wind"]["speed"]
                print("Weather fetched from openweather at {}".format(self.current["fetched_utctime"]))
            else:
                print("openweathermap API returned ERROR code {}".format(r.status_code))
                
        return self.current

if __name__ == '__main__':
    w = Weather()
    w.WEATHER_UPDATE_INTERVAL = 10
    print(w.get())
    time.sleep(5)
    print(w.get())
    time.sleep(10)
    print(w.get())
    
	