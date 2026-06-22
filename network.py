import struct

XOR_KEY = 173
SIGNATURE = 17652  # 0x44F4

def xor_crypt(data: bytes, key: int = XOR_KEY) -> bytes:
    """XORs bytes with the given key."""
    return bytes(b ^ key for b in data)

class PacketReader:
    """Helper to read binary types from incoming game packets."""
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def read_8(self) -> int:
        if self.offset + 1 > len(self.data):
            return 0
        val = self.data[self.offset]
        self.offset += 1
        return val

    def read_16(self) -> int:
        if self.offset + 2 > len(self.data):
            return 0
        val = struct.unpack_from('<H', self.data, self.offset)[0]
        self.offset += 2
        return val

    def read_32(self) -> int:
        if self.offset + 4 > len(self.data):
            return 0
        val = struct.unpack_from('<I', self.data, self.offset)[0]
        self.offset += 4
        return val

    def read_bool(self) -> bool:
        return self.read_8() != 0

    def read_string(self) -> str:
        length = self.read_8()
        if self.offset + length > len(self.data):
            return ""
        val = self.data[self.offset : self.offset + length].decode('ascii', errors='ignore')
        self.offset += length
        return val

    def read_string_n(self) -> str:
        """Reads remaining bytes as an ASCII string."""
        if self.offset >= len(self.data):
            return ""
        val = self.data[self.offset:].decode('ascii', errors='ignore')
        self.offset = len(self.data)
        return val

    def remaining_bytes(self) -> int:
        return max(0, len(self.data) - self.offset)


class PacketWriter:
    """Helper to build game packets in the correct binary format."""
    def __init__(self):
        self.buffer = bytearray()

    def write_8(self, val: int):
        self.buffer.append(val & 0xFF)
        return self

    def write_16(self, val: int):
        self.buffer.extend(struct.pack('<H', max(0, min(65535, val))))
        return self

    def write_32(self, val: int):
        self.buffer.extend(struct.pack('<I', val))
        return self

    def write_64(self, val: int):
        self.buffer.extend(struct.pack('<Q', val))
        return self

    def write_bool(self, val: bool):
        self.write_8(1 if val else 0)
        return self

    def write_string(self, val: str):
        if val is None:
            val = ""
        encoded = val.encode('ascii', errors='ignore')
        self.write_8(len(encoded))
        self.buffer.extend(encoded)
        return self

    def write_string_n(self, val: str):
        if val is None:
            val = ""
        self.buffer.extend(val.encode('ascii', errors='ignore'))
        return self

    def write_bytes(self, val: bytes):
        self.buffer.extend(val)
        return self

    def build(self) -> bytes:
        """Adds signature and length headers, and encrypts with XOR key."""
        payload = bytes(self.buffer)
        header = struct.pack('<HH', SIGNATURE, len(payload))
        full_packet = header + payload
        return xor_crypt(full_packet)
