"""Settings sub-pages: the name, a new channel, the quick replies, our own position and the
app's look."""

import lvgl as lv

from mpos import Activity, Intent

import ui_model
import ui_palette
import ui_theme as T
from meshcore_manager import MeshCoreManager, MESHCORE_APP, MAX_QUICK_REPLIES, MAX_QUICK_REPLY_LEN


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

    def hint(self, text, col=None):
        return T.label(self.body, text, 15, col=T.MUTED if col is None else col,
                       long_mode=lv.label.LONG_MODE.WRAP, width=lv.pct(100))


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


class _ReplyRow:
    """A quick reply in the list: its text (tap: edit) and a cross (remove)."""

    def __init__(self, parent, text, first, on_edit, on_remove):
        self.obj = T.row(parent, lv.pct(100), 52, 8)
        if not first:
            T.divider(self.obj, lv.BORDER_SIDE.TOP)
        lb = T.label(self.obj, text, 16, long_mode=lv.label.LONG_MODE.DOTS, emoji=True)
        lb.set_flex_grow(1)
        lb.add_flag(lv.obj.FLAG.EVENT_BUBBLE)
        T.clickable(self.obj, on_edit)
        self.remove = T.icon_button(self.obj, "close", on_remove, 44, 44, T.MUTED)


class QuickRepliesActivity(Activity):
    """The replies offered above the message box: tap one to edit it, the cross removes it,
    and up to MAX_QUICK_REPLIES can be added."""

    def onCreate(self):
        self.mgr = MeshCoreManager.get_instance()
        scr = T.make_screen()
        T.HeaderSub(scr, "Quick replies", back=self.finish)
        body = T.scroll_area(scr, 14, 8)
        body.set_style_pad_ver(8, lv.PART.MAIN)
        self.card = T.card(body, filled=False, pad_ver=0, pad_hor=14, gap=0)
        self._rows = []
        self._add = None
        T.label(body, "Tap one above the message box to send it.", 15, col=T.MUTED,
                long_mode=lv.label.LONG_MODE.WRAP, width=lv.pct(100))
        self.refresh()
        self.setContentView(scr)

    def onResume(self, screen):
        super().onResume(screen)
        self.refresh()

    def refresh(self):
        self.card.clean()
        replies = self.mgr.quick_replies()
        self._rows = [_ReplyRow(self.card, text, i == 0, lambda i=i: self.edit(i),
                                lambda i=i: self.remove(i)) for i, text in enumerate(replies)]
        self._add = T.SettingRow(self.card, "Add quick reply", None, lambda: self.edit(-1),
                                 first=not replies).obj
        self._add.get_child(0).set_style_text_color(T.color(T.ACCENT), lv.PART.MAIN)
        if len(replies) >= MAX_QUICK_REPLIES:
            self._add.add_flag(lv.obj.FLAG.HIDDEN)

    def edit(self, index):
        intent = Intent(activity_class=QuickReplyEditActivity)
        intent.putExtra("index", index)
        self.startActivity(intent)

    def remove(self, index):
        replies = self.mgr.quick_replies()
        if 0 <= index < len(replies):
            del replies[index]
            self.mgr.set_quick_replies(replies)
        self.refresh()


class QuickReplyEditActivity(_FormActivity):
    title = "Quick reply"

    def build(self):
        self.index = self.getIntent().extras.get("index", -1)
        replies = self.mgr.quick_replies()
        current = replies[self.index] if 0 <= self.index < len(replies) else ""
        self._text = self.field("Text, at most %d characters" % MAX_QUICK_REPLY_LEN, current, "")
        self._text.set_max_length(MAX_QUICK_REPLY_LEN)
        self._first = self._text
        T.button(self.body, "Save", self.save, width=lv.pct(100))
        if self.index >= 0:
            T.button(self.body, "Remove", self.remove, "outline", width=lv.pct(100))

    def save(self):
        text = self._text.get_text().strip()
        replies = self.mgr.quick_replies()
        if 0 <= self.index < len(replies):
            if text:
                replies[self.index] = text
            else:
                del replies[self.index]          # emptied: same as removing it
        elif text:
            replies.append(text)
        self.mgr.set_quick_replies(replies)
        self.finish()

    def remove(self):
        replies = self.mgr.quick_replies()
        if 0 <= self.index < len(replies):
            del replies[self.index]
            self.mgr.set_quick_replies(replies)
        self.finish()


class LocationActivity(Activity):
    """Our position: from a GPS when one is switched on and answers, else set by hand (picked
    on the map or typed). Whether adverts carry it."""

    def onCreate(self):
        self.mgr = MeshCoreManager.get_instance()
        scr = T.make_screen()
        T.HeaderSub(scr, "Location", back=self.finish)
        body = T.scroll_area(scr, 14, 8)
        body.set_style_pad_ver(8, lv.PART.MAIN)

        card = T.card(body, filled=False, pad_ver=0, pad_hor=14, gap=0)
        row = T.row(card, lv.pct(100), 52, 8)
        T.label(row, "Use GPS", 16).set_flex_grow(1)
        self._gps = T.switch(row, self.mgr.gps_status()["enabled"], self.set_gps)
        self._gps_state = T.label(body, "", 13, col=T.MUTED, long_mode=lv.label.LONG_MODE.WRAP,
                                  width=lv.pct(100))

        T.section_label(body, "My position")
        card = T.card(body, filled=True, pad_ver=12, pad_hor=14, gap=4)
        self._coords = T.label(card, "", 18, mono=True)
        self._source = T.label(card, "", 13, col=T.MUTED)
        actions = T.row(body, lv.pct(100), 48, 8)
        for text, cb in (("Pick on map", self.pick), ("Enter", self.enter), ("Clear", self.clear)):
            b = T.button(actions, text, cb, "tile", 48, width=1, size=16)
            b.set_flex_grow(1)
            if text == "Clear":
                self._clear = b

        card = T.card(body, filled=False, pad_ver=0, pad_hor=14, gap=0)
        row = T.row(card, lv.pct(100), 52, 8)
        T.label(row, "Share in adverts", 16).set_flex_grow(1)
        self._share = T.switch(row, self.mgr.share_position(), self.mgr.set_share_position)
        T.label(body, "Everyone on the mesh who hears your advert sees this position.", 13,
                col=T.MUTED, long_mode=lv.label.LONG_MODE.WRAP, width=lv.pct(100))
        self.refresh()
        self.setContentView(scr)

    def onResume(self, screen):
        super().onResume(screen)
        self.mgr.add_subscriber(self._on_event)
        self.refresh()

    def onPause(self, screen):
        self.mgr.remove_subscriber(self._on_event)
        super().onPause(screen)

    def _on_event(self, event, data):
        if event == "position":
            self.update_ui_threadsafe_if_foreground(self.refresh)

    def refresh(self):
        pos = self.mgr.position()
        coords, source = ui_model.position_text(pos)
        self._coords.set_text(coords)
        self._source.set_text(source)
        gps = self.mgr.gps_status()
        self._gps_state.set_text(ui_model.gps_text(gps))
        if gps["enabled"]:
            self._gps.add_state(lv.STATE.CHECKED)
        else:
            self._gps.remove_state(lv.STATE.CHECKED)
        if pos:
            self._clear.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            self._clear.add_flag(lv.obj.FLAG.HIDDEN)

    def set_gps(self, on):
        self.mgr.set_gps_enabled(on)
        self.refresh()

    def pick(self):
        import map_view
        self.startActivity(Intent(activity_class=map_view.MapPickActivity))

    def enter(self):
        self.startActivity(Intent(activity_class=CoordinatesActivity))

    def clear(self):
        self.mgr.clear_position()
        self.refresh()


class CoordinatesActivity(_FormActivity):
    title = "Enter position"

    def build(self):
        pos = self.mgr.position()
        text = "%.5f, %.5f" % (pos["lat"], pos["lon"]) if pos else ""
        self._coords = self.field("Latitude, longitude", text, "50.85045, 4.34878")
        self._first = self._coords
        self._msg = self.hint("Decimal degrees, south and west negative.")
        T.button(self.body, "Save", self.save, width=lv.pct(100))

    def save(self):
        ll = ui_model.parse_coords(self._coords.get_text())
        ok, err = self.mgr.set_position(*ll) if ll else (False, "two numbers, like 50.85, 4.35")
        if ok:
            self.finish()
        else:
            self._msg.set_text(err)
            self._msg.set_style_text_color(T.color(T.FAIL_TEXT), lv.PART.MAIN)


def appearance_text():
    """The Settings row's value: "System", or what the app pins ("Dark · Teal")."""
    from mpos import SharedPreferences
    prefs = SharedPreferences(MESHCORE_APP)
    theme = prefs.get_string("theme", "system") or "system"
    accent = prefs.get_string("accent", "system") or "system"
    parts = [n for n, v in ui_palette.THEMES if v == theme and v != "system"]
    parts += [n for n, v in ui_palette.ACCENTS if v == accent and v != "system"]
    style = prefs.get_string("map_style", "system") or "system"
    if style != "system":
        parts.append("map " + ui_model.cap(style))
    return " \u00b7 ".join(parts) if parts else "System"


class AppearanceActivity(Activity):
    """Light or dark, the accent colour and the map style: MicroPythonOS's look and the
    matching map by default, or the app's own choice."""

    SWATCH = 44

    def onCreate(self):
        from mpos import SharedPreferences
        self.prefs = SharedPreferences(MESHCORE_APP)
        self.scr = T.make_screen()
        self.build()
        self.setContentView(self.scr)

    def build(self):
        T.HeaderSub(self.scr, "Appearance", back=self.finish)
        body = T.scroll_area(self.scr, 14, 8)
        body.set_style_pad_ver(8, lv.PART.MAIN)
        theme = self.prefs.get_string("theme", "system") or "system"
        accent = self.prefs.get_string("accent", "system") or "system"
        values = [v for _, v in ui_palette.THEMES]
        T.section_label(body, "Theme")
        self.theme = T.Segmented(body, [n for n, _ in ui_palette.THEMES],
                                 lambda i: self.choose("theme", values[i]),
                                 values.index(theme) if theme in values else 0)
        T.section_label(body, "Accent colour")
        grid = T.box(body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW_WRAP)
        grid.set_style_pad_column(10, lv.PART.MAIN)
        grid.set_style_pad_row(10, lv.PART.MAIN)
        self.swatches = {}
        os_accent = T._os_look()[1]
        for name, value in ui_palette.ACCENTS:
            cell = T.column(grid, 52, lv.SIZE_CONTENT, 4)
            cell.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            sw = T.box(cell, self.SWATCH, self.SWATCH)
            c = (os_accent if os_accent is not None else ui_palette.DESIGN_ACCENT) \
                if value == "system" else int(value, 16)
            on = value == accent
            T.fill(sw, c, self.SWATCH // 2, T.TEXT if on else T.OUTLINE, 3 if on else 1)
            T.label(cell, name, 13, 600 if on else 400, col=T.TEXT if on else T.MUTED)
            T.clickable(cell, lambda v=value: self.choose("accent", v), feedback=False)
            self.swatches[value] = sw
        T.label(body, "System follows the light or dark mode and the colour set in "
                "MicroPythonOS's settings.", 13, col=T.MUTED,
                long_mode=lv.label.LONG_MODE.WRAP, width=lv.pct(100))
        self._map_section(body)

    def _map_section(self, body):
        import map_view
        style = self.prefs.get_string("map_style", "system") or "system"
        on_card = map_view.map_styles()
        self.map_choices = [("System", "system"), ("Dark", "dark"), ("Light", "light")]
        self.map_choices += [(ui_model.cap(n), n) for n in on_card if n not in ("dark", "light")]
        if style not in [v for _, v in self.map_choices]:
            self.map_choices.append((ui_model.cap(style), style))
        T.section_label(body, "Map")
        card = T.card(body, filled=False, pad_ver=0, pad_hor=14, gap=0)
        for i, (name, value) in enumerate(self.map_choices):
            row = T.row(card, lv.pct(100), 48, 8)
            if i:
                T.divider(row, lv.BORDER_SIDE.TOP)
            on = value == style
            T.label(row, name, 16, 600 if on else 400).set_flex_grow(1)
            if value != "system" and value not in on_card:
                T.label(row, "not on the card", 13, col=T.MUTED)
            if on:
                T.icon(row, "check", T.ACCENT)
            T.clickable(row, lambda v=value: self.choose("map_style", v))
        tiles = "%s/%%s/{z}/{x}/{y}.png" % map_view.MAPS
        if style == "system":
            where = "Follows the theme. Tiles go in %s and %s." % (tiles % "light", tiles % "dark")
        else:
            where = "Tiles go in %s%s." % (tiles % style, "" if style in on_card
                                           else " (not on the card yet)")
        self.map_note = T.label(body, where + " Each tile is a 256 px PNG in the usual web-map "
                                "layout: zoom, then column, then row. Another style is just "
                                "another folder next to these.", 13, col=T.MUTED,
                                long_mode=lv.label.LONG_MODE.WRAP, width=lv.pct(100))

    def choose(self, key, value):
        ed = self.prefs.edit()
        ed.put_string(key, value)
        ed.commit()
        T.apply()
        self.scr.clean()                # this page again, in the new colours
        T.fill(self.scr, T.BG)
        self.scr.set_style_text_color(T.color(T.TEXT), lv.PART.MAIN)
        self.build()
