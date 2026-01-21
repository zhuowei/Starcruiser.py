import asyncio
import struct

import bumble.logging
from bumble import core, hci, rfcomm, transport, utils, hfp, sdp, avrcp, l2cap, gatt_client
from bumble.colors import color
from bumble.device import Connection, Device, DeviceConfiguration
from bumble.l2cap import ClassicChannelSpec

from com.oculus.atc import atc_pb2

hci_transport = "android-netsim"
device_config = "device.json"
address = "BB:BB:BB:00:00:02/P@"

FB_PSM_SERVICE_UUID = "FD5F"
FB_PSM_CHARACTERISTIC_UUID = "05ACBE9F-6F61-4CA9-80BF-C8BBB52991C0"


async def airshield_handshake(channel: l2cap.LeCreditBasedChannel):
    # send initial request encryption packet...
    request = atc_pb2.RequestEncryption(
        public_key=
        b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        challenge=b"0123456789abcdef",
        elliptic_curve=0,
        supported_parameters=31)
    proto_data = request.SerializeToString()
    header = bytes([
        0x80,
        len(proto_data) + 4,
        0x80,
        0x01,
        0x81,
        0x00,
        0x00,
        0x05,
        0x02,
        0x00,
        0x00,
        0x01,
    ])
    channel.write(header + proto_data)


async def get_fb_psm(connection: Connection) -> int:
    gattclient = connection.gatt_client
    fb_psm_service_list = await gattclient.discover_service(FB_PSM_SERVICE_UUID
                                                            )
    fb_psm_service = fb_psm_service_list[0]
    fb_psm_characteristics = await fb_psm_service.discover_characteristics(
        [FB_PSM_CHARACTERISTIC_UUID])
    fb_psm_characteristic = fb_psm_characteristics[0]
    fb_psm_port_bytes = await fb_psm_characteristic.read_value()
    fb_psm_port = struct.unpack("<HH", fb_psm_port_bytes)[1]
    print(fb_psm_service, fb_psm_characteristic, fb_psm_port)
    return fb_psm_port


async def main():
    bumble.logging.setup_basic_logging("DEBUG")
    async with await transport.open_transport(hci_transport) as (
            hci_source,
            hci_sink,
    ):
        device = Device.from_config_file_with_hci(device_config, hci_source,
                                                  hci_sink)
        await device.power_on()
        async with await device.connect(
                address,
                transport=core.PhysicalTransport.LE,
                own_address_type=hci.OwnAddressType.PUBLIC) as connection:
            await connection.encrypt()
            fb_psm_port = await get_fb_psm(connection)
            channel = await connection.create_l2cap_channel(
                l2cap.LeCreditBasedChannelSpec(psm=fb_psm_port))
            print(channel)
            await airshield_handshake(channel)
            await asyncio.sleep(1)


asyncio.run(main())
