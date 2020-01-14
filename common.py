from datetime import datetime

class Common:
    @classmethod
    def getCurrentUTCTime(cls):
        return datetime.now().isoformat() + "Z"

