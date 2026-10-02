"""Nodes tab: everything heard via adverts (companions, repeaters, rooms), most recent
first. Tapping a companion opens a direct chat; anything else opens its detail screen."""

import lvgl as lv

from mpos import Intent

import ui_model
import ui_theme as T
import node_activity
import thread_activity
from ui_tabs import Tab

ROW_H = 64
FILTERS = (("all", "All"), ("chat", "Chat"), ("rptr", "Repeaters"), ("room", "Rooms"),
           ("new", "New"))
KIND_TAGS = {"chat": "chat", "rptr": "rptr", "room": "room", "sensor": "sens"}


class _Row:

    def __init__(self, parent, on_open):
        self.pubkey = None
        self.kind = None
        self.obj = T.box(parent, T.W, ROW_H, lv.FLEX_FLOW.ROW, "row")
        self.obj.set_style_pad_left(T.EDGE, lv.PART.MAIN)
        self.obj.set_style_pad_right(16, lv.PART.MAIN)
        self.obj.set_style_pad_column(12, lv.PART.MAIN)
        self.obj.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        T.clickable(self.obj, lambda: on_open(self.pubkey, self.kind))
        badge = T.box(self.obj, 48, 44, lv.FLEX_FLOW.COLUMN)
        badge.set_style_bg_color(T.color(T.SURFACE2), lv.PART.MAIN)
        badge.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
        badge.set_style_radius(8, lv.PART.MAIN)
        badge.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        self.hex = T.label(badge, "", "mono", T.TEXT)
        self.tag = T.label(badge, "", "small", T.MUTED)
        mid = T.box(self.obj, 1, lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN)
        mid.set_flex_grow(1)
        top = T.box(mid, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW)
        top.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        self.name = T.label(top, "", "strong", T.TEXT, lv.label.LONG_MODE.DOTS)
        self.name.set_width(260)
        self.age = T.label(top, "", "small", T.MUTED)
        self.meta = T.label(mid, "", "small", T.MUTED, lv.label.LONG_MODE.DOTS)
        self.meta.set_width(lv.pct(100))

    def update(self, r):
        self.pubkey = r["pubkey"]
        self.kind = r["kind"]
        self.hex.set_text(r["hex"])
        self.tag.set_text(KIND_TAGS.get(r["kind"], r["kind"]))
        self.name.set_text(r["name"])
        self.age.set_text(r["age"])
        self.age.set_style_text_color(T.color(r["age_color"]), lv.PART.MAIN)
        self.meta.set_text(r["meta"])


class NodesTab(Tab):
    title = "Nodes"

    def build(self, parent, activity):
        self.activity = activity
        self.mgr = activity.mgr
        self.filt = "all"
        self._rows = {}
        self._order = []
        self.header = T.Header(parent, "Nodes", action=("Advert", self.advert))
        bar = T.box(parent, T.W, 52, lv.FLEX_FLOW.ROW)
        bar.set_style_pad_left(T.EDGE, lv.PART.MAIN)
        bar.set_style_pad_right(T.EDGE, lv.PART.MAIN)
        bar.set_style_pad_column(8, lv.PART.MAIN)
        bar.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        bar.add_flag(lv.obj.FLAG.SCROLLABLE)
        bar.set_scroll_dir(lv.DIR.HOR)
        self._chips = {}
        for key, text in FILTERS:
            self._chips[key] = T.Chip(bar, text, lambda k=key: self.set_filter(k), key == "all")
        self.empty = T.label(parent, "No nodes heard yet. Send an advert to say hello.",
                             "body", T.MUTED, lv.label.LONG_MODE.WRAP)
        self.empty.set_width(T.W - 2 * T.EDGE)
        self.empty.set_style_pad_all(T.EDGE, lv.PART.MAIN)
        self.list = T.box(parent, T.W, 1, lv.FLEX_FLOW.COLUMN)
        self.list.set_flex_grow(1)
        self.list.add_flag(lv.obj.FLAG.SCROLLABLE)
        self.list.set_scroll_dir(lv.DIR.VER)
        self._timer = lv.timer_create(lambda t: self.refresh(), 30000, None)
        self.refresh()

    def destroy(self):
        if self._timer is not None:
            self._timer.delete()
            self._timer = None

    def advert(self):
        ok, err = self.mgr.advertise(flood=False)
        self.header.set_subtitle("Zero-hop advert sent" if ok else (err or "Advert failed"))

    def set_filter(self, key):
        self.filt = key
        for k, chip in self._chips.items():
            chip.set_selected(k == key)
        self.refresh()

    def refresh(self):
        nodes = self.mgr.get_learned_companions()
        now = self.mgr._now_ms()
        contacts = set(c["pubkey"] for c in self.mgr.get_contacts())
        model = ui_model.node_rows(nodes, now, self.filt, contacts)
        n_all = len(nodes)
        n_new = len(ui_model.node_rows(nodes, now, "new", contacts))
        self._chips["all"].set_text("All %d" % n_all if n_all else "All")
        self._chips["new"].set_text("New %d" % n_new if n_new else "New")
        keep = set(r["pubkey"] for r in model)
        for key in list(self._rows):
            if key not in keep:
                self._rows.pop(key).obj.delete()
        rows = {}
        for i, r in enumerate(model):
            row = self._rows.get(r["pubkey"])
            if row is None:
                row = _Row(self.list, self.open_node)
            row.update(r)
            if row.obj.get_index() != i:
                row.obj.move_to_index(i)
            rows[r["pubkey"]] = row
        self._rows = rows
        self._order = [r["pubkey"] for r in model]
        if rows:
            self.empty.add_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.empty.remove_flag(lv.obj.FLAG.HIDDEN)

    def open_node(self, pubkey, kind):
        if kind == "chat":
            if not self.mgr.is_contact(pubkey):
                self.mgr.add_contact(pubkey)
            intent = Intent(activity_class=thread_activity.DMChatActivity)
        else:
            intent = Intent(activity_class=node_activity.NodeDetailActivity)
        intent.putExtra("pubkey", pubkey)
        self.activity.startActivity(intent)

    def on_event(self, event, data):
        if event in ("node", "contacts"):
            self.refresh()
