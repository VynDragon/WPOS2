#
# SPDX-FileCopyrightText: 2023 <mail@massdriver.space>
# SPDX-License-Identifier: Apache-2.0
#

import machine, micropython, json, time, _thread, network
import Logger
import st7789, axp202, axp202_constants, ft6x36
import TextMode
import Events
import esp, esp32
import Single

DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240

class Hardware:
    Vc3V3 = 2700
    def __init__(self):
        self.hardware = []
        Logger.log("Initializing Hardware...")
        machine.freq(240000000)
        Logger.log("Initializing AXP202 PMU...")
        # BackLight Poweif fb[i*2*DISPLAY_HEIGHT + j*2] > 0 or fb[i*2*DISPLAY_HEIGHT + j*2 + 1] > 0:r
        self.pmu = axp202.PMU()
        self.pmu.enablePower(axp202.AXP202_LDO2)
        self.pmu.setLDO2Voltage(2800) #default backlight level
        self.pmu.setDC3Voltage(Hardware.Vc3V3)
        '''very low 3.3v rail to minimize power consumption,
        esp can go down to 2.3v and that's the highest necessary voltage (and might be fine down to 1.8v too)
        mpu/bma : 1.6v, typic:1.8v
        pmu:2.9v (but we dont care, this is the powersupply, this is how low the battery can go)
        display: 1.6v
        touch:2.7v but probably actually 1.8v
        rtc: 1v (wow)
        speaker: 2.5v (we might need to turn voltage back up when we use it, but it's mostly a amp so it might be fine)
        mic: 1.6v
        psram: 2.7v
        '''
        self.pmu.disablePower(axp202_constants.AXP202_LDO3)
        self.pmu.disablePower(axp202_constants.AXP202_LDO4)
        self.pmu.disablePower(axp202_constants.AXP202_DCDC2)
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
        display_spi = machine.SPI(1,baudrate=80000000,sck=machine.Pin(18, machine.Pin.OUT),mosi=machine.Pin(19, machine.Pin.OUT)) # will only work with modded MPY to add flag for dummy bit, otherwise use baudrate 27000000, limit is 80Mhz
        cs = machine.Pin(5, machine.Pin.OUT)
        dc = machine.Pin(27, machine.Pin.OUT)
        self.display = st7789.ST7789(display_spi, DISPLAY_WIDTH, DISPLAY_HEIGHT, cs=cs, dc=dc, backlight=machine.Pin(12, machine.Pin.OUT), rotation=2, buffer_size=DISPLAY_WIDTH*DISPLAY_HEIGHT*2,)
        self.display.init()
        self.display.on()
        self.display.fill(st7789.BLACK)
        Logger.log("Hi! Display initialized.")
        Logger.log("CPU frequ: " + str(machine.freq()))
        Logger.log("Flash Size: " + str(esp.flash_size()))
        Logger.log("Unique ID: " + str(machine.unique_id()))
        Logger.log("Reset Cause: " + str(machine.reset_cause()))
        Logger.log("Wake Cause: " + str(machine.wake_reason()))

        self.touch = ft6x36.FT6x36(machine.SoftI2C(scl=machine.Pin(32, machine.Pin.OUT), sda=machine.Pin(23, machine.Pin.OUT)))

        pin38 = machine.Pin(38, machine.Pin.IN) #irq touch
        pin37 = machine.Pin(37, machine.Pin.IN) #irq external rtc
        pin39 = machine.Pin(39, machine.Pin.IN) #irq IMU
        pin35 = machine.Pin(35, machine.Pin.IN) #irq axp202
        #esp32.wake_on_ext1((pin35, pin39, pin38, pin37), esp32.WAKEUP_ANY_HIGH)
        esp32.wake_on_ext0(pin35, esp32.WAKEUP_ALL_LOW)
        pin38.irq(self.irq_touch, trigger= machine.Pin.IRQ_RISING)

        self.irq_touch_buffer_pos1 = bytearray(4) #pre-allocation
        self.irq_touch_buffer_pos2 = bytearray(4)
        self.irq_touch_present = False
        self.irq_touch_time = 0
        self.irq_touch_fired_release = False

        #self.oldfb = bytearray(DISPLAY_WIDTH * DISPLAY_HEIGHT * 2)

        self.wifi_lock = _thread.allocate_lock()
        self.wifi = None

    def lightsleep(self, time_ms, force = False):
        if self.wifi_lock.locked() and not force:
            return False
        elif self.wifi_lock.locked() and force:
            self.releaseWifi(force) # fuck them apps
        self.display.off()
        self.display.sleep_mode(True)
        self.pmu.disablePower(axp202_constants.AXP202_LDO2)
        self.pmu.disablePower(axp202_constants.AXP202_LDO3)
        self.pmu.disablePower(axp202_constants.AXP202_LDO4)
        self.pmu.disablePower(axp202_constants.AXP202_DCDC2)
        self.pmu.clearIRQ()
        self.touch.power_mode = 1 # 0 = Active, 1 = Monitor, 2= Standby, 3= Hibernate
        #comes out of monitor whenever we touch
        machine.lightsleep(time_ms)
        self.pmu.setDC3Voltage(Hardware.Vc3V3)
        self.pmu.enablePower(axp202_constants.AXP202_LDO2)
        self.display.sleep_mode(False)
        self.display.on()
        return True

    def process(self):
        if not self.irq_touch_present and self.irq_touch_time + 200 < time.ticks_ms() and not self.irq_touch_fired_release:
            x = (self.irq_touch_buffer_pos1[0] << 8 | self.irq_touch_buffer_pos1[1]) & 0x0FFF
            y = (self.irq_touch_buffer_pos1[2] << 8 | self.irq_touch_buffer_pos1[3]) & 0x0FFF
            Single.Kernel.event(Events.ReleaseEvent(float(x) / float(DISPLAY_WIDTH), float(y) / float(DISPLAY_HEIGHT)))
            self.irq_touch_fired_release = True

    def irq_touch(self, pin):
        if not self.irq_touch_present:
            try:
                self.touch._i2c.readfrom_mem_into(self.touch._address, ft6x36._P1_XH_REG, self.irq_touch_buffer_pos1) #save positions at time of irq, processing it fast is not guratanteed
                self.touch._i2c.readfrom_mem_into(self.touch._address, ft6x36._P2_XH_REG, self.irq_touch_buffer_pos2)
                micropython.schedule(self.irq_touch_process, pin)
                self.irq_touch_present = True
                self.irq_touch_fired_release = False
                self.irq_touch_time = time.ticks_ms()
            except Exception as e:
                print("we shaint be there... And it's not okay, you might need to reboot(hardware irq)")
                print(e)

    def irq_touch_process(self, pin):
        self.irq_touch_present = False
        x = (self.irq_touch_buffer_pos1[0] << 8 | self.irq_touch_buffer_pos1[1]) & 0x0FFF
        y = (self.irq_touch_buffer_pos1[2] << 8 | self.irq_touch_buffer_pos1[3]) & 0x0FFF
        Single.Kernel.event(Events.TouchEvent(float(x) / float(DISPLAY_WIDTH), float(y) / float(DISPLAY_HEIGHT)))

    def fucky_wucky(self, e): # try to print exception to display
        from TextMode import TextMode_st7789
        tm = TextMode_st7789(self.display)
        tm.print(e)

    #wifi

    def acquireWifi(self, blocking = True, timeout = -1): # also use thatfor ESPNOW
        locked = self.wifi_lock.acquire(blocking, timeout)
        if locked:
            self.wifi_thread = _thread.get_ident()
        return locked

    def releaseWifi(self, force = False):
        if not self.precheckWifi() and not force:
            return False
        if self.wifi_lock.locked():
            self.wifi_lock.release()
        if self.wifi != None:
            wifi.active(False)
        return True

    def precheckWifi(self):
        if not self.wifi_lock.locked():
            return False
        if self.wifi_thread != _thread.get_ident():
            return False
        return True

    def connectWifi(self): #get a ready wifi client, possibly with internet access
        if not self.precheckWifi():
            return None
        self.initWifi_STA()
        self.wifi.active(True)
        # todo: connect to available configured network
        return self.wifi

    def initWifi_AP(self): #let user do
        if not self.precheckWifi():
            return None
        self.wifi = network.WLAN(network.AP_IF)
        return self.wifi

    def initWifi_STA(self):
        if not self.precheckWifi():
            return None
        self.wifi = network.WLAN(network.STA_IF)
        return self.wifi


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


