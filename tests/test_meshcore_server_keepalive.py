"""Staying logged in to repeaters and room servers: a password that worked is remembered and
used for the next login, a room session is kept alive (REQ_TYPE_KEEP_ALIVE, as the firmware's
BaseChatMesh::checkConnections sends it), and a session that went quiet logs in again by
itself. A server that does not answer that login has forgotten us.

Run:  PYTHONPATH=eu.axistem.micropymesh python3 tests/test_meshcore_server_keepalive.py
"""

import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fake_mpos  # noqa: E402
from test_meshcore_sessions import _setup, ROOM, REPEATER, STATUS  # noqa: E402

KEEP_ALIVE_MS = 128 * 1000


def _assert(c, m=""):
    if not c:
        raise AssertionError(m)


def _logged_in(kind=REPEATER, password=""):
    env, m, srv, events = _setup(kind)
    m.login(srv.hex, password)
    srv.answer_login(flood_path=b"\x3a")
    env.now_ms += 5000
    srv.take()
    return env, m, srv


def _tick(env, m, ms):
    env.now_ms += ms
    m._server_tick()


def _kinds(srv):
    out = []
    for kind, pkt, pt in srv.take():
        if kind == "req":
            out.append(("keep_alive", pt[:9]) if pt[4] == 0x02 else ("req", pt))
        elif kind == "login":
            out.append(("login", pt))
    return out


def _ack(m, srv, keep_alive_pt):
    from meshcore_packet import MeshCorePacket, make_header, encode_path_len, ROUTE_TYPE_DIRECT
    ack = hashlib.sha256(keep_alive_pt + srv.our_pub).digest()[:4]
    pkt = MeshCorePacket(make_header(ROUTE_TYPE_DIRECT, 0x03), encode_path_len(0), b"",
                         ack + bytes([0]))           # + the room's unsynced-post count
    m._ingest(pkt.to_bytes(), rssi=-80, snr=7)


# --- passwords --------------------------------------------------------------- #

def test_a_password_that_worked_is_remembered():
    env, m, srv = _logged_in(password="hunter2")
    _assert(m.remembered_password(srv.hex) == "hunter2")
    m2 = fake_mpos.new_manager(env)
    _assert(m2.remembered_password(srv.hex) == "hunter2", "kept across a restart")


def test_a_wrong_password_is_not_remembered():
    env, m, srv, events = _setup()
    m.login(srv.hex, "nope")
    srv.answer_login()
    _tick(env, m, 60000)
    _assert(m.remembered_password(srv.hex) is None)


def test_not_remembered_when_asked_not_to():
    env, m, srv = _logged_in(password="hunter2")
    m.login(srv.hex, "hunter2", remember=False)
    srv.answer_login()
    _assert(m.remembered_password(srv.hex) is None)


def test_a_login_without_a_password_uses_the_remembered_one():
    env, m, srv = _logged_in(password="hunter2")
    m.login(srv.hex)
    pt = srv.answer_login()
    _assert(pt[4:].rstrip(b"\x00") == b"hunter2", pt)
    _assert(m.server_session(srv.hex)["admin"])
    m.login(srv.hex, "")                         # explicitly as guest
    pt = srv.answer_login()
    _assert(pt[4:].rstrip(b"\x00") == b"", pt)


# --- keep-alive -------------------------------------------------------------- #

def test_a_room_session_is_kept_alive():
    env, m, srv = _logged_in(ROOM)               # logged in 5 s ago
    _tick(env, m, KEEP_ALIVE_MS - 6000)
    _assert(_kinds(srv) == [], "not yet")
    _tick(env, m, 2000)
    sent = _kinds(srv)
    _assert(len(sent) == 1 and sent[0][0] == "keep_alive", sent)
    pt = sent[0][1]
    _assert(struct.unpack("<I", pt[5:9])[0] == m.get_contact(srv.hex).get("sync_since", 0), pt)
    _ack(m, srv, pt)
    _tick(env, m, 2 * KEEP_ALIVE_MS)             # the ack counts: no new login
    _assert(all(k == "keep_alive" for k, _ in _kinds(srv)))
    _assert(m.server_session(srv.hex)["state"] == "ok")


def test_room_posts_count_as_activity():
    env, m, srv = _logged_in(ROOM)
    for i in range(4):
        env.now_ms += KEEP_ALIVE_MS - 1000
        srv.post(1790000100 + i, bytes.fromhex("c0ffee00"), "hi %d" % i)
        m._server_tick()
    _assert(all(k != "login" for k, _ in _kinds(srv)))
    _assert(m.server_session(srv.hex)["state"] == "ok")


def test_repeaters_get_no_keep_alive():
    env, m, srv = _logged_in(REPEATER)
    for _ in range(10):
        _tick(env, m, KEEP_ALIVE_MS)
    _assert(_kinds(srv) == [], "a repeater session is only used while you are on its page")


def test_a_room_that_went_quiet_logs_in_again():
    env, m, srv = _logged_in(ROOM, password="hunter2")
    for _ in range(3):
        _tick(env, m, KEEP_ALIVE_MS)             # keep-alives nobody acks
    sent = _kinds(srv)
    _assert(sent[-1][0] == "login", sent)
    _assert(sent[-1][1][8:].rstrip(b"\x00") == b"hunter2", "with the remembered password")
    s = m.server_session(srv.hex)
    _assert(s["state"] == "pending", s)


# --- logging in again -------------------------------------------------------- #

def test_a_request_without_answer_logs_in_again():
    env, m, srv = _logged_in(password="hunter2")
    m.request_server(srv.hex, "status")
    srv.take()
    _tick(env, m, 60000)
    s = m.server_session(srv.hex)
    _assert(s["state"] == "pending" and "again" in s["error"], s)
    sent = srv.take()
    _assert([k for k, _, _ in sent] == ["login"], sent)
    srv.login_reply(sent[0][2], True, 3)
    _assert(m.server_session(srv.hex)["state"] == "ok")
    _assert(m.request_server(srv.hex, "status")[0])
    srv.answer_request(lambda t, p: STATUS)
    _assert("status" in m.server_session(srv.hex)["results"])


def test_no_answer_to_that_login_means_the_server_forgot_us():
    env, m, srv = _logged_in()
    m.request_server(srv.hex, "status")
    srv.take()
    _tick(env, m, 60000)                         # request lost: logs in again by itself
    srv.take()
    _tick(env, m, 60000)                         # no answer to that either
    s = m.server_session(srv.hex)
    _assert(s["state"] == "failed" and "forgotten" in s["error"], s)
    _tick(env, m, 60000)
    _assert(_kinds(srv) == [], "it tries once, not forever")


if __name__ == "__main__":
    fake_mpos.run_all(globals())
