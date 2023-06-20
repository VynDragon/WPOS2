import Single
from system.Program import Program
import PTRS

import time



class wifi_settings(Program):
    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)
        self.nb = 0
        self.connection_error = False
        self.tested_wifi = False

    def start(self):
        self.sObject = Single.Settings.getSettingObject(Single.Settings.wifi)
        if not Single.Hardware.acquireWifi():
            raise Exception("Couldnt acquire wifi")
        self.wifi = Single.Hardware.initWifi_STA()
        self.wifi.active(True)
        self.networks_scan = self.wifi.scan()
        self.networks = [n[0].decode("utf-8") for n in self.networks_scan]  # predecode Bytes of ssid, wifi SSID can be UTF-8!
        self.wifi.active(False)
        self.button1 = PTRS.Button(0.0,0.0,0.25,0.25, self.previous,"Previous")
        self.button2 = PTRS.Button(0.75,0.0,0.25,0.25, self.next,"Next")
        self.buttonTest = PTRS.Button(0.0,0.80,0.4,0.20, self.test_wifi, "Test Wifi")
        self.textfield = PTRS.TextField(0.05,0.5,0.9,0.2, "", True, self.text_changed)
        self.update_textfield()


    def stop(self):
        Single.Hardware.releaseWifi()

    def update_textfield(self):
        if self.sObject != None:
            if len(self.networks) > self.nb and self.nb > -1:
                dic = self.sObject.get(self.networks[self.nb])
                if dic:
                    self.textfield.value = self.sObject[self.networks[self.nb]]
                    return
        self.textfield.value = ""



    def next(self):
        self.nb += 1
        if self.nb >= len(self.networks):
            self.nb = 0
        self.update_textfield()

    def previous(self):
        self.nb -= 1
        if self.nb < 0:
            self.nb = len(self.networks) - 1
        self.update_textfield()

    def text_changed(self):
        if self.sObject == None:
            self.sObject = {}
        if self.textfield.value == "":
            if self.sObject.get(self.networks[self.nb]):
                self.sObject.pop(self.networks[self.nb])
        else:
            self.sObject[self.networks[self.nb]] = self.textfield.value
        Single.Settings.saveSettingObject(Single.Settings.wifi, self.sObject) # in this program we only call the textfield's event from think so this is fine (it will be done in the think thread of this program)

    def test_wifi(self):
        self.wifi.active(True)
        self.wifi.connect(self.networks[self.nb], self.textfield.value)
        waited = 0
        while not self.wifi.isconnected() and waited < 10:
            time.sleep_ms(1000)
            waited += 1
        if waited >= 10:
            self.connection_error = True
            self.tested_wifi = False
            self.wifi.active(False)
            return
        self.ifconfig = self.wifi.ifconfig()
        self.connection_error = False
        self.tested_wifi = True
        self.wifi.active(False)


    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
                self.button1.event(event)
                self.button2.event(event)
                self.textfield.event(event)
                self.buttonTest.event(event)
        except IndexError:
            pass
        time.sleep_ms(250)


    @micropython.native
    def draw(self, buff):
        buff.fill(0)
        self.button1.draw(buff)
        self.button2.draw(buff)
        self.button2.draw(buff)
        self.textfield.draw(buff)
        self.buttonTest.draw(buff)
        if self.connection_error:
            buff.text("Connection Failed", 0.4, 0.8, Single.DEFAULT_TEXT_COLOR)
        if self.tested_wifi:
            buff.text(self.ifconfig[0], 0.4, 0.8, Single.DEFAULT_TEXT_COLOR)
            buff.text(self.ifconfig[1], 0.4, 0.8 + Single.DEFAULT_TEXT_RATIO_INV, Single.DEFAULT_TEXT_COLOR)
            buff.text(self.ifconfig[2], 0.4, 0.8 + Single.DEFAULT_TEXT_RATIO_INV * 2, Single.DEFAULT_TEXT_COLOR)
            buff.text(self.ifconfig[3], 0.4, 0.8 + Single.DEFAULT_TEXT_RATIO_INV * 3, Single.DEFAULT_TEXT_COLOR)
        if len(self.networks) > self.nb and self.nb > -1:
            buff.text(self.networks[self.nb], 0.25, 0.1, Single.DEFAULT_TEXT_COLOR)

