source /opt/esp-idf/export.sh
idf.py -D MICROPY_BOARD=LILYGO_TTGO_TWATCH -D USER_C_MODULES=../../../../ttgo.cmake clean
idf.py -D MICROPY_BOARD=LILYGO_TTGO_TWATCH -D USER_C_MODULES=../../../../ttgo.cmake build
