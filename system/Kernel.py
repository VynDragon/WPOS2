#
# SPDX-FileCopyrightText: 2023 <mail@massdriver.space>
# SPDX-License-Identifier: Apache-2.0
#

import Single
import Hardware
import Settings
import Events
import Program
import uasyncio
import machine
import Logger
import oframebuf, framebuf
import random, sys, os, gc
import _thread, time, micropython
from collections import deque #in deque append and popleft are ATOMIC (thread safe! This is of utmost importance and the base of the event system) Use try except for handling empty (IndexError)

# Thread 0: Kernel
# Thread 1: Render
# Thread 2+: Apps thinking


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
                    self.loading_program = True
                    self.runProgram(this_event.name, this_event.arg)
                elif isinstance(this_event, Events.StopEvent):
                    self.stopProgram(this_event.name)
                else:
                    self.running_lock.acquire()
                    if isinstance(this_event, Events.FrontEvent) and this_event.t_program_id == None:
                        self.running[self.running_front].event(this_event)
                    else:
                        for program in self.running:
                            if program.id == this_event.t_program_id:
                                program.event(this_event)
                            elif this_event.t_program_id == None:
                                program.event(this_event)
                    self.running_lock.release()
        except IndexError as e:
            pass

    def runProgram(self, name, arg):
        if __debug__:
            print("in runProgram for ", name)
        _thread.start_new_thread(self.runProgram2, (name, arg))


    def runProgram2(self, name, arg): # todo: give on device method to see why a program failed to start
        if __debug__:
            print("in runProgram2 for ", name, " with path ", sys.path, " in ", os.getcwd())
            #micropython.mem_info(1)
        self.running_lock.acquire()
        try:
            program = __import__("programs." + name, globals(), locals(), [], 0)
            pinstance = getattr(program, name)(_thread.get_ident(), True, arg)
            if __debug__:
                print("Free Ram status before gc", free(True))
                gc.collect()
                print("Free Ram after gc collect", free(True))
                print("program: ", name)
            self.running.append(pinstance)
            self.running_lock.release()
            if __debug__:
                print("started ", pinstance)
            self.runningProgram(pinstance)
        except Exception as e:
            print("program", name, "couldnt load, reason: ", e)
            sys.print_exception(e)
        self.loading_program = False
        if self.running_lock.locked(): # there is good reason for that
            self.running_lock.release()

    def runningProgram(self, program_instance):
        try:
            program_instance._do_start()
            self.loading_program = False
            while (not program_instance.should_exit):
                program_instance._do_think()
        except Exception as e:
            print("program", program_instance.id, "is dead reason: ", e)
            sys.print_exception(e)
            self.stopProgram(program_instance.id)
        self.loading_program = False


    def stopProgram(self, id = None):
        if id == None:
            self.running_lock.acquire()
            if len(self.running) > 0:
                self.running[-1]._do_stop()
                self.running.pop()
            self.running_lock.release()
            return
        self.running_lock.acquire()
        to_stop = [i for i in self.running if i.id == id]
        self.running = [i for i in self.running if i.id != id]
        self.running_lock.release()
        for prog in to_stop:
            prog._do_stop() # when called from itself, the thread kills itself in there, and if that doesnt happen somehow it will die when returning anyway.

    def switchProgram(self, id = -1): # switches back to 'last' program by DEFAULT_TEXT_COLOR
        # todo add a thing to not switch away from keyboard
        self.running_front = id
        return True



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
        self.loading_program = True
        self.kernel_thread = None
        self.input = deque((), 100)
        self.running = []
        self.running_front = -1 #position in LIST, not thread id
        self.running_lock = _thread.allocate_lock()



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
            self.settings = Settings.Settings()
            Single.Settings = self.settings
            self.hardware = Hardware.Hardware()
            Single.Hardware = self.hardware
            self.framebuffer_array = bytearray(240 * 240 * 2) # 2 byte per pixel
            #Kernel.framebuffer = oframebuf.OFrameBuffer(Kernel.framebuffer_array, 240, 240, framebuf.RGB565)
            #Kernel.framebuffer = framebuf.FrameBuffer(Kernel.framebuffer_array, 240, 240, framebuf.RGB565)
            self.framebuffer = oframebuf.WPFrameBuffer(self.framebuffer_array, 240, 240, framebuf.RGB565)
            #self.render_timer.init(mode=machine.Timer.PERIODIC, period=70, callback=self.render_callback) # 100 ms (10fps), starting the timer there seems to keep it on the same thread,
            # seems to be about how fast the SPI interface can keep up while hitting few cant keep up
            _thread.start_new_thread(self.render_thread, ())
            self._lock.release()
            machine.freq(80000000) # we have done most of the init we can chill
            self.event(Events.RunEvent("home"))
            while(True):
                self._lock.acquire()
                Logger.process()
                self.process_events()
                self.hardware.process()
                self._lock.release()
                time.sleep_ms(70)

        except Exception as e:
            Single.fucky_wucky = True
            print("Kernel thread is dead, reason: ", e)
            from sys import print_exception
            print_exception(e)
            self.hardware.fucky_wucky(e)
            time.sleep_ms(5000)
        finally:
            machine.reset()

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
        while(not Single.fucky_wucky):
            startrender = time.ticks_ms()
            if self.loading_program:
                self.render_loading_program()
            else:
                self.render()
            if not self.max_refresh:
                while(time.ticks_ms() - startrender < 100): # hold 10 fps
                    time.sleep_ms(5)


    @micropython.native
    def render(self):
        #self.render_tick = time.ticks_ms()
        #self.blit_tick = time.ticks_ms()
        # the slow bit:
        Single.Hardware.blit_buffer_rgb565(self.framebuffer_array)
        '''if __debug__:
            ft = time.ticks_ms() - self.blit_tick
            print("took", ft, "ms to blit,", 1000/ft, "fps")'''
        app = None
        self.running_lock.acquire()
        if len(self.running) > 0:
            app = self.running[self.running_front]
        self.running_lock.release()
        if app:
            app._do_draw(self.framebuffer)
        '''if __debug__:
            ft = time.ticks_ms() - self.render_tick
            print("took", ft, "ms to render,", 1000/ft, "fps")'''

    def render_loading_program(self):
        self.framebuffer.fill(0)
        self.framebuffer.text("LOADING", 0.5 - Single.DEFAULT_TEXT_RATIO_INV * 3.5, 0.5 - Single.DEFAULT_TEXT_RATIO_INV_2, Single.DEFAULT_TEXT_COLOR)
        Single.Hardware.blit_buffer_rgb565(self.framebuffer_array)
