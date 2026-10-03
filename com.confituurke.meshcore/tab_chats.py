"""Chats tab: channels and direct conversations, newest activity first."""

import lvgl as lv

from mpos import Intent

import meshcore_presets
import ui_model
import ui_theme as T
import thread_activity
from meshcore_manager import unix_time
from ui_tabs import Tab

FILTERS = (("all", "All"), ("unread", "Unread"), ("direct", "Direct"), ("channels", "Channels"))


class ChatsTab(Tab):
    title = "Chats"

    def build(self, parent, activity):
        self.activity = activity
        self.mgr = activity.mgr
        self.filt = "all"
        self._rows = {}          # key -> T.ListRow
        self._order = []         # keys in display order (MicroPython dicts are unordered)
        header = T.HeaderTop(parent, "Chats", pad_right=4, gap=8)
        T.preset_pill(header.obj, meshcore_presets.short_name(self.mgr.radio_preset()),
                      lambda: activity.select(2))
        T.icon_button(header.obj, "plus", self.new_chat)
        bar = T.chip_bar(parent, 8)
        self._chips = {}
        for key, text in FILTERS:
            self._chips[key] = T.Chip(bar, text, lambda k=key: self.set_filter(k), key == "all", 16, 14)
        self.empty = T.label(parent, "No messages yet. Tap + to start a chat with a node "
                             "you have heard.", 16, col=T.MUTED, long_mode=lv.label.LONG_MODE.WRAP,
                             width=T.W - 32)
        self.empty.set_style_pad_all(16, lv.PART.MAIN)
        self.list = T.scroll_area(parent)
        self.refresh()

    def new_chat(self):
        """A chat starts from a node: open Nodes on the companions."""
        self.activity.select(1)
        tab = self.activity._tab
        if hasattr(tab, "set_filter"):
            tab.set_filter("chat")

    def set_filter(self, key):
        self.filt = key
        for k, chip in self._chips.items():
            chip.set_selected(k == key)
        self.refresh()

    def refresh(self):
        model = ui_model.chat_rows(self.mgr, unix_time(), self.filt, T.tz_offset_s())
        unread = len(ui_model.chat_rows(self.mgr, 0, "unread"))
        self._chips["unread"].set_text("Unread %d" % unread if unread else "Unread")
        keep = set(r["key"] for r in model)
        for key in list(self._rows):
            if key not in keep:
                self._rows.pop(key).obj.delete()
        rows = {}
        for i, r in enumerate(model):
            row = self._rows.get(r["key"])
            if row is None:
                row = T.ListRow(self.list, lambda k=r["key"], kind=r["kind"]: self.open_chat(k, kind))
                T.on_long_press(row.obj, lambda k=r["key"], kind=r["kind"]: self.menu(k, kind))
            row.set_avatar(r["kind"], r["initials"])
            row.title.set_text(r["title"])
            row.right.set_text(r["time"])
            row.line2.set_text(r["preview"])
            row.badge.show(r["unread"], r["mention"])
            if row.obj.get_index() != i:
                row.obj.move_to_index(i)
            rows[r["key"]] = row
        self._rows = rows
        self._order = [r["key"] for r in model]
        if rows:
            self.empty.add_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.empty.remove_flag(lv.obj.FLAG.HIDDEN)

    def menu(self, key, kind):
        import quick_actions
        self.sheet = quick_actions.chat_menu(self.activity, self.mgr, key,
                                             "channel" if kind == "channel" else "dm",
                                             self.open_chat)

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
