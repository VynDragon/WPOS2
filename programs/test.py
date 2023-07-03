import system.Logger
from system.Program import Program
import time, machine
import random
import system.PTRS
import Events
import Single
import axp202_constants

class test(Program):
    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)
        self.clear = False
        self.started = False

    def button_pressed(self):
        Single.Hardware.lightsleep(5000)
        self.clear = True

    def slider_callback(self):
        Single.Hardware.pmu.setLDO2Voltage(self.slider.value * 900 + 2400)
        #Single.DEFAULT_COLOR = int(self.slider.value * 0xFFFF)

    def start(self):
        self.button = system.PTRS.Button(0.0,0.0,0.5,0.5, self.button_pressed,"Test")
        self.slider = system.PTRS.Slider(0.1,0.75,0.8,0.20, 0.5, self.slider_callback,"Test")
        self.switch = system.PTRS.Switch(0.5,0.0,0.5,0.5, False, self.button_pressed,"Test")
        self.textfield = system.PTRS.TextField(0.0,0.55,1.0,0.15)

    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
                self.button.event(event)
                self.slider.event(event)
                self.switch.event(event)
                self.textfield.event(event)
        except IndexError:
            pass
        #if __debug__:
        #    print("test thought")
        time.sleep(0)

    def event(self, event):
        if isinstance(event, Events.TouchEvent):
            self.button.event(event)
            self.slider.event(event)
            self.switch.event(event)
            self.textfield.event(event)
        else:
            super().event(event)


    @micropython.native
    def draw(self, buff):
        if self.clear:
            buff.fill(0)
            self.clear = False
        #for a in range(10):
        #    buff.line(random.randint(0,1000) / 1000.0,random.randint(0,1000) / 1000.0,random.randint(0,1000) / 1000.0,random.randint(0,1000) / 1000.0,0xffff)
        self.button.draw(buff)
        self.slider.draw(buff)
        self.switch.draw(buff)
        self.textfield.draw(buff)
