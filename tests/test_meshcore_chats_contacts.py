"""Chats and contacts are separate: removing a contact keeps its chat (unless asked to delete
it too); removing a chat keeps the contact; a former contact's chat stays listed and saved,
and it cannot be written to until it is a contact again.

Run:  PYTHONPATH=eu.axistem.micropymesh python3 tests/test_meshcore_chats_contacts.py
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
    peer_pub, _, _ = fake_mpos.with_peer(env, m)
    pk = peer_pub.hex()
    m.add_contact(pk, "Alex")
    m._add_dm(pk, {"ts": 1790000000, "sender": "Alex", "text": "hi", "incoming": True})
    return env, m, pk


def _restart(env):
    import meshcore_manager as mm
    mm.MeshCoreManager._instance = None
    return fake_mpos.new_manager(env)


def test_removing_a_contact_keeps_its_chat():
    env, m, pk = _setup()
    m.remove_contact(pk)
    _assert(not m.is_contact(pk) and len(m.get_dm_messages(pk)) == 1, "kept")
    chats = {c["pubkey"]: c for c in m.get_dm_chats()}
    _assert(pk in chats and chats[pk]["name"] == "Alex" and not chats[pk]["contact"], chats)
    m._flush_dirty(force=True)
    m2 = _restart(env)
    _assert(len(m2.get_dm_messages(pk)) == 1 and not m2.is_contact(pk), "saved")
    _assert({c["pubkey"]: c for c in m2.get_dm_chats()}[pk]["name"] == "Alex", "name saved")


def test_removing_a_contact_can_take_the_chat_along():
    env, m, pk = _setup()
    m.remove_contact(pk, delete_chat=True)
    _assert(m.get_dm_messages(pk) == [] and pk not in [c["pubkey"] for c in m.get_dm_chats()], "gone")


def test_removing_a_chat_keeps_the_contact():
    env, m, pk = _setup()
    m._bump_unread(pk)
    m.remove_chat(pk)
    _assert(m.is_contact(pk) and m.get_dm_messages(pk) == [] and m.get_unread(pk) == 0, "chat gone")
    _assert(pk not in [c["pubkey"] for c in m.get_dm_chats()], "an empty chat is not listed")


def test_only_conversations_are_chats():
    env, m, pk = _setup()
    m.add_contact("cd" * 32, "Quiet")
    _assert([c["pubkey"] for c in m.get_dm_chats()] == [pk], m.get_dm_chats())


def test_removing_a_channel_chat_leaves_the_channel():
    env, m, pk = _setup()
    m.add_channel("#test", "")
    m._add_message("#test", {"ts": 1790000000, "sender": "Sam", "text": "x", "incoming": True})
    m.remove_chat("#test")
    _assert("#test" not in m.get_channel_names() and m.get_messages("#test") == [], "left")


def test_a_former_contact_with_no_chat_is_not_listed():
    env, m, pk = _setup()
    m.remove_contact(pk)
    m.remove_chat(pk)
    _assert(pk not in [c["pubkey"] for c in m.get_dm_chats()], "nothing left to show")


def test_a_former_contact_cannot_be_written_to():
    env, m, pk = _setup()
    m.remove_contact(pk)
    ok, err = m.send_dm(pk, "back again")
    _assert(not ok and "contact" in err and not m.is_contact(pk), (ok, err))
    m.add_contact(pk, m.chat_name(pk))
    ok, err = m.send_dm(pk, "back again")
    _assert(ok and m.get_contact(pk)["name"] == "Alex", (ok, err))


if __name__ == "__main__":
    fake_mpos.run_all(globals())
