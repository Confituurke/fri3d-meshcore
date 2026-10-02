# MeshCore for MicroPythonOS — SenseCAP Indicator

A [MeshCore](https://meshcore.io/) LoRa messenger for [MicroPythonOS](https://micropythonos.com)
devices with a built-in SX1262 radio, aimed at the Seeed SenseCAP Indicator D1L (ESP32-S3,
480×480 touch). The app id is **`com.confituurke.meshcore`**. It is based on
[fri3d-meshcore](https://github.com/lucid-void/fri3d-meshcore) by lucid-void.

- **Channels:** Public plus `#hashtag` and private channels. Messages are sent and received
  interoperably with the MeshCore apps.
- **Direct messages:** 1:1 messages (X25519 + AES-128 + HMAC) with delivery acknowledgements.
- **Identity:** an on-device Ed25519 keypair and signed adverts.
- **Background radio service:** a toggle that keeps the node receiving while the app is closed.
  It recovers the radio automatically.

Protocol logic is pure Python and unit-tested on the desktop.

## Requirements

**MicroPythonOS with a board that publishes its radio** as `LoRaManager.radioChip` (the polled
SX126x driver). The board must also provide a reset hook (`LoRaManager.board_reset`).

**The native `meshcrypto` module is recommended.** It makes signing and verification take
milliseconds; without it the app falls back to pure-Python Ed25519/X25519, which takes seconds
per operation on the device.

## Layout

```
com.confituurke.meshcore/    # the app payload — exactly what ships in the .mpk
  MANIFEST.JSON              # app manifest (launcher activity + boot_completed service)
  icon_64x64.png
  meshcore.py                # UI (activities)
  meshcore_manager.py        # radio owner + background service (singleton)
  meshcore_packet.py         # packet parse/serialize
  meshcore_channel.py        # group-channel codec (AES-128 + HMAC)
  meshcore_crypto.py         # Ed25519 / X25519
  meshcore_advert.py         # advert parse/build + share URIs
  meshcore_dm.py             # direct-message + ack codec
  meshcore_radio.py          # driver adapter + radio lock helpers
  meshcore_boot_service.py   # boot_completed service (starts the radio if enabled)
  fonts/                     # Archivo Narrow (OFL)
tests/                       # desktop unit tests (CPython); fake_mpos.py stands in for the OS
tools/check_app.py           # bundle checks (compiles, manifest, icon)
build_mpk.py                 # build the .mpk locally (no external deps)
```

## Install for development

```
mpremote connect /dev/ttyUSB0 fs cp -r com.confituurke.meshcore :/apps/
```

Then restart the device, or call `AppManager.refresh_apps()`.

## Develop

Run the desktop tests (the app directory goes on `PYTHONPATH`):

```
for t in tests/test_*.py; do PYTHONPATH=com.confituurke.meshcore python3 "$t"; done
python3 tools/check_app.py com.confituurke.meshcore --slug com.confituurke.meshcore
```

Both run in CI on every push (`.github/workflows/ci.yml`).

To build the package:

```
python3 build_mpk.py          # -> com.confituurke.meshcore_<version>.mpk
```

## License & credits

MIT — © 2025 lucid-void and contributors. See [LICENSE](LICENSE).

Adapts, or interoperates with, these MIT-licensed works (full notices in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)):

- **[python-pure25519](https://github.com/warner/python-pure25519)** © Brian Warner: Ed25519 math.
- **[meshcore-pi](https://github.com/brianwiddas/meshcore-pi)** © Brian Widdas: X25519 and identity
  crypto, used as the reference implementation.
- **[MeshCore](https://github.com/ripplebiz/MeshCore)** © Scott Powell: the protocol and wire-format
  reference, and the wordmark the app icon is derived from.

The chat font is **[Archivo Narrow](https://github.com/Omnibus-Type/ArchivoNarrow)** © The
Archivo Narrow Project Authors. It is used under the **SIL Open Font License 1.1** (licence at
`com.confituurke.meshcore/fonts/OFL.txt`).

MESHCORE is a trademark of its owner. This is an independent, community-built client; it is not
affiliated with or endorsed by the MeshCore project.
