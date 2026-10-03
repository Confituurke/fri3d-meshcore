"""Settings sub-pages: editing the name and adding a channel, each with its own keyboard."""

import lvgl as lv

from mpos import Activity

import ui_theme as T
from meshcore_manager import MeshCoreManager


class _FormActivity(Activity):
    """Sub-page header, a form in a scrolling body, a primary button, and the keyboard."""

    title = ""

    def onCreate(self):
        self.mgr = MeshCoreManager.get_instance()
        scr = T.make_screen()
        T.HeaderSub(scr, self.title, back=self.finish)
        self.body = T.scroll_area(scr, 14, 8)
        self.body.set_style_pad_ver(8, lv.PART.MAIN)
        self.build()
        self._kb = T.keyboard(scr)
        self.setContentView(scr)
        self._first.add_state(lv.STATE.FOCUSED)
        self._kb.set_textarea(self._first)
        self._kb.show_keyboard()

    def field(self, title, text="", placeholder=""):
        T.label(self.body, title, 15, col=T.MUTED)
        ta = T.text_input(self.body, text, placeholder)
        ta.add_event_cb(lambda e: self._kb.set_textarea(ta), lv.EVENT.FOCUSED, None)
        return ta

    def hint(self, text, col=T.MUTED):
        return T.label(self.body, text, 15, col=col, long_mode=lv.label.LONG_MODE.WRAP,
                       width=lv.pct(100))


class NameActivity(_FormActivity):
    title = "Your name"

    def build(self):
        self._name = self.field("Your name on the mesh", self.mgr.nickname(), "Name")
        self._first = self._name
        self._msg = self.hint("Others see it next to your messages and in their node list.")
        T.button(self.body, "Save", self.save, width=lv.pct(100))

    def save(self):
        if self.mgr.set_nickname(self._name.get_text()):
            self.finish()
        else:
            self._msg.set_text("A name cannot be empty.")
            self._msg.set_style_text_color(T.color(T.FAIL_TEXT), lv.PART.MAIN)


class AddChannelActivity(_FormActivity):
    title = "New channel"

    def build(self):
        self._channel_name = self.field("Name", "", "#name, or a private channel name")
        self._first = self._channel_name
        self._channel_psk = self.field("Secret key (private channels only)", "", "base64")
        self.hint("Without a key you join the hashtag channel of that name, shared by everyone "
                  "who uses it. For a private channel, enter the key you were given.")
        self._channel_msg = self.hint("", T.FAIL_TEXT)
        T.button(self.body, "Add channel", self.add, width=lv.pct(100))

    def add(self):
        ok, err = self.mgr.add_channel(self._channel_name.get_text(), self._channel_psk.get_text())
        if ok:
            self.finish()
        else:
            self._channel_msg.set_text(err or "could not add")
