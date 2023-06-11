import system.Logger
from system.Program import Program
import time
import random
import system.PTRS
import Events

class test(Program):
    def __init__(self, id = None, draw = False):
        super().__init__(id, True)

    def start(self):
        self.button = system.PTRS.Button(0.25,0.25,0.5,0.5,lambda: print("button callback"), "Test")
        super().start()

    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
                if isinstance(event, Events.StopEvent):
                    self._do_stop()
                else:
                    self.button.event(event)
        except IndexError:
            pass
        #if __debug__:
        #    print("test thought")
        time.sleep_ms(1000)

    def event(self, event):
        if isinstance(event, Events.TouchEvent):
            self.button.event(event)
        else:
            super().event(event)


    @micropython.native
    def draw(self, buff):
        #for a in range(10):
        #    buff.line(random.randint(0,1000) / 1000.0,random.randint(0,1000) / 1000.0,random.randint(0,1000) / 1000.0,random.randint(0,1000) / 1000.0,0xffff)
        self.button.draw(buff)
