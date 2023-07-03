import system.Logger
from system.Program import Program
import time, machine
import random
import PTRS
import Events
import Single
class test(Program):
    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)
        self.context = 0



    def slider_callback(self):
        self.sObject_hw["Backlight"] = int(self.context_1[0].value * 65535)
        self.pwm_backlight.duty_u16(self.sObject_hw["Backlight"])

    def save_context_1(self):
        Single.Settings.saveSettingObject(Single.Settings.hardware, self.sObject_hw)

    def next_context(self):
        if self.context < len(self.contexts):
            self.context += 1

    def previous_context(self):
        if self.context > 0:
            self.context -= 1

    def start(self):
        self.sObject_hw = Single.Settings.getSettingObject(Single.Settings.hardware)
        if self.sObject_hw == None:
            self.sObject_hw = {}
        self.contexts =[]
        self.context_1 = []
        def_value = 8192/65535
        if self.sObject_hw.get("Backlight") != None:
            def_value = self.sObject_hw["Backlight"] / 65535
        self.context_1.append(PTRS.Slider(0.1,0.1,0.8,0.20, def_value, self.slider_callback,"Backlight"))
        self.context_1.append(PTRS.Button(0.3, 0.75, 0.3, 0.25, callback = self.save_context_1, name = "Save"))
        self.context_1.append(PTRS.Button(0.6, 0.75, 0.3, 0.25, callback = self.next_context, name = "Next"))
        self.context_1.append(PTRS.Button(0.6, 0.75, 0.3, 0.25, callback = self.previous_context, name = "Previous"))
        self.contexts.append(self.context_1)

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
        buff.fill(0)
        for element in self.contexts[self.context]:
                element.draw(buff)

