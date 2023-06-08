#
# SPDX-FileCopyrightText: 2023 <mail@massdriver.space>
# SPDX-License-Identifier: Apache-2.0
#

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
import test

# Thread 0: IRQs
# Thread 1: Kernel, Drivers, Apps drawing -> dot not use any of the busses out of this thread,
# we could offload rendering to another thread at some point, but we will need to carry the display driver to that thread (and other devices that share that SPI interface)
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
        print("checkHardwareThread " + str(_thread.get_ident()) + " = " + str(Kernel.kernel_thread))
    if _thread.get_ident() == Kernel.kernel_thread:
        return True
    return False

class Kernel:

    #singleton class
    hardware = None
    framebuffer = None
    framebuffer_array = None
    is_rendering = False
    kernel_thread = None
    input = deque((), 100)
    running = []
    running_lock = _thread.allocate_lock()

    def event(self, event):
        if __debug__:
            print("Kernel received event ", event)
        Kernel.input.append(event)

    def process_events(self):
        try:
            while True:
                event = Kernel.input.popleft()
                if __debug__:
                    print("processing ", event)
                if isinstance(event, Events.RunEvent):
                    self.runProgram(event.name)
                else:
                    Kernel.running_lock.acquire()
                    for program in Kernel.running:
                        if program.id == event.t_program_id:
                            program.event(event)
                        elif event.t_program_id == None:
                            program.event(event)
                    Kernel.running_lock.release()
        except IndexError:
            pass

    def runProgram(self, name):
        if __debug__:
            print("in runProgram for ", name)
        _thread.start_new_thread(self.runProgram2, (name,))


    def runProgram2(self, name):
        if __debug__:
            print("in runProgram2 for ", name, " with path ", sys.path, " in ", os.getcwd())
            #micropython.mem_info(1)
        Kernel.running_lock.acquire()
        program = __import__("programs." + name, globals(), locals(), [], 0)
        pinstance = getattr(program, name)(_thread.get_ident(), True)
        if __debug__:
            print("Free Ram status before gc", free(True))
            gc.collect()
            print("Free Ram after gc collect", free(True))
            print("program: ", pinstance)
        Kernel.running.append(pinstance)
        if __debug__:
            print("started ", pinstance)
        Kernel.running_lock.release()
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

    def run_forever(self): # thread 0
        try:
            Logger.addOutput(print)
            Logger.log("Welcome to WPOS2")
            _thread.stack_size(64*1024)
            Logger.log("Thread stack size is: " + str(_thread.stack_size()))
            Logger.log("Thread " + str(_thread.get_ident()) + " is starting Kernel Thread")
            Logger.process()
            _thread.start_new_thread(Kernel.kernel_main_thread, (self,))
            '''if not self._lock.acquire(1, 5.0):
            Logger.log("Kernel hasnt started within 5 seconds, rebooting")
            Logger.process()
            time.sleep_ms(200)
            machine.reset()
            self._lock.release()''' # threading is *really* preemptive, use a timer instead.

            while(True):
                Logger.process()
                #wdt.feed()
                time.sleep_ms(100)
                #await uasyncio.sleep_ms(1000)
        except Exception as e:
            print("IRQ thread is dead, reason: ", e)
            import sys
            sys.print_exception(e)

    def kernel_main_thread(self): # thread 1
        try:
            Logger.log("Thread " + str(_thread.get_ident()) + " is Kernel Thread")
            Logger.log("with stack size: " +  str(_thread.stack_size()))
            Kernel.kernel_thread = _thread.get_ident()
            Logger.log("Hardware thread: " + str(checkHardwareThread()))
            if not self._lock.acquire():
                Logger.log("Couldnt lock Kernel lock, probably a major issue")
            Kernel.hardware = Hardware.Hardware()
            Kernel.framebuffer_array = bytearray(240 * 240 * 2) # 2 byte per pixel
            #Kernel.framebuffer = oframebuf.OFrameBuffer(Kernel.framebuffer_array, 240, 240, framebuf.RGB565)
            #Kernel.framebuffer = framebuf.FrameBuffer(Kernel.framebuffer_array, 240, 240, framebuf.RGB565)
            Kernel.framebuffer = oframebuf.WPFrameBuffer(Kernel.framebuffer_array, 240, 240, framebuf.RGB565)
            self.render_timer.init(mode=machine.Timer.PERIODIC, period=40, callback=self.render_callback) # 60 ms (17fps), starting the timer there seems to keep it on the same thread,
            # seems to be about how fast the SPI interface can keep up while hitting few cant keep up, if you're fine with a few you can set it to 40 ms (25 fps) instead
            self._lock.release()
            self.event(Events.RunEvent("test"))
            while(True):
                self._lock.acquire()
                self.process_events()
                self._lock.release()
                time.sleep_ms(200)
                #machine.lightsleep()
        except Exception as e:
            print("Kernel thread is dead, reason: ", e)
            import sys
            sys.print_exception(e)

    def render_callback(self, timer):
        if Kernel.is_rendering == True: # we dont want to stress the schedule thing,we need it for events
            print("missed one frame")
            return
        try:
            micropython.schedule(self.render_ref, 0)
        except:
            print("we shaint be there...")

    def render(self, _):
        Kernel.is_rendering = True
        #self._lock.acquire() # we dont need to lock in theory (I would like to though)
        bA_ref = Kernel.framebuffer_array
        disp_ref = Kernel.hardware.display
        disp_ref.blit_buffer(bA_ref, 0, 0, 240, 240)
        if len(Kernel.running) > 0:
            Kernel.running[-1]._do_draw(Kernel.framebuffer)
        #self._lock.release()
        Kernel.is_rendering = False

