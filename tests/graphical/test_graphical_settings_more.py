import unittest

import lvgl as lv
import mpos.ui
from mpos import wait_for_render

import mc_fixtures


def top():
    return mpos.ui.screen_stack[-1][0]


def tap(obj):
    obj.send_event(lv.EVENT.CLICKED, None)
    wait_for_render(20)


class TestSettingsMore(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager()

    def tearDown(self):
        import ui_theme
        ui_theme.close_sheets()
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_automatic_adverts(self):
        act = mc_fixtures.open_app(tab="Settings")
        self.assertEqual(act._tab._advert_row.value.get_text(), "Off")
        tap(act._tab._advert_row.obj)
        page = top()
        self.assertEqual(type(page).__name__, "AutoAdvertActivity")
        tap(page.flood_rows[12])
        tap(page.zero_rows[30])
        self.assertEqual(self.m.auto_advert_settings(), {"flood_h": 12, "zero_hop_min": 30})
        page.finish()
        wait_for_render(20)
        self.assertEqual(act._tab._advert_row.value.get_text(), "12 h · nearby 30 min")


if __name__ == "__main__":
    unittest.main()
