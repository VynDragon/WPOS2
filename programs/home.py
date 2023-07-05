import Single
from system.Program import Program
import PTRS
import Events
import _thread
import time, ntptime, math
from fonts import led_32


def mode1_outline(buff):
    buff.rect(0.1, 0.1, 0.8, 0.8, Single.DEFAULT_BG_COLOR, True)
    buff.rect(0.1, 0.1, 0.8, 0.8, Single.DEFAULT_OUTLINE_COLOR, False)


class home(Program):

    cycle_sleep = 50

    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)
        self.mode = 0
        self.percent = 0
        self.mv = 0
        self.ma = 0
        self.lastSeconds = 0
        self.lastGraphUpdate = time.ticks_ms()
        self.mode1_context = None
        self.mode1_lock = _thread.allocate_lock()
        self.lastSleepCounterIncrease = time.ticks_ms()


    def start(self):
        if not Single.Hardware.acquireWifi():
            raise Exception("Couldnt acquire wifi")
        wifi = Single.Hardware.connectWifi()
        if wifi:
            Single.Hardware.sync_ntp()
        Single.Hardware.releaseWifi()
        self.ampgraph = PTRS.Graph(0.0, Single.DEFAULT_TEXT_RATIO_INV + 1/Single.Hardware.DISPLAY_HEIGHT, 1.0, 0.22)
        self.sleep_counter = 0
        Single.Kernel.thread_0 = self.thread

    def stop(self):
        pass

    def mode1_switch(self, thread_id):
        if Single.Kernel.switchProgram(thread_id):
            self.mode = 0
        else:
            Single.Kernel.event(Events.RunEvent("popup", "cannot switch to program " + str(thread_id)))

    def mode1_stop(self, thread_id):
        Single.Kernel.event(Events.StopEvent(thread_id))
        self.mode = 0

    def init_mode1(self):
        self.mode1_lock.acquire()
        self.mode1_context = []
        outline = PTRS.Generic()
        outline.draw = mode1_outline
        self.mode1_context.append(outline)
        programs = Single.Kernel.getPrograms()
        pix_x = 1.0 / Single.Hardware.DISPLAY_WIDTH
        pix_y = 1.0 / Single.Hardware.DISPLAY_HEIGHT
        program_y = 0.1 + pix_y
        for program in programs:
            thread_copy = program.thread # copy not assignement so lambda remembers the right number
            classname_copy = "{}#{}".format(program.__class__.__name__, thread_copy) # basically program name
            self.mode1_context.append(PTRS.Button(0.1 + pix_x, program_y, 0.6, Single.DEFAULT_TEXT_RATIO_INV * 4, callback = lambda: self.mode1_switch(thread_copy) , name = classname_copy))
            self.mode1_context.append(PTRS.Button(0.7, program_y, 0.2 - pix_x, Single.DEFAULT_TEXT_RATIO_INV * 4, callback = lambda: self.mode1_stop(thread_copy) , name = "X"))
            program_y += Single.DEFAULT_TEXT_RATIO_INV * 4
        self.mode1_lock.release()
        self.mode = 1


    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
                self.sleep_counter = 0
                if isinstance(event, Events.GestureEvent):
                    if self.mode != 1 and event.gesture == 2:
                        Single.Kernel.switchProgram(self.id)
                        self.init_mode1()
                    elif self.mode == 1 and event.gesture == 3:
                        self.mode = 0
                        Single.Kernel.switchProgram()
                elif self.mode == 1:
                    for elem in self.mode1_context:
                        elem.event(event)
        except IndexError:
            if time.ticks_diff(time.ticks_add(self.lastSleepCounterIncrease, 100), time.ticks_ms()) <= 0:
                self.sleep_counter += 1
                self.lastSleepCounterIncrease = time.ticks_ms()

        if self.sleep_counter > self.cycle_sleep:
            Single.Hardware.lightsleep(1000, False, self.sleep_callback)
            self.sleep_counter = 0
        if time.ticks_diff(time.ticks_add(self.lastGraphUpdate, 100), time.ticks_ms()) <= 0: # ever 100 ms update graph and battery stuffs (we dont care to do it precisely)
            self.percent = Single.Hardware.get_battery_gauge()
            self.mv = Single.Hardware.get_battery_voltage()
            self.ma = Single.Hardware.get_battery_current()
            if Single.Hardware.WatchVersion == 3:
                self.ampgraph.add_point(self.mv / 4200.0) # trace voltage instead we cant measure current
            else:
                self.ampgraph.add_point(self.ma / 80.0)
            self.lastGraphUpdate = time.ticks_ms()
        time.sleep(0)

    def sleep_callback(self):
        time.sleep(0)
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


    def rightometer(self, buff, px, py):
        buff.rect(px - 0.225, py - 0.225, 0.5, 0.5, Single.DEFAULT_BG_COLOR, True)
        x, y, z = Single.Hardware.imu.read_accel()
        buff.ellipse(px, py, 0.2, 0.2, Single.DEFAULT_OUTLINE_COLOR)
        buff.ellipse(px, py, 0.05, 0.05, Single.DEFAULT_OUTLINE_COLOR)
        # at 8g sensitivity '256 LSB/G', 1g = 9.80 m/s2, me thinks those are firmware dependant because i had to guess the right one
        gx = 0
        gy = 0
        if Single.Hardware.WatchVersion == 1:
            gx = y / 1024.0
            gy = - x / 1024.0
        elif Single.Hardware.WatchVersion == 0:
            gx = - x / 1024.0
            gy = - y / 1024.0
        elif Single.Hardware.WatchVersion == 3:
            gx = y / 1024.0
            gy = - x / 1024.0
        bubblex = gx * 0.2
        bubbley = gy * 0.2 # range 1 G
        if abs(bubblex) > 0.2:
            bubblex = ((bubblex > 0) - (bubblex < 0)) * 0.2
        if abs(bubbley) > 0.2:
            bubbley = ((bubbley > 0) - (bubbley < 0)) * 0.2
        bubblex += px
        bubbley += py
        buff.ellipse(bubblex, bubbley, 0.04, 0.04, Single.DEFAULT_TEXT_COLOR, True)
        buff.text("{:.3f} G (lateral)".format(math.sqrt(gx*gx+gy*gy)), 0.0, 1.0 - Single.DEFAULT_TEXT_RATIO_INV, Single.DEFAULT_TEXT_COLOR)

    @micropython.native
    def draw_watchface(self, buff):
        #buff.fill(0) # that doesnt set a boundary
        buff.rect(0, 0, 1.0, Single.DEFAULT_TEXT_RATIO_INV , Single.DEFAULT_BG_COLOR, True)
        #buff.hline(0.0, 0.25, 1.0, Single.DEFAULT_OUTLINE_COLOR)
        curtime = time.gmtime()
        if curtime[5] != self.lastSeconds: # update those only once per second
            onthtw = 1.0/(Single.Hardware.DISPLAY_WIDTH/32.0)
            onthth = 1.0/(Single.Hardware.DISPLAY_HEIGHT/32.0)
            buff.rect(0, Single.DEFAULT_TEXT_RATIO_INV, 1.0, 0.5 - Single.DEFAULT_TEXT_RATIO_INV_2, Single.DEFAULT_BG_COLOR, True)
            buff.hline(0.0, 0.25 + onthth, 1.0, Single.DEFAULT_OUTLINE_COLOR)
            self.ampgraph.draw(buff)
            if Single.Hardware.charging():
                buff.text("CHARGING", 0.02, Single.DEFAULT_TEXT_RATIO_INV * 2, Single.DEFAULT_TEXT_COLOR)
            buff.text2("{:0>2d}:{:0>2d}:{:0>2d}".format(curtime[3], curtime[4], curtime[5]), 0.0 + onthtw * 1.0, 0.25, led_32)
            self.lastSeconds = curtime[5]
        if self.percent < 101:
            buff.text("{}% {}mV {}mA".format(int(self.percent), self.mv, self.ma), 0.0, 0.0, Single.DEFAULT_TEXT_COLOR)
        else:
            buff.text("-(= {}mV {}mA".format(int(self.percent), self.mv, self.ma), 0.0, 0.0, Single.DEFAULT_TEXT_COLOR)
        buff.hline(0.0, Single.DEFAULT_TEXT_RATIO_INV, 1.0, Single.DEFAULT_OUTLINE_COLOR)
        self.rightometer(buff, 0.25, 0.75)
        buff.text("{}/{}/{}".format(curtime[2],curtime[1],curtime[0]), 0.5 - Single.DEFAULT_TEXT_RATIO_INV_2 * 10.0,0.5, Single.DEFAULT_TEXT_COLOR)

    @micropython.native
    def draw(self, buff):
        if self.mode == 0:
            self.draw_watchface(buff)
        if self.mode == 1:
            buff.fill(0) # remeber this doesnt set boundaries of the fb so
            if self.mode1_lock.acquire():
                for elem in self.mode1_context:
                    elem.draw(buff)
                self.mode1_lock.release()

