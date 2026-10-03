"""Conversation screens: a channel thread, a direct-message thread, and channel info.

A thread is a header, the messages as bubbles (newest at the bottom), a bar of quick
replies and the composer. The on-screen keyboard takes the bottom of the screen while
typing; the quick replies step aside for it."""

import lvgl as lv

from mpos import Activity

import ui_model
import ui_theme as T
from meshcore_manager import MeshCoreManager

MAX_BUBBLES = 50
FIRST_BUBBLES = 25          # shown on opening; "Show earlier messages" loads up to MAX_BUBBLES
BUBBLE_MAX_W = 360


class _Bubble:
    """One message. Incoming: sender line (channels), surface bubble with its top-left
    corner squared, meta line. Ours: blue bubble on the right with its top-right corner
    squared and a status line (time · heard ×N with dots, delivered ✓, or failed ↻)."""

    def __init__(self, parent, msg, show_sender, tz_s, on_resend, pad_ver):
        self.msg = msg
        own = not msg.get("incoming")
        self.obj = T.row(parent, lv.pct(100), lv.SIZE_CONTENT, 0,
                         lv.FLEX_ALIGN.END if own else lv.FLEX_ALIGN.START)
        group = T.column(self.obj, lv.SIZE_CONTENT, lv.SIZE_CONTENT, 3)
        group.set_style_max_width(BUBBLE_MAX_W, lv.PART.MAIN)
        group.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.END if own else lv.FLEX_ALIGN.START,
                             lv.FLEX_ALIGN.START)
        if show_sender and not own:
            name = msg.get("sender") or "?"
            T.label(group, ui_model.display(name), 15, 600, ui_model.sender_color(name), emoji=True)
        self.bubble = T.box(group, lv.SIZE_CONTENT, lv.SIZE_CONTENT)
        T.fill(self.bubble, T.OWN if own else T.SURFACE, 16)
        self.bubble.set_style_pad_ver(pad_ver, lv.PART.MAIN)
        self.bubble.set_style_pad_hor(13, lv.PART.MAIN)
        self.bubble.set_style_max_width(BUBBLE_MAX_W, lv.PART.MAIN)
        # The canvas squares one corner (radius 4) next to the sender; LVGL has one radius
        # per object, so a small rounded square covers that corner.
        tail = T.box(self.bubble, 16, 16)
        T.fill(tail, T.OWN if own else T.SURFACE, 4)
        tail.add_flag(lv.obj.FLAG.IGNORE_LAYOUT)
        tail.align(lv.ALIGN.TOP_RIGHT if own else lv.ALIGN.TOP_LEFT, 13 if own else -13, -pad_ver)
        text = T.label(self.bubble, ui_model.display(msg.get("text", "")), 18, col=T.OWN_TEXT if own else T.TEXT,
                       long_mode=lv.label.LONG_MODE.WRAP, emoji=True)
        text.set_style_max_width(BUBBLE_MAX_W - 26, lv.PART.MAIN)
        text.set_width(lv.SIZE_CONTENT)
        text.set_style_text_line_space(4, lv.PART.MAIN)
        self.meta = T.row(group, lv.SIZE_CONTENT, lv.SIZE_CONTENT, 5)
        if own:
            # "tap to resend" sits in the meta line, so it answers taps as well as the bubble.
            T.clickable(self.bubble, lambda: on_resend(self.msg), feedback=False)
            T.clickable(self.meta, lambda: on_resend(self.msg), feedback=False)
        self._tz = tz_s
        self.update()

    def update(self):
        self.meta.clean()
        if self.msg.get("incoming"):
            meta = ui_model.clock_text(self.msg.get("ts", 0), self._tz)
            if self.msg.get("snr") is not None:
                meta += " · " + ui_model.signal_report(self.msg)
            T.label(self.meta, meta, 12, mono=True, col=T.MUTED)
            return
        d = ui_model.delivery(self.msg, self._tz)
        if d["icon"]:
            T.icon(self.meta, d["icon"], d.get("icon_color", d["color"]))
        T.label(self.meta, d["text"], 12, mono=True, col=d["color"])
        if d["dots"]:
            dots = T.row(self.meta, lv.SIZE_CONTENT, 6, 3)
            for _ in range(d["dots"]):
                T.fill(T.box(dots, 6, 6), T.ACCENT, 3)
        for i in range(self.meta.get_child_count()):
            self.meta.get_child(i).add_flag(lv.obj.FLAG.EVENT_BUBBLE)
        failed = ui_model.can_resend(self.msg)
        self.bubble.set_style_border_width(2 if failed else 0, lv.PART.MAIN)
        self.bubble.set_style_border_color(T.color(T.FAIL), lv.PART.MAIN)


class ThreadActivity(Activity):
    """Shared by both thread kinds; subclasses say where messages come from and go to."""
    pad_ver = 9          # bubble padding (canvas: 9 in channels, 8 in direct threads)
    bottom_aligned = False

    def key(self):
        raise NotImplementedError

    def build_header(self, scr):
        raise NotImplementedError

    def messages(self):
        raise NotImplementedError

    def send_text(self, text):
        raise NotImplementedError

    def budget(self, text):
        return ui_model.budget(text)

    def placeholder(self):
        return "Message"

    def show_sender(self):
        return False

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
        self._divider = None
        scr = T.make_screen()
        self.build_header(scr)
        gap = 10 if self.pad_ver == 9 else 8
        self.list = T.scroll_area(scr, 14, gap)
        self.list.set_style_pad_ver(gap, lv.PART.MAIN)
        if self.bottom_aligned:
            self.list.set_flex_align(lv.FLEX_ALIGN.END, lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START)
        self._build_quick_replies(scr)
        self._build_composer(scr)
        self._kb = T.keyboard(scr, self._ta, self._on_kb_show, self._on_kb_hide)
        self._new_divider_at = self.mgr.get_unread(self.key())
        self.refresh()
        self.mgr.clear_unread(self.key())
        if __debug__:
            print("%s: %d bubbles built in %d ms" % (type(self).__name__, len(self._bubbles),
                                                     time.ticks_diff(time.ticks_ms(), t0)))
        self.setContentView(scr)

    def _build_quick_replies(self, scr):
        self.quick = T.chip_bar(scr, 8)
        for text in ui_model.QUICK_REPLIES:
            T.quick_chip(self.quick, text, lambda t=text: self._quick(t))

    def _build_composer(self, scr):
        bar = T.row(scr, T.W, T.COMPOSER_H + 1, 8)
        T.fill(bar, T.BAR)
        T.divider(bar, lv.BORDER_SIDE.TOP)
        bar.set_style_pad_left(12, lv.PART.MAIN)
        bar.set_style_pad_right(8, lv.PART.MAIN)
        self._ta = T.text_input(bar, "", self.placeholder(), 1)
        self._ta.set_flex_grow(1)
        self._ta.add_event_cb(lambda e: self._update_counter(), lv.EVENT.VALUE_CHANGED, None)
        self._counter = T.label(bar, "", 12, mono=True, col=T.MUTED)
        self._send = T.box(bar, 44, 44)
        T.fill(self._send, T.ACCENT, 22)
        self._send.set_style_bg_opa(lv.OPA._40, lv.PART.MAIN | lv.STATE.DISABLED)
        T.icon(self._send, "send", T.BG).center()
        T.clickable(self._send, self._send_typed, feedback=False)
        self._update_counter()

    # --- behaviour ------------------------------------------------------- #
    def _update_counter(self):
        text = self._ta.get_text()
        left = self.budget(text)
        self._counter.set_text("%d left" % left)
        if text:
            self._counter.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            self._counter.add_flag(lv.obj.FLAG.HIDDEN)
        self._counter.set_style_text_color(T.color(T.FAIL_TEXT if left < 0 else T.MUTED), lv.PART.MAIN)
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
        if self.budget(text) < 0:
            return
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

    def _new_divider(self):
        r = T.row(self.list, lv.pct(100), 18, 10)
        left = T.box(r, 1, 1)
        left.set_flex_grow(1)
        T.fill(left, T.ACCENT)
        T.label(r, "New", 14, 600, T.ACCENT)
        right = T.box(r, 1, 1)
        right.set_flex_grow(1)
        T.fill(right, T.ACCENT)
        return r

    def refresh(self, scroll=True):
        all_msgs = self.messages()
        msgs = all_msgs[-self._limit:]
        if len(all_msgs) > len(msgs) and self._limit < MAX_BUBBLES and self._earlier is None:
            r = T.row(self.list, lv.pct(100), lv.SIZE_CONTENT, 0, lv.FLEX_ALIGN.CENTER)
            T.quick_chip(r, "Show earlier messages", self.show_earlier)
            self._earlier = r
        live = set(id(m) for m in msgs)
        for k in list(self._bubbles):
            if k not in live:
                self._bubbles.pop(k).obj.delete()
        added = False
        for i, m in enumerate(msgs):
            b = self._bubbles.get(id(m))
            if b is None:
                if (self._new_divider_at and i == len(msgs) - self._new_divider_at
                        and self._divider is None):
                    self._divider = self._new_divider()
                b = _Bubble(self.list, m, self.show_sender(), self._tz, self._resend, self.pad_ver)
                self._bubbles[id(m)] = b
                added = True
            else:
                b.update()
        if added and scroll:
            self._scroll_to_end()

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

    def build_header(self, scr):
        kind = self.mgr.channel_kind(self.key()) or "public"
        sub = {"public": "Public channel", "hashtag": "Hashtag channel"}.get(kind, "Private channel")
        self.header = T.HeaderSub(scr, self.key(), sub, back=self.finish, border=True,
                                  menu=self.open_info)

    def open_info(self):
        from mpos import Intent
        intent = Intent(activity_class=ChannelInfoActivity)
        intent.putExtra("channel", self.key())
        self.startActivity(intent)

    def placeholder(self):
        return "Message %s" % self.key()

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
    pad_ver = 8
    bottom_aligned = True

    def key(self):
        return self.getIntent().extras.get("pubkey")

    def _contact(self):
        return self.mgr.get_contact(self.key()) or {}

    def title(self):
        c = self._contact()
        return ui_model.display(c.get("name")) or self.key()[:8]

    def route_text(self):
        c = self._contact()
        if not c.get("path"):
            return "flood"
        hops = (c.get("path_raw") or 0) & 63
        return "direct" if hops == 0 else ("1 hop" if hops == 1 else "%d hops" % hops)

    def build_header(self, scr):
        self.header = T.HeaderCompact(scr, self.title(), self.finish, self.route_text(),
                                      self.forget_route)

    def forget_route(self):
        """Tapping the route pill drops a stale direct route: the next message floods."""
        self.mgr.reset_route(self.key())
        self.header.pill_label.set_text(self.route_text())

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
        return (event == "dm" and data[0] == self.key()) or event == "contacts"

    def _on_change(self):
        self.header.pill_label.set_text(self.route_text())
        super()._on_change()


class ChannelInfoActivity(Activity):
    """What a channel is and how others join it: its kind, its key to share (hashtag and
    private channels), and leaving it."""

    def onCreate(self):
        self.mgr = MeshCoreManager.get_instance()
        name = self.getIntent().extras.get("channel")
        ch = self.mgr.get_channel(name)
        kind = self.mgr.channel_kind(name) or "public"
        scr = T.make_screen()
        T.HeaderSub(scr, name, "Channel info", back=self.finish)
        body = T.scroll_area(scr, 14, 10)
        info = T.card(body, filled=False, pad_ver=0, gap=0)
        T.SettingRow(info, "Kind", kind, first=True)
        if ch is not None and getattr(ch, "psk_b64", None):
            T.SettingRow(info, "Key", ch.psk_b64)
        if kind == "hashtag":
            hint = "Anyone who joins %s gets the same key from its name." % name
        elif kind == "private":
            hint = "Share the key with the people you want in this channel."
        else:
            hint = "Public is the channel every MeshCore node listens to."
        T.label(body, hint, 15, col=T.MUTED, long_mode=lv.label.LONG_MODE.WRAP, width=lv.pct(100))
        if name != "Public":
            T.button(body, "Leave channel", lambda: self.leave(name), kind="outline",
                     h=52, width=lv.pct(100))
        self.setContentView(scr)

    def leave(self, name):
        self.mgr.remove_channel(name)
        self.finish()
