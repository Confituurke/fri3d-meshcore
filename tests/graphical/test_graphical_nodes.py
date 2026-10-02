import unittest

import lvgl as lv
import mpos.ui
from mpos import wait_for_render, find_label_with_text, click_label

import mc_fixtures


class TestNodes(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager()
        mc_fixtures.seed_nodes(self.m)

    def tearDown(self):
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_node_rows_and_filters(self):
        act = mc_fixtures.open_app(tab=1)
        self.assertEqual(len(act._tab._order), 4)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "All 4"))
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "2 hops · SNR −3.5"))
        self.assertTrue(click_label("Repeaters"))
        wait_for_render(10)
        self.assertEqual(len(act._tab._order), 2)

    def test_tap_chat_node_opens_dm(self):
        mc_fixtures.open_app(tab=1)
        self.assertTrue(click_label("Bob"))
        wait_for_render(20)
        self.assertTrue(self.m.is_contact(mc_fixtures.BOB))
        act = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(act).__name__, "DMChatActivity")

    def test_tap_repeater_opens_detail(self):
        mc_fixtures.open_app(tab=1)
        self.assertTrue(click_label("Gent-Noord"))
        wait_for_render(20)
        act = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(act).__name__, "NodeDetailActivity")
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "repeater · F1A7…9C2E"))
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "2 hops · SNR −3.5 dB · heard 14 min ago"))

    def test_advert_button_zero_hop(self):
        rec = mc_fixtures.Recorder(self.m, "advertise", result=(True, None))
        mc_fixtures.open_app(tab=1)
        self.assertTrue(click_label("Advert"))
        wait_for_render(5)
        self.assertEqual(rec.calls[0][2], {"flood": False})


if __name__ == "__main__":
    unittest.main()
