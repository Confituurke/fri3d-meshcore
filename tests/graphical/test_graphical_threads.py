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


    def test_long_thread_opens_on_the_newest_and_loads_earlier(self):
        import meshcore_manager as mm
        now = mm.unix_time()
        for i in range(40):
            self.m._add_message("Public", {"ts": now - 400 + i, "sender": "Sam",
                                           "text": "msg %d" % i, "incoming": True})
        act = mc_fixtures.open_thread("channel", "Public")
        self.assertEqual(len(act._bubbles), 25)
        self.assertIsNone(find_label_with_text(lv.screen_active(), "msg 0"))
        self.assertTrue(click_label("Show earlier messages"))
        wait_for_render(10)
        self.assertEqual(len(act._bubbles), 42)            # 40 + the 2 seeded ones: one page
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "msg 0"))
        self.assertIsNone(find_label_with_text(lv.screen_active(), "Show earlier messages"))


    def test_a_drag_on_a_bubble_scrolls_the_thread(self):
        # LVGL scrolls the first scrollable object up from the one under the finger; with
        # nothing pressable under it, the press lands on the screen and nothing scrolls
        import meshcore_manager as mm
        now = mm.unix_time()
        for i in range(30):
            self.m._add_message("Public", {"ts": now - 400 + i, "sender": "Sam",
                                           "text": "msg %d" % i, "incoming": True})
        act = mc_fixtures.open_thread("channel", "Public")
        view = lv.area_t()
        act.list.get_coords(view)
        a = lv.area_t()
        for b in act._bubbles.values():            # one that is in view
            b.obj.get_coords(a)
            if a.y1 >= view.y1 and a.y2 <= view.y2:
                break
        p = lv.point_t()
        p.x, p.y = (a.x1 + a.x2) // 2, (a.y1 + a.y2) // 2
        hit = lv.indev_search_obj(lv.screen_active(), p)
        self.assertIsNotNone(hit)
        while hit is not None and not hit.has_flag(lv.obj.FLAG.SCROLLABLE):
            hit = hit.get_parent()
        self.assertTrue(hit is not None and hit == act.list)

    def test_earlier_messages_load_a_page_at_a_time(self):
        import meshcore_manager as mm
        now = mm.unix_time()
        for i in range(80):
            self.m._add_message("Public", {"ts": now - 400 + i, "sender": "Sam",
                                           "text": "msg %d" % i, "incoming": True})
        act = mc_fixtures.open_thread("channel", "Public")
        total = len(self.m.get_messages("Public"))
        counts = [len(act._bubbles)]
        while click_label("Show earlier messages"):
            wait_for_render(10)
            counts.append(len(act._bubbles))
        self.assertEqual(counts[0], 25)
        self.assertEqual(counts[-1], total)
        self.assertTrue(len(counts) >= 3, counts)


class TestDayDividers(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager()

    def tearDown(self):
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_a_divider_before_each_day(self):
        import meshcore_manager as mm
        import ui_theme
        now = mm.unix_time()
        tz = ui_theme.tz_offset_s()
        midnight = (now + tz) // 86400 * 86400 - tz
        for ts, text in ((midnight - 7200, "late last night"), (midnight - 3600, "still up"),
                         (midnight + 60, "after midnight")):
            self.m._add_message("Public", {"ts": ts, "sender": "Sam", "text": text,
                                           "incoming": True})
        act = mc_fixtures.open_thread("channel", "Public")
        labels = lambda: sorted(text for text, _ in act._days.values())
        self.assertEqual(labels(), ["Today", "Yesterday"])
        scr = lv.screen_active()
        self.assertIsNotNone(find_label_with_text(scr, "Yesterday"))
        self.assertIsNotNone(find_label_with_text(scr, "Today"))
        kids = [act.list.get_child(i) for i in range(act.list.get_child_count())]
        today = [o for text, o in act._days.values() if text == "Today"][0]
        self.assertEqual(kids.index(today),
                         kids.index(act._bubbles[id(self.m.get_messages("Public")[2])].obj) - 1)
        self.m.delete_message("Public", self.m.get_messages("Public")[2])
        act.refresh(scroll=False)
        self.assertEqual(labels(), ["Yesterday"], "a day without messages loses it")


if __name__ == "__main__":
    unittest.main()
