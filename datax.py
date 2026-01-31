from cryptography.hazmat.primitives.asymmetric import ec
from com.oculus.atc import atc_pb2
from bumble import l2cap
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


class Datax:
    channel: l2cap.LeCreditBasedChannel
    ec_key = ec.generate_private_key(curve=ec.SECP256R1())
    remote_request_encryption_message: atc_pb2.RequestEncryption
    local_request_encryption_message: atc_pb2.RequestEncryption
    remote_enable_encryption_message: atc_pb2.EnableEncryption
    local_enable_encryption_message: atc_pb2.EnableEncryption
    decryption_key = None

    # TODO(zhuowei): handle Wi-Fi and RFCOMM
    def __init__(self, channel: l2cap.LeCreditBasedChannel):
        self.channel = channel
        self.encryption_has_initial_40 = True
        self.multiplexing_enabled = True
        channel.sink = self.handle_received_packet

    def public_key_bytes(self) -> bytes:
        return self.ec_key.public_key().public_bytes(
            encoding=Encoding.X962, format=PublicFormat.UncompressedPoint)[1:]

    def send_unencrypted(self, data: bytes):
        print("send unencrypted:", data.hex())
        self.channel.write(data)

    def send_initial_request_encryption_packet(self):
        # send initial request encryption packet...
        request = atc_pb2.RequestEncryption(public_key=self.public_key_bytes(),
                                            challenge=b"0123456789abcdef",
                                            elliptic_curve=0,
                                            supported_parameters=31)
        self.local_enable_encryption_message = request
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
        self.send_unencrypted(header + proto_data)

    def handle_received_packet(self, packet_data: bytes):
        print("received packet:", packet_data)
        if self.decryption_key != None and len(packet_data) > (
                1 if self.encryptionHasInitial40 else 0) + 8 + 1 and (
                    not self.encryptionHasInitial40 or packet_data[0] == 0x40):
            self.handle_received_encrypted_packet(packet_data)
        else:
            self.handle_received_unencrypted_packet(packet_data)

    def handle_received_encrypted_packet(self, packet_data: bytes):
        print("encrypted")

    def handle_received_unencrypted_packet(self, data: bytes):
        # 0x03 is error
        if len(data) > 8 and data[0] == 0x80 and data[4] != 0x03:
            payload_header_off = 8 if (data[2] & 0x80) == 0x80 else 4
            proto_data = data[payload_header_off + 4:]
            proto_type = data[payload_header_off + 3]
            if proto_type == atc_pb2.MessageTypeSetup.REQUEST_ENCRYPTION:
                msg = atc_pb2.RequestEncryption.FromString(proto_data)
                print(msg)
                self.remote_request_encryption_message = msg
                self.send_enable_encryption_packet()
            elif proto_type == atc_pb2.MessageTypeSetup.ENABLE_ENCRYPTION:
                msg = atc_pb2.EnableEncryption.FromString(proto_data)
                print(msg)
                self.remote_enable_encryption_message = msg
                self.handle_enable_encryption()
            else:
                print("unknown type", proto_type)

    def send_enable_encryption_packet(self):
        if not self.encryption_has_initial_40:
            protocol_version = 0
        elif not self.multiplexing_enabled:
            protocol_version = 7
        else:
            protocol_version = 31
        request = atc_pb2.EnableEncryption(
            public_key=self.public_key_bytes(),
            seed=b"A" * 0x20,  # TODO: zhuowei: randomly generate this
            iv=b"B" * 0x10,  # TODO: zhuowei: randomly generate this
            base=0x41424344,  # TODO: zhuowei: randomly generate this
            parameters=protocol_version,
        )
        self.local_enable_encryption_message = request
        proto_data = request.SerializeToString()
        header = bytes([
            0x80,
            len(proto_data) + 4, 0x00, 0x01, 0x02, 0x00, 0x00,
            atc_pb2.MessageTypeSetup.ENABLE_ENCRYPTION
        ])
        self.send_unencrypted(header + proto_data)

    def handle_enable_encryption(self):
        # TODO(zhuowei): actually get the right bits for these...
        self.multiplexing_enabled = self.remote_enable_encryption_message.parameters == 31
        self.encryption_has_initial_40 = self.remote_enable_encryption_message.parameters != 0
        # X962 UncompressedPoint = [0x04] + raw points
        peer_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            curve=ec.SECP256R1(),
            data=bytes([0x04]) +
            self.remote_enable_encryption_message.public_key)
        shared_secret = self.ec_key.exchange(algorithm=ec.ECDH(),
                                             peer_public_key=peer_public_key)
        print(shared_secret.hex())
        pass
        # TODO(zhuowei): setup encryption
