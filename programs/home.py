import Single
from system.Program import Program
import PTRS
import Events
import _thread
import time, ntptime, math
from fonts import led_32
import programs.programs as programs_data
import machine


def mode1_outline(buff):
    buff.rect(0.05, 0.1, 0.9, 0.8, Single.DEFAULT_BG_COLOR, True)
    buff.rect(0.05, 0.1, 0.9, 0.8, Single.DEFAULT_OUTLINE_COLOR, False)


class home(Program):
    sleep_timeout = 10000 #ms

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
        self.mode2_lock = _thread.allocate_lock()
        self.mode2_page = 0


    def start(self):
        if not Single.Hardware.acquireWifi():
            raise Exception("Couldnt acquire wifi")
        wifi = Single.Hardware.connectWifi()
        if wifi:
            Single.Hardware.sync_ntp()
        Single.Hardware.releaseWifi()
        self.ampgraph = PTRS.Graph(0.0, Single.DEFAULT_TEXT_RATIO_INV + 1/Single.Hardware.DISPLAY_HEIGHT, 1.0, 0.22)
        self.open_mode2 = PTRS.Button(0.6, 0.6, 0.3, 0.3, callback = lambda: self.init_mode2() , name = "Programs")
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
            classname= "{}#{}".format(program.__class__.__name__, thread_copy) # basically program name
            self.mode1_context.append(PTRS.Button(0.05 + pix_x, program_y, 0.65, Single.DEFAULT_TEXT_RATIO_INV * 8, callback = lambda thread=thread_copy: self.mode1_switch(thread) , name = classname))
            self.mode1_context.append(PTRS.Button(0.7, program_y, 0.25 - pix_x, Single.DEFAULT_TEXT_RATIO_INV * 8, callback = lambda thread=thread_copy: self.mode1_stop(thread) , name = "X"))
            program_y += Single.DEFAULT_TEXT_RATIO_INV * 8
        self.mode1_lock.release()
        self.mode = 1

    def mode2_run(self, name):
        Single.Kernel.event(Events.RunEvent(name))
        self.mode2_leave()

    def mode2_leave(self):
        self.mode = 0

    def mode2_nextpage(self):
        self.mode2_context = self.mode2_context[0:2]
        self.mode2_page += 1
        if len(programs_data.programs_list) >= self.mode2_page * 4 + 1:
            self.init_mode2_page(self.mode2_page)
        else:
            self.mode2_page = 0

    def init_mode2_page(self, page):
        program_y = 0.0
        leftprogram = min(4, len(programs_data.programs_list) - page*4)
        for program in programs_data.programs_list[page * 4:page*4+leftprogram]:
            self.mode2_context.append(PTRS.Button(0.0, program_y, Single.DEFAULT_TEXT_RATIO_INV * 16.0, 0.25, callback = lambda name=program: self.mode2_run(name) , name = program))
            program_y += 0.25
            if program_y > 1.0:
                program_y = 0.0
            if __debug__:
                print("added:", program, program_y)

    def init_mode2(self):
        self.mode2_lock.acquire()
        self.mode2_context = []
        self.mode2_context.append(PTRS.Button(0.6, 0.6, 0.3, 0.3, callback = lambda: self.mode2_leave(), name = "Programs"))
        self.mode2_context.append(PTRS.Button(0.6, 0.1, 0.3, 0.3, callback = lambda: self.mode2_nextpage(), name = "Next"))
        self.init_mode2_page(self.mode2_page)
        self.mode2_lock.release()
        self.mode = 2


    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
                if isinstance(event, Events.GestureEvent):
                    if self.mode != 1 and event.gesture == 2:
                        Single.Kernel.switchProgram(self.id)
                        self.init_mode1()
                    elif self.mode == 1 and event.gesture == 3:
                        self.mode = 0
                        Single.Kernel.switchProgram()
                elif self.mode == 0:
                    self.open_mode2.event(event)
                elif self.mode == 1:
                    for elem in self.mode1_context:
                        elem.event(event)
                elif self.mode == 2:
                    for elem in self.mode2_context:
                        elem.event(event)
        except IndexError:
            pass

        if time.ticks_diff(time.ticks_add(Single.Kernel.last_event_time, home.sleep_timeout), time.ticks_ms()) <=0 :
            Single.Hardware.lightsleep(1000, False, self.sleep_callback)
        if time.ticks_diff(time.ticks_add(self.lastGraphUpdate, 100), time.ticks_ms()) <= 0: # ever 100 ms update graph and battery stuffs (we dont care to do it precisely)
            self.percent = Single.Hardware.get_battery_gauge()
            self.mv = Single.Hardware.get_battery_voltage()
            self.ma = Single.Hardware.get_battery_current()
            if Single.Hardware.WatchVersion == 3:
                self.ampgraph.add_point(self.percent / 100.0) # trace % instead we cant measure current
            else:
                self.ampgraph.add_point(self.ma / 80.0)
            self.lastGraphUpdate = time.ticks_ms()
        time.sleep(0)

    def sleep_callback(self):
        if not Single.Hardware.WatchVersion > 0: # only if we didnt reset and wait 5 ms for the touch screen to wake up
            time.sleep_ms(5) #let events get there
        if Single.Hardware.WatchVersion == 3:
            self.percent = Single.Hardware.get_battery_gauge()
            self.ampgraph.add_point(self.percent / 100.0) # trace % instead we cant measure current
        else:
            self.ma = Single.Hardware.get_battery_current()
            self.ampgraph.add_point(self.ma / 80.0, Single.DEFAULT_BG_COLOR)
        '''try:
            while True: #event treatment
                event = self.input.popleft()
                if isinstance(event, Events.IMUEvent):
                    if event.int == 32:
                        return False
                elif isinstance(event, Events.PhysButtonEvent):
                    return False

        except IndexError:
            pass'''
        if machine.wake_reason() == machine.EXT0_WAKE or machine.wake_reason() == machine.EXT1_WAKE:
            return False
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
            buff.fill(0)
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
        self.open_mode2.draw(buff)

    @micropython.native
    def draw(self, buff):
        if self.mode == 0:
            self.draw_watchface(buff)
        elif self.mode == 1:
            buff.fill(0) # remeber this doesnt set boundaries of the fb so
            if self.mode1_lock.acquire():
                for elem in self.mode1_context:
                    elem.draw(buff)
                self.mode1_lock.release()
        elif self.mode == 2:
            buff.fill(0)
            if self.mode2_lock.acquire():
                for elem in self.mode2_context:
                    elem.draw(buff)
                self.mode2_lock.release()

