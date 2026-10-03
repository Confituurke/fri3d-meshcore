"""Nodes tab: everything heard via adverts (companions, repeaters, rooms), most recent
first. Tapping a companion opens a direct chat; anything else opens its detail screen."""

import lvgl as lv

from mpos import Intent

import ui_model
import ui_theme as T
import node_activity
import thread_activity
from ui_tabs import Tab

FILTERS = (("all", "All"), ("chat", "Chat"), ("rptr", "Repeaters"), ("room", "Rooms"),
           ("new", "New"))
KIND_TAGS = {"chat": "chat", "rptr": "rptr", "room": "room", "sensor": "sens"}


class NodesTab(Tab):
    title = "Nodes"

    def build(self, parent, activity):
        self.activity = activity
        self.mgr = activity.mgr
        self.filt = "all"
        self.query = ""
        self._rows = {}          # pubkey -> T.ListRow
        self._order = []         # pubkeys in display order (MicroPython dicts are unordered)
        self._kb = None
        self._timer = None
        header = T.HeaderTop(parent, "Nodes", pad_right=8, gap=4)
        self.search_button = T.icon_button(header.obj, "search", self.open_search)
        T.advert_button(header.obj, self.advert)
        self.chips_bar = T.chip_bar(parent, 6)
        self._chips = {"contacts": T.Chip(self.chips_bar, "", lambda: self.set_filter("contacts"),
                                          False, 14, 12, "star")}
        for key, text in FILTERS:
            self._chips[key] = T.Chip(self.chips_bar, text, lambda k=key: self.set_filter(k),
                                      key == "all", 14, 12)
        self.search_bar = T.row(parent, T.W, 44, 8)
        self.search_bar.set_style_pad_left(12, lv.PART.MAIN)
        self.search_bar.set_style_pad_right(4, lv.PART.MAIN)
        self.search = T.text_input(self.search_bar, "", "Name or hex id", 1)
        self.search.set_flex_grow(1)
        self.search.add_event_cb(lambda e: self._on_query(), lv.EVENT.VALUE_CHANGED, None)
        T.icon_button(self.search_bar, "close", self.close_search, 44, 44)
        self.search_bar.add_flag(lv.obj.FLAG.HIDDEN)
        self.status = T.label(parent, "", 15, col=T.MUTED)
        self.status.set_style_pad_hor(16, lv.PART.MAIN)
        self.status.add_flag(lv.obj.FLAG.HIDDEN)
        self.empty = T.label(parent, "", 16, col=T.MUTED, long_mode=lv.label.LONG_MODE.WRAP,
                             width=T.W - 32)
        self.empty.set_style_pad_all(16, lv.PART.MAIN)
        self.list = T.scroll_area(parent)
        self._timer = lv.timer_create(lambda t: self.refresh(), 30000, None)
        self.refresh()

    def destroy(self):
        if self._timer is not None:
            self._timer.delete()
            self._timer = None
        self._drop_keyboard()

    # --- search ------------------------------------------------------------ #
    def open_search(self):
        self.chips_bar.add_flag(lv.obj.FLAG.HIDDEN)
        self.search_bar.remove_flag(lv.obj.FLAG.HIDDEN)
        if self._kb is None:
            # The keyboard floats over the bottom of the screen, tab bar included.
            self._kb = T.keyboard(self.list.get_screen(), self.search, floating=True)
        self.search.add_state(lv.STATE.FOCUSED)
        self._kb.show_keyboard()

    def close_search(self):
        self._drop_keyboard()
        self.search.set_text("")
        self.search.remove_state(lv.STATE.FOCUSED)
        self.search_bar.add_flag(lv.obj.FLAG.HIDDEN)
        self.chips_bar.remove_flag(lv.obj.FLAG.HIDDEN)
        self._on_query()

    def _drop_keyboard(self):
        # The keyboard lives on the screen, not in the tab's container: delete it here.
        if self._kb is not None:
            self._kb.delete()
            self._kb = None

    def _on_query(self):
        q = self.search.get_text()
        if q != self.query:
            self.query = q
            self.refresh()

    # --- behaviour --------------------------------------------------------- #
    def advert(self):
        ok, err = self.mgr.advertise(flood=False)
        self.status.set_text("Zero-hop advert sent" if ok else (err or "Advert failed"))
        self.status.set_style_text_color(T.color(T.MUTED if ok else T.FAIL_TEXT), lv.PART.MAIN)
        self.status.remove_flag(lv.obj.FLAG.HIDDEN)

    def set_filter(self, key):
        self.filt = key
        for k, chip in self._chips.items():
            chip.set_selected(k == key)
        self.refresh()

    def refresh(self):
        nodes = self.mgr.get_learned_companions()
        now = self.mgr._now_ms()
        contacts = set(c["pubkey"] for c in self.mgr.get_contacts())
        model = ui_model.node_rows(nodes, now, self.filt, contacts, self.query)
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
                row = T.ListRow(self.list, lambda pk=r["pubkey"], kind=r["kind"]: self.open_node(pk, kind))
            row.set_avatar("node", r["hex"] + "\n" + KIND_TAGS.get(r["kind"], r["kind"]))
            row.title.set_text(r["name"])
            row.right.set_text(r["age"])
            row.right.set_style_text_color(T.color(r["age_color"]), lv.PART.MAIN)
            row.line2.set_text(r["meta"])
            if row.obj.get_index() != i:
                row.obj.move_to_index(i)
            rows[r["pubkey"]] = row
        self._rows = rows
        self._order = [r["pubkey"] for r in model]
        if rows:
            self.empty.add_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.empty.set_text(self._empty_text(n_all))
            self.empty.remove_flag(lv.obj.FLAG.HIDDEN)

    def _empty_text(self, n_all):
        if not n_all:
            return "No nodes heard yet. Send an advert to say hello."
        if self.query:
            return "No node matches \"%s\"." % self.query
        if self.filt == "contacts":
            return "No saved contacts yet. Tap a companion to chat; it is saved as a contact."
        return "Nothing here yet."

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
