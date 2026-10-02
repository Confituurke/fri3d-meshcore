"""Detail screen of a node (repeater, room server or sensor): who it is and how we hear it."""

import lvgl as lv

from mpos import Activity

import ui_model
import ui_theme as T
from meshcore_manager import MeshCoreManager


class NodeDetailActivity(Activity):

    def onCreate(self):
        self.mgr = MeshCoreManager.get_instance()
        pk = self.getIntent().extras.get("pubkey")
        node = self.mgr.get_node(pk) or {"pubkey": pk}
        d = ui_model.node_detail(node, self.mgr._now_ms())
        scr = T.make_screen()
        scr.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        T.Header(scr, d["title"], d["subtitle"], back=self.finish)
        body = T.box(scr, T.W, 1, lv.FLEX_FLOW.COLUMN)
        body.set_flex_grow(1)
        body.add_flag(lv.obj.FLAG.SCROLLABLE)
        body.set_scroll_dir(lv.DIR.VER)
        body.set_style_pad_hor(T.EDGE, lv.PART.MAIN)
        body.set_style_pad_row(10, lv.PART.MAIN)
        T.label(body, d["info"], "body", T.TEXT, lv.label.LONG_MODE.WRAP).set_width(lv.pct(100))
        card = T.box(body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN, "surface")
        card.set_style_pad_all(14, lv.PART.MAIN)
        card.set_style_pad_row(8, lv.PART.MAIN)
        for name, value in d["fields"]:
            T.label(card, name, "small", T.MUTED)
            role = "mono" if name == "Public key" else "body"
            v = T.label(card, value, role, T.TEXT, lv.label.LONG_MODE.WRAP)
            v.set_width(lv.pct(100))
        self.setContentView(scr)
