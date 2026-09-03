"""
Client Version and Integrity Validator module.

Handles client version inspection, file integrity check validation,
and authentic disconnect/error packet generation (Opcode 0x00) matching
the official Wonderland Online aLogin.exe client.
"""

from enum import IntEnum
import logging
from typing import Optional, Set, Tuple

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class ClientDisconnectReason(IntEnum):
    """
    Authentic Wonderland Online disconnect error codes dispatched via Opcode 0x00.
    Mapped directly to aLogin.exe FUN_002f21b8 switch jump table.
    """
    TOO_MANY_PACKETS = 0       # 0x00
    FAIL_QA_3_TIMES = 1        # 0x01
    WRONG_PWD = 2              # 0x02
    DISCONNECTED = 3           # 0x03
    ILLEGAL_ACTIVITY_1 = 4     # 0x04
    ILLEGAL_ACTIVITY_2 = 5     # 0x05
    EVENT_ERROR = 6            # 0x06
    INCORRECT_TRIGGER = 7      # 0x07
    WRONG_EVENT_TABLE = 8      # 0x08
    TABLE_ERROR = 9            # 0x09
    LIMITER_TRIGGERED = 10     # 0x0A
    ILLEGAL_PRESS = 11         # 0x0B
    STREAM_VIOLATION = 12      # 0x0C
    MOVEMENT_TOO_FAST = 13     # 0x0D
    DELETE_SUCCESSFUL = 14     # 0x0E
    BLOCKED_IP = 15            # 0x0F
    UPDATE_GAME_FILES = 16     # 0x10
    DATA_ALTERED = 17          # 0x11
    REPEATED_LOGIN = 18        # 0x12
    ABNORMAL_DC = 19           # 0x13
    ABNORMAL_SAFE_DATA = 20    # 0x14
    INVALID_PACKET_DATA = 21   # 0x15
    NAME_CHANGED = 22          # 0x16
    PASSWORD_TOO_SHORT = 23    # 0x17
    DUPLICATED_NAME = 24       # 0x18
    EVENT_TRIGGER_ERROR = 25   # 0x19
    LOGIN_ERROR_DC = 26        # 0x1A
    FIREWALL_DC = 27           # 0x1B
    TOO_MUCH_DATA = 28         # 0x1C
    ACCOUNT_LOCK = 29          # 0x1D
    LOGIN_ID_UNAVAILABLE = 30  # 0x1E
    INVALID_SLOT = 32          # 0x20
    RELAY_SERVER_DC = 56       # 0x38
    CONNECTION_LOST = 57       # 0x39
    SERVER_IS_BUSY = 58        # 0x3A
    INCORRECT_PASSWORD = 59    # 0x3B
    MINIGAME_ERROR_DC = 60     # 0x3C
    ILLEGAL_APP_USED = 61      # 0x3D
    WRONG_VERSION = 65         # 0x41 (Authentic 'Wrong Version' dialog)
    IP_ZONE_BLOCKED = 66       # 0x42
    EXTERNAL_DC = 67           # 0x43
    IP_ADDRESS_ERROR = 68      # 0x44
    ITEM_DAT_ERROR = 69        # 0x45 (Authentic 'Item.dat File Error' dialog)
    INSTANCE_PURGED = 70       # 0x46
    MAX_LOGINS_REACHED = 72    # 0x48


class ClientVersionValidator:
    """
    Validates client version numbers and file integrity verification payloads
    received during AC 63 Sub 4 authentication attempts.
    """

    DEFAULT_ALLOWED_VERSIONS = {1205, 1206, 1207, 1208, 1209, 1210}

    def __init__(self, db=None) -> None:
        self.db = db
        self._enforce: bool = True
        self._allowed_versions: Set[int] = set(self.DEFAULT_ALLOWED_VERSIONS)
        self._expected_file_hash: Optional[bytes] = None
        self._load_config()

    def _load_config(self) -> None:
        """Loads version validation configuration from database if available."""
        if not self.db:
            return

        try:
            enforce_str = self.db.get_config("enforce_client_version", "1")
            self._enforce = enforce_str.strip().lower() in ("1", "true", "yes", "on")

            versions_str = self.db.get_config("allowed_client_versions", "")
            if versions_str.strip():
                parsed = set()
                for part in versions_str.split(","):
                    part = part.strip()
                    if part.isdigit():
                        parsed.add(int(part))
                if parsed:
                    self._allowed_versions = parsed

            file_hash_hex = self.db.get_config("expected_item_dat_hash", "")
            if file_hash_hex.strip():
                try:
                    self._expected_file_hash = bytes.fromhex(file_hash_hex.strip())
                except ValueError:
                    self._expected_file_hash = None
        except Exception as e:
            logger.warning(f"[VersionValidator] Failed loading config: {e}")

    @property
    def is_enforced(self) -> bool:
        """Returns True if client version enforcement is active."""
        return self._enforce

    def set_enforced(self, enforced: bool) -> None:
        """Enables or disables client version checking."""
        self._enforce = bool(enforced)
        if self.db:
            self.db.set_config("enforce_client_version", "1" if self._enforce else "0")

    def get_allowed_versions(self) -> Set[int]:
        """Returns the set of currently accepted client versions."""
        return set(self._allowed_versions)

    def set_allowed_versions(self, versions: Set[int] | list[int]) -> None:
        """Sets accepted client versions and persists to database."""
        self._allowed_versions = {int(v) for v in versions if int(v) > 0}
        if self.db:
            v_str = ",".join(str(v) for v in sorted(self._allowed_versions))
            self.db.set_config("allowed_client_versions", v_str)

    def add_allowed_version(self, version: int) -> None:
        """Adds a single allowed version."""
        self._allowed_versions.add(int(version))
        if self.db:
            v_str = ",".join(str(v) for v in sorted(self._allowed_versions))
            self.db.set_config("allowed_client_versions", v_str)

    def remove_allowed_version(self, version: int) -> None:
        """Removes a single allowed version."""
        self._allowed_versions.discard(int(version))
        if self.db:
            v_str = ",".join(str(v) for v in sorted(self._allowed_versions))
            self.db.set_config("allowed_client_versions", v_str)

    def set_expected_file_hash(self, file_hash: Optional[bytes]) -> None:
        """Sets expected client Data\\Item.Dat file verification hash bytes."""
        self._expected_file_hash = file_hash
        if self.db:
            val = file_hash.hex() if file_hash else ""
            self.db.set_config("expected_item_dat_hash", val)

    def validate(
        self,
        client_version: int,
        verification_payload: bytes = b""
    ) -> Tuple[bool, int, str]:
        """
        Validates client build version and file integrity checks.
        
        Parameters:
            client_version: 16-bit unsigned integer from login packet header.
            verification_payload: Remaining bytes containing file/dat verification tokens.
            
        Returns:
            Tuple of (is_valid: bool, error_code: int, message: str)
            error_code corresponds to ClientDisconnectReason enum.
        """
        if not self._enforce:
            return True, 0, "Enforcement disabled"

        # 1. Version check
        if client_version not in self._allowed_versions:
            logger.warning(
                f"[VersionValidator] Version mismatch: client version {client_version} (0x{client_version:04X}) "
                f"not in allowed list: {sorted(self._allowed_versions)}"
            )
            return False, int(ClientDisconnectReason.WRONG_VERSION), f"Version mismatch: {client_version}"

        # 2. File integrity hash check (if configured)
        if self._expected_file_hash is not None:
            if not verification_payload:
                logger.warning("[VersionValidator] Missing file verification payload from client.")
                return False, int(ClientDisconnectReason.ITEM_DAT_ERROR), "Missing file verification payload"

            if self._expected_file_hash not in verification_payload:
                logger.warning(
                    f"[VersionValidator] File verification payload mismatch: expected {self._expected_file_hash.hex()}, "
                    f"got {verification_payload.hex()}"
                )
                return False, int(ClientDisconnectReason.ITEM_DAT_ERROR), "File integrity verification failed"

        return True, 0, "Valid"

    @staticmethod
    def build_disconnect_packet(reason_code: int = int(ClientDisconnectReason.WRONG_VERSION)) -> PacketWriter:
        """
        Builds authentic Opcode 0 disconnect reason packet.
        Payload: [0, reason_code] (Length: 2 bytes).
        """
        pkt = PacketWriter()
        pkt.write_8(0).write_8(reason_code)
        return pkt
