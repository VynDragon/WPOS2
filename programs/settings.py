import system.Logger
from system.Program import Program
import time, machine
import random
import PTRS
import Events
import Single

def context_1_generic_draw(buff):
    buff.text("Backlight", 0.5, 0.15, Single.DEFAULT_TEXT_COLOR)
    buff.text("GMT", 0.1, 0.62, Single.DEFAULT_TEXT_COLOR)


class settings(Program):
    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)
        self.context = 0



    def slider_callback(self):
        self.sObject_hw["Backlight"] = int(max(self.context_1[0].value * 60000 - 2000,0))
        Single.Hardware.pwm_backlight.duty_u16(self.sObject_hw["Backlight"])

    def gmt_update(self):
        self.sObject_general["GMT"] = int(self.context_1[1].value)

    def freq_set(self, freq):
        if freq == 160000000 or freq == 240000000 or freq == 80000000:
            self.sObject_hw["Freq"] = int(freq)
            machine.freq(freq)
            if freq == 240000000:
                self.context_2[2].value = True
                self.context_2[1].value = False
                self.context_2[0].value = False
            elif freq == 160000000:
                self.context_2[2].value = False
                self.context_2[1].value = True
                self.context_2[0].value = False
            else:
                self.context_2[2].value = False
                self.context_2[1].value = False
                self.context_2[0].value = True


    def save_context_1(self):
        Single.Settings.saveSettingObject(Single.Settings.hardware, self.sObject_hw)
        if self.sObject_general["GMT"] > -13 and self.sObject_general["GMT"] < 13:
            Single.Settings.saveSettingObject(Single.Settings.general, self.sObject_general)

    def save_context_2(self):
        Single.Settings.saveSettingObject(Single.Settings.hardware, self.sObject_hw)


    def next_context(self):
        if self.context < len(self.contexts) - 1:
            self.context += 1

    def previous_context(self):
        if self.context > 0:
            self.context -= 1

    def start(self):
        self.sObject_hw = Single.Settings.getSettingObject(Single.Settings.hardware)
        if self.sObject_hw == None:
            self.sObject_hw = {}
        self.sObject_general = Single.Settings.getSettingObject(Single.Settings.general)
        if self.sObject_general == None:
            self.sObject_general = {}
        gmt = self.sObject_general.get("GMT")
        if gmt == None:
            gmt = 0
        self.contexts =[]
        self.context_1 = []
        def_value = 8192/65535
        if self.sObject_hw.get("Backlight") != None:
            def_value = self.sObject_hw["Backlight"] / 65535
        self.context_1.append(PTRS.Slider(0.1,0.1,0.8,0.20, def_value, self.slider_callback,"Backlight"))
        self.context_1.append(PTRS.TextField(0.3, 0.5, 0.4, 0.25, str(gmt), False, self.gmt_update))
        self.context_1.append(PTRS.Button(0.3, 0.75, 0.4, 0.25, callback = self.save_context_1, name = "Save"))
        self.context_1.append(PTRS.Button(0.7, 0.75, 0.3, 0.25, callback = self.next_context, name = "Next"))
        self.context_1.append(PTRS.Button(0.0, 0.75, 0.3, 0.25, callback = self.previous_context, name = "Previous"))
        context_1_generic = PTRS.Generic()
        context_1_generic.draw = context_1_generic_draw
        self.context_1.append(context_1_generic)
        self.contexts.append(self.context_1)
        self.context_2 = []
        def_value = 80000000
        if self.sObject_hw.get("Freq") != None:
            def_value = self.sObject_hw["Freq"]
        self.context_2.append(PTRS.Switch(0.0, 0.0, 0.5, 0.25, False, lambda: self.freq_set(80000000), "80Mhz"))
        self.context_2.append(PTRS.Switch(0.0, 0.25, 0.5, 0.25, False, lambda: self.freq_set(160000000), "160Mhz"))
        self.context_2.append(PTRS.Switch(0.0, 0.5, 0.5, 0.25, False, lambda: self.freq_set(240000000), "240Mhz"))
        if def_value == 240000000:
            self.context_2[2].value = True
        elif def_value == 160000000:
            self.context_2[1].value = True
        else:
            self.context_2[0].value = True
        self.context_2.append(PTRS.Button(0.3, 0.75, 0.4, 0.25, callback = self.save_context_2, name = "Save"))
        self.context_2.append(PTRS.Button(0.7, 0.75, 0.3, 0.25, callback = self.next_context, name = "Next"))
        self.context_2.append(PTRS.Button(0.0, 0.75, 0.3, 0.25, callback = self.previous_context, name = "Previous"))
        self.contexts.append(self.context_2)

    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
                for element in self.contexts[self.context]:
                    element.event(event)
        except IndexError:
            pass
        time.sleep(0)

    @micropython.native
    def draw(self, buff):
        buff.rect(0.0,0.0,1.0,1.0, Single.DEFAULT_BG_COLOR, True)
        for element in self.contexts[self.context]:
                element.draw(buff)

