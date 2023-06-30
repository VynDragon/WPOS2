LILYGO_TTGO_TWATCH -> ports/esp32/boards

LILYGO_TTGO_TWATCH_S3 -> ports/esp32/boards

build.sh -> ports/esp32

build_s3.sh -> ports/esp32

ttgo.cmake -> ../ports (next to st7789_mpy and micropython git clone, which you put in the same folder, right? Otherwise you will need to edit this file and build.sh)


# For V1, V2, and V3

```
cd micropython/ports/esp32
rm -r build # important, compilation will fail if this folder is present
./build.sh
source /opt/esp-idf/export.sh
idf.py erase-flash
idf.py flash
```

# For S3

```
cd micropython/ports/esp32
rm -r build # important, compilation will fail if this folder is present
./build_s3.sh
source /opt/esp-idf/export.sh
idf.py erase-flash # s3 is a lot faster at boot so you might need to follow the instructions to put it into download mode (in the lilygo library github)
idf.py flash
```
