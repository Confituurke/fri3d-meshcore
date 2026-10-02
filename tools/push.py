"""Copy files to a MicroPython device and check each one arrived whole.

    python3 tools/push.py PORT DEST_DIR FILE [FILE ...]

Uses mpremote's serial transport in plain raw-REPL mode (no raw-paste), in small base64
chunks, retrying a file whose size does not match: log lines the device prints on its own
(Wi-Fi, time sync, apps) break mpremote's raw-paste transfers. DEST_DIR and its parent are
created when missing. Exit status 1 if any file could not be copied.
"""
import binascii
import os
import sys

from mpremote.transport_serial import SerialTransport

CHUNK = 768


def _exec(t, code):
    return t.exec(code).decode("utf-8", "replace")


def push(t, src, dest):
    data = open(src, "rb").read()
    _exec(t, "f = open(%r, 'wb')" % dest)
    for i in range(0, len(data), CHUNK):
        b64 = binascii.b2a_base64(data[i:i + CHUNK], newline=False).decode()
        _exec(t, "f.write(__import__('binascii').a2b_base64(%r))" % b64)
    _exec(t, "f.close()")
    size = int(_exec(t, "import os; print(os.stat(%r)[6])" % dest).strip().split()[-1])
    return size == len(data)


def main():
    port, dest_dir, files = sys.argv[1], sys.argv[2].rstrip("/"), sys.argv[3:]
    t = SerialTransport(port, baudrate=115200)
    t.use_raw_paste = False
    t.enter_raw_repl(soft_reset=False)
    parent = os.path.dirname(dest_dir)
    for d in (parent, dest_dir):
        if d and d != "/":
            _exec(t, "import os\ntry:\n os.mkdir(%r)\nexcept OSError:\n pass" % d)
    failed = []
    for src in files:
        dest = dest_dir + "/" + os.path.basename(src)
        for attempt in range(3):
            try:
                if push(t, src, dest):
                    print("ok  ", dest)
                    break
            except Exception as e:
                print("retry %s (%s)" % (dest, e))
                try:
                    t.enter_raw_repl(soft_reset=False)
                except Exception:
                    pass
        else:
            print("FAIL", dest)
            failed.append(dest)
    t.exit_raw_repl()
    t.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
