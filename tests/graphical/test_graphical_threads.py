import unittest

import lvgl as lv
import mpos.ui
from mpos import wait_for_render, find_label_with_text, click_label

import mc_fixtures


class TestThreads(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager()
        mc_fixtures.seed_chats(self.m)

    def tearDown(self):
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_channel_bubbles_and_meta(self):
        import ui_model
        import ui_theme
        act = mc_fixtures.open_thread("channel", "Public")
        ts = self.m.get_messages("Public")[0]["ts"]
        meta = "%s · SNR 6.5 · 3 hops" % ui_model.clock_text(ts, ui_theme.tz_offset_s())
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), meta))
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "road closed near Aalst"))
        self.assertEqual(len(act._bubbles), 2)

    def test_outgoing_heard_label(self):
        import meshcore_manager as mm
        self.m._add_message("Public", {"ts": mm.unix_time(), "sender": "Kim", "text": "thanks",
                                       "incoming": False, "tx": True, "heard": 4})
        mc_fixtures.open_thread("channel", "Public")
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "heard ×4"))

    def test_counter_and_send_disabled(self):
        act = mc_fixtures.open_thread("dm", mc_fixtures.ALEX)
        act._ta.set_text("x" * 161)
        wait_for_render(5)
        self.assertEqual(act._counter.get_text(), "-1 left")
        self.assertTrue(act._send.has_state(lv.STATE.DISABLED))
        act._ta.set_text("hi")
        wait_for_render(5)
        self.assertEqual(act._counter.get_text(), "158 left")
        self.assertFalse(act._send.has_state(lv.STATE.DISABLED))

    def test_channel_counter_counts_the_sender_prefix(self):
        act = mc_fixtures.open_thread("channel", "Public")
        act._ta.set_text("hi")
        wait_for_render(5)
        self.assertEqual(act._counter.get_text(), "153 left")      # 160 - "Kim: " - 2

    def test_quick_reply_sends(self):
        rec = mc_fixtures.Recorder(self.m, "send_group_text")
        mc_fixtures.open_thread("channel", "Public")
        self.assertTrue(click_label("on my way"))
        wait_for_render(5)
        self.assertEqual(rec.calls[0][1], ("Public", "on my way"))

    def test_failed_dm_tap_resends(self):
        import meshcore_manager as mm
        self.m._add_dm(mc_fixtures.ALEX, {"ts": mm.unix_time(), "sender": "Kim", "text": "spare antenna?",
                                         "incoming": False, "tx": True, "delivered": False,
                                         "failed": True, "ack": "01"})
        rec = mc_fixtures.Recorder(self.m, "resend")
        mc_fixtures.open_thread("dm", mc_fixtures.ALEX)
        self.assertTrue(click_label("tap to resend"))
        wait_for_render(5)
        self.assertEqual(rec.names(), ["resend"])
        self.assertEqual(rec.calls[0][1][0], mc_fixtures.ALEX)

    def test_open_clears_unread(self):
        self.assertEqual(self.m.get_unread("Public"), 2)
        mc_fixtures.open_thread("channel", "Public")
        self.assertEqual(self.m.get_unread("Public"), 0)

    def test_new_message_event_appends_a_bubble(self):
        import meshcore_manager as mm
        act = mc_fixtures.open_thread("channel", "Public")
        msg = {"ts": mm.unix_time(), "sender": "Robin", "text": "copy that", "incoming": True}
        self.m._add_message("Public", msg)
        self.m._notify("message", ("Public", msg))
        wait_for_render(10)
        self.assertEqual(len(act._bubbles), 3)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "copy that"))


if __name__ == "__main__":
    unittest.main()
