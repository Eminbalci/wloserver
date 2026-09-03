"""
Unit tests for Client Version & File Integrity Validation System.
Validates protocol handling of authentic Opcode 0 disconnect errors (e.g. 0x41 'Wrong Version').
"""

import unittest
import asyncio
from server.network import PacketReader, PacketWriter, SIGNATURE, xor_crypt
from server.version_validator import ClientVersionValidator, ClientDisconnectReason
from server.handlers import handle_63_login


class MockSession:
    def __init__(self):
        self.packets_sent = []
        self.ip = "127.0.0.1"
        self.user_id = None
        self.username = None
        self.cipher = None
        self.is_gm = False
        self.pkable = True
        self.joinable = True
        self.tradable = True

    async def send_packet(self, packet_writer):
        raw_payload = packet_writer.to_bytes()
        built_encrypted = packet_writer.build()
        self.packets_sent.append((raw_payload, built_encrypted))


class MockDatabase:
    def __init__(self):
        self.config = {
            "enforce_client_version": "1",
            "allowed_client_versions": "1205,1206,1207,1208,1210",
            "expected_item_dat_hash": ""
        }

    def get_config(self, key, default=""):
        return self.config.get(key, default)

    def set_config(self, key, value):
        self.config[key] = str(value)

    def get_character_by_id(self, char_id):
        return None

    def verify_user(self, username, password):
        if username == "valid_user" and password == "valid_pass":
            return {
                "id": 1,
                "username": "valid_user",
                "character1_id": None,
                "character2_id": None,
                "cipher": None,
                "banned": False,
                "is_gm": False
            }
        return None


class MockServer:
    def __init__(self, db=None):
        self.db = db or MockDatabase()
        self.sessions = {}
        self.version_validator = ClientVersionValidator(self.db)

    def serialize_character_slot(self, char):
        return b""


class TestVersionValidation(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabase()
        self.server = MockServer(self.db)
        self.session = MockSession()

    def test_client_disconnect_reason_values(self):
        """Validates that reason codes match reverse-engineered aLogin.exe table."""
        self.assertEqual(int(ClientDisconnectReason.WRONG_VERSION), 65)  # 0x41
        self.assertEqual(int(ClientDisconnectReason.ITEM_DAT_ERROR), 69)  # 0x45
        self.assertEqual(int(ClientDisconnectReason.DATA_ALTERED), 17)   # 0x11
        self.assertEqual(int(ClientDisconnectReason.UPDATE_GAME_FILES), 16)  # 0x10

    def test_build_disconnect_packet(self):
        """Checks that disconnect packet has opcode 0 and correct reason code."""
        pkt = ClientVersionValidator.build_disconnect_packet(65)
        payload = pkt.to_bytes()
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0], 0)
        self.assertEqual(payload[1], 65)

        # Build with XOR encryption & signature
        built = pkt.build()
        dec = xor_crypt(built)
        sig = int.from_bytes(dec[:2], 'little')
        length = int.from_bytes(dec[2:4], 'little')
        self.assertEqual(sig, SIGNATURE)
        self.assertEqual(length, 2)
        self.assertEqual(dec[4:], bytes([0, 65]))

    def test_validator_allowed_versions(self):
        validator = ClientVersionValidator()
        self.assertIn(1205, validator.get_allowed_versions())

        # Test valid version
        is_valid, code, msg = validator.validate(1205)
        self.assertTrue(is_valid)
        self.assertEqual(code, 0)

        # Test invalid version
        is_valid, code, msg = validator.validate(9999)
        self.assertFalse(is_valid)
        self.assertEqual(code, int(ClientDisconnectReason.WRONG_VERSION))

    def test_login_handler_rejects_wrong_version(self):
        """Simulates AC 63 Sub 4 with an unapproved client version (e.g. 1209)."""
        # Set allowed versions to 1205, 1206 (1209 is forbidden)
        self.server.version_validator.set_allowed_versions([1205, 1206])

        # Client builds packet: Opcode 63 (0x3F), Sub 4, Version 1209 (0x04B9), User, Pass
        pw = PacketWriter()
        pw.write_8(63).write_8(4)
        pw.write_16(1209)
        pw.write_string("valid_user")
        pw.write_string("valid_pass")
        pw.write_bytes(bytes([7, 216, 235, 234, 224, 225, 233, 236, 235]))

        reader = PacketReader(pw.to_bytes())
        # First byte is read by dispatcher
        op = reader.read_8()
        self.assertEqual(op, 63)

        asyncio.run(handle_63_login.handle(self.server, self.session, reader))

        # Check that server sent disconnect packet: Opcode 0, Reason 65 (0x41)
        self.assertGreaterEqual(len(self.session.packets_sent), 1)
        first_payload = self.session.packets_sent[0][0]
        self.assertEqual(first_payload, bytes([0, 65]))

    def test_login_handler_accepts_valid_version(self):
        """Simulates AC 63 Sub 4 with an approved client version (1205)."""
        self.server.version_validator.set_allowed_versions([1205])

        pw = PacketWriter()
        pw.write_8(63).write_8(4)
        pw.write_16(1205)
        pw.write_string("valid_user")
        pw.write_string("valid_pass")

        reader = PacketReader(pw.to_bytes())
        reader.read_8()

        asyncio.run(handle_63_login.handle(self.server, self.session, reader))

        # Check that server sent AC 63 Sub 1 (character list)
        self.assertGreaterEqual(len(self.session.packets_sent), 1)
        first_payload = self.session.packets_sent[0][0]
        self.assertEqual(first_payload[0], 63)
        self.assertEqual(first_payload[1], 1)

    def test_validator_file_integrity_check(self):
        """Validates file integrity hash verification if enabled."""
        validator = ClientVersionValidator()
        validator.set_allowed_versions([1205])
        expected_hash = bytes([0xDE, 0xAD, 0xBE, 0xEF])
        validator.set_expected_file_hash(expected_hash)

        # Fails when payload missing
        valid, code, _ = validator.validate(1205, b"")
        self.assertFalse(valid)
        self.assertEqual(code, int(ClientDisconnectReason.ITEM_DAT_ERROR))

        # Fails when payload does not contain hash
        valid, code, _ = validator.validate(1205, bytes([1, 2, 3, 4]))
        self.assertFalse(valid)
        self.assertEqual(code, int(ClientDisconnectReason.ITEM_DAT_ERROR))

        # Succeeds when payload contains expected hash
        valid, code, _ = validator.validate(1205, bytes([0xAA, 0xDE, 0xAD, 0xBE, 0xEF, 0xBB]))
        self.assertTrue(valid)
        self.assertEqual(code, 0)

    def test_validator_enforcement_toggle(self):
        """Checks disabling version enforcement permits any version."""
        validator = ClientVersionValidator()
        validator.set_allowed_versions([1205])
        validator.set_enforced(False)

        valid, code, _ = validator.validate(9999)
        self.assertTrue(valid)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
