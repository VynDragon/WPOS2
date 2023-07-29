import uasyncio
import bluetooth
import aioble
import machine
import Single

_ADV_INTERVAL_US = const(250000)
_UUID_SERVICE_ALERT_NOTIFICATION = bluetooth.UUID(0x1811)
_UUID_SERVICE_BATTERY_SERVICE = bluetooth.UUID(0x180F)
_UUID_SERVICE_DEVICE_INFORMATION = bluetooth.UUID(0x180A)
_UUID_SERVICE_GENERIC_ACCESS = bluetooth.UUID(0x1800)
_UUID_SERVICE_GENERIC_ATTRIBUTE = bluetooth.UUID(0x1801)
_UUID_SERVICE_HUMAN_INTERFACE_DEVICE = bluetooth.UUID(0x1812)
_UUID_SERVICE_LOCATION_AND_NAVIGATION = bluetooth.UUID(0x1819)
_UUID_SERVICE_PHONE_ALERT_STATUS = bluetooth.UUID(0x180E)
_UUID_SERVICE_SCAN_PARAMETERS = bluetooth.UUID(0x1813)
_UUID_SERVICE_TX_POWER = bluetooth.UUID(0x1804)
_UUID_SERVICE_USER_DATA = bluetooth.UUID(0x181C)
_UUID_SERVICE_LINK_LOSS = bluetooth.UUID(0x1803)


class Bluetooth:
 
    def __init__(self):
        self.connectionBLE = None
        #servicesBLE = [_UUID_SERVICE_DEVICE_INFORMATION, _UUID_SERVICE_ALERT_NOTIFICATION, _UUID_SERVICE_BATTERY_SERVICE]
        self.servicesBLE = [_UUID_SERVICE_DEVICE_INFORMATION, _UUID_SERVICE_BATTERY_SERVICE]
        device_infos = aioble.Service(_UUID_SERVICE_DEVICE_INFORMATION)
        aioble.Characteristic(device_infos, bluetooth.UUID(0x2A29), read=True, notify=False, initial="Lilygo")
        aioble.Characteristic(device_infos, bluetooth.UUID(0x2A24), read=True, initial="T-WATCH")
        aioble.Characteristic(device_infos, bluetooth.UUID(0x2A25), read=True, initial="idk")
        aioble.Characteristic(device_infos, bluetooth.UUID(0x2A26), read=True, initial="0")
        aioble.Characteristic(device_infos, bluetooth.UUID(0x2A27), read=True, initial="idk")
        aioble.Characteristic(device_infos, bluetooth.UUID(0x2A28), read=True, initial="0")
        aioble.Characteristic(device_infos, bluetooth.UUID(0x2A23), read=True, initial=str(int.from_bytes(machine.unique_id(), 'big', False)))
        #aioble.Characteristic(device_infos, 0x2A2A, read=True, initial="???")
        #aioble.Characteristic(device_infos, 0x2A50, read=True, initial="???")
        aioble.register_services(device_infos)
        battery_infos = aioble.Service(_UUID_SERVICE_BATTERY_SERVICE)
        self.battery_level_characteristic = aioble.Characteristic(battery_infos, bluetooth.UUID(0x2A19), read=True, notify=True, initial="100")
        aioble.register_services(battery_infos)

    async def _connectBLE(self):
        return await aioble.advertise(
                _ADV_INTERVAL_US,
                name="Espruino T-Watch",
                services=self.servicesBLE,
                appearance=0x00C2, # smart watch
                manufacturer=(0xabcd, b"1234"),
            )

    async def connectBLE(self):
        while self.connectionBLE == None if True else not self.connectionBLE.is_connected():
            self.connectionBLE = await self._connectBLE()

    def processBLE(self):
        if self.connectionBLE == None if True else not self.connectionBLE.is_connected():
            return
        self.battery_level_characteristic.write(str(Single.Hardware.get_battery_gauge()))
