"""Settings tab: profile, radio, channels and about, as grouped rows; editing the name and
adding a channel open their own pages."""

import lvgl as lv

from mpos import Intent

import meshcore_presets
import ui_theme as T
import settings_pages
import setup_activity
import thread_activity
from ui_tabs import Tab

VERSION = "0.7.0"


class SettingsTab(Tab):
    title = "Settings"

    def build(self, parent, activity):
        self.activity = activity
        self.mgr = activity.mgr
        T.HeaderTop(parent, "Settings")
        body = T.scroll_area(parent, 14, 8)
        body.set_style_pad_bottom(12, lv.PART.MAIN)

        T.section_label(body, "Profile")
        card = self._card(body)
        self._name_row = T.SettingRow(card, "Name", self.mgr.nickname(),
                                      lambda: self._open(settings_pages.NameActivity), first=True)
        pub, _ = self.mgr.get_identity()
        T.SettingRow(card, "Node ID", pub.hex()[:8].upper() if pub else "—")

        T.section_label(body, "Radio")
        card = self._card(body)
        self._preset_row = T.SettingRow(card, "Radio preset", self._preset_text(),
                                        self.change_preset, first=True)
        row = T.row(card, lv.pct(100), 52, 8)
        T.divider(row, lv.BORDER_SIDE.TOP)
        T.label(row, "Receive in background", 16).set_flex_grow(1)
        self._service = T.switch(row, self.mgr.is_service_enabled(), self.mgr.set_service_enabled)

        T.section_label(body, "Location")
        card = self._card(body)
        self._location_row = T.SettingRow(card, "My position", self._location_text(),
                                          lambda: self._open(settings_pages.LocationActivity),
                                          first=True)

        T.section_label(body, "Sounds")
        self._build_sounds(body)

        T.section_label(body, "Messages")
        card = self._card(body)
        T.SettingRow(card, "Quick replies", None,
                     lambda: self._open(settings_pages.QuickRepliesActivity), first=True)

        T.section_label(body, "Auto-add contacts")
        card = self._card(body)
        auto = self.mgr.auto_add_settings()
        self._auto = {}
        for i, (key, text) in enumerate(self._AUTO):
            row = T.row(card, lv.pct(100), 52, 8)
            if i:
                T.divider(row, lv.BORDER_SIDE.TOP)
            T.label(row, text, 16).set_flex_grow(1)
            self._auto[key] = T.switch(row, auto[key], lambda v, k=key: self.mgr.set_auto_add(**{k: v}))
        T.label(body, "Nodes of the switched-on kinds become contacts when their advert is heard.",
                13, col=T.MUTED, long_mode=lv.label.LONG_MODE.WRAP, width=lv.pct(100))

        T.section_label(body, "Channels")
        self._channels = self._card(body)
        self._fill_channels()

        T.section_label(body, "About")
        card = self._card(body)
        T.SettingRow(card, "Version", VERSION, first=True)
        T.label(body, "MeshCore is a trademark of its owner.", 13, col=T.MUTED)

    _KINDS = (("channel", "Channel messages"), ("dm", "Direct messages"),
              ("mention", "Mentions"), ("advert", "Adverts heard"))
    _AUTO = (("chat", "Companions"), ("rptr", "Repeaters"), ("room", "Room servers"),
             ("sensor", "Sensors"))

    def _build_sounds(self, body):
        cfg = self.mgr.sound_settings()
        card = self._card(body)
        self._sound = {}
        row = T.row(card, lv.pct(100), 52, 8)
        T.label(row, "Buzzer", 16).set_flex_grow(1)
        self._sound["enabled"] = T.switch(row, cfg["enabled"], self._set_enabled)
        self._sound_rows = T.column(card, lv.pct(100), lv.SIZE_CONTENT, 0)
        for key, text in (("all", "All"),) + self._KINDS:
            row = T.row(self._sound_rows, lv.pct(100), 52, 8)
            T.divider(row, lv.BORDER_SIDE.TOP)
            T.label(row, text, 16).set_flex_grow(1)
            self._sound[key] = T.switch(row, cfg[key], lambda v, k=key: self._set_kind(k, v))
        self._show_kinds(cfg)
        T.SettingRow(self._sound_rows, "Play a test sound", None, self.mgr.test_sound, chevron=False)
        if not self.mgr.has_buzzer():
            T.label(self._sound_rows, "This device has no buzzer the app can use.", 13, col=T.MUTED)
        self._show_sound_rows(cfg["enabled"])

    def _show_sound_rows(self, on):
        if on:
            self._sound_rows.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            self._sound_rows.add_flag(lv.obj.FLAG.HIDDEN)

    def _set_enabled(self, on):
        self.mgr.set_sound_settings(enabled=on)
        self._show_sound_rows(on)

    def _set_kind(self, key, on):
        self._show_kinds(self.mgr.set_sound_settings(**{key: on}))

    def _show_kinds(self, cfg):
        """With All on, every kind sounds: their switches show on and are locked; with All
        off they show (and edit) the own choice, which All leaves untouched."""
        self._check(self._sound["all"], cfg["all"])
        for k, _ in self._KINDS:
            sw = self._sound[k]
            self._check(sw, cfg["all"] or cfg[k])
            if cfg["all"]:
                sw.add_state(lv.STATE.DISABLED)
            else:
                sw.remove_state(lv.STATE.DISABLED)

    @staticmethod
    def _check(sw, on):
        if on:
            sw.add_state(lv.STATE.CHECKED)
        else:
            sw.remove_state(lv.STATE.CHECKED)

    def _card(self, parent):
        return T.card(parent, filled=False, pad_ver=0, pad_hor=14, gap=0)

    def _location_text(self):
        pos = self.mgr.position()
        if self.mgr.gps_status()["enabled"]:
            return "GPS"
        return "set" if pos else "not set"

    def _preset_text(self):
        return meshcore_presets.short_name(self.mgr.radio_preset())

    def _fill_channels(self):
        self._channels.clean()
        for i, ch in enumerate(self.mgr.get_channels()):
            T.SettingRow(self._channels, ch.name, self.mgr.channel_kind(ch.name) or "public",
                         lambda n=ch.name: self.channel_info(n), first=i == 0)
        add = T.SettingRow(self._channels, "Add channel", None,
                           lambda: self._open(settings_pages.AddChannelActivity))
        add.title.set_style_text_color(T.color(T.ACCENT), lv.PART.MAIN)

    def _open(self, cls):
        self.activity.startActivity(Intent(activity_class=cls))

    def channel_info(self, name):
        intent = Intent(activity_class=thread_activity.ChannelInfoActivity)
        intent.putExtra("channel", name)
        self.activity.startActivity(intent)

    def change_preset(self):
        intent = Intent(activity_class=setup_activity.SetupActivity)
        intent.putExtra("step", 2)
        self.activity.startActivity(intent)

    def on_resume(self):
        self._name_row.value.set_text(self.mgr.nickname())
        self._preset_row.value.set_text(self._preset_text())
        self._location_row.value.set_text(self._location_text())
        self._fill_channels()

    def on_event(self, event, data):
        if event == "channels":
            self._fill_channels()
