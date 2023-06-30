source /opt/esp-idf/export.sh
idf.py -D MICROPY_BOARD=LILYGO_TTGO_TWATCH_S3 -D USER_C_MODULES=../../../../ttgo.cmake clean
idf.py -D MICROPY_BOARD=LILYGO_TTGO_TWATCH_S3 -D USER_C_MODULES=../../../../ttgo.cmake build
