"""Chats tab: channels and direct conversations, newest activity first."""

import lvgl as lv

from mpos import Intent

import ui_model
import ui_theme as T
import thread_activity
from meshcore_manager import unix_time
from ui_tabs import Tab

ROW_H = 64
FILTERS = (("all", "All"), ("unread", "Unread"), ("direct", "Direct"), ("channels", "Channels"))


class _Row:
    """Widgets of one chat row, kept so events can update it in place."""

    def __init__(self, parent, on_open):
        self.key = None
        self.kind = None
        self.obj = T.box(parent, T.W, ROW_H, lv.FLEX_FLOW.ROW, "row")
        self.obj.set_style_pad_left(T.EDGE, lv.PART.MAIN)
        self.obj.set_style_pad_right(16, lv.PART.MAIN)
        self.obj.set_style_pad_column(12, lv.PART.MAIN)
        self.obj.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        T.clickable(self.obj, lambda: on_open(self.key, self.kind))
        self.avatar = T.box(self.obj, 40, 40)
        self.avatar.set_style_bg_color(T.color(T.SURFACE2), lv.PART.MAIN)
        self.avatar.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
        self.avatar.set_style_radius(20, lv.PART.MAIN)
        self.initials = T.label(self.avatar, "", "strong", T.TEXT)
        self.initials.center()
        mid = T.box(self.obj, 1, lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN)
        mid.set_flex_grow(1)
        self.title = T.label(mid, "", "strong", T.TEXT, lv.label.LONG_MODE.DOTS)
        self.title.set_width(lv.pct(100))
        self.preview = T.label(mid, "", "small", T.MUTED, lv.label.LONG_MODE.DOTS)
        self.preview.set_width(lv.pct(100))
        right = T.box(self.obj, lv.SIZE_CONTENT, lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN)
        right.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.END, lv.FLEX_ALIGN.END)
        right.set_style_pad_row(4, lv.PART.MAIN)
        self.time = T.label(right, "", "small", T.MUTED)
        self.badge = T.badge(right, "")
        self.badge_label = self.badge.get_child(0)

    def update(self, r):
        self.key = r["key"]
        self.kind = r["kind"]
        self.initials.set_text(r["initials"])
        self.initials.set_style_text_color(T.color(T.ACCENT if r["kind"] == "channel" else T.TEXT),
                                           lv.PART.MAIN)
        self.title.set_text(r["title"])
        self.preview.set_text(r["preview"])
        self.time.set_text(r["time"])
        if r["mention"]:
            self.badge_label.set_text("@")
        elif r["unread"]:
            self.badge_label.set_text(str(r["unread"]))
        if r["mention"] or r["unread"]:
            self.badge.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.badge.add_flag(lv.obj.FLAG.HIDDEN)


class ChatsTab(Tab):
    title = "Chats"

    def build(self, parent, activity):
        self.activity = activity
        self.mgr = activity.mgr
        self.filt = "all"
        self._rows = {}          # key -> _Row
        self._order = []         # keys in display order (MicroPython dicts are unordered)
        preset = self.mgr.radio_preset().get("name") or "Custom"
        T.Header(parent, "Chats", action=(preset, lambda: activity.select(2)))
        bar = T.box(parent, T.W, 52, lv.FLEX_FLOW.ROW)
        bar.set_style_pad_left(T.EDGE, lv.PART.MAIN)
        bar.set_style_pad_column(8, lv.PART.MAIN)
        bar.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        self._chips = {}
        for key, text in FILTERS:
            self._chips[key] = T.Chip(bar, text, lambda k=key: self.set_filter(k), key == "all")
        self.empty = T.label(parent, "No messages yet", "body", T.MUTED)
        self.empty.set_style_pad_all(T.EDGE, lv.PART.MAIN)
        self.list = T.box(parent, T.W, 1, lv.FLEX_FLOW.COLUMN)
        self.list.set_flex_grow(1)
        self.list.add_flag(lv.obj.FLAG.SCROLLABLE)
        self.list.set_scroll_dir(lv.DIR.VER)
        self.refresh()

    def set_filter(self, key):
        self.filt = key
        for k, chip in self._chips.items():
            chip.set_selected(k == key)
        self.refresh()

    def refresh(self):
        model = ui_model.chat_rows(self.mgr, unix_time(), self.filt, T.tz_offset_s())
        unread = sum(1 for r in ui_model.chat_rows(self.mgr, 0, "unread"))
        self._chips["unread"].set_text("Unread %d" % unread if unread else "Unread")
        keep = set(r["key"] for r in model)
        for key in list(self._rows):
            if key not in keep:
                self._rows.pop(key).obj.delete()
        rows = {}
        for i, r in enumerate(model):
            row = self._rows.get(r["key"])
            if row is None:
                row = _Row(self.list, self.open_chat)
            row.update(r)
            if row.obj.get_index() != i:
                row.obj.move_to_index(i)
            rows[r["key"]] = row
        self._rows = rows
        self._order = [r["key"] for r in model]
        if rows:
            self.empty.add_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.empty.remove_flag(lv.obj.FLAG.HIDDEN)

    def open_chat(self, key, kind):
        if kind == "channel":
            intent = Intent(activity_class=thread_activity.ChannelChatActivity)
            intent.putExtra("channel", key)
        else:
            intent = Intent(activity_class=thread_activity.DMChatActivity)
            intent.putExtra("pubkey", key)
        self.activity.startActivity(intent)

    def on_event(self, event, data):
        if event in ("message", "dm", "unread", "contacts", "channels"):
            self.refresh()
