# Winsock Asynchronous Socket I/O Engine

This document outlines the client-side Winsock socket bindings, non-blocking state toggles, Windows message loops (`WSAAsyncSelect`), and socket connection managers extracted from the raw decompile code of `aLogin.exe.1.c` (lines 87600 to 88900).

---

## 1. Socket Memory Structures & Offsets

The client stores active socket descriptors and session variables using a custom network pointer layout:

| Offset | Data Type | Field / Purpose | Description |
|---|---|---|---|
| `+0x04` | `SOCKET` | Socket Descriptor | Windows socket identifier handle |
| `+0x14` | `HWND` | Window Handle | Target window handle (`hWnd`) receiving message events |
| `+0x18` | `sockaddr_in` | Socket Address Struct | Network IP and port destination mapping parameters |
| `+0x28` | `byte` | Notification Flag | Controls event selection bits for reading/writing status |
| `+0x29` | `byte` | Connection State | Status code tracking: `2` (resolving/connecting), `0` (ready) |
| `+0x2c` | `HANDLE` | DNS Async Thread | Thread handle returned by `WSAAsyncGetHostByName` |

---

## 2. Key Decompiled Winsock Handlers

### A. Socket Bind & Listen (`FUN_00079948`)
- **Logic**:
  1. Executes Winsock `bind()` on the active socket descriptor `*(param_1 + 4)` using address structure `*(param_1 + 0x18)`.
  2. Binds event selectors by calling `FUN_000798ec`.
  3. Begins listening for incoming connections: `listen(*(SOCKET *)(param_1 + 4), queue_limit)`.

### B. Asynchronous Event Selectors (`FUN_000798ec`)
- **Logic**:
  1. Configures asynchronous event messaging loops using **`WSAAsyncSelect`**:
     - **Event Message ID**: `0x401` (user-defined window message constant).
     - **Flags**: Toggles notifications based on flag mask stored at `+0x28`.
  2. **Non-Blocking Fallback**: If the mask is `0`, disables async notifications and toggles non-blocking mode explicitly:
     - Command: `ioctlsocket(*(SOCKET *)(param_1 + 4), FIONBIO, &mode)` where FIONBIO control command key is **`-0x7ffb9982`** or **`0x4004667f`**.

### C. Connect Handler (`FUN_000799c8`)
- **Logic**:
  1. Registers non-blocking states via `WSAAsyncSelect`.
  2. Dispatches connection handshake request: `connect(*(SOCKET *)(param_1 + 4), sockaddr, 0x10)`.
  3. Validates socket status: if the descriptor is valid (`!= -1`), sets connection status flag.

### D. Hostname Resolution wrappers (`WSAAsyncGetHostByName` / `WSAAsyncGetServByName`)
- **Logic**:
  - Toggles host domain name resolution asynchronously to prevent client thread locking:
    - Triggers `WSAAsyncGetServByName` using event message ID **`0x403`**.
    - Stores the lookup worker handle at `+0x2c` for verification.
