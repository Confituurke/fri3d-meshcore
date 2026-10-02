"""Desktop stand-ins for the parts of MicroPythonOS the manager touches.

`install()` puts a fake `mpos` into sys.modules (and hides `machine`/`lvgl`), so
meshcore_manager imports on CPython; `new_manager()` then builds a manager wired to a
`FakePolledChip` without starting any thread, so tests can drive _poll_radio_rx(),
_ingest(), _transmit() and _retry_tick() by hand.
"""

import copy
import json
import sys
import types


class _Editor:
    def __init__(self, prefs):
        self._prefs = prefs
        self._data = copy.deepcopy(prefs.data)

    def put_string(self, k, v):
        self._data[k] = v
        return self

    put_int = put_bool = put_list = put_dict = put_string

    def put_dict_item(self, dict_key, item_key, value):
        self._data.setdefault(dict_key, {})[item_key] = value
        return self

    def remove_dict_item(self, dict_key, item_key):
        self._data.get(dict_key, {}).pop(item_key, None)
        return self

    def remove_all(self):
        self._data = {}
        return self

    def commit(self):
        # Round-trip through JSON, as the real store does, so tests catch unserialisable values.
        self._prefs.env.store[(self._prefs.appname, self._prefs.filename)] = json.loads(
            json.dumps(self._data))
        self._prefs.data = copy.deepcopy(self._data)
        return True

    apply = commit


class FakeEnv:
    def __init__(self):
        self.store = {}            # (appname, filename) -> dict
        self.constructions = 0     # SharedPreferences(...) calls, i.e. file reads on device
        self.lora = None
        self.notifications = []

    def prefs(self, app, filename="config.json"):
        return self.store.setdefault((app, filename), {})

    def make_prefs_class(self):
        env = self

        class SharedPreferences:
            def __init__(self, appname, filename="config.json", defaults=None):
                env.constructions += 1
                self.env = env
                self.appname = appname
                self.filename = filename
                raw = env.store.get((appname, filename), {})
                self.data = copy.deepcopy(raw) if isinstance(raw, dict) else {}

            def _get(self, k, default, kind):
                v = self.data.get(k, default)
                return v if isinstance(v, kind) else default

            def get_string(self, k, default=None):
                return self._get(k, default, str)

            def get_int(self, k, default=0):
                return self._get(k, default, int)

            def get_bool(self, k, default=False):
                return self._get(k, default, bool)

            def get_list(self, k, default=None):
                return self._get(k, default, list)

            def get_dict(self, k, default=None):
                return self._get(k, default, dict)

            def edit(self):
                return _Editor(self)

        return SharedPreferences


class FakeLoRaManager:
    def __init__(self):
        self.radioChip = None
        self.holder_name = None
        self.acquired = []
        self.released = []
        self.watchdog_stopped = False
        self.resets = 0

    def acquire(self, name):
        if self.holder_name not in (None, name):
            return False
        self.holder_name = name
        self.acquired.append(name)
        return True

    def release(self, name):
        if self.holder_name == name:
            self.holder_name = None
        self.released.append(name)

    def stop_watchdog(self):
        self.watchdog_stopped = True

    def reset_chip(self):
        self.resets += 1
        return True

    @property
    def holder(self):
        return self.holder_name


class _FakeInnerRadio:
    """The inner lora.SX1262 that PolledSX126x wraps (`chip._radio` / `chip.radio`)."""

    def __init__(self, chip):
        self._chip = chip
        self.calibrations = 0
        self.slept = []
        self._dio1 = None
        self.rssi_inst_raw = 212      # GetRssiInst byte: -raw/2 dBm

    def calibrate_image(self):
        self.calibrations += 1

    def sleep(self, warm_start=True):
        self.slept.append(warm_start)

    def _cmd(self, fmt, cmd, *args, n_read=0, **kw):
        if cmd == 0x15:
            return bytes([0xA2, self.rssi_inst_raw])
        return bytes(n_read)


class FakePolledChip:
    """Behaves like mpos.polled_sx126x.PolledSX126x where it matters to the manager.

    - `_last_events` is sticky: recv() leaves it set; only clear_irq_status() clears it.
    - start_recv() goes through standby, so it aborts a frame that is being received.
    - send() blocks for the airtime itself (the real driver waits for TX_DONE).
    """
    TX_DONE = 1
    RX_DONE = 2
    CRC_ERR = 64
    RX_TIMEOUT = 512
    STATUS = {0: "ERR_NONE", -6: "ERR_RX_TIMEOUT", -7: "ERR_CRC_MISMATCH"}

    def __init__(self):
        self._radio = _FakeInnerRadio(self)
        self.radio = self._radio
        self._last_events = 0
        self._frames = []
        self._in_op = False
        self.in_flight = False
        self.aborted = 0
        self.rearm_count = 0
        self.sent = []
        self.cfg = None
        self.callback = None
        self._pkt_status = (0, 0)

    # --- test controls ---
    def inject(self, frame):
        self._frames.append(bytes(frame))
        self._last_events |= self.RX_DONE

    def begin_frame(self):
        self.in_flight = True

    def set_packet_status(self, rssi_raw, snr_raw):
        self._pkt_status = (rssi_raw & 0xFF, snr_raw & 0xFF)

    # --- driver API ---
    def get_irq_status(self):
        return self._last_events

    def clear_irq_status(self):
        self._last_events = 0

    def start_recv(self):
        self.rearm_count += 1
        if self.in_flight:
            self.aborted += 1
            self.in_flight = False

    def recv(self, len_=0):
        if not self._frames:
            return (b"", -6)
        return (self._frames.pop(0), 0)

    def send(self, data):
        self.sent.append(bytes(data))
        return (len(data), 0)

    def get_status(self):
        return 0x52

    def try_get_status(self):
        return 0x52

    def get_packet_status(self):
        rssi_raw, snr_raw = self._pkt_status
        return (rssi_raw << 16) | (snr_raw << 8) | rssi_raw

    def configure(self, cfg):
        self.cfg = cfg

    def clear_callback(self):
        self.callback = None

    def set_callback(self, cb):
        self.callback = cb

    def disable_irq(self):
        pass


def install(native=None):
    """Install the fakes; returns the FakeEnv. Re-imports the app modules fresh."""
    env = FakeEnv()
    env.lora = FakeLoRaManager()
    mpos = types.ModuleType("mpos")
    mpos.SharedPreferences = env.make_prefs_class()
    mpos.LoRaManager = env.lora

    class DeviceInfo:
        hardware_id = "sensecap_indicator"

        @staticmethod
        def get_hardware_id():
            return "sensecap_indicator"

    class TaskManager:
        disabled = True

        @staticmethod
        def create_task(coro):
            try:
                coro.close()
            except Exception:
                pass

    class Notification:
        PRIORITY_DEFAULT = 0

        def __init__(self, **kw):
            self.__dict__.update(kw)

    class NotificationManager:
        @staticmethod
        def notify(n):
            env.notifications.append(n)

        @staticmethod
        def cancel(nid):
            pass

    mpos.DeviceInfo = DeviceInfo
    mpos.TaskManager = TaskManager
    mpos.Notification = Notification
    mpos.NotificationManager = NotificationManager
    mpos.get_foreground_app = lambda: None
    sys.modules["mpos"] = mpos
    for name in ("machine", "lvgl"):
        sys.modules.pop(name, None)
    if native is not None:
        sys.modules["meshcrypto"] = native
    else:
        sys.modules.pop("meshcrypto", None)
    for name in [n for n in sys.modules if n.startswith("meshcore")]:
        del sys.modules[name]
    return env


def new_manager(env, chip=None):
    """A manager on the fake radio, ready to poll/transmit, with no threads started."""
    import meshcore_manager as mm
    import meshcore_radio
    mm.simulation_mode = False
    m = mm.MeshCoreManager()
    chip = chip or FakePolledChip()
    env.lora.radioChip = chip
    m._radio = meshcore_radio.adapt(chip)
    m._radio_ready = True
    m.chip = chip
    return m


def run_all(namespace):
    tests = [v for k, v in sorted(namespace.items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print("ok   %s" % t.__name__)
    print("\n%d/%d tests passed" % (len(tests), len(tests)))
