"""Timestamps on the air are Unix time, also on ports whose epoch is 2000 (ESP32).

Run:  PYTHONPATH=com.confituurke.meshcore python3 tests/test_meshcore_clock.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import fake_mpos  # noqa: E402

DEVICE_NOW = 844275762            # what time.time() said on the device, 2026-10-02
UNIX_NOW = DEVICE_NOW + 946684800


def _assert(c, m=""):
    if not c:
        raise AssertionError(m)


class _Epoch2000:
    """Make the CPython time module look like MicroPython on ESP32 for a while."""

    def __enter__(self):
        self._time, self._gmtime = time.time, time.gmtime
        real_gmtime = time.gmtime
        time.time = lambda: float(DEVICE_NOW)
        time.gmtime = lambda t=None: real_gmtime(946684800 if t == 0 else t)
        return self

    def __exit__(self, *a):
        time.time, time.gmtime = self._time, self._gmtime


def test_unix_time_on_a_2000_epoch_port():
    fake_mpos.install()
    import meshcore_manager as mm
    with _Epoch2000():
        _assert(mm.unix_time() == UNIX_NOW, mm.unix_time())


def test_unix_time_on_a_unix_epoch_port():
    fake_mpos.install()
    import meshcore_manager as mm
    _assert(abs(mm.unix_time() - int(time.time())) <= 1)


def test_outgoing_messages_and_adverts_carry_unix_time():
    env = fake_mpos.install()
    m = fake_mpos.new_manager(env)
    m.generate_identity()
    from meshcore_packet import MeshCorePacket
    from meshcore_advert import parse_advert
    with _Epoch2000():
        m.send_group_text("Public", "hi")
        m.advertise()
    _assert(m.get_messages("Public")[-1]["ts"] == UNIX_NOW)
    fake_mpos.drain(m)
    adv = MeshCorePacket.parse(m.chip.sent[-1])
    _assert(parse_advert(adv.payload)["timestamp"] == UNIX_NOW)


if __name__ == "__main__":
    fake_mpos.run_all(globals())
