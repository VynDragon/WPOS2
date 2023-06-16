# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()
import micropython, machine, esp
micropython.alloc_emergency_exception_buf(100)
micropython.opt_level(3)
esp.osdebug(None)

#if machine.reset_cause() == machine.SOFT_RESET: #soft resets break i2c, until that's specifically taken care of when can just do that.
#    machine.reset()
