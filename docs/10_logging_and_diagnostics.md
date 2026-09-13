# Logging & Diagnostics Subsystem

This document specifies the logging architecture, log rotation policies, real-time pipeline handlers, and operational diagnostics in Wonderland Online Server.

## Architecture Overview

The logging subsystem centralizes logging across all server threads, network workers, database managers, and GUI interfaces using Python's standard `logging` library augmented with rotating file persistence and thread-safe UI hooks.

```
                      +-----------------------------+
                      | Application Loggers         |
                      | (WLO_Server, Main, Auth,    |
                      |  Battle, EveInterpreter...) |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      | Root Logger (logging.DEBUG) |
                      +--------------+--------------+
                                     |
             +-----------------------+-----------------------+
             |                       |                       |
             v                       v                       v
+------------------------+ +--------------------+ +---------------------+
| StreamHandler          | | RotatingFileHandler| | TkLogHandler        |
| - stdout streaming     | | - logs/server.log  | | - Real-time GUI     |
| - ANSI/console output  | | - 10 MB limit      | | - Thread-safe       |
|                        | | - 5 backups        | | - CTkText pipe      |
|                        | | - UTF-8 encoding   | |                     |
+------------------------+ +--------------------+ +---------------------+
```

## Configuration & Core Interface (`server/logger_config.py`)

### `setup_logging` Function

Initializes or reconfigures rotating file and stream logging.

#### Function Prototype
```python
def setup_logging(
    log_dir: Optional[str] = None,
    log_filename: str = "server.log",
    level: int = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> str
```

#### Parameters
- `log_dir` (`Optional[str]`): Directory path where log files will be persisted. Defaults to `<repo_root>/logs/`. Automatically created if missing.
- `log_filename` (`str`): Base filename for log storage. Defaults to `"server.log"`.
- `level` (`int`): Minimum logging threshold severity. Defaults to `logging.DEBUG`.
- `max_bytes` (`int`): Maximum file size in bytes before triggering rotation. Defaults to `10,485,760` (10 MB).
- `backup_count` (`int`): Maximum number of rotated archives to retain (`server.log.1`, `server.log.2`, etc.). Defaults to `5`.

#### Return Value
- `str`: Absolute filesystem path to the active log file.

#### Exceptions & Edge Cases
- **Directory Creation (`os.makedirs`)**: Safe against race conditions via `exist_ok=True`.
- **Duplicate Handler Prevention**: Inspects existing `root_logger.handlers` to prevent duplicate log records when modules re-import or initialize.
- **Windows File Locking**: Closed cleanly in tests to prevent `PermissionError: [WinError 32]` during tempdir cleanups.
- **Encoding Safety**: Enforces strict `UTF-8` encoding to support Big5 characters, Unicode character names, and international item strings without `UnicodeEncodeError`.

## Log Format Standard

All logging handlers format messages according to the standardized pattern:

```
%(asctime)s [%(levelname)s] [%(name)s] %(message)s
```

Example output:
```
2026-09-12 19:21:57 [INFO] [WLO_Server] [Server] Saved 2 active sessions to database.
2026-09-12 19:21:58 [INFO] [EveInterpreter] Loaded 10644 native event trees across 1119 maps.
```

## Output Targets

1. **Standard Console Output (`StreamHandler`)**: Streams directly to `sys.stdout` for CLI monitoring, shell redirects, and Docker stdout capture.
2. **Rotating File Storage (`RotatingFileHandler`)**: Writes to `logs/server.log`. Files roll over when reaching 10 MB, maintaining up to 5 history files (`server.log.1` through `server.log.5`).
3. **Desktop GUI Pipe (`TkLogHandler`)**: Intercepts log records and posts them to the GUI log console via `after(0, ...)` for thread-safe asynchronous GUI updates.
