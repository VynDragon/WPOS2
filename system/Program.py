
import _thread
from collections import deque
import Events
import time

class Program:
    def __init__(self, id = None, draw = False):
        self._lock = _thread.allocate_lock()
        self._draw = draw
        self.input = deque((), 5)
        if id == None:
            self.id = _thread.get_ident()
        else:
            self.id = id

    def _do_think(self):# expected to be called from its own thread whenever possible.
        if self._lock.acquire():
            self.think()
            self._lock.release()

    def _do_draw(self, WPFramebuffer): #same as think but nonblocking, expected to be called from display thread every X time
        if self._draw:
            self.draw(WPFramebuffer)

    def _do_stop(self):
        self.stop()
        _thread.exit()

    def event(self, event):
        self.input.append(event)

    def think(self):
        try:
            while True:
                event = self.input.popleft()
                if event is Events.StopEvent:
                    self._do_stop()
        except IndexError:
            pass
        time.sleep_ms(1000)

    def draw(self, WPFramebuffer):
        pass

    def start(self):
        pass

    def stop(self):
        pass
