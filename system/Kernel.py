#
# SPDX-FileCopyrightText: 2023 <mail@massdriver.space>
# SPDX-License-Identifier: Apache-2.0
#

import Single
import Hardware
import Events
import Program
import uasyncio
import machine
import Logger
import oframebuf, framebuf
import random, sys, os, gc
import _thread, time, micropython
from collections import deque #in deque append and popleft are ATOMIC (thread safe! This is of utmost importance.) Use try except for handling empty (IndexError)

# Thread 0: Kernel
# Thread 1: Render
# Thread 2+: Apps thinking


# REMBER ACCESSING HARDWARE LIKE I2C OR SPI OUT OF THREAD 1 WILL CRASH THE ESP
# doc says micropython.schedule is actually thread safe


def free(full=False): #https://forum.micropython.org/viewtopic.php?t=3499
    F = gc.mem_free()
    A = gc.mem_alloc()
    T = F+A
    P = '{0:.2f}%'.format(F/T*100)
    if not full: return P
    else : return ('Total:{0} Free:{1} ({2})'.format(T,F,P))

def checkHardwareThread():
    if __debug__:
        print("checkHardwareThread " + str(_thread.get_ident()) + " = " + str(Single.Kernel.kernel_thread))
    if _thread.get_ident() == Single.Kernel.kernel_thread:
        return True
    return False

class Kernel:

    def event(self, this_event):
        if __debug__:
            print("Kernel received event ", this_event)
        self.input.append(this_event)

    def process_events(self):
        try:
            while True:
                this_event = self.input.popleft()
                if __debug__:
                    print("processing ", this_event)
                if isinstance(this_event, Events.RunEvent):
                    self.runProgram(this_event.name)
                else:
                    self.running_lock.acquire()
                    for program in self.running:
                        if program.id == this_event.t_program_id:
                            program.event(this_event)
                        elif this_event.t_program_id == None:
                            program.event(this_event)
                    self.running_lock.release()
        except IndexError as e:
            pass

    def runProgram(self, name):
        if __debug__:
            print("in runProgram for ", name)
        _thread.start_new_thread(self.runProgram2, (name,))


    def runProgram2(self, name):
        if __debug__:
            print("in runProgram2 for ", name, " with path ", sys.path, " in ", os.getcwd())
            #micropython.mem_info(1)
        self.running_lock.acquire()
        program = __import__("programs." + name, globals(), locals(), [], 0)
        pinstance = getattr(program, name)(_thread.get_ident(), True)
        if __debug__:
            print("Free Ram status before gc", free(True))
            gc.collect()
            print("Free Ram after gc collect", free(True))
            print("program: ", pinstance)
        self.running.append(pinstance)
        if __debug__:
            print("started ", pinstance)
        self.running_lock.release()
        self.runningProgram(pinstance)

    def runningProgram(self, program_instance):
        try:
            program_instance.start()
            while (program_instance):
                program_instance._do_think()
        except Exception as e:
            print("program", program_instance.id, "is dead reason: ", e)
            import sys
            sys.print_exception(e)

    def __init__(self):
        self._lock = _thread.allocate_lock() # lock for IRQ
        self.render_ref = self.render
        self.render_timer = machine.Timer(3)
        self.render_tick = time.ticks_ms()
        self.blit_tick = time.ticks_ms()
        self.max_refresh = False

        self.hardware = None
        self.framebuffer = None
        self.framebuffer_array = None
        self.is_rendering = False
        self.kernel_thread = None
        self.input = deque((), 100)
        self.running = []
        self.running_lock = _thread.allocate_lock()

    '''def run_forever(self): # thread 0
        try:
            Logger.addOutput(print)
            Logger.log("Welcome to WPOS2")
            _thread.stack_size(64*1024)
            Logger.log("Thread stack size is: " + str(_thread.stack_size()))
            Logger.log("Thread " + str(_thread.get_ident()) + " is starting Kernel Thread")
            Logger.process()
            _thread.start_new_thread(Kernel.kernel_main_thread, (self,))

            pin38 = machine.Pin(38, machine.Pin.IN) #irq touch
            pin37 = machine.Pin(37, machine.Pin.IN) #irq external rtc
            pin39 = machine.Pin(39, machine.Pin.IN) #irq IMU
            pin35 = machine.Pin(35, machine.Pin.IN) #irq axp202
            esp32.wake_on_ext0((pin35), esp32.WAKEUP_ANY_HIGH)

            while(True):
                Logger.process()
                #wdt.feed()
                time.sleep_ms(100)
                #await uasyncio.sleep_ms(1000)
        except Exception as e:
            print("IRQ thread is dead, reason: ", e)
            import sys
            sys.print_exception(e)'''

    @micropython.native
    def kernel_main_thread(self): # thread 0
        Single.Kernel = self # make sure
        try:
            Logger.addOutput(print)
            Logger.log("Welcome to WPOS2")
            _thread.stack_size(64*1024)
            Logger.log("Thread stack size is: " + str(_thread.stack_size()))
            Logger.process()
            Logger.log("Thread " + str(_thread.get_ident()) + " is Kernel Thread")
            Logger.log("with stack size: " +  str(_thread.stack_size()))
            self.kernel_thread = _thread.get_ident()
            Logger.log("Hardware thread: " + str(checkHardwareThread()))
            if not self._lock.acquire():
                Logger.log("Couldnt lock Kernel lock, probably a major issue")
            self.hardware = Hardware.Hardware()
            self.framebuffer_array = bytearray(240 * 240 * 2) # 2 byte per pixel
            #Kernel.framebuffer = oframebuf.OFrameBuffer(Kernel.framebuffer_array, 240, 240, framebuf.RGB565)
            #Kernel.framebuffer = framebuf.FrameBuffer(Kernel.framebuffer_array, 240, 240, framebuf.RGB565)
            self.framebuffer = oframebuf.WPFrameBuffer(self.framebuffer_array, 240, 240, framebuf.RGB565)
            #self.render_timer.init(mode=machine.Timer.PERIODIC, period=70, callback=self.render_callback) # 100 ms (10fps), starting the timer there seems to keep it on the same thread,
            # seems to be about how fast the SPI interface can keep up while hitting few cant keep up
            _thread.start_new_thread(self.render_thread, ())
            self._lock.release()
            self.event(Events.RunEvent("test"))
            while(True):
                self._lock.acquire()
                Logger.process()
                self.process_events()
                self.hardware.process()
                self._lock.release()
                time.sleep_ms(100)
                #machine.lightsleep()
        except Exception as e:
            print("Kernel thread is dead, reason: ", e)
            import sys
            sys.print_exception(e)

    ''''@micropython.native
    def render_callback(self, timer):
        if self.is_rendering == True: # we dont want to stress the schedule thing,we need it for events
            print("missed one frame, cant keep up")
            return
        try:
            micropython.schedule(self.render_ref, 0) # takes about 10 ms to get us to render
            self.is_rendering = True
        except:
            print("we shaint be there... but it's probably okay (render timer irq)")'''

    @micropython.native
    def render_thread(self):
        while(True):
            startrender = time.ticks_ms()
            self.render()
            if not self.max_refresh:
                while(time.ticks_ms() - startrender < 100): # hold 10 fps
                    time.sleep_ms(5)


    @micropython.native
    def render(self):
        self.render_tick = time.ticks_ms()
        self.blit_tick = time.ticks_ms()
        self.hardware.display.blit_buffer(self.framebuffer_array, 0, 0, 240, 240) # O(1) for the whole render pipeline with that, but quite slow... but not much more than even a simple direct draw
        '''if __debug__:
            ft = time.ticks_ms() - self.blit_tick
            print("took", ft, "ms to blit,", 1000/ft, "fps")'''
        self.running_lock.acquire()
        if len(self.running) > 0:
            self.running[-1]._do_draw(self.framebuffer)
        self.running_lock.release()
        self.is_rendering = False
        '''if __debug__:
            ft = time.ticks_ms() - self.render_tick
            print("took", ft, "ms to render,", 1000/ft, "fps")'''

