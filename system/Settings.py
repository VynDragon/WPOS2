import json, os, _thread


class Settings:

    wifi = "Wifi"
    home = "Home"

    def __init__(self):
        try:
            state = os.stat("/settings")
        except:
            os.mkdir("/settings")
        state = os.stat("/settings")
        self._lock = _thread.allocate_lock() # so we dont read or write from same file from different threads
        return

    def getSettingObject(self, name):
        self._lock.acquire()
        try:
            with open("/settings/" + name + ".json") as f:
                sObject = json.load(f)
                self._lock.release()
                return sObject
        except Exception as e:
            print(e)
            self._lock.release()
        return None

    def saveSettingObject(self, name, sObject):
        self._lock.acquire()
        try:
            with open("/settings/" + name + ".json", 'w') as f:
                ret = json.dump(sObject, f)
                self._lock.release()
                return ret
        except Exception as e:
            print(e)
            self._lock.release()

