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
import oframebuf

WATCHV1 = int(0)
WATCHV2 = int(1)
WATCHV3 = int(2)
WATCHS3 = int(3)

# Remember to write irq handlers for SPEED, we have SO MUCH RAM
# also everything that has to do with hardware probably should be lbyl

class Hardware:
    Vc3V3 = 3300 # we brownout often when disconnecting USB at lower voltages, workaround is resetting the device when USB disconnect
    Vc3V3S3 = 3300
    #Vc3V3 = 3300
    DISPLAY_WIDTH = 240
    DISPLAY_HEIGHT = 240
    #RELEASE_TWITCHYNESS = 100 dont need anymore since we figured the touchscreen already does that, contrary to our driver
    BACKLIGHT_PWM_DEFAULT = int(8192)

    def identify_version(self):
        if "S3" in os.uname()[4]:
            return WATCHS3 #S3
        try:
            drv_i2c = machine.SoftI2C(scl=machine.Pin(22, machine.Pin.OUT), sda=machine.Pin(21, machine.Pin.OUT), freq=100000)
            vibration_controller = adafruit_drv2605.DRV2605(drv_i2c)
        except OSError:
            return WATCHV1
        return WATCHV2 #V2

    def init_ft6336(self):
        if self.WatchVersion == WATCHV2:
            self.pmu.disablePower(axp202_constants.AXP202_EXTEN) # reset touch
            time.sleep_ms(15)
            self.pmu.enablePower(axp202_constants.AXP202_EXTEN)
        elif self.WatchVersion == WATCHS3:
            pass # we do in axp2101
        time.sleep_ms(15)
        if self.WatchVersion == WATCHS3:
            self.touch = ft6x36.FT6x36(machine.SoftI2C(scl=machine.Pin(40, machine.Pin.OUT), sda=machine.Pin(39, machine.Pin.OUT), freq=100000))
        else:
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
        if self.WatchVersion != WATCHS3:
            display_spi = machine.SPI(1)
            display_spi.deinit()
            display_spi = machine.SPI(2)
            display_spi.deinit()
        elif self.WatchVersion == WATCHS3:
            cs = machine.Pin(12, machine.Pin.OUT)
            dc = machine.Pin(38, machine.Pin.OUT)
            #display_spi = machine.SoftSPI(baudrate=800000,sck=machine.Pin(18, machine.Pin.OUT),mosi=machine.Pin(13, machine.Pin.OUT), miso=machine.Pin(9)) # still init as softSPI, if you REALLY need to write to the screen you can force it to refresh (it will take ages and the other programs will be unhappy)
             # we dont actually want to write to pin 9, it's sx1262's, but softspi insists on a miso
            display_spi = machine.SPI(2, baudrate=80000000,sck=machine.Pin(18, machine.Pin.OUT),mosi=machine.Pin(13, machine.Pin.OUT), miso=machine.Pin(2))
            machine.Pin(9, machine.Pin.IN)
            #self.display = st7789.ST7789(display_spi, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT, cs=cs, dc=dc, backlight=machine.Pin(45, machine.Pin.OUT), rotation=2, buffer_size=Hardware.DISPLAY_WIDTH*Hardware.DISPLAY_HEIGHT*2,)
            self.display = st7789.ST7789(display_spi, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT, cs=cs, dc=dc, rotation=2, buffer_size=16,)
        else:
            cs = machine.Pin(5, machine.Pin.OUT)
            dc = machine.Pin(27, machine.Pin.OUT)
            display_spi = machine.SPI(2,baudrate=60000000, polarity=0, phase=0, bits=8, firstbit=machine.SPI.MSB,sck=machine.Pin(18),mosi=machine.Pin(19), miso=machine.Pin(23)) # will only work with modded MPY to add flag for dummy bit, otherwise use baudrate 27000000, ESP32 limit is 80Mhz
            #display_spi = machine.SPI(2,baudrate=80000000, polarity=0, phase=0, bits=8, firstbit=machine.SPI.MSB,sck=machine.Pin(18),mosi=machine.Pin(19))
            #self.display = st7789.ST7789(display_spi, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT, cs=cs, dc=dc, backlight=machine.Pin(12, machine.Pin.OUT), rotation=2, buffer_size=Hardware.DISPLAY_WIDTH*Hardware.DISPLAY_HEIGHT*2,)
            #self.display = st7789.ST7789(display_spi, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT, cs=cs, dc=dc, rotation=2, buffer_size=Hardware.DISPLAY_WIDTH*Hardware.DISPLAY_HEIGHT*2,)
            self.display = st7789.ST7789(display_spi, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT, cs=cs, dc=dc, rotation=2, buffer_size=16,)
        self.display.init()
        self.display.on()
        #self.display.fill(st7789.BLACK)
        Logger.log("Hi! Display initialized.")

    def init_axp202(self):
        Logger.log("Initializing AXP202 PMU...")

        self.pmu = axp202.PMU()
        self.pmu.setLDO2Voltage(3300) #backlight
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
        if self.WatchVersion == WATCHV1:
            self.pmu.setLDO3Mode(axp202_constants.AXP202_LDO3_DCIN_MODE) # what, why? (watch unhappy if not do like that)
            #self.pmu.setLDO3Voltage(3300)
            self.pmu.enablePower(axp202_constants.AXP202_LDO3)

    def init_axp2101(self, sensors_i2c):
        Logger.log("Initializing AXP2101 PMU...")
        self.pmu = AXP2101.AXP2101(sensors_i2c)
        self.pmu.disableALDO2()

        self.pmu.setVbusVoltageLimit(self.pmu.XPOWERS_AXP2101_VBUS_VOL_LIM_4V36)
        self.pmu.setVbusCurrentLimit(self.pmu.XPOWERS_AXP2101_VBUS_CUR_LIM_100MA) # would've liked to set that to 150 but next step is 500mA
        self.pmu.setSysPowerDownVoltage(2600)
        self.pmu.setDC1Voltage(Hardware.Vc3V3S3)
        self.pmu.setALDO1Voltage(3100) # backup battery voltage should be 3.1 (MS412FE max charge voltage is '3.3(3.1)')
        self.pmu.setALDO3Voltage(3300) # and display touch 3v3
        self.pmu.setALDO4Voltage(3300); # sx1262
        self.pmu.setBLDO2Voltage(3300); # drv2605
        self.pmu.setALDO2Voltage(3300) # backlight

        self.pmu.disableDC2()
        self.pmu.disableDC3()
        self.pmu.disableDC4()
        self.pmu.disableDC5() # this is actually the touch reset pin
        self.pmu.disableBLDO1()
        self.pmu.disableCPUSLDO()
        self.pmu.disableDLDO1()
        self.pmu.disableDLDO2()

        self.pmu.enableALDO1()# RTC VBAT
        self.pmu.enableALDO2()# TFT and BACKLIGHT   VDD
        self.pmu.enableALDO3()# Screen touch VDD
        self.pmu.enableALDO4()# Radio VDD
        self.pmu.enableBLDO2()# drv2605 enable

        self.pmu.setPowerKeyPressOffTime(self.pmu.XPOWERS_POWEROFF_6S)
        self.pmu.setPowerKeyPressOnTime(self.pmu.XPOWERS_POWERON_1S)

        self.pmu.disableTSPinMeasure() # no temperature pin

        self.pmu.enableBattDetection() # adcs
        self.pmu.enableVbusVoltageMeasure()
        self.pmu.enableBattVoltageMeasure()
        self.pmu.enableSystemVoltageMeasure()

        self.pmu.setChargingLedMode(self.pmu.XPOWERS_CHG_LED_OFF) # no chg led

        self.pmu.disableIRQ(self.pmu.XPOWERS_AXP2101_ALL_IRQ) # irqs

        self.pmu.enableIRQ(self.pmu.XPOWERS_AXP2101_BAT_INSERT_IRQ | self.pmu.XPOWERS_AXP2101_BAT_REMOVE_IRQ |
                           self.pmu.XPOWERS_AXP2101_VBUS_REMOVE_IRQ  | self.pmu.XPOWERS_AXP2101_PKEY_SHORT_IRQ |
                           self.pmu.XPOWERS_AXP2101_PKEY_LONG_IRQ, __debug__)
        self.pmu.clearIrqStatus()

        self.pmu.setPrechargeCurr(self.pmu.XPOWERS_AXP2101_PRECHARGE_50MA)
        self.pmu.setChargerConstantCurr(self.pmu.XPOWERS_AXP2101_CHG_CUR_100MA)
        self.pmu.setChargerTerminationCurr(self.pmu.XPOWERS_AXP2101_CHG_ITERM_25MA)
        self.pmu.setChargeTargetVoltage(self.pmu.XPOWERS_AXP2101_CHG_VOL_4V2)
        self.pmu.enableButtonBatteryCharge()

        # seems LDO2/DCDC5 is tied to RST
        self.pmu.disableDC5() # reset touch
        time.sleep_ms(15)
        self.pmu.setDC5Voltage(3300)
        self.pmu.enableDC5()


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
        pin21 = machine.Pin(21, machine.Pin.IN, machine.Pin.PULL_UP, drive=machine.Pin.DRIVE_0) #irq axp2101, 1.8v doesnt register as high in micropython and we cant change that
        #print("axp irq value:", pin21.value())
        pin21.irq(self.irq_pmu, trigger=machine.Pin.IRQ_FALLING, wake=machine.DEEPSLEEP | machine.SLEEP)
        pin16.irq(self.irq_touch, trigger= machine.Pin.IRQ_RISING)
        pin14.irq(self.irq_imu, trigger= machine.Pin.IRQ_RISING, wake=machine.DEEPSLEEP | machine.SLEEP)

        self.irq_touch_buffer_pos1 = bytearray(4) #pre-allocation
        self.irq_touch_buffer_pos2 = bytearray(4)
        self.irq_touch_present = False
        self.irq_feedback_present = False

    def init_backlight(self):
        sObject = Single.Settings.getSettingObject(Single.Settings.hardware)
        if sObject == None:
            sObject = {}
        if self.WatchVersion == WATCHS3:
            self.pwm_backlight = machine.PWM(machine.Pin(45), freq=1000, duty_u16=self.BACKLIGHT_PWM_DEFAULT)
        elif self.WatchVersion == WATCHV2:
            self.pwm_backlight = machine.PWM(machine.Pin(25), freq=1000, duty_u16=self.BACKLIGHT_PWM_DEFAULT)
        elif self.WatchVersion == WATCHV1:
            self.pwm_backlight = machine.PWM(machine.Pin(12), freq=1000, duty_u16=self.BACKLIGHT_PWM_DEFAULT)
        elif self.WatchVersion == WATCHV3:
            self.pwm_backlight = machine.PWM(machine.Pin(15), freq=1000, duty_u16=self.BACKLIGHT_PWM_DEFAULT)
        if sObject.get("Backlight") != None:
            if sObject["Backlight"] >= 0 and sObject["Backlight"] < 65536:
                self.pwm_backlight.duty_u16(int(sObject["Backlight"]))
        time.sleep_ms(2)
        if __debug__:
            print("pwm:", self.pwm_backlight)

    def __init__(self):
        self.WatchVersion = 0 # V1
        self.hardware = []
        Logger.log("Initializing Hardware...")
        machine.freq(240000000)

        self.WatchVersion = self.identify_version()
        self.display_lock = _thread.allocate_lock() # for locking render while we sleep, notably on V2 watch where we need to re-initialize at wake up
        self.display_lock.acquire()

        sensor_i2c = None
        if self.WatchVersion < WATCHS3:
            sensor_i2c = machine.SoftI2C(scl=machine.Pin(22), sda=machine.Pin(21), freq=100000) #we dont need i2c very fast here and that can save us 0.6 ma on BMA423
        else:
            sensor_i2c = machine.SoftI2C(scl=machine.Pin(11), sda=machine.Pin(10), freq=100000)

        if self.WatchVersion < WATCHS3:
            self.init_axp202()
            time.sleep_ms(20)
        else:
            self.init_axp2101(sensor_i2c)
            time.sleep_ms(20)

        self.init_st7789()

        self.init_backlight()

        Logger.log("CPU frequ: " + str(machine.freq()))
        Logger.log("Flash Size: " + str(esp.flash_size()))
        Logger.log("Unique ID: " + str(int.from_bytes(machine.unique_id(), 'big', False)))
        Logger.log("Reset Cause: " + str(machine.reset_cause()))
        Logger.log("Wake Cause: " + str(machine.wake_reason()))
        network.hostname(str(int.from_bytes(machine.unique_id(), 'big', False))) # in case of multiple watches on same network
        Logger.log("Hostname: " + str(network.hostname()))


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
        if gmt < 0:
            day -= 1
            weekday -= 1
            gmt += 24
            if day < 1:
                day += 31
            if weekday < 0:
                weekday += 7
        dtt = (self.rtc.year()+2000, self.rtc.month(), day, weekday, gmt, self.rtc.minutes(), self.rtc.seconds(), 0)
        machine.RTC().datetime(dtt)
        Logger.log("Time: " + str(machine.RTC().datetime()))


        bouf = bytearray(1)  # reset bma for when we shut down without cutting power because for some reason it likes to lose its register when esp32 resets
        bouf[0] = 0xB6 #reset command
        sensor_i2c.writeto_mem(bma423.BMA4_I2C_ADDR_SECONDARY, bma423.BMA4_CMD_ADDR, bouf) # there is trace of this being previously done in the drivers but not anymore?
        time.sleep_ms(5)
        self.imu = bma423.BMA423(sensor_i2c) # re-initialize
        self.imu.advance_power_save = 0
        bouf[0] = 0x08 | 0x02 << 4 | 0 << 7
        sensor_i2c.writeto_mem(bma423.BMA4_I2C_ADDR_SECONDARY, bma423.BMA4_ACCEL_CONFIG_ADDR, bouf)
        self.imu.accel_range = bma423.BMA4_ACCEL_RANGE_8G # 4g ??

        #print("BMA internal status:", self.imu.read_byte(bma423.BMA4_INTERNAL_STAT))
        #self.imu.feature_enable("wakeup")
        #self.imu.feature_enable("any_motion")
        #self.imu.feature_enable("tilt")
        #int1config = self.imu.read_byte(bma423.BMA4_INT1_IO_CTRL_ADDR)
        int1config = 0b01010
        self.imu.write_byte(bma423.BMA4_INT1_IO_CTRL_ADDR, int1config) # important irq pin settings
        #acc_config = 0x17
        #self.imu.write_byte(bma423.BMA4_ACCEL_CONFIG_ADDR, acc_config)
        #print("int1 imu:", self.imu.read_byte(bma423.BMA4_INT1_IO_CTRL_ADDR))
        self.imu.map_int(0, bma423.BMA423_WAKEUP_INT) # enable interrupt for wakeup (double tap) feature
        self.imu.map_int(1, 0)
        feat_data = self.imu.read_data(bma423.BMA4_FEATURE_CONFIG_ADDR, bma423.BMA423_FEATURE_SIZE)
        feat_data[bma423.BMA423_WAKEUP_OFFSET] = 0x03 # enable and sensitivity 2/7
        self.imu.write_data(bma423.BMA4_FEATURE_CONFIG_ADDR, feat_data)
        #print(list(feat_data))
        self.imu.advance_power_save = 0
        bouf[0] = 0x04
        sensor_i2c.writeto_mem(bma423.BMA4_I2C_ADDR_SECONDARY, bma423.BMA4_POWER_CTRL_ADDR, bouf)
        #self.imu.accel_enable = 1
        #print(self.imu.int_status())
        #print("BMA internal status:", self.imu.read_byte(bma423.BMA4_INTERNAL_STAT)) # todo: add check for that see if BMA is all good after init
        self.imu_int1 = 0
        self.imu_int2 = 0

        self.init_ft6336()

        self.gesture_startpos = (0,0) # gesture emulation

        if self.WatchVersion == WATCHS3:
            self.init_irq_s3()
        else:
            self.init_irq()

        state = machine.disable_irq()# you never know if something disabled them previously
        machine.enable_irq(state)


        self.wifi_lock = _thread.allocate_lock()
        self.wifi = None
        self.audio_buffer = bytearray(10000)
        self.audio_buffer_mv = memoryview(self.audio_buffer)
        self.audio = None
        self.audio_thread = None
        self.audio_lock = _thread.allocate_lock()
        self.audio_data_bytes = 0

        if self.WatchVersion == WATCHV1 or self.WatchVersion == WATCHV3:
            self.vibrator = machine.Pin(4, machine.Pin.OUT)
            self.vibrator.off() # if we crashed
            self.vibration_controller = None
            self.feedback1_on = False
            self.feedback2_on = False
            _thread.stack_size(256) # do that before EVERY new thread, see Single.py for explanation
            _thread.start_new_thread(self.feedback_frames, ()) # WATCHV1 and V3 vibration
        else:
            self.vibration_controller = adafruit_drv2605.DRV2605(sensor_i2c)
            self.vibration_controller._write_u8(0x01, 0b10000000) # reset
            time.sleep_ms(10)
            self.vibration_controller = adafruit_drv2605.DRV2605(sensor_i2c)
            self.vibration_controller.mode = adafruit_drv2605.MODE_INTTRIG
            self.vibrator = None

        machine.freq(160000000) #todo: set to user value (give a slider with choice between 240, 160, and 80 mhz?)
        self.display_lock.release()



    def get_battery_gauge(self): # 0-127
        if self.WatchVersion == WATCHS3:
            return self.pmu.getBatteryPercent()
        return self.pmu.getBattPercentage()

    def get_battery_voltage(self):
        if self.WatchVersion == WATCHS3:
            self.pmu.enableBattVoltageMeasure()
            return self.pmu.getBattVoltage()
        self.pmu.enableADC(1, 7)
        return self.pmu.getBattVoltage()

    def get_battery_current(self):
        if self.WatchVersion == WATCHS3:
            return 0
        self.pmu.enableADC(1, 6)
        return self.pmu.getBattDischargeCurrent()

    def charging(self):
        if self.WatchVersion == WATCHS3:
            return bool(self.pmu.isCharging())
        return bool(self.pmu.isChargeing())

    def lightsleep(self, time_ms, force = False, callback = None):
        if self.WatchVersion == WATCHS3:
            if self.pmu.isVbusIn() and not force:
                return False
        else:
            if self.pmu.isVBUSPlug() and not force: # are we plugged in?
                return False
        if (self.wifi_lock.locked() or self.audio_lock.locked()) and not force:
            return False
        elif (self.wifi_lock.locked() or self.audio_lock.locked()) and force:
            self.releaseWifi(force) # fuck them apps
            self.releaseAudio()
        if not self.display_lock.acquire():
            if force:
                self.display_lock.release()
                self.display_lock.acquire()# O(1) for the whole render pipeline with that, but quite slow... but not much more than even a simple direct draw
        # seems like to get more speed would need to do quite a lot on the C side of things
            else:
                return False
        machine.freq(240000000) # go fastly to go to sleep faster
        self.display.off() # unnecessary if pwm backlight
        self.display.sleep_mode(True)
        self.pwm_backlight.deinit()
        if self.WatchVersion == WATCHV2 or self.WatchVersion == WATCHS3:
            self.touch.power_mode = 3
            self.vibration_controller._write_u8(0x01, 0b01000000) # standby
        if self.WatchVersion != WATCHS3:
            self.pmu.disablePower(axp202_constants.AXP202_LDO4)
            self.pmu.disablePower(axp202_constants.AXP202_DCDC2)
            self.pmu.disablePower(axp202_constants.AXP202_LDO2)
            self.pmu.disablePower(axp202_constants.AXP202_LDO3)
            self.pmu.clearIRQ()
        # 0 = Active, 1 = Monitor, 2= Standby, 3= Hibernate
        #comes out of monitor whenever we touch
        # power mode is NOT documented but this should workif self.WatchVersion == WATCHV2: # todo: same section but for WatchS3
        # hibernation of FT6336 is up to 1.5 ma savings (active:4mA, monitor: 1.5mA, hibernate: 50 uA)
        # except lilygo didnt connect the reset pin and we need it to restart the display
        # monitor mode low rate of update good workaround?
        if self.WatchVersion == WATCHV1:
            self.touch.power_mode = 1
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
        if self.WatchVersion != WATCHS3:
            self.pmu.setDC3Voltage(Hardware.Vc3V3)
            self.pmu.enablePower(axp202_constants.AXP202_LDO2)
            self.pmu.enablePower(axp202_constants.AXP202_LDO3)
        if self.WatchVersion == WATCHV2:
            self.pmu.disablePower(axp202_constants.AXP202_EXTEN); # reset touch
            time.sleep_ms(5)
            self.pmu.enablePower(axp202_constants.AXP202_EXTEN);
            self.init_ft6336()
        if self.WatchVersion == WATCHS3:
            self.pmu.disableDC5() # reset touch
            time.sleep_ms(5)
            self.pmu.setDC5Voltage(3300)
            self.pmu.enableDC5()
            self.init_ft6336()
        if self.WatchVersion == WATCHV2 or self.WatchVersion == WATCHS3:
            self.vibration_controller._write_u8(0x01, 0b00000000) #exit standby
        self.init_backlight()
        self.display.sleep_mode(False)
        self.display.on()
        machine.freq(160000000) # no more fast, todo: see other place where this is
        self.display_lock.release()
        return True

    def blit_buffer_rgb565(self, array):
        self.display.blit_buffer(array, 0, 0, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT) # O(1) for the whole render pipeline with that, but quite slow... but not much more than even a simple direct draw
        # seems like to get more speed would need to do quite a lot on the C side of things

    @micropython.native
    def blit_framebuffer_rgb565(self, fbuf: oframebuf.WPFrameBuffer):
        if fbuf.minX == None: # drew nothing
            return
        buff_mv = memoryview(fbuf.buffer) # we no want copies
        uwidth = min(fbuf.maxX - fbuf.minX, self.DISPLAY_WIDTH)
        uheight = min(fbuf.maxY - fbuf.minY, self.DISPLAY_HEIGHT)

        if uwidth == self.DISPLAY_WIDTH: # whole lines so we can skip the copies
            if fbuf.minY == 0:
                self.display.blit_buffer(buff_mv, 0, 0, Hardware.DISPLAY_WIDTH, uheight)
            else:
                self.display.blit_buffer(buff_mv[fbuf.minY * 2 * self.DISPLAY_HEIGHT:(fbuf.minY + uheight) * 2 * self.DISPLAY_HEIGHT], 0, 0, Hardware.DISPLAY_WIDTH, uheight)
            if __debug__:
                print("update full line zone:", uwidth, uheight)
            return
        if uheight == self.DISPLAY_HEIGHT: # not worth doing copy, whole screen is updated
            self.display.blit_buffer(buff_mv, 0, 0, Hardware.DISPLAY_WIDTH, Hardware.DISPLAY_HEIGHT)
            return

        ustart = int(fbuf.minX * 2 + fbuf.minY * self.DISPLAY_WIDTH * 2)

        uend = int(uheight * uwidth) * 2

        if __debug__ and False:
            print("update zone:", fbuf.minX, fbuf.minY, ustart, uend, uwidth, uheight)

        tmp_buff = bytearray(uwidth * uheight * 2)
        for line in range(0, uheight):
            linestart = line * uwidth * 2
            tmp_buff[linestart : linestart + uwidth * 2] = buff_mv[ustart + line * self.DISPLAY_WIDTH * 2:ustart + line * self.DISPLAY_WIDTH * 2 + uwidth * 2]

        self.display.blit_buffer(tmp_buff, fbuf.minX, fbuf.minY, uwidth, uheight)
        fbuf.clear_max()

    @micropython.native
    def blit_framebuffer_rgb565_halfmode1(self, fbuf: oframebuf.WPFrameBuffer, line_off: int = 0): # blit only half the screen, line_off 0 or 1
        if fbuf.minX == None: # drew nothing
            return
        uwidth = min(fbuf.maxX - fbuf.minX, self.DISPLAY_WIDTH)
        buff_mv = memoryview(fbuf.buffer) # we no want copies
        for half_line in range(int(fbuf.minY / 2), int(fbuf.maxY / 2) - line_off + 1):
            self.display.blit_buffer(buff_mv[(half_line * 2 + line_off) * 2 * self.DISPLAY_WIDTH + fbuf.minX * 2:(half_line * 2 + line_off) * 2 * self.DISPLAY_WIDTH + (fbuf.minX + uwidth) * 2], fbuf.minX, half_line * 2 + line_off, uwidth, 1)
        if __debug__ and False:
            print("blitted zone:", fbuf.minY, fbuf.maxY)
        fbuf.clear_max()


    @micropython.native
    def blit_framebuffer_rgb565_halfmode2(self, fbuf: oframebuf.WPFrameBuffer, line_off: int = 0, chunk_size: int = 8): # blit only half the screen, line_off 0 or 1
        if fbuf.minX == None: # drew nothing
            return
        buff_mv = memoryview(fbuf.buffer) # we no want copies
        #for half_line in range(int(fbuf.minY / 2), int(fbuf.maxY / 2) - line_off):
        #    self.display.blit_buffer(buff_mv[(half_line * 2 + line_off) * 2 * self.DISPLAY_WIDTH:(half_line * 2 + line_off) * 2 * self.DISPLAY_WIDTH + self.DISPLAY_WIDTH * 2], 0, half_line * 2 + line_off, Hardware.DISPLAY_WIDTH, 1)
        rline_off = line_off * chunk_size
        if __debug__ and False:
            print("blitting zone:", fbuf.minY, fbuf.maxY)
        for half_line in range(fbuf.minY, fbuf.maxY - rline_off, chunk_size * 2): # less chunks = more faster
            self.display.blit_buffer(buff_mv[(half_line + rline_off) * 2 * self.DISPLAY_WIDTH:(half_line + rline_off) * 2 * self.DISPLAY_WIDTH + self.DISPLAY_WIDTH * chunk_size * 2], 0, half_line + rline_off, Hardware.DISPLAY_WIDTH, chunk_size)
        fbuf.clear_max()


    def readyAudio(self):
        if self.audio_thread != None:
            return False
        try:
            _thread.stack_size(Single.MP_THREAD_STACK_SIZE)
            _thread.start_new_thread(self.audio_threadf, ())
        except Exception as e:
            return False, e
        return True

    def audio_threadf(self):
        self.audio_thread = _thread.get_ident()
        self.audio = machine.I2S(0, sck=machine.Pin(26), ws=machine.Pin(25), sd=machine.Pin(33),
                mode=machine.I2S.TX,
                bits=16,
                format=machine.I2S.MONO,
                rate=4000,
                ibuf=4000)
        while self.audio != None:
            self.audio_lock.acquire()
            if self.audio == None:
                break
            if self.audio_data_bytes > 0:
                self.audio.write(self.audio_buffer_mv[0:self.audio_data_bytes])
                self.audio_data_bytes = 0
            self.audio_lock.release()
            time.sleep(0)


    def releaseAudio(self, blocking = True, timeout = -1):
        if self.audio_lock.acquire(blocking, timeout):
            self.audio.deinit()
            self.audio = None
            self.audio_lock.release()
            return True
        return False

    def writeAudio(self, data: bytearray, blocking = True, timeout = -1):
        print("sending pcm:", data)
        if self.audio_lock.acquire(blocking, timeout):
            self.audio_data_bytes = len(data)
            self.audio_buffer_mv[0:self.audio_data_bytes] = data
            self.audio_lock.release()
            return True
        return False


    def feedback1(self, _ = None):
        if self.vibrator:
            self.feedback1_on = True
        elif self.vibration_controller:
            self.vibration_controller.sequence[0] = adafruit_drv2605.Effect(2)
            self.vibration_controller.play()

    def feedback2(self, _ = None):
        if self.vibrator:
            self.feedback2_on = True
        elif self.vibration_controller:
            self.vibration_controller.sequence[0] = adafruit_drv2605.Effect(1)
            self.vibration_controller.play()

    def feedback_frames(self): # vibration handler
        while True:
            if self.feedback1_on:
                self.vibrator.on()
                time.sleep_ms(20)
                self.vibrator.off()
                self.feedback1_on = False
            elif self.feedback2_on:
                self.vibrator.on()
                time.sleep_ms(50)
                self.vibrator.off()
                self.feedback2_on = False
            time.sleep(0)

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
            if gmt < 0:
                day -= 1
                weekday -= 1
                gmt += 24
                if day < 1:
                    day += 31
                if weekday < 0:
                    weekday += 7
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
        if self.WatchVersion == WATCHS3:
            self.pmu.getIrqStatus()
            if self.pmu.isVbusRemoveIrq(): #workaround for brownouts and other bugs when disconnect USB
                machine.reset()
            if self.pmu.isPekeyShortPressIrq():
                self.feedback2()
                Single.Kernel.event(Events.PhysButtonEvent(0))
            if self.pmu.isPekeyLongPressIrq():
                self.feedback2()
                Single.Kernel.event(Events.PhysButtonEvent(1.5))
            self.pmu.clearIrqStatus()
            return
        self.pmu.readIRQ()
        if self.pmu.irqbuf[0] & axp202_constants.AXP202_VBUS_REMOVED_IRQ > 0: #workaround for brownouts and other bugs when disconnect USB
            machine.reset()
        if self.pmu.irqbuf[2] & axp202_constants.AXP202_VBUS_REMOVED_IRQ > 0: #actually AXP202_PEK_SHORTPRESS_IRQ!
            self.feedback2()
            Single.Kernel.event(Events.PhysButtonEvent(0))
        if self.pmu.irqbuf[2] & axp202_constants.AXP202_VBUS_VHOLD_LOW_IRQ > 0: #actually AXP202_PEK_LONGPRESS_IRQ!
            self.feedback2()
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
                    time.sleep(0)
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


