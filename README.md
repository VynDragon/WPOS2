# A firmware for Lilygo T-Watch 2020 (and soon S3 version) written in micropython
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
- Compiling with T-Watch board folder for MPY from this repository (not strictly necessary, but let you use the full esp's flash and sets options that might do something)

## Installing:
- Go to micropython folder from this repository and follow instructions
- Copy ALL the .py and .fw (and ONLY the .py and .fw, there is only python files that go in the watch for now) files from this repository to the watch, keeping the folders (CopyToWatch.sh might do it all for you)
- devices.json is optional, look into Hardware.py for why (but might come handy to you)

## Modifying for other platforms
For other esp32 platforms, all the code that is platform-specific should be in Hardware.py (make yourself a new Hardware.py), with the exception of the blit command in render thread in Kernel.py (FOR NOW)
For a different MCU, it should be mostly the same with more exceptions (stuffs like timers may not match, amount of ram, random platform-specific functions i forgot in the code...)


## Notes
Dont expect fast display on anything but T-WATCH S3, the 2020 watches uses the wrong MOSI pin.

I've also capped the FPS to 10 by default, there is a way to uncap it from applications (but be aware that blitting the full screen takes at minimum about 40ms on T-WATCH 2020 V1)

T-Watch 2020 V1 uses about 1.6ma in light sleep with current code


Currently Only T-Watch V1 and T-Watch V2 have been tested, I do not own any V3.
