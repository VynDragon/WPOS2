#
# SPDX-FileCopyrightText: 2023 <mail@massdriver.space>
# SPDX-License-Identifier: Apache-2.0
#

import machine, micropython, json, time, _thread, network, os
import Logger
import st7789, axp202, axp202_constants, ft6x36, pcf8563, bma423, adafruit_drv2605, AXP2101
import TextMode
import Events
import esp, esp32
import Single

WATCHV1 = int(0)
WATCHV2 = int(1)
WATCHV3 = int(2)
WATCHS3 = int(3)

# Remember to write irq handlers for SPEED, we have SO MUCH RAM
# also everything that has to do with hardware probably should be lbyl

class Hardware:
    Vc3V3 = 2800 # we brownout often when disconnecting USB at lower voltages, workaround is resetting the device when USB disconnect
    #Vc3V3 = 3300
    DISPLAY_WIDTH = 240
    DISPLAY_HEIGHT = 240
    #RELEASE_TWITCHYNESS = 100 dont need anymore since we figured the touchscreen already does that, contrary to our driver

    def identify_version(self):
        try:
            drv_i2c = machine.SoftI2C(scl=machine.Pin(22, machine.Pin.OUT), sda=machine.Pin(21, machine.Pin.OUT), freq=100000)
            vibration_controller = adafruit_drv2605.DRV2605(drv_i2c)
        except OSError:
            return WATCHV1
        if "S3" in os.uname()[4]:
            return WATCHS3 #S3
        return WATCHV2 #V2

    def init_ft6336(self):
        if self.WatchVersion == WATCHV2:
            self.pmu.disablePower(axp202_constants.AXP202_EXTEN); # reset touch
            time.sleep_ms(15)
            self.pmu.enablePower(axp202_constants.AXP202_EXTEN);
        self.touch = ft6x36.FT6x36(machine.SoftI2C(scl=machine.Pin(32, machine.Pin.OUT), sda=machine.Pin(23, machine.Pin.OUT), freq=100000))
        self.touch.power_mode = 0
        # something is seriously wrong with gestures on this controller
        # we probably need to upload a firmware blob to the device and from looking at drivers, it is complicated and i dont want to bother
        self.irq_gesture_buffer_1 = bytearray(2)
        self.irq_gesture_buffer_1[0] = 0x00 # 1 = 'enter into gesture', disables touch :(, 0: 'disable or resume'
        self.irq_gesture_buffer_1[1] = 0x00 # 1 = gestures enabled, 0: gestures disabled (theory)
        self.touch._i2c.writeto_mem(self.touch._address, 0xD0, self.irq_gesture_buffer_1) #gestures, bad focaltech datasheet
        '''self.irq_gesture_buffer_2 = bytearray(2)
        tmpbuff = bytearray(1)
        tmpbuff[0] = 0x03
        self.touch._i2c.writeto_mem(self.touch._address, 0x94, tmpbuff) #assuming this is in number of points, testing show we rarely get over ten sliding over the entire screen
        self.touch._i2c.writeto_mem(self.touch._address, 0x95, tmpbuff)'''

    def init_st7789(self):
        display_spi = machine.SPI(1)
        display_spi.deinit()
        # shameful display of 3 wire SPI and slow updates
        # why not 2-line or 4-line  SPI lilygo?
        # also uses wrong MOSI pin, slowing it down even more, fixed on TWATCH S3
        if self.WatchVersion == WATCHV2:
            cs = machine.Pin(5, machine.Pin.OUT)
            dc = machine.Pin(27, machine.Pin.OUT)
            display_spi = machine.SPI(1,baudrate=80000000,sck=machine.Pin(18, machine.Pin.OUT),mosi=machine.Pin(19, machine.Pin.OUT)) # will only work with modded MPY to add flag for dummy bit, otherwise use baudrate 27000000, ESP32 limit is 80Mhz
            self.display = st7789.ST7789(display_spi, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT, cs=cs, dc=dc, backlight=machine.Pin(25, machine.Pin.OUT), rotation=2, buffer_size=Hardware.DISPLAY_WIDTH*Hardware.DISPLAY_HEIGHT*2,)
        elif self.WatchVersion == WATCHS3:
            cs = machine.Pin(12, machine.Pin.OUT)
            dc = machine.Pin(38, machine.Pin.OUT)
            display_spi = machine.SPI(0,baudrate=80000000,sck=machine.Pin(18, machine.Pin.OUT),mosi=machine.Pin(13, machine.Pin.OUT)) # will only work with modded MPY to add flag for dummy bit, otherwise use baudrate 27000000, ESP32 limit is 80Mhz
            self.display = st7789.ST7789(display_spi, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT, cs=cs, dc=dc, backlight=machine.Pin(45, machine.Pin.OUT), rotation=2, buffer_size=Hardware.DISPLAY_WIDTH*Hardware.DISPLAY_HEIGHT*2,)
        else:
            cs = machine.Pin(5, machine.Pin.OUT)
            dc = machine.Pin(27, machine.Pin.OUT)
            display_spi = machine.SPI(1,baudrate=80000000,sck=machine.Pin(18, machine.Pin.OUT),mosi=machine.Pin(19, machine.Pin.OUT)) # will only work with modded MPY to add flag for dummy bit, otherwise use baudrate 27000000, ESP32 limit is 80Mhz
            self.display = st7789.ST7789(display_spi, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT, cs=cs, dc=dc, backlight=machine.Pin(12, machine.Pin.OUT), rotation=2, buffer_size=Hardware.DISPLAY_WIDTH*Hardware.DISPLAY_HEIGHT*2,)
        self.display.init()
        self.display.on()
        #self.display.fill(st7789.BLACK)
        Logger.log("Hi! Display initialized.")

    def init_axp202(self):
        Logger.log("Initializing AXP202 PMU...")
        sObject = Single.Settings.getSettingObject(Single.Settings.hardware)
        if sObject == None:
            sObject = {}
        self.pmu = axp202.PMU()
        if sObject.get("BacklightVoltage") != None:
            self.pmu.setLDO2Voltage(sObject["BacklightVoltage"])
        else:
            self.pmu.setLDO2Voltage(2800) #default backlight level todo: load from settings (or load it from app 0)
        self.pmu.enablePower(axp202_constants.AXP202_LDO2)
        self.pmu.setDC3Voltage(Hardware.Vc3V3)
        '''very low 3.3v rail to minimize power consumption,
        esp can go down to 2.3v (and might be fine down to 1.8v too)
        imu/bma : 1.6v, typic:1.8v
        pmu:2.9v (but we dont care, this is the powersupply, this is how low the battery can go)
        display: 1.6v
        touch:2.7v but probably actually 1.8v
        rtc: 1v (wow)
        speaker: 2.5v (we might need to turn voltage back up when we use it, but it's mostly a amp so it might be fine)
        mic: 1.6v
        psram: 2.7v :(
        '''
        if self.WatchVersion != WATCHV2:
            self.pmu.disablePower(axp202_constants.AXP202_LDO3) # on V2, Touch+ TFT
        self.pmu.disablePower(axp202_constants.AXP202_LDO4) # on V2, GPS
        self.pmu.disablePower(axp202_constants.AXP202_DCDC2)
        self.pmu.clearIRQ()
        self.pmu.disableIRQ(axp202_constants.AXP202_ALL_IRQ)
        # following uses the button which is broken on my test watch so might not work as expected, I will test it later with another watch
        self.pmu.write_byte(axp202_constants.AXP202_POK_SET, 0b00011001)  # power off time = 6s, longpress time = 1.5 seconds, timeout shutdow = yes
        self.pmu.enableIRQ(axp202_constants.AXP202_PEK_SHORTPRESS_IRQ)
        self.pmu.enableIRQ(axp202_constants.AXP202_PEK_LONGPRESS_IRQ)
        self.pmu.enableIRQ(axp202_constants.AXP202_VBUS_REMOVED_IRQ)
        self.pmu.enableIRQ(axp202_constants.AXP202_BATT_REMOVED_IRQ)
        self.pmu.enableIRQ(axp202_constants.AXP202_BATT_CONNECT_IRQ)
        #elf.pmu.setShutdownTime(axp202_constants.AXP_POWER_OFF_TIME_65)
        #self.pmu.setlongPressTime(axp202_constants.AXP_LONGPRESS_TIME_2S)
        #self.pmu.setTimeOutShutdown(True)
        #self.pmu.enableIRQ(axp202_constants.AXP202_ALL_IRQ)
        self.pmu.setChargingTargetVoltage(axp202_constants.AXP202_TARGET_VOL_4_2V) # sane voltage values for battery management
        if self.WatchVersion == WATCHV2:
            self.pmu.setLDO3Voltage(3300)
            self.pmu.enablePower(axp202_constants.AXP202_LDO3)
            self.pmu.write_byte(axp202_constants.AXP202_GPIO0_CTL, 1) # everything to 0 except first byte, enable GPIO as high so it desinhibit DRV2605... why was this necessary, and only on V2 ?

    def init_irq(self):
        pin38 = machine.Pin(38, machine.Pin.IN) #irq touch
        pin37 = machine.Pin(37, machine.Pin.IN) #irq external rtc
        pin39 = machine.Pin(39, machine.Pin.IN) #irq IMU
        pin35 = machine.Pin(35, machine.Pin.IN) #irq axp202
        #esp32.wake_on_ext1((pin35, pin39, pin38, pin37), esp32.WAKEUP_ANY_HIGH)
        #esp32.wake_on_ext0(pin35, esp32.WAKEUP_ALL_LOW)
        pin35.irq(self.irq_pmu, trigger=machine.Pin.IRQ_FALLING, wake=machine.DEEPSLEEP | machine.SLEEP)
        pin38.irq(self.irq_touch, trigger= machine.Pin.IRQ_RISING)
        pin39.irq(self.irq_imu, trigger= machine.Pin.IRQ_RISING, wake=machine.DEEPSLEEP | machine.SLEEP)
        #print("pin 39 is", pin39.value())

        self.irq_touch_buffer_pos1 = bytearray(4) #pre-allocation
        self.irq_touch_buffer_pos2 = bytearray(4)
        self.irq_touch_present = False
        #self.irq_touch_time = 0
        #self.irq_touch_fired_release = True
        self.irq_feedback_present = False

    def init_irq_s3(self):
        pin16 = machine.Pin(16, machine.Pin.IN) #irq touch
        pin17 = machine.Pin(17, machine.Pin.IN) #irq external rtc
        pin14 = machine.Pin(14, machine.Pin.IN) #irq IMU
        pin21 = machine.Pin(21, machine.Pin.IN) #irq axp2101
        pin21.irq(self.irq_pmu, trigger=machine.Pin.IRQ_FALLING, wake=machine.DEEPSLEEP | machine.SLEEP)
        pin16.irq(self.irq_touch, trigger= machine.Pin.IRQ_RISING)
        pin14.irq(self.irq_imu, trigger= machine.Pin.IRQ_RISING, wake=machine.DEEPSLEEP | machine.SLEEP)

        self.irq_touch_buffer_pos1 = bytearray(4) #pre-allocation
        self.irq_touch_buffer_pos2 = bytearray(4)
        self.irq_touch_present = False
        self.irq_feedback_present = False

    def __init__(self):
        self.WatchVersion = 0 # V1
        self.hardware = []
        Logger.log("Initializing Hardware...")
        machine.freq(240000000)

        self.WatchVersion = self.identify_version()
        self.display_lock = _thread.allocate_lock() # for locking render while we sleep, notably on V2 watch where we need to re-initialize at wake up
        self.display_lock.acquire()
        if self.WatchVersion < WATCHS3:
            self.init_axp202()
            time.sleep_ms(20)
        else:
            self.init_axp2101()

        self.init_st7789()

        Logger.log("CPU frequ: " + str(machine.freq()))
        Logger.log("Flash Size: " + str(esp.flash_size()))
        Logger.log("Unique ID: " + str(int.from_bytes(machine.unique_id(), 'big', False)))
        Logger.log("Reset Cause: " + str(machine.reset_cause()))
        Logger.log("Wake Cause: " + str(machine.wake_reason()))
        network.hostname(str(int.from_bytes(machine.unique_id(), 'big', False))) # in case of multiple watches on same network
        Logger.log("Hostname: " + str(network.hostname()))

        sensor_i2c = machine.SoftI2C(scl=machine.Pin(22, machine.Pin.OUT), sda=machine.Pin(21, machine.Pin.OUT), freq=100000) #we dont need i2c very fast here and that can save us 0.6 ma on BMA423
        self.rtc = pcf8563.PCF8563(sensor_i2c)

        sObject_general = Single.Settings.getSettingObject(Single.Settings.general)
        if sObject_general == None:
            sObject_general = {}
        gmt = sObject_general.get("GMT")
        if gmt == None:
            gmt = 0
        gmt = self.rtc.hours() + gmt
        day = self.rtc.date()
        weekday = self.rtc.day()
        if gmt > 23:
            day += 1
            weekday += 1
            gmt -= 24
            if day > 31:
                day -= 31
            if weekday > 6:
                weekday -= 7
        dtt = (self.rtc.year()+2000, self.rtc.month(), day, weekday, gmt, self.rtc.minutes(), self.rtc.seconds(), 0)
        machine.RTC().datetime(dtt)
        Logger.log("Time: " + str(machine.RTC().datetime()))


        bouf = bytearray(1)  # reset bma for when we shut down without cutting power because for some reason it likes to lose its register when esp32 resets
        bouf[0] = 0xB6 #reset command
        sensor_i2c.writeto_mem(bma423.BMA4_I2C_ADDR_SECONDARY, bma423.BMA4_CMD_ADDR, bouf) # there is trace of this being previously done in the drivers but not anymore?
        self.imu = bma423.BMA423(sensor_i2c) # re-initialize
        self.imu.accel_range = bma423.BMA4_ACCEL_RANGE_8G # 4g ??
        self.imu.advance_power_save = 0
        #print("BMA internal status:", self.imu.read_byte(bma423.BMA4_INTERNAL_STAT))
        #self.imu.feature_enable("wakeup")
        #self.imu.feature_enable("any_motion")
        #self.imu.feature_enable("tilt")
        #int1config = self.imu.read_byte(bma423.BMA4_INT1_IO_CTRL_ADDR)
        int1config = 0b01010
        self.imu.write_byte(bma423.BMA4_INT1_IO_CTRL_ADDR, int1config)
        #acc_config = 0x17
        #self.imu.write_byte(bma423.BMA4_ACCEL_CONFIG_ADDR, acc_config)
        #print("int1 imu:", self.imu.read_byte(bma423.BMA4_INT1_IO_CTRL_ADDR))
        self.imu.map_int(0, bma423.BMA423_WAKEUP_INT | bma423.BMA423_ANY_NO_MOTION_INT)
        self.imu.map_int(1, 0)
        feat_data = self.imu.read_data(bma423.BMA4_FEATURE_CONFIG_ADDR, bma423.BMA423_FEATURE_SIZE)
        feat_data[bma423.BMA423_WAKEUP_OFFSET] = 0x03 # enable and sensitivity 2/7
        self.imu.write_data(bma423.BMA4_FEATURE_CONFIG_ADDR, feat_data)
        #print(list(feat_data))
        self.imu.accel_enable = 1
        #print(self.imu.int_status())
        #print("BMA internal status:", self.imu.read_byte(bma423.BMA4_INTERNAL_STAT))

        self.imu_int1 = 0
        self.imu_int2 = 0

        self.init_ft6336()

        self.gesture_startpos = (0,0) # gesture emulation

        if self.WatchVersion < WATCHS3:
            self.init_irq()
        else:
            self.init_irq_s3()


        self.wifi_lock = _thread.allocate_lock()
        self.wifi = None

        if self.WatchVersion == WATCHV1 or self.WatchVersion == WATCHV3:
            self.vibrator = machine.Pin(4, machine.Pin.OUT)
        else:
            self.vibration_controller = adafruit_drv2605.DRV2605(sensor_i2c)
            self.vibration_controller._write_u8(0x01, 0b10000000) # reset
            time.sleep_ms(10)
            self.vibration_controller = adafruit_drv2605.DRV2605(sensor_i2c)
            self.vibration_controller.mode = adafruit_drv2605.MODE_INTTRIG # i really cant be bothered lol drv looks like it has nice functions but i have other priorities rn
            self.vibrator = None

        machine.freq(80000000) #todo: set to user value (give a slider with choice between 240, 160, and 80 mhz?)
        self.display_lock.release()


    def get_battery_gauge(self): # 0-127
        return self.pmu.getBattPercentage()

    def get_battery_voltage(self):
        self.pmu.enableADC(1, 7)
        return self.pmu.getBattVoltage()

    def get_battery_current(self):
        self.pmu.enableADC(1, 6)
        return self.pmu.getBattDischargeCurrent()

    def charging(self):
        return bool(self.pmu.isChargeing())

    def lightsleep(self, time_ms, force = False, callback = None):
        if self.pmu.isVBUSPlug() and not force: # are we plugged in?
            return False
        if self.wifi_lock.locked() and not force:
            return False
        elif self.wifi_lock.locked() and force:
            self.releaseWifi(force) # fuck them apps
        if not self.display_lock.acquire():
            if force:
                self.display_lock.release()
                self.display_lock.acquire()
            else:
                return False
        machine.freq(240000000) # go fastly to go to sleep faster
        self.display.off()
        self.display.sleep_mode(True)
        self.pmu.disablePower(axp202_constants.AXP202_LDO2)
        if self.WatchVersion == WATCHV2:
            self.touch.power_mode = 3 # permannet sleep until reset
            # self.pmu.disablePower(axp202_constants.AXP202_LDO3) # shutdown full LCD in case of V2 watch
        if self.WatchVersion == WATCHV2 or self.WatchVersion == WATCHS3:
            self.vibration_controller._write_u8(0x01, 0b01000000) # standby
        self.pmu.disablePower(axp202_constants.AXP202_LDO4)
        self.pmu.disablePower(axp202_constants.AXP202_DCDC2)
        self.pmu.clearIRQ()
        # 0 = Active, 1 = Monitor, 2= Standby, 3= Hibernate
        #comes out of monitor whenever we touch
        # power mode is NOT documented but this should work
        # hibernation of FT6336 is up to 1.5 ma savings (active:4mA, monitor: 1.5mA, hibernate: 50 uA)
        # except lilygo didnt connect the reset pin and we need it to restart the display
        # monitor mode low rate of update good workaround?
        should_sleep = True
        while should_sleep:
            if self.WatchVersion == WATCHV1:
                self.touch.monitor_period = 254 # low refresh? Seems to work (datasheet says 25 time a second and default value is 40, i suppose that's milliseconds)
                self.touch.power_mode = 1
            machine.lightsleep(time_ms)
            if callback != None:
                should_sleep = callback()
            else:
                should_sleep = False
        if self.WatchVersion == WATCHV1:
            self.touch.power_mode = 0
        self.pmu.setDC3Voltage(Hardware.Vc3V3)
        self.pmu.enablePower(axp202_constants.AXP202_LDO2)
        if self.WatchVersion == WATCHV2:
            self.pmu.disablePower(axp202_constants.AXP202_EXTEN); # reset touch
            time.sleep_ms(15)
            self.pmu.enablePower(axp202_constants.AXP202_EXTEN);
            # self.pmu.setLDO3Voltage(3300)
            # self.pmu.enablePower(axp202_constants.AXP202_LDO3)
            #time.sleep_ms(20) # wait for potaaytoes to be warmed up
            self.init_ft6336()
            #self.init_st7789()
        if self.WatchVersion == WATCHV2 or self.WatchVersion == WATCHS3:
            self.vibration_controller._write_u8(0x01, 0b00000000) #exit standby
        self.display.sleep_mode(False)
        self.display.on()
        machine.freq(80000000) # no more fast, todo: see other place where this is
        self.display_lock.release()
        return True

    def blit_buffer_rgb565(self, array):
        self.display.blit_buffer(array, 0, 0, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT) # O(1) for the whole render pipeline with that, but quite slow... but not much more than even a simple direct draw
        # seems like to get more speed would need to do quite a lot on the C side of things

    def feedback1(self, _ = None):
        if self.vibrator:
            self.vibrator.on()
            machine.Timer(-1, mode=machine.Timer.ONE_SHOT, period=20, callback=self.feedback_frame)
        elif self.vibration_controller:
            self.vibration_controller.sequence[0] = adafruit_drv2605.Effect(2)
            self.vibration_controller.play()




    def feedback2(self, _ = None):
        if self.vibrator:
            self.vibrator.on()
            machine.Timer(-1, mode=machine.Timer.ONE_SHOT, period=50, callback=self.feedback_frame)
        elif self.vibration_controller:
            self.vibration_controller.sequence[0] = adafruit_drv2605.Effect(1)
            self.vibration_controller.play()

    def feedback_frame(self, _):
        if self.vibrator:
            self.vibrator.off()

    def sync_ntp(self):
        try:
            ntptime.settime()
            ct = time.gmtime()
            Single.Hardware.rtc.write_all(ct[5],ct[4],ct[3],ct[6],ct[2],ct[1],ct[0]-2000)
            sObject_general = Single.Settings.getSettingObject(Single.Settings.general)
            if sObject_general == None:
                sObject_general = {}
            gmt = sObject_general.get("GMT")
            gmt = self.rtc.hours() + gmt
            day = self.rtc.date()
            weekday = self.rtc.day()
            if gmt > 23:
                day += 1
                weekday += 1
                gmt -= 24
                if day > 31:
                    day -= 31
                if weekday > 6:
                    weekday -= 7
            machine.RTC().datetime((ct[0], ct[1], day, ct[6] + 1, gmt, ct[4], ct[5], 0))
        except:
            return False
        return True


    def process(self):
        pass
       # if not self.irq_touch_present and self.irq_touch_time + self.RELEASE_TWITCHYNESS < time.ticks_ms() and not self.irq_touch_fired_release:
       #     x = (self.irq_touch_buffer_pos1[0] << 8 | self.irq_touch_buffer_pos1[1]) & 0x0FFF
       #     y = (self.irq_touch_buffer_pos1[2] << 8 | self.irq_touch_buffer_pos1[3]) & 0x0FFF
       #     Single.Kernel.event(Events.ReleaseEvent(float(x) / float(Hardware.DISPLAY_WIDTH), float(y) / float(Hardware.DISPLAY_HEIGHT)))
       #     self.feedback1()
       #     self.irq_touch_fired_release = True



    def irq_imu(self, pin):
        self.imu_int1, self.imu_int2 = Single.Hardware.imu.int_status()
        micropython.schedule(self.irq_imu_process, pin)

    def irq_imu_process(self, pin):
        if self.imu_int1 > 0:
            Single.Kernel.event(Events.IMUEvent(self.imu_int1))

    def irq_pmu(self, pin):
        micropython.schedule(self.irq_pmu_process, pin)

    def irq_pmu_process(self, pin):
        self.pmu.readIRQ()
        print("irq_pmu:", list(self.pmu.irqbuf))
        if self.pmu.irqbuf[0] & axp202_constants.AXP202_VBUS_REMOVED_IRQ > 0: #workaround for brownouts and other bugs when disconnect USB
            machine.reset()
        if self.pmu.irqbuf[2] & axp202_constants.AXP202_VBUS_REMOVED_IRQ > 0: #actually AXP202_PEK_SHORTPRESS_IRQ!
            Single.Kernel.event(Events.PhysButtonEvent(0))
        if self.pmu.irqbuf[2] & axp202_constants.AXP202_VBUS_VHOLD_LOW_IRQ > 0: #actually AXP202_PEK_LONGPRESS_IRQ!
            Single.Kernel.event(Events.PhysButtonEvent(1.5))
        self.pmu.clearIRQ()


    def irq_touch(self, pin):
        #if self.display_lock.locked(): # dont query display it is *busy*
        #    return
        if not self.irq_touch_present:
            try:
                self.touch._i2c.readfrom_mem_into(self.touch._address, ft6x36._P1_XH_REG, self.irq_touch_buffer_pos1) #save positions at time of irq, processing it fast is not guratanteed
                self.touch._i2c.readfrom_mem_into(self.touch._address, ft6x36._P2_XH_REG, self.irq_touch_buffer_pos2)
                micropython.schedule(self.irq_touch_process, pin)
                self.irq_touch_present = True
                #self.irq_touch_fired_release = False
                self.irq_touch_time = time.ticks_ms()
            except OSError as e:
                if self.WatchVersion != WATCHV2:  # that's a possibility on V2 because we cant check lock in irq without causing issues so we do EAFP, since it's only a problem when going to sleep
                    print(e)
            except Exception as e:
                print("we shaint be there... And it's not okay, you might need to reboot(touch irq)")
                print(e)

    def irq_touch_process(self, pin):
        self.irq_touch_present = False
        x = (self.irq_touch_buffer_pos1[0] << 8 | self.irq_touch_buffer_pos1[1]) & 0x0FFF
        y = (self.irq_touch_buffer_pos1[2] << 8 | self.irq_touch_buffer_pos1[3]) & 0x0FFF
        tevent = (self.irq_touch_buffer_pos1[0] & 0xC0) >> 6# driver isnt doing that... actually stupid
        # 0 = touch down
        # 1 = lift up
        # 2 = currently contacting
        # 3 = nothing

        if tevent == 0:
            self.gesture_startpos = (x,y)
            Single.Kernel.event(Events.TouchEvent(float(x) / float(Hardware.DISPLAY_WIDTH), float(y) / float(Hardware.DISPLAY_HEIGHT)))
        elif tevent == 1:
            w2 = Hardware.DISPLAY_WIDTH / 2 # we only use 2 points for gesture emulation idc this is probably going to be used only for a single thing
            w8 = Hardware.DISPLAY_WIDTH / 6
            h2 = Hardware.DISPLAY_HEIGHT / 2
            h8 = Hardware.DISPLAY_HEIGHT / 6
            if w2 < x - self.gesture_startpos[0] and h8 > y - self.gesture_startpos[1] and -h8 < y - self.gesture_startpos[1]:
                Single.Kernel.event(Events.GestureEvent(0))
            elif -w2 > x - self.gesture_startpos[0] and h8 > y - self.gesture_startpos[1] and -h8 < y - self.gesture_startpos[1]:
                Single.Kernel.event(Events.GestureEvent(1))
            elif h2 < y - self.gesture_startpos[1] and w8 > x - self.gesture_startpos[0] and -w8 < x - self.gesture_startpos[0]:
                Single.Kernel.event(Events.GestureEvent(2))
            elif -h2 > y - self.gesture_startpos[1] and w8 > x - self.gesture_startpos[0] and -w8 < x - self.gesture_startpos[0]:
                Single.Kernel.event(Events.GestureEvent(3))

            Single.Kernel.event(Events.ReleaseEvent(float(x) / float(Hardware.DISPLAY_WIDTH), float(y) / float(Hardware.DISPLAY_HEIGHT)))
            #micropython.schedule(self.feedback1(), "bruh") # why? idk. It's giving recursion errors where it shouldnt
            self.feedback1()

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
            self.wifi.active(False)
        return True

    def precheckWifi(self):
        if not self.wifi_lock.locked():
            return False
        if self.wifi_thread != _thread.get_ident():
            return False
        return True

    def connectWifi(self): #get a ready wifi client to the first available network, possibly with internet access
        if not self.precheckWifi():
            return None
        sObject_wifi = Single.Settings.getSettingObject(Single.Settings.wifi)
        if sObject_wifi == None:
            sObject_wifi = {}
        self.initWifi_STA()
        self.wifi.active(True)
        networks_scan = self.wifi.scan()
        networks = [n[0].decode("utf-8") for n in networks_scan]
        for a_network in networks:
            a_pass = sObject_wifi.get(a_network)
            if a_pass != None:
                self.wifi.connect(a_network, a_pass)
                while self.wifi.status() == network.STAT_CONNECTING:
                    time.sleep_ms(500)
                if self.wifi.status() == network.STAT_GOT_IP:
                    self.wifi.config(pm=self.wifi.PM_POWERSAVE)
                    return self.wifi
        return None

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


