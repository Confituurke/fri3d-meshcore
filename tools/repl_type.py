"""Type one line into MicroPythonOS's asyncio REPL, slowly enough that it keeps every
character, and print what comes back. Needs pyserial (it ships with mpremote).

    python3 tools/repl_type.py PORT "import mpos; mpos.TaskManager.stop()"

Stopping the TaskManager drops the device to the plain REPL, which mpremote can use.
"""
import sys
import time

import serial


def main():
    port, line = sys.argv[1], sys.argv[2]
    wait = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    s = serial.Serial(port, 115200, timeout=0.1)
    s.write(b"\r")
    time.sleep(0.3)
    s.read(65536)
    for ch in line.encode():
        s.write(bytes([ch]))
        time.sleep(0.03)
    s.write(b"\r")
    end = time.time() + wait
    out = b""
    while time.time() < end:
        out += s.read(4096)
    sys.stdout.write(out.decode("utf-8", "replace"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
