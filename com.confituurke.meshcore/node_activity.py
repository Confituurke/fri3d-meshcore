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
        T.HeaderSub(scr, d["title"], d["subtitle"], back=self.finish, mono_subtitle=True)
        body = T.scroll_area(scr, 14, 10)
        body.set_style_pad_bottom(12, lv.PART.MAIN)
        lead, via, tail = d["route"]
        route = T.box(body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW_WRAP)
        T.label(route, lead, 16, col=T.MUTED)
        if via:
            T.label(route, via, 16, mono=True)
        T.label(route, tail, 16, col=T.MUTED)
        T.kv_grid(body, d["fields"])
        T.section_label(body, "Public key")
        key = T.card(body, filled=False, pad_ver=10, pad_hor=14)
        T.label(key, d["pubkey"], 14, mono=True, long_mode=lv.label.LONG_MODE.WRAP,
                width=lv.pct(100))
        self.setContentView(scr)
