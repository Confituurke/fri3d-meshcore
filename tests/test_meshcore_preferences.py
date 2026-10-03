"""User preferences and the radio monitor: editable quick replies, contacts added
automatically per node type, a sound for messages that mention us, and the list of
recently heard packets.

Run:  PYTHONPATH=com.confituurke.meshcore python3 tests/test_meshcore_preferences.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fake_mpos  # noqa: E402


def _assert(c, m=""):
    if not c:
        raise AssertionError(m)


def _setup():
    env = fake_mpos.install()
    m = fake_mpos.new_manager(env)
    m.generate_identity()
    m.set_nickname("Kim")
    return env, m


def _group(sender, text, ts):
    from meshcore_channel import encode_group_text, PUBLIC_CHANNEL
    from meshcore_packet import MeshCorePacket, make_header, encode_path_len
    from meshcore_packet import ROUTE_TYPE_FLOOD, PAYLOAD_TYPE_GRP_TXT
    payload = encode_group_text(PUBLIC_CHANNEL, sender, text, ts)
    return MeshCorePacket(make_header(ROUTE_TYPE_FLOOD, PAYLOAD_TYPE_GRP_TXT),
                          encode_path_len(2), b"\x01\x02", payload).to_bytes()


# --- quick replies ----------------------------------------------------------- #

def test_quick_replies_default_and_edit():
    env, m = _setup()
    _assert(m.quick_replies() == ["copy", "on my way", "ETA 10 min", "signal report"], m.quick_replies())
    m.set_quick_replies(["wilco", "  ", "stand by", "x" * 60])
    _assert(m.quick_replies() == ["wilco", "stand by", "x" * 40], m.quick_replies())
    _assert(fake_mpos.new_manager(env).quick_replies() == ["wilco", "stand by", "x" * 40])


def test_at_most_eight_quick_replies():
    env, m = _setup()
    m.set_quick_replies(["r%d" % i for i in range(12)])
    _assert(len(m.quick_replies()) == 8)


# --- auto-add ------------------------------------------------------------------ #

def test_auto_add_is_off_by_default():
    env, m = _setup()
    _assert(m.auto_add_settings() == {"chat": False, "rptr": False, "room": False, "sensor": False})
    pub, raw = fake_mpos.advert_frame(bytes([9]) * 32, "Robin", 1790000000, node_type=1)
    m._ingest(raw, rssi=-90, snr=4)
    _assert(not m.is_contact(pub.hex()))


def test_auto_add_per_type():
    env, m = _setup()
    m.set_auto_add(rptr=True, room=True)
    rptr, raw = fake_mpos.advert_frame(bytes([7]) * 32, "Gent-Noord", 1790000000, node_type=2)
    m._ingest(raw, rssi=-90, snr=4)
    chat, raw = fake_mpos.advert_frame(bytes([9]) * 32, "Robin", 1790000000, node_type=1)
    m._ingest(raw, rssi=-90, snr=4)
    _assert(m.is_contact(rptr.hex()) and m.get_contact(rptr.hex())["type"] == 2)
    _assert(not m.is_contact(chat.hex()))
    _assert(fake_mpos.new_manager(env).auto_add_settings()["rptr"])


# --- mention sound -------------------------------------------------------------- #

def test_mention_has_its_own_sound():
    env, m = _setup()
    played = []
    m._play_tune = played.append
    m.set_sound_settings(enabled=True, channel=False, mention=True)
    m._ingest(_group("Sam", "hello all", 1790000000), rssi=-90, snr=4)
    env.now_ms += 5000
    m._ingest(_group("Sam", "@[Kim] are you there?", 1790000010), rssi=-90, snr=4)
    _assert(played == ["mention"], played)


def test_mention_sound_can_be_off():
    env, m = _setup()
    played = []
    m._play_tune = played.append
    m.set_sound_settings(enabled=True, channel=True, mention=False)
    m._ingest(_group("Sam", "@[Kim] hi", 1790000000), rssi=-90, snr=4)
    _assert(played == ["channel"], played)


def test_mention_is_in_the_sound_settings():
    env, m = _setup()
    _assert(m.sound_settings()["mention"] is True)
    import meshcore_manager as mm
    _assert(mm.TUNES["mention"] not in (mm.TUNES["channel"], mm.TUNES["dm"]))


# --- recently heard -------------------------------------------------------------- #

def test_recently_heard_packets():
    env, m = _setup()
    m._ingest(_group("Sam", "one", 1790000000), rssi=-54, snr=10.25)
    env.now_ms += 61000
    _, raw = fake_mpos.advert_frame(bytes([9]) * 32, "Robin", 1790000000)
    m._ingest(raw, rssi=-66, snr=12.0)
    recent = m.radio_stats()["recent"]
    _assert(recent[0] == {"age_s": 0, "kind": "ADV", "rssi": -66, "snr": 12.0, "hops": 0}, recent[0])
    _assert(recent[1] == {"age_s": 61, "kind": "GRP", "rssi": -54, "snr": 10.25, "hops": 2}, recent[1])


def test_recent_list_is_bounded_and_counts_per_minute():
    env, m = _setup()
    for i in range(30):
        m._ingest(_group("Sam", "msg %d" % i, 1790000000 + i), rssi=-60, snr=5)
        env.now_ms += 10000
    st = m.radio_stats()
    _assert(len(st["recent"]) == 20, len(st["recent"]))
    _assert(st["rx_per_min"] == 6.0, st["rx_per_min"])      # one every 10 s over 10 min


if __name__ == "__main__":
    fake_mpos.run_all(globals())
