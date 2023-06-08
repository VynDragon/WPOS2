#
# SPDX-FileCopyrightText: 2023 <mail@massdriver.space>
# SPDX-License-Identifier: Apache-2.0
#

import machine
import Logger
import st7789, axp202, axp202_constants
import TextMode
import esp
import json

class Hardware:
    def __init__(self):
        self.hardware = []
        Logger.log("Initializing Hardware...")
        machine.freq(240000000)
        Logger.log("Initializing AXP202 PMU...")
        # BackLight Power
        self.pmu = axp202.PMU()
        self.pmu.enablePower(axp202.AXP202_LDO2)
        self.pmu.setLDO2Voltage(2800)
        self.pmu.clearIRQ()
        self.pmu.disableIRQ(axp202_constants.AXP202_ALL_IRQ)
        self.pmu.write_byte(axp202_constants.AXP202_POK_SET, 0b00011001)  # power off time = 6s, longpress time = 1.5 seconds, timeout shutdow = yes
        self.pmu.enableIRQ(axp202_constants.AXP202_PEK_SHORTPRESS_IRQ)
        self.pmu.enableIRQ(axp202_constants.AXP202_PEK_LONGPRESS_IRQ)
        #elf.pmu.setShutdownTime(axp202_constants.AXP_POWER_OFF_TIME_65)
        #self.pmu.setlongPressTime(axp202_constants.AXP_LONGPRESS_TIME_2S)
        #self.pmu.setTimeOutShutdown(True)
        #self.pmu.enableIRQ(axp202_constants.AXP202_ALL_IRQ)
        Logger.log("Initializing firmware pre-init graphics.")
        display_spi = machine.SPI(1,baudrate=160000000,sck=machine.Pin(18, machine.Pin.OUT),mosi=machine.Pin(19, machine.Pin.OUT)) # will only work with modded MPY to add flag for dummy bit, otherwise use baudrate 27000000
        cs = machine.Pin(5, machine.Pin.OUT)
        dc = machine.Pin(27, machine.Pin.OUT)
        self.display = st7789.ST7789(display_spi, 240,240,cs=cs,dc=dc,backlight=machine.Pin(12, machine.Pin.OUT),rotation=2,buffer_size=240*240*2)
        self.display.init()
        self.display.on()
        self.display.fill(st7789.BLACK)
        Logger.log("Hi! Display initialized.")
        Logger.log("CPU frequ: " + str(machine.freq()))
        Logger.log("Flash Size: " + str(esp.flash_size()))
        Logger.log("Unique ID: " + str(machine.unique_id()))
        Logger.log("Reset Cause: " + str(machine.reset_cause()))
        Logger.log("Wake Cause: " + str(machine.wake_reason()))
        detect = HardwareDetector()
        #detect.scan(0)
        #detect.scan(1)
        detect.scan(0, 22, 21)

class HardwareDetector:
    def __init__(self):
        self.devices = None
        #load i2c device list
        try:
            self.devices = json.load(open("/system/devices.json"))
        except:
            Logger.log("no i2c device list")

    def scan(self, id , scl = None, sda = None):
        Logger.log("Scanning Hardware i2c Channel " + str(id))
        i2c = None
        if scl == None:
            i2c = machine.I2C(id, freq=400000)
        else:
            #i2c = machine.I2C(id, freq=400000, scl=machine.Pin(scl), sda=machine.Pin(sda))
            i2c = machine.SoftI2C(freq=400000, scl=machine.Pin(scl), sda=machine.Pin(sda))
        dat = i2c.scan()
        if len(dat) > 0:
            Logger.log("Found i2C devices:")
            for dev in dat:
                possibility = ""
                if not self.devices:
                    return
                for device in self.devices:
                    for addr in device["addresses"]:
                        if addr == dev:
                            possibility += device["friendly_name"] + ", "
                Logger.log(str(dev) + " : " + possibility)

