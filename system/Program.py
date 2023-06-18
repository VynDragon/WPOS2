
import _thread
from collections import deque
import Events
import time

class Program:
    def __init__(self, id = None, draw = False, arg = None):
        self._lock = _thread.allocate_lock()
        self._draw = draw
        self.ready = False
        self.input = deque((), 5)
        self.should_exit = False
        self.thread = _thread.get_ident()
        if id == None:
            self.id = _thread.get_ident()
        else:
            self.id = id

    def _do_think(self):# expected to be called from its own thread whenever possible.
        if not self.ready:
            time.sleep_ms(100)
            return
        if self._lock.acquire():
            self.think()
            self._lock.release()

    @micropython.native
    def _do_draw(self, WPFramebuffer): #same as think but nonblocking, expected to be called from display thread every X time
        if self._draw and self.ready:
            self.draw(WPFramebuffer)

    def _do_stop(self):
        self.stop()
        if _thread.get_ident() == self.thread:
            _thread.exit()
        self.should_exit = True

    def event(self, event): #fast event handling from kernel thread, least amount of code possible in there please
        self.input.append(event)

    def think(self):
        try:
            while True:
                event = self.input.popleft()
        except IndexError:
            pass
        time.sleep_ms(1000)

    def draw(self, WPFramebuffer):
        pass

    def _do_start(self):
        self.start()
        self.ready = True

    def start(self):
        pass

    def stop(self):
        pass
