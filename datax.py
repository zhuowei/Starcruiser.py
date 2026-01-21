from cryptography.hazmat.primitives.asymmetric import ec
from com.oculus.atc import atc_pb2
from bumble import l2cap
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


class Datax:
    channel: l2cap.LeCreditBasedChannel
    ec_key = ec.generate_private_key(curve=ec.SECP256R1())

    # TODO(zhuowei): handle Wi-Fi and RFCOMM
    def __init__(self, channel: l2cap.LeCreditBasedChannel):
        self.channel = channel
        channel.sink = self.handle_received_packet

    def send_initial_request_encryption_packet(self):
        # send initial request encryption packet...
        request = atc_pb2.RequestEncryption(
            public_key=self.ec_key.public_key().public_bytes(
                encoding=Encoding.X962,
                format=PublicFormat.UncompressedPoint)[1:],
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
        self.channel.write(header + proto_data)

    def handle_received_packet(self, packet_data):
        print("received packet:", packet_data)
