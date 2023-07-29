freeze("$(PORT_DIR)/modules")
include("$(MPY_DIR)/extmod/asyncio")

# Useful networking-related packages.
require("bundle-networking")

require("neopixel")
require("umqtt.robust")
require("umqtt.simple")
require("upysh")

require("aioble")
require("aioespnow")
require("lora")
require("ntptime")
