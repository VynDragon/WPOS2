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
- Compiling with T-Watch board folder for MPY from this repository (not necessary, but let you use the full esp's flash and sets options that might do something)

