"""Radio presets, the firmware preamble rule and LoRa airtime.

Run:  PYTHONPATH=com.confituurke.meshcore python3 tests/test_meshcore_presets.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fake_mpos  # noqa: E402

APP = "com.confituurke.meshcore"


def _assert(c, m=""):
    if not c:
        raise AssertionError(m)


def _presets():
    fake_mpos.install()
    import meshcore_presets
    return meshcore_presets


def test_preset_ids():
    p = _presets()
    _assert([x["id"] for x in p.PRESETS] == ["eu-narrow", "eu-legacy", "eu-433"])
    _assert(p.DEFAULT_PRESET == "eu-narrow")


def test_preamble_rule():
    p = _presets()
    _assert(p.preamble_for(8) == 32)
    _assert(p.preamble_for(7) == 32)
    _assert(p.preamble_for(11) == 16)


def test_airtime_eu_narrow_40_bytes():
    p = _presets()
    _assert(p.airtime_ms(p.PRESETS[0], 40) == 542, p.airtime_ms(p.PRESETS[0], 40))


def test_airtime_eu_legacy():
    p = _presets()
    _assert(p.airtime_ms(p.PRESETS[1], 40) == 559, p.airtime_ms(p.PRESETS[1], 40))


def test_airtime_uses_ldro_for_slow_symbols():
    # SF12 at 125 kHz: 32.768 ms symbols, so low-data-rate optimisation is on (DE=1).
    p = _presets()
    custom = {"id": "custom", "freq": 869.525, "bw": 125, "sf": 12, "cr": 5}
    _assert(p.airtime_ms(custom, 40) == 2236, p.airtime_ms(custom, 40))


def test_describe_eu_narrow():
    p = _presets()
    _assert(p.describe(p.PRESETS[0]) == "869.618 MHz · 62.5 kHz · SF8 · CR 4/8",
            p.describe(p.PRESETS[0]))


def test_radio_kwargs_match_the_driver():
    p = _presets()
    kw = p.radio_kwargs(p.PRESETS[1])
    _assert(kw["preambleLength"] == 16)
    _assert(kw["syncWord"] == 0x12)
    _assert(kw["power"] == 22)
    # The driver looks the bandwidth up by str(bw): "250", never "250.0".
    _assert(str(kw["bw"]) == "250", kw["bw"])
    _assert(str(p.radio_kwargs(p.PRESETS[0])["bw"]) == "62.5")


def test_resolve_falls_back_to_default():
    p = _presets()
    _assert(p.resolve({"id": "nope"})["id"] == "eu-narrow")
    _assert(p.resolve(None)["id"] == "eu-narrow")
    _assert(p.resolve({"id": "eu-433"})["freq"] == 433.650)
    custom = {"id": "custom", "freq": 868.0, "bw": 125, "sf": 9, "cr": 5}
    _assert(p.resolve(custom) == custom)


def test_manager_default_preset_is_eu_narrow():
    env = fake_mpos.install()
    m = fake_mpos.new_manager(env)
    _assert(m.radio_preset()["id"] == "eu-narrow")


def test_set_preset_persists():
    env = fake_mpos.install()
    m = fake_mpos.new_manager(env)
    m.set_radio_preset("eu-433")
    _assert(env.prefs(APP).get("radio") == {"id": "eu-433"}, env.prefs(APP))
    _assert(m.radio_preset()["freq"] == 433.650)


def test_bring_up_uses_the_stored_preset():
    env = fake_mpos.install()
    m = fake_mpos.new_manager(env)
    m.set_radio_preset("eu-433")
    m._radio_ready = False
    _assert(m._bring_up_radio() is True)
    _assert(m.chip.cfg["freq_khz"] == 433650, m.chip.cfg)
    _assert(m.chip.cfg["preamble_len"] == 32, m.chip.cfg)


if __name__ == "__main__":
    fake_mpos.run_all(globals())
