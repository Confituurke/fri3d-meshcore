"""Pure view models behind the screens (no LVGL).

Run:  PYTHONPATH=com.confituurke.meshcore python3 tests/test_ui_model.py
"""

import calendar
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fake_mpos  # noqa: E402

NOW = calendar.timegm((2026, 10, 2, 14, 32, 0))     # a Friday, 14:32 UTC


def _assert(c, m=""):
    if not c:
        raise AssertionError(m)


def _ui():
    import ui_model
    return ui_model


def _seeded():
    env = fake_mpos.install()
    m = fake_mpos.new_manager(env)
    m.generate_identity()
    m.set_nickname("Kim")
    m.add_channel("#test")
    peer_pub, _, _ = fake_mpos.with_peer(env, m, name="Alex")
    m._add_message("Public", {"ts": NOW - 180, "sender": "Sam", "text": "anyone near the Gent repeater tonight?",
                              "incoming": True})
    m._bump_unread("Public")
    m._add_message("#test", {"ts": NOW - 60, "sender": "Robin", "text": "@[Kim] signal check",
                             "incoming": True})
    m._bump_unread("#test", mention=True)
    m._add_dm(peer_pub.hex(), {"ts": NOW - 120, "sender": "Kim", "text": "see you at three",
                               "incoming": False, "tx": True, "delivered": True})
    return m, peer_pub.hex()


def test_chat_rows_sorted_and_filtered():
    m, alex = _seeded()
    ui = _ui()
    rows = ui.chat_rows(m, NOW)
    _assert([r["title"] for r in rows] == ["#test", "Alex", "Public"], rows)
    _assert([r["key"] for r in ui.chat_rows(m, NOW, "direct")] == [alex])
    _assert([r["title"] for r in ui.chat_rows(m, NOW, "channels")] == ["#test", "Public"])
    _assert([r["title"] for r in ui.chat_rows(m, NOW, "unread")] == ["#test", "Public"])
    t = {r["title"]: r for r in rows}
    _assert(t["#test"]["mention"] is True and t["#test"]["unread"] == 1)
    _assert(t["Public"]["kind"] == "channel" and t["Alex"]["kind"] == "dm")
    _assert(t["Public"]["initials"] == "#" and t["Alex"]["initials"] == "AL")
    _assert(t["Public"]["time"] == "14:29", t["Public"]["time"])


def test_chat_row_without_messages():
    env = fake_mpos.install()
    m = fake_mpos.new_manager(env)
    rows = _ui().chat_rows(m, NOW)
    _assert(rows[0]["title"] == "Public" and rows[0]["preview"] == "" and rows[0]["time"] == "")


def test_preview_prefixes():
    m, alex = _seeded()
    t = {r["title"]: r for r in _ui().chat_rows(m, NOW)}
    _assert(t["Public"]["preview"] == "Sam: anyone near the Gent repeater tonight?")
    _assert(t["Alex"]["preview"] == "You: see you at three", t["Alex"]["preview"])
    m._add_dm(alex, {"ts": NOW - 10, "sender": "Alex", "text": "ok!", "incoming": True})
    t = {r["title"]: r for r in _ui().chat_rows(m, NOW)}
    _assert(t["Alex"]["preview"] == "ok!", t["Alex"]["preview"])


def test_time_text():
    ui = _ui()
    _assert(ui.time_text(NOW - 60, NOW) == "14:31")
    _assert(ui.time_text(NOW - 60, NOW, tz_s=7200) == "16:31")
    _assert(ui.time_text(NOW - 2 * 86400, NOW) == "Wed")
    _assert(ui.time_text(NOW - 20 * 86400, NOW) == "12 Sep")


def test_tz_offset():
    ui = _ui()
    _assert(ui.tz_offset((2026, 10, 2, 16, 32, 0), (2026, 10, 2, 14, 32, 0)) == 7200)
    _assert(ui.tz_offset((2026, 10, 3, 1, 0, 0), (2026, 10, 2, 23, 0, 0)) == 7200)
    _assert(ui.tz_offset((2026, 10, 2, 20, 0, 0), (2026, 10, 3, 1, 0, 0)) == -5 * 3600)
    _assert(ui.tz_offset((2026, 10, 2, 14, 32, 0), (2026, 10, 2, 14, 32, 0)) == 0)


def test_delivery_states():
    ui = _ui()
    _assert(ui.delivery({"incoming": False, "tx": False}) == ("⏳", "sending", ui.MUTED))
    _assert(ui.delivery({"incoming": False, "tx": True, "delivered": True, "ack": "ab"})
            == ("✓", "delivered", ui.OK))
    _assert(ui.delivery({"incoming": False, "tx": True, "failed": True, "ack": "ab"})
            == ("✗", "no ack after 4 tries · tap to resend", ui.ERR))
    _assert(ui.delivery({"incoming": False, "tx": True, "heard": 4}) == ("✓", "heard ×4", ui.OK))
    _assert(ui.delivery({"incoming": False, "tx": True, "heard": 0, "unheard": True})
            == ("?", "not heard by a repeater · tap to resend", ui.WARN))
    _assert(ui.delivery({"incoming": False, "tx": True, "heard": 0}) == ("→", "sent", ui.MUTED))


def test_budget_counts_utf8_bytes():
    ui = _ui()
    _assert(ui.budget("é" * 10) == 140)
    _assert(ui.budget("x" * 161) == -1)


def test_channel_budget_includes_sender_prefix():
    _assert(_ui().budget("hi", "Public", "Kim") == 160 - 5 - 2)


def test_node_rows_meta_and_age_colors():
    ui = _ui()
    now_ms = 10 * 3600 * 1000
    nodes = [
        {"pubkey": "a3" * 32, "id": "a3", "type": 1, "name": "Alex", "snr": 8.0, "hops": 0,
         "heard_ms": now_ms - 120 * 1000},
        {"pubkey": "f1" * 32, "id": "f1", "type": 2, "name": "Gent-Noord", "snr": -3.5, "hops": 2,
         "heard_ms": now_ms - 3600 * 1000},
        {"pubkey": "7c" * 32, "id": "7c", "type": 3, "name": "Gent BBS", "snr": None, "hops": 3,
         "heard_ms": now_ms - 7 * 3600 * 1000},
    ]
    rows = ui.node_rows(nodes, now_ms)
    _assert([(r["hex"], r["kind"]) for r in rows] == [("A3", "chat"), ("F1", "rptr"), ("7C", "room")])
    _assert(rows[0]["meta"] == "direct · SNR 8.0" and rows[0]["age"] == "2 min", rows[0])
    _assert(rows[1]["meta"] == "2 hops · SNR −3.5" and rows[1]["age"] == "1 h", rows[1])
    _assert(rows[2]["meta"] == "3 hops", rows[2]["meta"])
    _assert([r["age_color"] for r in rows] == [ui.OK, ui.WARN, ui.MUTED])
    _assert([r["name"] for r in ui.node_rows(nodes, now_ms, "rptr")] == ["Gent-Noord"])
    _assert([r["name"] for r in ui.node_rows(nodes, now_ms, "new", contacts={"a3" * 32})] == [])
    _assert(len(ui.node_rows(nodes, now_ms, "new")) == 1)


def test_node_detail():
    ui = _ui()
    now_ms = 10 * 3600 * 1000
    pk = "f1a7" + "33" * 28 + "9c2e"
    d = ui.node_detail({"pubkey": pk, "id": "f1", "type": 2, "name": "Gent-Noord", "snr": -3.5,
                        "hops": 2, "heard_ms": now_ms - 840 * 1000, "verified": True,
                        "lat": 51.05, "lon": 3.72}, now_ms)
    _assert(d["title"] == "Gent-Noord")
    _assert(d["subtitle"] == "repeater · F1A7…9C2E", d["subtitle"])
    _assert(d["info"] == "2 hops · SNR −3.5 dB · heard 14 min ago", d["info"])
    _assert(("Location", "51.05000, 3.72000") in d["fields"], d["fields"])
    _assert(("Signature", "verified") in d["fields"])
    d2 = ui.node_detail({"pubkey": pk, "type": 1, "name": "", "snr": None, "hops": 0,
                         "heard_ms": now_ms, "verified": False}, now_ms)
    _assert(d2["subtitle"].startswith("companion · ") and d2["info"] == "direct · heard now", d2)
    _assert(("Signature", "not checked") in d2["fields"])


def test_radio_texts():
    ui = _ui()
    st = {"rx_on": True, "last_rx_s": 40, "noise_dbm": -106.0, "noise_series": [-106.0],
          "peak_rssi_30m": -74.0, "packets_per_h": 6, "tx_air_pct": 0.1}
    t = ui.radio_texts(st)
    _assert(t == {"subtitle": "RX on · last packet 40 s ago", "noise": "−106",
                  "peak": "Peak −74", "packets": "Packets 6/h", "tx_air": "TX air 0.1 %"}, t)
    t = ui.radio_texts({"rx_on": False, "last_rx_s": None, "noise_dbm": None, "noise_series": [],
                        "peak_rssi_30m": None, "packets_per_h": 0, "tx_air_pct": 0.0})
    _assert(t["subtitle"] == "RX off" and t["noise"] == "—" and t["peak"] == "Peak —", t)
    _assert(ui.radio_texts(dict(st, last_rx_s=None))["subtitle"] == "RX on · nothing heard yet")
    _assert(ui.radio_texts(dict(st, last_rx_s=7200))["subtitle"] == "RX on · last packet 2 h ago")


def test_age_text():
    ui = _ui()
    _assert([ui.age_text(s) for s in (5, 120, 3700, 3 * 86400)] == ["now", "2 min", "1 h", "3 d"])


def test_preset_summary_airtime():
    fake_mpos.install()
    import meshcore_presets
    title, detail, air = _ui().preset_summary(meshcore_presets.by_id("eu-narrow"), 22)
    _assert(title == "EU/UK (Narrow)")
    _assert(detail == "869.618 MHz · 62.5 kHz · SF8 · CR 4/8 · 22 dBm", detail)
    _assert(air == "≈ 0.54 s on air per 40-byte message", air)


def test_signal_report_and_quick_replies():
    ui = _ui()
    _assert(ui.QUICK_REPLIES == ("copy", "on my way", "ETA 10 min", "signal report"))
    _assert(ui.signal_report({"snr": 6.5, "hops": 3}) == "SNR 6.5 · 3 hops")
    _assert(ui.signal_report({"snr": -2.0, "hops": 1}) == "SNR −2.0 · 1 hop")


if __name__ == "__main__":
    fake_mpos.run_all(globals())
