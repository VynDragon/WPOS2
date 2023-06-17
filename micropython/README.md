LILYGO_TTGO_TWATCH -> ports/esp32/boards

build.sh -> ports/esp32

ttgo.cmake -> ../ports (next to st7789_mpy and micropython git clone, which you put in the same folder, right? Otherwise you will need to edit this file and build.sh)


```
cd micropython/ports/esp32
rm -r build # important, compilation will fail if this folder is present
./build.sh
source /opt/esp-idf/export.sh
idf.py erase-flash
idf.py flash
```
