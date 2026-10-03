"""Adding a contact by hand: a 64-hex public key, or a meshcore:// contact card (as the
MeshCore apps share them).

Run:  PYTHONPATH=com.confituurke.meshcore python3 tests/test_meshcore_contact_add.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fake_mpos  # noqa: E402,F401

import meshcore_advert as A  # noqa: E402

KEY = "7aa6d679625b17999e96855b8969366f34d0a8ed0cca83be4996617c76980142"


def _assert(c, m=""):
    if not c:
        raise AssertionError(m)


def test_a_bare_key():
    _assert(A.parse_contact_text(KEY) == (KEY, None, 1), A.parse_contact_text(KEY))
    spaced = " ".join(KEY[i:i + 8].upper() for i in range(0, 64, 8))
    _assert(A.parse_contact_text(spaced) == (KEY, None, 1), "groups and capitals")


def test_a_contact_card_round_trips():
    uri = A.contact_share_uri("BE-KJK Stadhuis \\u263c", KEY, 2)
    _assert(A.parse_contact_text(uri) == (KEY, "BE-KJK Stadhuis \\u263c", 2), A.parse_contact_text(uri))


def test_not_a_contact():
    for text in ("", "hello", KEY[:-2], KEY + "00", "meshcore://contact/add?name=x",
                 "meshcore://channel/add?name=x&public_key=" + KEY):
        _assert(A.parse_contact_text(text) is None, text)


if __name__ == "__main__":
    fake_mpos.run_all(globals())
