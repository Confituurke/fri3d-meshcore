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
  ui_model.py                # what the screens show (pure Python, desktop-tested)
  ui_theme.py                # colours, fonts, shared styles, header / chips / tab bar
  fonts/                     # Archivo Narrow + Mesh Mono (subset of IBM Plex Mono), OFL
tests/                       # desktop unit tests (CPython); fake_mpos.py stands in for the OS
tools/check_app.py           # bundle checks (compiles, manifest, icon)
tools/run_tests.sh           # the desktop test suite
tools/make_fonts.py          # builds the subset fonts (needs fontTools)
tools/deploy.sh              # copy the app to a device over USB serial
tools/engine_probe.py        # run the engine on a device without the UI
build_mpk.py                 # build the .mpk locally (no external deps)
```

## Install for development

```
MPREMOTE=mpremote PYTHON=python3 tools/deploy.sh --start
```

MicroPythonOS's asyncio REPL ignores mpremote, so `deploy.sh` first types
`TaskManager.stop()` into it slowly (`tools/repl_type.py`, needs pyserial), copies the app to
`/apps/`, and then restarts the device.

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

The text font is **[Archivo Narrow](https://github.com/Omnibus-Type/ArchivoNarrow)** © The
Archivo Narrow Project Authors. The font for IDs and numbers is **Mesh Mono**, a subset of
[IBM Plex Mono](https://github.com/IBM/plex) © IBM Corp., renamed because "Plex" is a Reserved
Font Name. Both are used under the **SIL Open Font License 1.1**; the licences ship in
`com.confituurke.meshcore/fonts/`.

MESHCORE is a trademark of its owner. This is an independent, community-built client; it is not
affiliated with or endorsed by the MeshCore project.
