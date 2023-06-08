import system.Logger
from system.Program import Program
import time
import random
import system.PTRS

class test(Program):
    def __init__(self, id = None, draw = False):
        super().__init__(id, True)

    def start(self):
        self.button = system.PTRS.Button(0.25,0.25,0.5,0.5,lambda: print("button callback"), "Test")

    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
                if event is Events.StopEvent:
                    self._do_stop()
        except IndexError:
            pass
        print("test thought")
        time.sleep_ms(10000)

    def draw(self, buff):
        buff.fill(0)
        for a in range(10):
            buff.line(random.randint(0,1000) / 1000.0,random.randint(0,1000) / 1000.0,random.randint(0,1000) / 1000.0,random.randint(0,1000) / 1000.0,0xffff)
        self.button.draw(buff)
