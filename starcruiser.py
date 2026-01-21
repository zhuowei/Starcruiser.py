import asyncio
import struct

import bumble.logging
from bumble import core, hci, rfcomm, transport, utils, hfp, sdp, avrcp, l2cap, gatt_client
from bumble.colors import color
from bumble.device import Connection, Device, DeviceConfiguration
from bumble.l2cap import ClassicChannelSpec

hci_transport = "android-netsim"
device_config = "device.json"
address = "BB:BB:BB:00:00:02/P@"

FB_PSM_CHARACTERISTIC_UUID = "05ACBE9F-6F61-4CA9-80BF-C8BBB52991C0"


async def main():
    bumble.logging.setup_basic_logging("INFO")
    async with await transport.open_transport(hci_transport) as (
            hci_source,
            hci_sink,
    ):
        device = Device.from_config_file_with_hci(device_config, hci_source,
                                                  hci_sink)
        await device.power_on()
        connection = await device.connect(
            address,
            transport=core.PhysicalTransport.LE,
            own_address_type=hci.OwnAddressType.PUBLIC)
        await connection.encrypt()
        gattclient = connection.gatt_client
        fb_psm_service_list = await gattclient.discover_service("FD5F")
        fb_psm_service = fb_psm_service_list[0]
        fb_psm_characteristics = await fb_psm_service.discover_characteristics(
            [FB_PSM_CHARACTERISTIC_UUID])
        fb_psm_characteristic = fb_psm_characteristics[0]
        fb_psm_port_bytes = await fb_psm_characteristic.read_value()
        fb_psm_port = struct.unpack("<HH", fb_psm_port_bytes)[1]
        print(fb_psm_service, fb_psm_characteristic, fb_psm_port)
        channel = await connection.create_l2cap_channel(
            l2cap.LeCreditBasedChannelSpec(psm=fb_psm_port))
        print(channel)
        await connection.disconnect()
        await asyncio.sleep(1)


asyncio.run(main())
