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
        act = mc_fixtures.open_app(tab=3)
        tab = act._tab
        tab._channel_name.set_text("#test")
        self.assertTrue(click_label("Add channel"))
        wait_for_render(10)
        self.assertIn("#test", self.m.get_channel_names())
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "#test"))

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


if __name__ == "__main__":
    unittest.main()
