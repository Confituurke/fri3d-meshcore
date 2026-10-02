"""Conversation screens: a channel thread and a direct-message thread.

Header, the last MAX_BUBBLES messages as bubbles, a row of quick replies, and the
composer with a byte counter. The on-screen keyboard takes the bottom of the screen while
typing; the quick replies step aside for it."""

import lvgl as lv

from mpos import Activity, MposKeyboard

import ui_model
import ui_theme as T
from meshcore_manager import MeshCoreManager

MAX_BUBBLES = 50
FIRST_BUBBLES = 25          # shown on opening; "Show earlier messages" loads up to MAX_BUBBLES
BUBBLE_MAX_W = 340
KEYBOARD_H = 188


class _Bubble:
    """One message: incoming on the left (surface), ours on the right (blue), with its
    delivery line. Kept so that state changes update it in place."""

    def __init__(self, parent, msg, show_sender, tz_s, on_resend):
        self.msg = msg
        own = not msg.get("incoming")
        self.obj = T.box(parent, T.W, lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW)
        self.obj.set_style_pad_hor(16, lv.PART.MAIN)
        self.obj.set_style_pad_ver(4, lv.PART.MAIN)
        self.obj.set_flex_align(lv.FLEX_ALIGN.END if own else lv.FLEX_ALIGN.START,
                                lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START)
        self.bubble = T.box(self.obj, lv.SIZE_CONTENT, lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN,
                            "bubble_out" if own else "bubble_in")
        self.bubble.set_style_max_width(BUBBLE_MAX_W, lv.PART.MAIN)
        self.bubble.set_style_pad_row(2, lv.PART.MAIN)
        if show_sender and not own:
            T.label(self.bubble, msg.get("sender") or "?", "strong", T.ACCENT)
        text = T.label(self.bubble, msg.get("text", ""), "body", T.TEXT, lv.label.LONG_MODE.WRAP)
        text.set_style_max_width(BUBBLE_MAX_W - 20, lv.PART.MAIN)
        self.status = None
        self.glyph = None
        if own:
            row = T.box(self.bubble, lv.SIZE_CONTENT, lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW)
            row.set_style_pad_column(6, lv.PART.MAIN)
            row.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.glyph = T.symbol(row, "", T.MUTED)
            self.status = T.label(row, "", "small", T.MUTED)
            T.clickable(self.bubble, lambda: on_resend(self.msg))
        else:
            meta = ui_model.clock_text(msg.get("ts", 0), tz_s)
            if msg.get("snr") is not None:
                meta += " · " + ui_model.signal_report(msg)
            T.label(self.bubble, meta, "small", T.MUTED)
        self.update()

    def update(self):
        if self.status is None:
            return
        glyph, text, col = ui_model.delivery(self.msg)
        self.glyph.set_text(T.GLYPHS.get(glyph, glyph))
        self.glyph.set_style_text_color(T.color(col), lv.PART.MAIN)
        self.status.set_text(text)
        self.status.set_style_text_color(T.color(col), lv.PART.MAIN)


class ThreadActivity(Activity):
    """Shared by both thread kinds; subclasses say where messages come from and go to."""

    def key(self):
        raise NotImplementedError

    def title(self):
        raise NotImplementedError

    def subtitle(self):
        return ""

    def messages(self):
        raise NotImplementedError

    def send_text(self, text):
        raise NotImplementedError

    def budget(self, text):
        return ui_model.budget(text)

    def placeholder(self):
        return "Message"

    def event_matches(self, event, data):
        raise NotImplementedError

    # --- building -------------------------------------------------------- #
    def onCreate(self):
        if __debug__:
            import time
            t0 = time.ticks_ms()
        self.mgr = MeshCoreManager.get_instance()
        self._tz = T.tz_offset_s()
        self._bubbles = {}            # id(msg) -> _Bubble
        self._limit = FIRST_BUBBLES
        self._earlier = None
        scr = T.make_screen()
        scr.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        self.header = T.Header(scr, self.title(), self.subtitle(), back=self.finish)
        self.list = T.box(scr, T.W, 1, lv.FLEX_FLOW.COLUMN)
        self.list.set_flex_grow(1)
        self.list.add_flag(lv.obj.FLAG.SCROLLABLE)
        self.list.set_scroll_dir(lv.DIR.VER)
        self.list.set_style_pad_ver(8, lv.PART.MAIN)
        self._build_quick_replies(scr)
        self._build_composer(scr)
        self._kb = MposKeyboard(scr)
        self._kb.set_size(T.W, KEYBOARD_H)
        self._kb.set_style_bg_color(T.color(T.SURFACE), lv.PART.MAIN)
        self._kb.set_style_bg_color(T.color(T.SURFACE2), lv.PART.ITEMS)
        self._kb.set_style_text_color(T.color(T.TEXT), lv.PART.ITEMS)
        self._kb.add_flag(lv.obj.FLAG.HIDDEN)
        self._kb.set_textarea(self._ta, on_show=self._on_kb_show, on_hide=self._on_kb_hide)
        unread = self.mgr.get_unread(self.key())
        self._new_divider_at = unread       # messages from the end that are new
        self._divider = None
        self.refresh()
        self.mgr.clear_unread(self.key())
        if __debug__:
            print("%s: %d bubbles built in %d ms" % (type(self).__name__, len(self._bubbles),
                                                     time.ticks_diff(time.ticks_ms(), t0)))
        self.setContentView(scr)

    def _build_quick_replies(self, scr):
        self.quick = T.box(scr, T.W, T.CHIP_H + 8, lv.FLEX_FLOW.ROW)
        self.quick.set_style_pad_left(T.EDGE, lv.PART.MAIN)
        self.quick.set_style_pad_column(8, lv.PART.MAIN)
        self.quick.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        self.quick.add_flag(lv.obj.FLAG.SCROLLABLE)
        self.quick.set_scroll_dir(lv.DIR.HOR)
        for text in ui_model.QUICK_REPLIES:
            T.Chip(self.quick, text, lambda t=text: self._quick(t), h=T.CHIP_H - 6)

    def _build_composer(self, scr):
        row = T.box(scr, T.W, T.COMPOSER_H, lv.FLEX_FLOW.ROW)
        row.set_style_pad_hor(12, lv.PART.MAIN)
        row.set_style_pad_column(8, lv.PART.MAIN)
        row.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        row.set_style_bg_color(T.color(T.SURFACE), lv.PART.MAIN)
        row.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
        self._ta = lv.textarea(row)
        self._ta.set_one_line(True)
        self._ta.set_placeholder_text(self.placeholder())
        self._ta.set_height(40)
        self._ta.set_flex_grow(1)
        self._ta.set_style_text_font(T.font("body"), lv.PART.MAIN)
        self._ta.set_style_bg_color(T.color(T.SURFACE2), lv.PART.MAIN)
        self._ta.set_style_text_color(T.color(T.TEXT), lv.PART.MAIN)
        self._ta.set_style_border_width(0, lv.PART.MAIN)
        self._ta.set_style_radius(20, lv.PART.MAIN)
        self._ta.set_style_pad_hor(14, lv.PART.MAIN)
        self._ta.add_event_cb(lambda e: self._update_counter(), lv.EVENT.VALUE_CHANGED, None)
        self._counter = T.label(row, "", "mono", T.MUTED)
        self._send = T.box(row, 44, 44)
        self._send.set_style_bg_color(T.color(T.ACCENT), lv.PART.MAIN)
        self._send.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
        self._send.set_style_bg_opa(lv.OPA._40, lv.PART.MAIN | lv.STATE.DISABLED)
        self._send.set_style_radius(22, lv.PART.MAIN)
        T.symbol(self._send, lv.SYMBOL.RIGHT, T.BG).center()
        T.clickable(self._send, self._send_typed)
        self._update_counter()

    # --- behaviour ------------------------------------------------------- #
    def _update_counter(self):
        text = self._ta.get_text()
        left = self.budget(text)
        self._counter.set_text("%d left" % left)
        self._counter.set_style_text_color(T.color(T.ERR if left < 0 else T.MUTED), lv.PART.MAIN)
        if left < 0 or not text.strip():
            self._send.add_state(lv.STATE.DISABLED)
        else:
            self._send.remove_state(lv.STATE.DISABLED)

    def _send_typed(self):
        text = self._ta.get_text().strip()
        if not text or self.budget(text) < 0:
            return
        self._ta.set_text("")
        self.send_text(text)

    def _quick(self, text):
        if text == "signal report":
            last = None
            for m in reversed(self.messages()):
                if m.get("incoming"):
                    last = m
                    break
            if last is None:
                return
            text = ui_model.signal_report(last)
        self.send_text(text)

    def _resend(self, msg):
        if ui_model.can_resend(msg):
            self.mgr.resend(self.key(), msg)

    def _on_kb_show(self):
        self.quick.add_flag(lv.obj.FLAG.HIDDEN)

    def _on_kb_hide(self):
        self.quick.remove_flag(lv.obj.FLAG.HIDDEN)
        self._scroll_to_end()

    def _scroll_to_end(self):
        n = self.list.get_child_count()
        if n:
            self.list.get_child(n - 1).scroll_to_view_recursive(False)

    def show_earlier(self):
        self._limit = MAX_BUBBLES
        self._bubbles = {}
        self._divider = None
        self._earlier = None
        self.list.clean()
        self.refresh(scroll=False)

    def refresh(self, scroll=True):
        all_msgs = self.messages()
        msgs = all_msgs[-self._limit:]
        if len(all_msgs) > len(msgs) and self._limit < MAX_BUBBLES and self._earlier is None:
            row = T.box(self.list, T.W, lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW)
            row.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            row.set_style_pad_ver(6, lv.PART.MAIN)
            T.Chip(row, "Show earlier messages", self.show_earlier)
            self._earlier = row
        live = set(id(m) for m in msgs)
        for k in list(self._bubbles):
            if k not in live:
                self._bubbles.pop(k).obj.delete()
        added = False
        for i, m in enumerate(msgs):
            b = self._bubbles.get(id(m))
            if b is None:
                if self._new_divider_at and i == len(msgs) - self._new_divider_at and self._divider is None:
                    self._divider = T.label(self.list, "New", "small", T.ACCENT)
                    self._divider.set_style_pad_left(T.EDGE, lv.PART.MAIN)
                b = _Bubble(self.list, m, self.show_sender(), self._tz, self._resend)
                self._bubbles[id(m)] = b
                added = True
            else:
                b.update()
        if added and scroll:
            self._scroll_to_end()

    def show_sender(self):
        return False

    def onResume(self, screen):
        super().onResume(screen)
        self.mgr.add_subscriber(self._on_event)

    def onPause(self, screen):
        self.mgr.remove_subscriber(self._on_event)
        super().onPause(screen)

    def _on_event(self, event, data):
        if self.event_matches(event, data):
            self.update_ui_threadsafe_if_foreground(self._on_change)

    def _on_change(self):
        self.refresh()
        self.mgr.clear_unread(self.key())


class ChannelChatActivity(ThreadActivity):

    def key(self):
        return self.getIntent().extras.get("channel")

    def title(self):
        return self.key()

    def subtitle(self):
        kind = self.mgr.channel_kind(self.key()) or "public"
        return {"public": "Public channel", "hashtag": "Hashtag channel"}.get(kind, "Private channel")

    def show_sender(self):
        return True

    def messages(self):
        return self.mgr.get_messages(self.key())

    def budget(self, text):
        return ui_model.budget(text, self.key(), self.mgr.nickname())

    def send_text(self, text):
        self.mgr.send_group_text(self.key(), text)

    def event_matches(self, event, data):
        return event == "message" and data[0] == self.key()


class DMChatActivity(ThreadActivity):

    def key(self):
        return self.getIntent().extras.get("pubkey")

    def _contact(self):
        return self.mgr.get_contact(self.key()) or {}

    def title(self):
        c = self._contact()
        return c.get("name") or self.key()[:8]

    def subtitle(self):
        c = self._contact()
        if not c.get("path"):
            return "route unknown · flood"
        hops = (c.get("path_raw") or 0) & 63
        return "direct" if hops == 0 else ("1 hop" if hops == 1 else "%d hops" % hops)

    def placeholder(self):
        return "Message to %s" % self.title()

    def messages(self):
        return self.mgr.get_dm_messages(self.key())

    def send_text(self, text):
        # Encryption may need an ECDH first: keep it off the UI thread.
        key = self.key()
        try:
            import _thread
            _thread.start_new_thread(self.mgr.send_dm, (key, text))
        except Exception:
            self.mgr.send_dm(key, text)

    def event_matches(self, event, data):
        return event == "dm" and data[0] == self.key()
