import unittest

import lvgl as lv
import mpos.ui
from mpos import AppManager, wait_for_render, find_label_with_text, click_label

import mc_fixtures


class TestShell(unittest.TestCase):
    def tearDown(self):
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_tabs_switch_and_fill_the_screen(self):
        mc_fixtures.fresh_manager()
        AppManager.start_app(mc_fixtures.APP)
        wait_for_render(20)
        scr = lv.screen_active()
        self.assertEqual(scr.get_width(), 480)
        self.assertIsNotNone(find_label_with_text(scr, "Chats"))
        self.assertTrue(click_label("Nodes"))
        wait_for_render(10)
        act = mpos.ui.screen_stack[-1][0]
        self.assertEqual(act._tab_index, 1)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Nodes"))

    def test_first_run_starts_setup(self):
        mc_fixtures.fresh_manager(setup_done=False)
        AppManager.start_app(mc_fixtures.APP)
        wait_for_render(20)
        act = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(act).__name__, "SetupActivity")


if __name__ == "__main__":
    unittest.main()
