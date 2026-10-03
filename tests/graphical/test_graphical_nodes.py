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
        act = mc_fixtures.open_app(tab="Nodes")
        self.assertEqual(len(act._tab._order), 4)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "All 4"))
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "2 hops · SNR −3.5"))
        self.assertTrue(click_label("Repeaters"))
        wait_for_render(10)
        self.assertEqual(len(act._tab._order), 2)

    def test_tap_chat_node_opens_dm(self):
        mc_fixtures.open_app(tab="Nodes")
        self.assertTrue(click_label("Bob"))
        wait_for_render(20)
        self.assertTrue(self.m.is_contact(mc_fixtures.BOB))
        act = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(act).__name__, "DMChatActivity")

    def test_tap_repeater_opens_detail(self):
        mc_fixtures.open_app(tab="Nodes")
        self.assertTrue(click_label("Gent-Noord"))
        wait_for_render(20)
        act = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(act).__name__, "NodeDetailActivity")
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "repeater · F1A7…9C2E"))
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), " · SNR −3.5 dB · heard 14 min ago"))
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Last SNR"))
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "−3.5 dB"))

    def test_star_chip_shows_saved_contacts(self):
        self.m.add_contact(mc_fixtures.BOB, "Bob")
        act = mc_fixtures.open_app(tab="Nodes")
        act._tab._chips["contacts"].obj.send_event(lv.EVENT.CLICKED, None)
        wait_for_render(10)
        self.assertEqual(act._tab._order, [mc_fixtures.BOB])

    def test_search_filters_by_name_and_closes(self):
        act = mc_fixtures.open_app(tab="Nodes")
        tab = act._tab
        tab.search_button.send_event(lv.EVENT.CLICKED, None)
        wait_for_render(10)
        tab.search.set_text("aalst")
        wait_for_render(10)
        self.assertEqual(len(tab._order), 1)
        tab.close_search()
        wait_for_render(10)
        self.assertEqual(len(tab._order), 4)
        self.assertTrue(tab.search_bar.has_flag(lv.obj.FLAG.HIDDEN))

    def test_advert_button_zero_hop(self):
        rec = mc_fixtures.Recorder(self.m, "advertise", result=(True, None))
        mc_fixtures.open_app(tab="Nodes")
        self.assertTrue(click_label("Advert"))
        wait_for_render(5)
        self.assertEqual(rec.calls[0][2], {"flood": False})


STATUS = {"battery_mv": 4020, "uptime_s": 1051200, "noise_floor": -112, "last_snr": -3.5,
          "airtime_s": 22151, "rx_airtime_s": 67507, "packets_rx": 18233, "packets_tx": 9120}


def _open_detail(pk):
    import node_activity
    from mpos import Intent
    from mpos.activity_navigator import ActivityNavigator
    intent = Intent(activity_class=node_activity.NodeDetailActivity, app_fullname=mc_fixtures.APP)
    intent.putExtra("pubkey", pk)
    ActivityNavigator.startActivity(intent)
    wait_for_render(20)
    return mpos.ui.screen_stack[-1][0]


class TestServerDetail(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager()
        mc_fixtures.seed_nodes(self.m)

    def tearDown(self):
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def _logged_in(self, role="guest", **results):
        s = self.m.server_session(mc_fixtures.GENT)
        s.update(state="ok", role=role)
        for k, v in results.items():
            s["results"][k] = {"data": v, "at": 1790000000}

    def test_not_logged_in_and_guest_login(self):
        rec = mc_fixtures.Recorder(self.m, "login", result=(True, None))
        _open_detail(mc_fixtures.GENT)
        scr = lv.screen_active()
        self.assertIsNotNone(find_label_with_text(scr, "Not logged in"))
        self.assertTrue(click_label("Log in"))
        wait_for_render(5)
        self.assertEqual(rec.calls[0][1], (mc_fixtures.GENT, ""))

    def test_status_tab(self):
        self._logged_in(status=STATUS)
        _open_detail(mc_fixtures.GENT)
        scr = lv.screen_active()
        for text in ("Guest login", "Battery", "4.02 V", "12 d 4 h", "\u2212112 dBm", "18 233",
                     "Status as of"):
            self.assertIsNotNone(find_label_with_text(scr, text), text)

    def test_neighbours_and_telemetry_tabs(self):
        self._logged_in(neighbours={"total": 1, "rows": [{"prefix": "3a444444", "secs_ago": 120, "snr": 4.25}]},
                        telemetry=[{"channel": 1, "kind": "voltage", "value": 4.02}])
        act = _open_detail(mc_fixtures.GENT)
        rec = mc_fixtures.Recorder(self.m, "request_server", result=(True, None))
        self.assertTrue(click_label("Neighbours"))
        wait_for_render(10)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Aalst-Kerk"))
        self.assertTrue(click_label("Telemetry"))
        wait_for_render(10)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Voltage"))

    def test_refresh_asks_for_the_tab_in_view(self):
        self._logged_in(status=STATUS)
        _open_detail(mc_fixtures.GENT)
        rec = mc_fixtures.Recorder(self.m, "request_server", result=(True, None))
        self.assertTrue(click_label("Refresh"))
        wait_for_render(5)
        self.assertEqual(rec.calls[0][1], (mc_fixtures.GENT, "status"))

    def test_ping_and_its_result(self):
        rec = mc_fixtures.Recorder(self.m, "ping", result=(True, None))
        act = _open_detail(mc_fixtures.GENT)
        self.assertTrue(click_label("Ping"))
        wait_for_render(5)
        self.assertEqual(rec.calls[0][1], (mc_fixtures.GENT,))
        self.m.server_session(mc_fixtures.GENT)["results"]["ping"] = {
            "data": {"hop_snrs": [6.0], "final_snr": 5.5, "rtt_ms": 350, "hashes": [0xF1]}, "at": 1}
        act.on_server_event(mc_fixtures.GENT)
        wait_for_render(5)
        self.assertIsNotNone(find_label_with_text(lv.screen_active(), "Ping 350 ms"))

    def test_admin_login_page(self):
        rec = mc_fixtures.Recorder(self.m, "login", result=(True, None))
        _open_detail(mc_fixtures.GENT)
        self.assertTrue(click_label("Admin"))
        wait_for_render(20)
        page = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(page).__name__, "AdminLoginActivity")
        page._password.set_text("hunter2")
        self.assertTrue(click_label("Log in"))
        wait_for_render(20)
        self.assertEqual(rec.calls[0][1], (mc_fixtures.GENT, "hunter2"))
        self.assertEqual(type(mpos.ui.screen_stack[-1][0]).__name__, "NodeDetailActivity")

    def test_a_login_that_succeeds_fetches_the_tab(self):
        rec = mc_fixtures.Recorder(self.m, "request_server", result=(True, None))
        act = _open_detail(mc_fixtures.GENT)
        self.m.server_session(mc_fixtures.GENT).update(state="ok", role="guest")
        act.on_server_event(mc_fixtures.GENT)
        wait_for_render(5)
        self.assertEqual(rec.calls[0][1], (mc_fixtures.GENT, "status"))

    def test_room_has_a_chat_action(self):
        room = "7c" + "55" * 31
        _open_detail(room)
        self.assertTrue(click_label("Chat"))
        wait_for_render(20)
        act = mpos.ui.screen_stack[-1][0]
        self.assertEqual(type(act).__name__, "DMChatActivity")
        self.assertTrue(self.m.is_contact(room))


if __name__ == "__main__":
    unittest.main()
