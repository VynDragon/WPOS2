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
                self.last_event_time = time.ticks_ms()
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
                if self.loading_program and isinstance(this_event, Events.PhysButtonEvent): # there is something hanging program loading, leave and go back home
                    self.running_front = 0
                    self.loading_program = False
        except IndexError as e:
            pass

    def runProgram(self, name, arg):
        if __debug__:
            print("in runProgram for ", name)
            print("Free Ram:", free(True))
        self.running_front = -1
        _thread.stack_size(Single.MP_THREAD_STACK_SIZE) # do that before EVERY new thread, see Single.py for explanation
        _thread.start_new_thread(self.runProgram2, (name, arg))


    def runProgram2(self, name, arg): # todo: give on device method to see why a program failed to start
        if __debug__:
            print("in runProgram2 for ", name, " with path ", sys.path, " in ", os.getcwd())
            #micropython.mem_info(1)
        self.running_lock.acquire()
        try:
            gc.collect()
            program = None
            if self.program_cache.get(name) != None:
                program = self.program_cache[name]
            else:
                program = __import__("programs." + name, globals(), locals(), [], 0)
                self.program_cache[name] = program
            pinstance = getattr(program, name)(_thread.get_ident(), True, arg)
            if __debug__:
                print("Free Ram after gc collect", free(True))
                print("program: ", name)
            self.running.append(pinstance)
            self.running_lock.release()
            if __debug__:
                print("started ", pinstance)
            self.runningProgram(pinstance)
        except Exception as e:
            self.loading_program = False
            print("program", name, "couldnt load, reason: ", e)
            sys.print_exception(e)
            self.event(Events.RunEvent("popup", str(e)))
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
            if program_instance.thread == self.thread_0:
                Single.fucky_wucky = True
            else:
                self.stopProgram(program_instance.thread)
        self.loading_program = False


    def stopProgram(self, id = None):
        if id == self.thread_0:# dont stop home we need it :(
            self.event(Events.RunEvent("popup", "cannot kill program 0"))
            return
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

    def switchProgram(self, id = -1): # switches back to 'last' program by default
        # todo add a thing to not switch away from keyboard
        if id  == -1:
            self.running_front = id
            return True
        self.running_lock.acquire()
        if len(self.running) > 0:
           for x in range(0, len(self.running)):
               if self.running[x].id == id:
                   self.running_lock.release()
                   self.running_front = x
                   return True
        self.running_lock.release()
        return False

    def getPrograms(self):
        programs = []
        try:
            if self.running_lock.acquire():
                if len(self.running) > 0:
                    for x in self.running:
                        programs.append(x)
                self.running_lock.release()
        except:
            pass
        return programs



    def __init__(self):
        self._lock = _thread.allocate_lock() # lock for IRQ
        self.render_ref = self.render
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
        self.thread_0 = None # so we dont kill the system home
        self.program_cache = {} # cache for alreayd loaded programs
        self.loading_animation = None
        self.last_event_time = time.ticks_ms()



    @micropython.native
    def kernel_main_thread(self): # thread 0
        Single.Kernel = self # make sure
        try:
            Logger.addOutput(print)
            Logger.log("Welcome to WPOS2")
            _thread.stack_size(Single.MP_THREAD_STACK_SIZE) # does not actually sets stack size
            Logger.log("Thread stack size is: " + str(_thread.stack_size())) # because this sets it back to 4K
            Logger.process()
            Logger.log("Thread " + str(_thread.get_ident()) + " is Kernel Thread")
            _thread.stack_size(Single.MP_THREAD_STACK_SIZE)
            Logger.log("with stack size: " +  str(_thread.stack_size())) # same deal
            self.kernel_thread = _thread.get_ident()
            Logger.log("Hardware thread: " + str(checkHardwareThread()))
            if not self._lock.acquire():
                Logger.log("Couldnt lock Kernel lock, probably a major issue")
            self.settings = Settings.Settings()
            Single.Settings = self.settings
            self.hardware = Hardware.Hardware()
            Single.Hardware = self.hardware
            self.framebuffer_array = bytearray(240 * 240 * 2) # 2 byte per pixel)
            self.framebuffer = oframebuf.WPFrameBuffer(self.framebuffer_array, 240, 240, framebuf.RGB565)
            #if not Single.Hardware.WatchVersion == 3: # dont render for WATCHS3 until SPI is fixed as softSPI is too slow and hogs the CPU
            _thread.stack_size(Single.MP_THREAD_STACK_SIZE)
            _thread.start_new_thread(self.render_thread, ())
            _thread.stack_size(Single.MP_SMALLTHREAD_STACK_SIZE)
            _thread.start_new_thread(self.blit_thread, ())
            self._lock.release()
            self.event(Events.RunEvent("home"))
            while(not Single.fucky_wucky):
                self._lock.acquire()
                Logger.process()
                self.process_events()
                self.hardware.process()
                self._lock.release()
                time.sleep(0)

        except Exception as e:
            Single.fucky_wucky = True
            print("Kernel thread is dead, reason: ", e)
            from sys import print_exception
            print_exception(e)
            self.hardware.fucky_wucky(e)
            time.sleep_ms(5000)
        finally:
            if Single.fucky_wucky:
                print("Kernel has exited due to the failure of another important thing")
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


    # single writer thread and single reader thread, in theory we can have 2 threads for render

    @micropython.native
    def render_thread(self):
        self.render_gate = False # gates for both so they work at the same time but wait for each others, the idea is to leave the maximum amount of 'CPU S
        while(not Single.fucky_wucky):
            startrender = time.ticks_ms()
            if self.loading_program:
                self.render_loading_program()
            else:
                self.render()
            self.render_gate = True
            #if not self.max_refresh:
            #    time.sleep(0) # attempt to prevent rendering multiple times in a blit (give time to blit thread to start waiting for lock)
            #Single.Hardware.display_lock.acquire() # wait for blitting to finish before starting next frame
            #Single.Hardware.display_lock.release()
            if not self.max_refresh:
                while time.ticks_diff(time.ticks_add(startrender, 50), time.ticks_ms()) > 0 or self.render_gate == True: # hold 20 fps, good, will not wrap around unless the difference between startrender and time.ticks_ms is very big
                    time.sleep(0)
            else:
                while self.render_gate == True:
                    time.sleep(0)

    @micropython.native
    def blit_thread(self):
        self.line_off = 0
        self.blit_gate = False
        while(not Single.fucky_wucky):
            startblit = time.ticks_ms()
            self.blit()
            self.render_gate = False
            if not self.max_refresh:
                while time.ticks_diff(time.ticks_add(startblit, 50), time.ticks_ms()) > 0 or self.render_gate == False: # attempt to hold 20 fps
                    time.sleep(0)
            else:
                while self.render_gate == False:
                    time.sleep(0)

    @micropython.native
    def blit(self):
        self.blit_tick = time.ticks_ms()
        # the slow bit:
        if Single.Hardware.display_lock.acquire():
            #Single.Hardware.blit_buffer_rgb565(self.framebuffer_array)
            #Single.Hardware.blit_framebuffer_rgb565(self.framebuffer)
            #Single.Hardware.blit_framebuffer_rgb565_halfmode2(self.framebuffer, self.line_off, 16)
            Single.Hardware.blit_framebuffer_rgb565_halfmode1(self.framebuffer, self.line_off)
            if self.line_off == 0:
                self.line_off = 1
            else:
                self.line_off = 0
            #Single.Hardware.blit_buffer_rgb565(self.framebuffer_array)
            #time.sleep(0) # give time to grab lock
            Single.Hardware.display_lock.release()
        if __debug__ and False:
            ft = time.ticks_ms() - self.blit_tick # bad, shouldltn be done, will wrap around at some point
            if ft > 0:
                print("took", ft, "ms to blit,", 1000/ft, "fps")

    @micropython.native
    def render(self):
        self.render_tick = time.ticks_ms()
        app = None
        self.running_lock.acquire()
        if len(self.running) > 0:
            try:
                app = self.running[self.running_front]
            except Exception as e:
                self.running_front = -1
                print(e)
        self.running_lock.release()
        if app:
            try:
                app._do_draw(self.framebuffer)
            except Exception as e:
                print(e)
                self.event(Events.RunEvent("popup", str(e)))
        if __debug__ and False:
            ft = time.ticks_ms() - self.render_tick # still bad
            if ft > 0:
                print("took", ft, "ms to render,", 1000/ft, "fps")

    def render_loading_program(self):
        self.framebuffer.fill(0) # fill doesnt set boundaries in buffer
        if not self.loading_animation:
            with open("/system/loading.bw.gz") as the_video:
                import zlib
                self.loading_animation = memoryview(bytearray(zlib.DecompIO(the_video, 31).read()))
            self.loading_animation_frame = 0
            self.loading_animation_palette = oframebuf.WPPalette()
            self.loading_animation_framesize = int(120*120/8)
            self.loading_animation_frame
        tmpbuf = oframebuf.FrameBuffer(self.loading_animation[ self.loading_animation_framesize * self.loading_animation_frame:], 120, 120, framebuf.MONO_HLSB)
        self.framebuffer.blit(tmpbuf, 0.25, 0.25, 0, self.loading_animation_palette)
        self.loading_animation_frame += 1
        if self.loading_animation_frame >= 60:
            self.loading_animation_frame = 0
        self.framebuffer.text("LOADING", 0.5 - Single.DEFAULT_TEXT_RATIO_INV * 3.5, 0.5 - Single.DEFAULT_TEXT_RATIO_INV_2, Single.DEFAULT_TEXT_COLOR)
