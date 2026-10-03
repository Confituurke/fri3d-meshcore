import unittest

import lvgl as lv
import mpos.ui
from mpos import Intent, SharedPreferences, wait_for_render, find_label_with_text, click_label

import mc_fixtures


def _open_setup(step=None):
    from mpos.activity_navigator import ActivityNavigator
    import setup_activity
    intent = Intent(activity_class=setup_activity.SetupActivity, app_fullname=mc_fixtures.APP)
    if step:
        intent.putExtra("step", step)
    ActivityNavigator.startActivity(intent)
    wait_for_render(20)
    return mpos.ui.screen_stack[-1][0]


class TestSetup(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager(setup_done=False)

    def tearDown(self):
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_setup_three_steps_and_finish(self):
        rec = mc_fixtures.Recorder(self.m, "advertise", result=(True, None))
        mc_fixtures.push_base()
        act = _open_setup()
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Step 1 of 3"))
        act._name.set_text("Indy")
        self.assertTrue(click_label("Next"))
        wait_for_render(10)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Which mesh are you on?"))
        self.assertTrue(click_label("Next"))
        wait_for_render(10)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Step 3 of 3"))
        self.assertTrue(click_label("Finish"))
        wait_for_render(20)
        self.assertTrue(SharedPreferences(mc_fixtures.APP).get_bool("setup_done", False))
        self.assertEqual(self.m.nickname(), "Indy")
        self.assertEqual(self.m.radio_preset()["id"], "eu-narrow")
        self.assertEqual(rec.calls[0][2], {"flood": True})
        self.assertEqual(mc_fixtures.stack_names()[-1], "MeshCoreHome")
        self.assertFalse("SetupActivity" in mc_fixtures.stack_names())
        self.assertTrue(self.m.is_running())

    def test_setup_back_goes_to_previous_step(self):
        act = _open_setup()
        self.assertTrue(click_label("Next"))
        wait_for_render(10)
        self.assertTrue(click_label("Back"))
        wait_for_render(10)
        self.assertEqual(act._step, 1)

    def test_change_preset_only_mode(self):
        ed = SharedPreferences(mc_fixtures.APP).edit()
        ed.put_bool("setup_done", True)
        ed.commit()
        mc_fixtures.open_app(tab=2)
        self.assertTrue(click_label("Change"))
        wait_for_render(20)
        self.assertEqual(type(mpos.ui.screen_stack[-1][0]).__name__, "SetupActivity")
        self.assertTrue(click_label("Czech Republic (Narrow)"))
        wait_for_render(5)
        self.assertTrue(click_label("Save"))
        wait_for_render(20)
        self.assertEqual(self.m.radio_preset()["id"], "cz-narrow")
        self.assertEqual(type(mpos.ui.screen_stack[-1][0]).__name__, "MeshCoreHome")


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager()

    def tearDown(self):
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_settings_add_hashtag_channel(self):
        mc_fixtures.open_app(tab=3)
        self.assertTrue(click_label("Add channel"))
        wait_for_render(20)
        page = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(page).__name__, "AddChannelActivity")
        page._channel_name.set_text("#test")
        self.assertTrue(click_label("Add channel"))
        wait_for_render(20)
        self.assertIn("#test", self.m.get_channel_names())
        self.assertEqual(mc_fixtures.stack_names()[-1], "MeshCoreHome")
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "#test"))

    def test_settings_add_channel_error_keeps_the_page(self):
        mc_fixtures.open_app(tab=3)
        self.assertTrue(click_label("Add channel"))
        wait_for_render(20)
        page = mpos.ui.screen_stack[-1][0]
        page._channel_name.set_text("Club")
        page._channel_psk.set_text("not a key!")
        self.assertTrue(click_label("Add channel"))
        wait_for_render(10)
        self.assertEqual(mc_fixtures.stack_names()[-1], "AddChannelActivity")
        self.assertNotEqual(page._channel_msg.get_text(), "")

    def test_settings_edit_name_on_its_own_page(self):
        mc_fixtures.open_app(tab=3)
        self.assertTrue(click_label("Name"))
        wait_for_render(20)
        page = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(page).__name__, "NameActivity")
        page._name.set_text("Indy two")
        self.assertTrue(click_label("Save"))
        wait_for_render(20)
        self.assertEqual(self.m.nickname(), "Indy two")
        self.assertEqual(mc_fixtures.stack_names()[-1], "MeshCoreHome")
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Indy two"))

    def test_settings_channel_row_opens_channel_info(self):
        mc_fixtures.open_app(tab=3)
        self.assertTrue(click_label("Public"))
        wait_for_render(20)
        self.assertEqual(mc_fixtures.stack_names()[-1], "ChannelInfoActivity")

    def test_settings_service_switch(self):
        act = mc_fixtures.open_app(tab=3)
        sw = act._tab._service
        self.assertFalse(self.m.is_service_enabled())
        sw.add_state(lv.STATE.CHECKED)
        sw.send_event(lv.EVENT.VALUE_CHANGED, None)
        wait_for_render(5)
        self.assertTrue(self.m.is_service_enabled())

    def test_settings_shows_name_and_node_id(self):
        mc_fixtures.open_app(tab=3)
        pub, _ = self.m.get_identity()
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), pub.hex()[:8].upper()))


class TestSoundSettings(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager()
        ed = SharedPreferences(mc_fixtures.APP).edit()
        ed.put_dict("sound", {})
        ed.commit()
        self.m._sound_cache = None

    def tearDown(self):
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def _flip(self, sw, on):
        if on:
            sw.add_state(lv.STATE.CHECKED)
        else:
            sw.remove_state(lv.STATE.CHECKED)
        sw.send_event(lv.EVENT.VALUE_CHANGED, None)
        wait_for_render(5)

    def test_buzzer_switch_shows_the_choices(self):
        act = mc_fixtures.open_app(tab=3)
        tab = act._tab
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Buzzer"))
        self.assertTrue(tab._sound_rows.has_flag(lv.obj.FLAG.HIDDEN))
        self._flip(tab._sound["enabled"], True)
        self.assertTrue(self.m.sound_settings()["enabled"])
        self.assertFalse(tab._sound_rows.has_flag(lv.obj.FLAG.HIDDEN))
        for text in ("All", "Channel messages", "Direct messages", "Adverts heard"):
            self.assertIsNotNone(find_label_with_text(lv.screen_active(), text), text)

    def test_choose_kinds_and_all(self):
        act = mc_fixtures.open_app(tab=3)
        tab = act._tab
        self._flip(tab._sound["enabled"], True)
        self._flip(tab._sound["advert"], True)
        self.assertTrue(self.m.sound_settings()["advert"])
        self.assertTrue(tab._sound["all"].has_state(lv.STATE.CHECKED))
        self._flip(tab._sound["channel"], False)
        self.assertFalse(tab._sound["all"].has_state(lv.STATE.CHECKED))
        self._flip(tab._sound["all"], True)
        st = self.m.sound_settings()
        self.assertTrue(st["channel"] and st["dm"] and st["advert"], st)
        self._flip(tab._sound["all"], False)
        st = self.m.sound_settings()
        self.assertFalse(st["channel"] or st["dm"] or st["advert"], st)

    def test_test_sound(self):
        rec = mc_fixtures.Recorder(self.m, "test_sound")
        act = mc_fixtures.open_app(tab=3)
        self._flip(act._tab._sound["enabled"], True)
        self.assertTrue(click_label("Play a test sound"))
        wait_for_render(5)
        self.assertEqual(rec.names(), ["test_sound"])


class TestContactAndReplySettings(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager()
        ed = SharedPreferences(mc_fixtures.APP).edit()
        ed.put_dict("auto_add", {})
        ed.put_list("quick_replies", ["copy", "on my way", "ETA 10 min", "signal report"])
        ed.commit()
        self.m._auto_add_cache = None

    def tearDown(self):
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_auto_add_switches(self):
        act = mc_fixtures.open_app(tab=3)
        sw = act._tab._auto["rptr"]
        sw.add_state(lv.STATE.CHECKED)
        sw.send_event(lv.EVENT.VALUE_CHANGED, None)
        wait_for_render(5)
        self.assertTrue(self.m.auto_add_settings()["rptr"])
        self.assertFalse(self.m.auto_add_settings()["chat"])

    def test_mention_sound_row(self):
        act = mc_fixtures.open_app(tab=3)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Mentions"))
        self.assertTrue("mention" in act._tab._sound)

    def test_edit_quick_replies_and_use_them(self):
        mc_fixtures.open_app(tab=3)
        self.assertTrue(click_label("Quick replies"))
        wait_for_render(20)
        page = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(page).__name__, "QuickRepliesActivity")
        page._fields[0].set_text("wilco")
        page._fields[1].set_text("")
        self.assertTrue(click_label("Save"))
        wait_for_render(20)
        self.assertEqual(self.m.quick_replies(), ["wilco", "ETA 10 min", "signal report"])
        mc_fixtures.open_thread("channel", "Public")
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "wilco"))


if __name__ == "__main__":
    unittest.main()
