import system.Logger
from system.Program import Program
import time, machine
import random
import PTRS
import Events
import Single

def context_1_generic_draw(buff):
    buff.text("Tool to free", 0.0, 0.5, Single.DEFAULT_TEXT_COLOR)
    buff.text("resources grabbed by", 0.0, 0.5 + Single.DEFAULT_TEXT_RATIO_INV, Single.DEFAULT_TEXT_COLOR)
    buff.text("crashed programs", 0.0, 0.5 + Single.DEFAULT_TEXT_RATIO_INV * 2, Single.DEFAULT_TEXT_COLOR)

class free_hardware(Program):
    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)
        self.context = 0



    def free_wifi(self):
        Single.Hardware.releaseWifi(True)

    def free_audio(self):
        Single.Hardware.releaseAudio(True)

    def exit(self):
        Single.Kernel.event(Events.StopEvent(self.thread))

    def start(self):
        self.contexts =[]
        self.context_1 = []
        self.context_1.append(PTRS.Button(0.0, 0.0, 0.5, 0.5, callback = self.free_wifi, name = "Free Wifi"))
        self.context_1.append(PTRS.Button(0.5, 0.0, 0.5, 0.5, callback = self.free_audio, name = "Free Audio"))
        self.context_1.append(PTRS.Button(0.5, 0.5, 0.5, 0.5, callback = self.exit, name = "Exit"))
        context_1_generic = PTRS.Generic()
        context_1_generic.draw = context_1_generic_draw
        self.context_1.append(context_1_generic)
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
        buff.rect(0.0,0.0,1.0,1.0, Single.DEFAULT_BG_COLOR, True)
        for element in self.contexts[self.context]:
                element.draw(buff)

