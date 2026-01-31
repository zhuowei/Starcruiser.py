from cryptography.hazmat.primitives.asymmetric import ec
from com.oculus.atc import atc_pb2
from bumble import l2cap
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes, CipherContext
from cryptography.hazmat.primitives import hashes, hmac
import hashlib
import struct


class Datax:
    channel: l2cap.LeCreditBasedChannel
    ec_key = ec.generate_private_key(curve=ec.SECP256R1())
    remote_request_encryption_message: atc_pb2.RequestEncryption
    local_request_encryption_message: atc_pb2.RequestEncryption
    remote_enable_encryption_message: atc_pb2.EnableEncryption
    local_enable_encryption_message: atc_pb2.EnableEncryption
    encryption_encryptor: CipherContext = None
    encryption_hmac: hmac.HMAC = None
    decryption_decryptor: CipherContext = None
    decryption_hmac: hmac.HMAC = None
    encryption_hmac_base: int = None
    decryption_hmac_base: int = None

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

    def send_encrypted(self, data: bytes):
        print("send encrypted:", data.hex())
        encrypted_data = self.encryption_encryptor.update(data)
        encrypted_data_with_00_header = bytes([0]) + encrypted_data
        hmac = self.encryption_hmac.copy()
        hmac.update(
            struct.pack("<I", self.encryption_hmac_base) +
            encrypted_data_with_00_header)
        packet_hmac = hmac.finalize()
        self.encryption_hmac_base += 1
        self.encryption_hmac_base &= 0xffffffff
        output_packet_data = packet_hmac[0:8] + encrypted_data_with_00_header
        self.send_unencrypted(output_packet_data)

    def send_initial_request_encryption_packet(self):
        # send initial request encryption packet...
        # TODO(zhuowei): support newer protocols
        request = atc_pb2.RequestEncryption(public_key=self.public_key_bytes(),
                                            challenge=b"0123456789abcdef",
                                            elliptic_curve=0,
                                            supported_parameters=0)
        self.local_request_encryption_message = request
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
        print("received packet:", packet_data.hex())
        if self.decryption_decryptor != None and len(packet_data) > (
                1 if self.encryption_has_initial_40 else 0) + 8 + 1 and (
                    not self.encryption_has_initial_40
                    or packet_data[0] == 0x40):
            self.handle_received_encrypted_packet(packet_data)
        else:
            self.handle_received_unencrypted_packet(packet_data)

    def handle_received_encrypted_packet(self, packet_data: bytes):
        print("encrypted")
        hmac = self.decryption_hmac.copy()
        hmac.update(
            struct.pack("<I", self.decryption_hmac_base) + packet_data[8:])
        packet_hmac = hmac.finalize()
        self.decryption_hmac_base += 1
        self.decryption_hmac_base &= 0xffffffff
        print("hmac:", packet_hmac.hex())
        data_for_decryption = packet_data[9:]
        decrypted_data = self.decryption_decryptor.update(data_for_decryption)
        print("decrypted:", decrypted_data.hex())
        self.handle_received_unencrypted_packet(packet_data)

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
            parameters=protocol_version if protocol_version else None,
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
        parameters = self.remote_enable_encryption_message.parameters
        # TODO(zhuowei): actually get the right bits for these...
        self.multiplexing_enabled = parameters == 31
        self.encryption_has_initial_40 = parameters != 0
        # X962 UncompressedPoint = [0x04] + raw points
        peer_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            curve=ec.SECP256R1(),
            data=bytes([0x04]) +
            self.remote_enable_encryption_message.public_key)
        shared_secret = self.ec_key.exchange(algorithm=ec.ECDH(),
                                             peer_public_key=peer_public_key)
        print(shared_secret.hex())
        encryption_key = compute_encryption_key(
            shared_secret, self.remote_request_encryption_message.challenge,
            self.local_enable_encryption_message.seed, parameters)
        encryption_hmac_key = compute_hmac_key(
            shared_secret, self.remote_request_encryption_message.challenge,
            self.local_enable_encryption_message.seed, parameters)
        decryption_key = compute_encryption_key(
            shared_secret, self.local_request_encryption_message.challenge,
            self.remote_enable_encryption_message.seed, parameters)
        decryption_hmac_key = compute_hmac_key(
            shared_secret, self.local_request_encryption_message.challenge,
            self.remote_enable_encryption_message.seed, parameters)
        print("encryption_key:", encryption_key.hex())
        print("encryption_hmac_key:", encryption_hmac_key.hex())
        print("decryption_key:", decryption_key.hex())
        print("decryption_hmac_key:", decryption_hmac_key.hex())

        encryption_cipher = Cipher(
            algorithm=algorithms.AES256(encryption_key),
            mode=modes.CBC(self.local_enable_encryption_message.iv))
        self.encryption_encryptor = encryption_cipher.encryptor()
        self.encryption_hmac = hmac.HMAC(encryption_hmac_key, hashes.SHA256())

        decryption_cipher = Cipher(
            algorithm=algorithms.AES256(decryption_key),
            mode=modes.CBC(self.remote_enable_encryption_message.iv))
        self.decryption_decryptor = decryption_cipher.decryptor()
        self.decryption_hmac = hmac.HMAC(decryption_hmac_key, hashes.SHA256())

        self.encryption_hmac_base = self.local_enable_encryption_message.base
        self.decryption_hmac_base = self.remote_enable_encryption_message.base

        # send first encrypted message...
        self.send_identity_request_packet()

    def send_identity_request_packet(self):
        # what padding is this?
        header = bytes([
            0x80,
            0x08,
            0x80,
            0x02,
            0x81,
            0x00,
            0x00,
            0x24,
            0x02,
            0x00,
            0x30,
            0x00,
            0xc4,
            0xc4,
            0xc4,
            0xc4,
        ])
        self.send_encrypted(header)


def compute_encryption_key(shared_secret: bytes, challenge: bytes, seed: bytes,
                           parameters: int) -> bytes:
    shared_secret_hash = hashlib.sha256(shared_secret).digest()
    # TODO(zhuowei): multiplexing enabled...
    salt = hashlib.sha256(shared_secret_hash + challenge + seed).digest()
    # TODO(zhuowei): later protocol versions...
    return salt


def compute_hmac_key(shared_secret: bytes, challenge: bytes, seed: bytes,
                     parameters: int) -> bytes:
    return compute_encryption_key(shared_secret, challenge, seed, parameters)
