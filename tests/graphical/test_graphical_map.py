import os
import struct
import unittest

import lvgl as lv
import mpos.ui
from mpos import wait_for_render, find_label_with_text

import mc_fixtures

BRUSSELS = (50.8467, 4.3525)
GENT = (51.0543, 3.7174)
TILES = "/tmp/mc_map_tiles"


def _crc(data):
    import binascii
    return binascii.crc32(data) & 0xFFFFFFFF


def _chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", _crc(kind + body))


def _zlib_stored(raw):
    """A zlib stream with stored (uncompressed) blocks: no compressor needed."""
    out = bytearray(b"\x78\x01")
    for i in range(0, len(raw), 65535):
        block = raw[i:i + 65535]
        final = 1 if i + 65535 >= len(raw) else 0
        out += bytes([final]) + struct.pack("<HH", len(block), len(block) ^ 0xFFFF) + block
    a, b = 1, 0
    for c in raw:
        a = (a + c) % 65521
        b = (b + a) % 65521
    out += struct.pack(">I", (b << 16) | a)
    return bytes(out)


def tile_png(index=1):
    raw = b"".join(b"\x00" + bytes([index]) * 256 for _ in range(256))
    pal = bytes((20, 27, 35, 11, 33, 51))
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 3, 0, 0, 0))
            + _chunk(b"PLTE", pal) + _chunk(b"IDAT", _zlib_stored(raw)) + _chunk(b"IEND", b""))


def _mkdirs(path):
    parts = path.strip("/").split("/")
    for i in range(1, len(parts) + 1):
        try:
            os.mkdir("/" + "/".join(parts[:i]))
        except OSError:
            pass


def wait_until(cond, frames=200):
    for _ in range(frames):
        if cond():
            return True
        wait_for_render(2)
    return cond()


class TestMap(unittest.TestCase):
    def setUp(self):
        import map_view
        self.map_view = map_view
        self.root = map_view.ROOT
        map_view.ROOT = "/nonexistent/maps/dark"
        self.m = mc_fixtures.fresh_manager()
        mc_fixtures.seed_nodes(self.m)
        self.m._nodes[mc_fixtures.BOB].update(lat=BRUSSELS[0], lon=BRUSSELS[1])
        self.m._nodes[mc_fixtures.GENT].update(lat=GENT[0], lon=GENT[1])

    def tearDown(self):
        self.map_view.ROOT = self.root
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_tab_shows_a_pin_per_positioned_node(self):
        act = mc_fixtures.open_app(tab="Map")
        view = act._tab.view
        self.assertEqual(sorted(p["pubkey"] for p in view._pin_model),
                         sorted([mc_fixtures.BOB, mc_fixtures.GENT]))
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Bob"))
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Gent-Noord"))
        self.assertTrue(wait_until(lambda: not view.note.has_flag(lv.obj.FLAG.HIDDEN)))
        self.assertIn("No map tiles here", view.note.get_text())

    def test_tapping_a_repeater_pin_opens_its_detail(self):
        act = mc_fixtures.open_app(tab="Map")
        view = act._tab.view
        pin = [p for p in view._pin_model if p["pubkey"] == mc_fixtures.GENT][0]
        hit = view.pin_at(pin["sx"] + 5, pin["sy"] - 5)
        self.assertEqual(hit["pubkey"], mc_fixtures.GENT)
        self.assertIsNone(view.pin_at(pin["sx"] + 60, pin["sy"] + 60))
        view.open_node(hit["pubkey"], hit["kind"])
        wait_for_render(20)
        self.assertEqual(type(mpos.ui.screen_stack[-1][0]).__name__, "NodeDetailActivity")

    def test_zoom_and_fit(self):
        act = mc_fixtures.open_app(tab="Map")
        view = act._tab.view
        z = view.z
        view.zoom(1)
        self.assertEqual(view.z, z + 1)
        self.assertTrue(len(view._pin_model) <= 2)
        view.fit_all()
        self.assertEqual(view.z, z)
        self.assertEqual(len(view._pin_model), 2)

    def test_tiles_come_from_the_folder_stretched_from_an_ancestor(self):
        _mkdirs(TILES + "/0/0")
        with open(TILES + "/0/0/0.png", "wb") as f:
            f.write(tile_png())
        self.map_view.ROOT = TILES
        act = mc_fixtures.open_app(tab="Map")
        view = act._tab.view
        shown = lambda: all(s.entry is not None and s.entry[0] == "rgb565"
                            for s in view._slots if s.key is not None)
        self.assertTrue(wait_until(shown))
        self.assertTrue(view.note.has_flag(lv.obj.FLAG.HIDDEN))

    def test_node_detail_map_button_opens_the_map_on_that_node(self):
        from mpos import Intent
        from mpos.activity_navigator import ActivityNavigator
        import node_activity
        intent = Intent(activity_class=node_activity.NodeDetailActivity, app_fullname=mc_fixtures.APP)
        intent.putExtra("pubkey", mc_fixtures.GENT)
        ActivityNavigator.startActivity(intent)
        wait_for_render(20)
        detail = mpos.ui.screen_stack[-1][0]
        detail.map_button.send_event(lv.EVENT.CLICKED, None)
        wait_for_render(20)
        act = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(act).__name__, "MapActivity")
        pin = [p for p in act.view._pin_model if p["pubkey"] == mc_fixtures.GENT][0]
        self.assertTrue(abs(pin["sx"] - act.view.w / 2) < 2 and abs(pin["sy"] - act.view.h / 2) < 2)

    def test_node_without_a_position_has_no_map_button(self):
        from mpos import Intent
        from mpos.activity_navigator import ActivityNavigator
        import node_activity
        intent = Intent(activity_class=node_activity.NodeDetailActivity, app_fullname=mc_fixtures.APP)
        intent.putExtra("pubkey", "7c" + "55" * 31)
        ActivityNavigator.startActivity(intent)
        wait_for_render(20)
        detail = mpos.ui.screen_stack[-1][0]
        self.assertFalse(detail.map_button.has_flag(lv.obj.FLAG.CLICKABLE))


if __name__ == "__main__":
    unittest.main()
