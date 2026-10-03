import unittest

import lvgl as lv
import mpos.ui
from mpos import wait_for_render

import mc_fixtures

KEY = "7aa6d679625b17999e96855b8969366f34d0a8ed0cca83be4996617c76980142"


def top():
    return mpos.ui.screen_stack[-1][0]


def sheet_click(text):
    import ui_theme
    ui_theme.ActionSheet.shown[-1].rows[text].send_event(lv.EVENT.CLICKED, None)
    wait_for_render(20)


class TestNew(unittest.TestCase):
    def setUp(self):
        self.m = mc_fixtures.fresh_manager()

    def tearDown(self):
        import ui_theme
        ui_theme.close_sheets()
        mpos.ui.remove_and_stop_all_activities()
        wait_for_render(5)

    def test_plus_offers_the_ways_to_start(self):
        act = mc_fixtures.open_app()
        act._tab.new_chat()
        import ui_theme
        rows = ui_theme.ActionSheet.shown[-1].rows
        for text in ("New channel", "Message a contact", "Add contact by key", "Discovered nodes"):
            self.assertTrue(text in rows, text)
        sheet_click("New channel")
        self.assertEqual(type(top()).__name__, "AddChannelActivity")

    def test_message_a_contact_opens_the_companions(self):
        act = mc_fixtures.open_app()
        act._tab.new_chat()
        sheet_click("Message a contact")
        self.assertEqual(act._tab_index, 1)
        self.assertEqual(act._tab.nodes.filt, "chat")

    def test_add_contact_by_key_and_by_card(self):
        act = mc_fixtures.open_app()
        act._tab.new_chat()
        sheet_click("Add contact by key")
        page = top()
        self.assertEqual(type(page).__name__, "AddContactActivity")
        page._key.set_text("not a key")
        page.save()
        self.assertTrue("not a public key" in page._msg.get_text())
        page._key.set_text(KEY)
        page._name.set_text("Stadhuis")
        page.set_type(1)
        page.save()
        wait_for_render(20)
        c = self.m.get_contact(KEY)
        self.assertEqual((c["name"], c["type"]), ("Stadhuis", 2))
        act._tab.new_chat()
        sheet_click("Add contact by key")
        page = top()
        from meshcore_advert import contact_share_uri
        other = "ab" * 32
        page._key.set_text(contact_share_uri("Room Gent", other, 3))
        page.save()
        wait_for_render(20)
        c = self.m.get_contact(other)
        self.assertEqual((c["name"], c["type"]), ("Room Gent", 3))


if __name__ == "__main__":
    unittest.main()
