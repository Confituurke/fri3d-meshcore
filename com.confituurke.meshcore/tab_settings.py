"""Settings tab: name, node id, background receiving, channels, radio preset, about."""

import lvgl as lv

from mpos import Intent, MposKeyboard

import ui_theme as T
import setup_activity
from ui_tabs import Tab

VERSION = "0.7.0"


class SettingsTab(Tab):
    title = "Settings"

    def build(self, parent, activity):
        self.activity = activity
        self.mgr = activity.mgr
        self.header = T.Header(parent, "Settings")
        body = T.box(parent, T.W, 1, lv.FLEX_FLOW.COLUMN)
        body.set_flex_grow(1)
        body.add_flag(lv.obj.FLAG.SCROLLABLE)
        body.set_scroll_dir(lv.DIR.VER)
        body.set_style_pad_hor(T.EDGE, lv.PART.MAIN)
        body.set_style_pad_row(8, lv.PART.MAIN)
        body.set_style_pad_bottom(200, lv.PART.MAIN)    # room to scroll above the keyboard
        self.body = body
        self._kb = MposKeyboard(parent.get_screen())
        self._kb.set_size(T.W, 188)
        self._kb.add_flag(lv.obj.FLAG.HIDDEN)

        self._section("Name")
        row = self._row()
        self._name = self._textarea(row, self.mgr.nickname())
        self._name.set_flex_grow(1)
        T.Chip(row, "Save", self.save_name)

        self._section("Node ID")
        pub, _ = self.mgr.get_identity()
        T.label(body, pub.hex()[:8].upper() if pub else "—", "mono", T.TEXT)

        self._section("Radio")
        row = self._row()
        T.label(row, "Receive in background", "body", T.TEXT).set_flex_grow(1)
        self._service = lv.switch(row)
        if self.mgr.is_service_enabled():
            self._service.add_state(lv.STATE.CHECKED)
        self._service.set_style_bg_color(T.color(T.ACCENT), lv.PART.INDICATOR | lv.STATE.CHECKED)
        self._service.add_event_cb(lambda e: self.mgr.set_service_enabled(
            self._service.has_state(lv.STATE.CHECKED)), lv.EVENT.VALUE_CHANGED, None)
        row = self._row()
        T.label(row, self.mgr.radio_preset().get("name") or "Custom", "body", T.TEXT).set_flex_grow(1)
        T.Chip(row, "Change", self.change_preset)

        self._section("Channels")
        self._channels = T.box(body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN)
        self._fill_channels()
        self._channel_name = self._textarea(body, "", "#name, or a private channel name")
        self._channel_psk = self._textarea(body, "", "Secret key (base64), private channels only")
        row = self._row()
        self._channel_msg = T.label(row, "", "small", T.ERR)
        self._channel_msg.set_flex_grow(1)
        T.Chip(row, "Add channel", self.add_channel)

        self._section("About")
        T.label(body, "MeshCore for MicroPythonOS %s" % VERSION, "body", T.TEXT)
        T.label(body, "MeshCore is a trademark of its owner.", "small", T.MUTED)

    def _section(self, text):
        lb = T.label(self.body, text, "small", T.ACCENT)
        lb.set_style_pad_top(10, lv.PART.MAIN)

    def _row(self):
        row = T.box(self.body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW)
        row.set_style_pad_column(8, lv.PART.MAIN)
        row.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        return row

    def _textarea(self, parent, text, placeholder=""):
        ta = lv.textarea(parent)
        ta.set_one_line(True)
        ta.set_text(text)
        ta.set_placeholder_text(placeholder)
        ta.set_width(lv.pct(100))
        ta.set_style_text_font(T.font("body"), lv.PART.MAIN)
        ta.set_style_bg_color(T.color(T.SURFACE2), lv.PART.MAIN)
        ta.set_style_text_color(T.color(T.TEXT), lv.PART.MAIN)
        ta.set_style_border_width(0, lv.PART.MAIN)
        ta.set_style_radius(10, lv.PART.MAIN)
        ta.add_event_cb(lambda e: self._attach_keyboard(ta), lv.EVENT.FOCUSED, None)
        return ta

    def _attach_keyboard(self, ta):
        # Focus moves between textareas while a screen is being torn down, after the
        # keyboard may already be gone.
        if self._kb is None:
            return
        try:
            self._kb.set_textarea(ta)
        except Exception:
            self._kb = None

    def _fill_channels(self):
        self._channels.clean()
        for ch in self.mgr.get_channels():
            row = T.box(self._channels, lv.pct(100), 44, lv.FLEX_FLOW.ROW, "row")
            row.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            T.label(row, ch.name, "body", T.TEXT)
            T.label(row, ch.kind, "small", T.MUTED)
            if ch.name != "Public":
                x = T.box(row, 40, 40)
                T.symbol(x, lv.SYMBOL.CLOSE, T.ERR).center()
                T.clickable(x, lambda n=ch.name: self.remove_channel(n))

    def save_name(self):
        if self.mgr.set_nickname(self._name.get_text()):
            self.header.set_subtitle("Name saved")

    def change_preset(self):
        intent = Intent(activity_class=setup_activity.SetupActivity)
        intent.putExtra("step", 2)
        self.activity.startActivity(intent)

    def add_channel(self):
        ok, err = self.mgr.add_channel(self._channel_name.get_text(), self._channel_psk.get_text())
        if ok:
            self._channel_name.set_text("")
            self._channel_psk.set_text("")
            self._channel_msg.set_text("")
        else:
            self._channel_msg.set_text(err or "could not add")

    def remove_channel(self, name):
        self.mgr.remove_channel(name)

    def destroy(self):
        # The keyboard lives on the screen, not in the tab's container: delete it here.
        if self._kb is not None:
            self._kb.delete()
            self._kb = None

    def on_event(self, event, data):
        if event == "channels":
            self._fill_channels()
