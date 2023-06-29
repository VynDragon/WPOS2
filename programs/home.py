import Single
from system.Program import Program
import PTRS
import Events

import time, ntptime
import led_32



class home(Program):

    cycle_sleep = 50

    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)
        self.mode = 0
        self.percent = 0
        self.mv = 0
        self.ma = 0

    def start(self):
        if not Single.Hardware.acquireWifi():
            raise Exception("Couldnt acquire wifi")
        wifi = Single.Hardware.connectWifi()
        if wifi:
            Single.Hardware.sync_ntp()
        Single.Hardware.releaseWifi()
        self.ampgraph = PTRS.Graph(0.0, Single.DEFAULT_TEXT_RATIO_INV + 1/Single.Hardware.DISPLAY_HEIGHT, 1.0, 0.22)
        self.sleep_counter = 0

    def stop(self):
        pass


    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
                self.sleep_counter = 0
                if isinstance(event, Events.GestureEvent):
                    if self.mode != 1 and event.gesture == 2: # todo: check if we are front app, if not, become it
                        self.mode = 1
                    elif self.mode == 1 and event.gesture == 3:
                        self.mode = 0
                        pass # todo: switch back to app if we werente front app
        except IndexError:
            self.sleep_counter += 1
        if self.sleep_counter > self.cycle_sleep:
            Single.Hardware.lightsleep(1000, False, self.sleep_callback)
            self.sleep_counter = 0
        self.percent = Single.Hardware.get_battery_gauge()
        self.mv = Single.Hardware.get_battery_voltage()
        self.ma = Single.Hardware.get_battery_current()
        self.ampgraph.add_point(self.ma / 80.0)
        time.sleep_ms(100)

    def sleep_callback(self):
        time.sleep_ms(25) # give it a little time to find its bearing.. i guess?
        self.ma = Single.Hardware.get_battery_current()
        self.ampgraph.add_point(self.ma / 80.0, Single.DEFAULT_BG_COLOR)
        try:
            while True: #event treatment
                event = self.input.popleft()
                if isinstance(event, Events.IMUEvent):
                    if event.int == 32:
                        return False
                elif isinstance(event, Events.PhysButtonEvent):
                    return False

        except IndexError:
            pass
        return True


    @micropython.native
    def draw(self, buff):
        buff.fill(0)
        if self.mode == 0:

            onthtw = 1.0/(Single.Hardware.DISPLAY_WIDTH/32.0)
            onthth = 1.0/(Single.Hardware.DISPLAY_HEIGHT/32.0)
            #buff.hline(0.0, 0.25, 1.0, Single.DEFAULT_OUTLINE_COLOR)
            buff.hline(0.0, 0.25 + onthth, 1.0, Single.DEFAULT_OUTLINE_COLOR)
            self.ampgraph.draw(buff)
            if Single.Hardware.charging():
                buff.text("CHARGING", 0.02, Single.DEFAULT_TEXT_RATIO_INV * 2, Single.DEFAULT_TEXT_COLOR)
            buff.text2("{:0>2d}:{:0>2d}:{:0>2d}".format(time.gmtime()[3], time.gmtime()[4], time.gmtime()[5]), 0.0 + onthtw * 1.0, 0.25, led_32)
            curtime = time.gmtime()
            buff.text("{}/{}/{}".format(curtime[2],curtime[1],curtime[0]), 0.5 - Single.DEFAULT_TEXT_RATIO_INV_2 * 10.0,0.5, Single.DEFAULT_TEXT_COLOR)
            if self.percent < 101:
                buff.text("{}% {}mV {}mA".format(int(self.percent), self.mv, self.ma), 0.0, 0.0, Single.DEFAULT_TEXT_COLOR)
            else:
                buff.text("-(= {}mV {}mA".format(int(self.percent), self.mv, self.ma), 0.0, 0.0, Single.DEFAULT_TEXT_COLOR)
            buff.hline(0.0, Single.DEFAULT_TEXT_RATIO_INV, 1.0, Single.DEFAULT_OUTLINE_COLOR)

        if self.mode == 1:
            pass


