# A firmware for Lilygo T-Watch 2020 and S3 written in micropython
## Requirements:
- Micropython (with dummy bit SPI setting added in ports/esp32/machine_hw_spi.c if possible to maximize SPI speed)
- st7789_mpy library
- Frozen modules (ports/esp32/modules, or dont freeze them, im not your mom):
  - pcf8653 by lewis he
  - writer by peterhinch for fonts
  - axp202 by lewis he (with the constants file renamed to axp202_constants and the main file modified accordingly)
  - bma423 by franz schaefer
  - ft6x36 by lbuque
  - MicroPython Human Interface Device library
  - png 'Pure Python PNG Reader/Writer'
  - itertools.py (required by png)
  - DRV2605 driver from https://github.com/VynDragon/Adafruit_MicroPython_DRV2605
  - axp2101 and i2cinterface files from lewis he at: https://github.com/lewisxhe/XPowersLib/tree/master/Micropython/src
- Compiling with T-Watch board folder for MPY from this repository
### YOU CAN ALSO USE THE MODULES.TAR.GZ FILE IN THIS REPOSITORY


## Installing:
- Go to micropython folder from this repository and follow instructions
- Copy ALL the .py, .fw, and .gz files from this repository to the watch, keeping the folders (CopyToWatch.sh might do it all for you)
- devices.json is optional, look into Hardware.py for why (but might come handy to you)

## Modifying for other platforms
For other esp32 platforms, all the code that is platform-specific should be in Hardware.py (make yourself a new Hardware.py), with the exception of the blit command in render thread in Kernel.py (FOR NOW)
For a different MCU, it should be mostly the same with more exceptions (stuffs like timers may not match, amount of ram, random platform-specific functions i forgot in the code...)


## Notes
Dont expect fast display on anything but T-WATCH S3.

I've also capped the FPS to 20 by default, there is a way to uncap it from applications (but be aware that blitting the full screen takes at minimum about 40ms on T-WATCH 2020 V1)

T-Watch 2020 V1 uses about 1.6ma in light sleep with current code


Currently Only T-Watch V1, T-Watch V2, and T-Watch S3 have been tested, I do not own any V3.

## Demo of the render system

[badapple.webm](https://github.com/VynDragon/WPOS2/assets/3176238/f5cddced-452e-42a6-afce-37359ef99bf2)

This uses 2 threads in the kernel and one to feed data and time within a program
