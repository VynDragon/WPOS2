import Single
from system.Program import Program
import PTRS

import time, ntptime
import square_32



class home(Program):
    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)

    def start(self):
        if not Single.Hardware.acquireWifi():
            raise Exception("Couldnt acquire wifi")
        wifi = Single.Hardware.connectWifi()
        if wifi:
            Single.Hardware.sync_ntp()
        Single.Hardware.releaseWifi()


    def stop(self):
        pass


    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
        except IndexError:
            pass
        time.sleep_ms(250)


    @micropython.native
    def draw(self, buff):
        buff.fill(0)
        buff.text2(str(time.gmtime()[5]), 0.5, 0.5, square_32)
        #buff.text(self.networks[self.nb], 0.25, 0.1, Single.DEFAULT_TEXT_COLOR)


