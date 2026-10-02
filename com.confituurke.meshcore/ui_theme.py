"""Look of the app: colours, fonts, shared styles and the header / tab-bar / chip pieces.

Dark theme with an amber accent, on the 480x480 screen. MicroPythonOS keeps two gesture
strips on top of every app (the top 24 px opens the drawer, the left 24 px is "back"), so
headers start with a 24 px pad and text keeps 24 px from the left edge.
"""

import os

import lvgl as lv

from mpos import FontManager

from ui_model import (BG, SURFACE, SURFACE2, LINE, TEXT, MUTED, ACCENT, OWN,  # noqa: F401
                      OK, WARN, ERR)

W = 480
H = 480
TOP_PAD = 24        # under the drawer gesture strip
EDGE = 24           # clear of the back gesture strip
HEADER_H = 48
TABBAR_H = 56
CHIP_H = 44
COMPOSER_H = 52

_DIR = os.path.dirname(os.path.abspath(__file__))
_FONTS = {
    "body": ("ArchivoNarrow-Regular.ttf", 18),
    "small": ("ArchivoNarrow-Regular.ttf", 15),
    "title": ("ArchivoNarrow-SemiBold.ttf", 22),
    "strong": ("ArchivoNarrow-SemiBold.ttf", 18),
    "mono": ("MeshMono-Regular.ttf", 15),
    "big": ("MeshMono-Regular.ttf", 40),
}

# Delivery glyphs (see ui_model.delivery) come from LVGL's built-in symbol font: the
# bundled text fonts have no tick, cross or hourglass.
GLYPHS = {"⏳": lv.SYMBOL.LOOP, "→": lv.SYMBOL.RIGHT, "✓": lv.SYMBOL.OK,
          "✗": lv.SYMBOL.CLOSE, "?": "?"}
SYMBOL_FONT = lv.font_montserrat_14

_styles = {}


def color(c):
    return lv.color_hex(c)


_font_cache = {}


def font(role):
    """The font for a text role. Kept per role: FontManager.getFont() is far slower than
    creating a widget, and every label asks for a font. A font that is held stays valid
    (FontManager never destroys fonts)."""
    f = _font_cache.get(role)
    if f is None:
        name, size = _FONTS[role]
        f = FontManager.getFont(size=size, ttf="M:%s/fonts/%s" % (_DIR, name))
        _font_cache[role] = f
    return f


def style(name):
    """Shared lv.style_t objects, made once."""
    st = _styles.get(name)
    if st is not None:
        return st
    st = lv.style_t()
    st.init()
    if name == "screen":
        st.set_bg_color(color(BG))
        st.set_bg_opa(lv.OPA.COVER)
        st.set_text_color(color(TEXT))
        st.set_pad_all(0)
        st.set_border_width(0)
        st.set_radius(0)
    elif name == "plain":           # a transparent layout box
        st.set_bg_opa(lv.OPA.TRANSP)
        st.set_border_width(0)
        st.set_pad_all(0)
        st.set_radius(0)
    elif name == "row":
        st.set_bg_opa(lv.OPA.TRANSP)
        st.set_border_width(1)
        st.set_border_side(lv.BORDER_SIDE.BOTTOM)
        st.set_border_color(color(LINE))
        st.set_radius(0)
    elif name == "pressed":
        st.set_bg_color(color(SURFACE2))
        st.set_bg_opa(lv.OPA.COVER)
    elif name == "surface":
        st.set_bg_color(color(SURFACE))
        st.set_bg_opa(lv.OPA.COVER)
        st.set_border_width(0)
        st.set_radius(12)
    elif name == "chip":
        st.set_bg_color(color(SURFACE))
        st.set_bg_opa(lv.OPA.COVER)
        st.set_border_color(color(LINE))
        st.set_border_width(1)
        st.set_radius(22)
        st.set_pad_hor(16)
        st.set_pad_ver(0)
        st.set_text_color(color(TEXT))
        st.set_shadow_width(0)
    elif name == "chip_on":
        st.set_bg_color(color(ACCENT))
        st.set_border_color(color(ACCENT))
        st.set_text_color(color(BG))
    elif name == "bubble_in":
        st.set_bg_color(color(SURFACE))
        st.set_bg_opa(lv.OPA.COVER)
        st.set_radius(14)
        st.set_pad_all(10)
        st.set_border_width(0)
    elif name == "bubble_out":
        st.set_bg_color(color(OWN))
        st.set_bg_opa(lv.OPA.COVER)
        st.set_radius(14)
        st.set_pad_all(10)
        st.set_border_width(0)
    elif name == "badge":
        st.set_bg_color(color(ACCENT))
        st.set_bg_opa(lv.OPA.COVER)
        st.set_radius(11)
        st.set_pad_hor(7)
        st.set_pad_ver(1)
        st.set_text_color(color(BG))
    elif name == "tabbar":
        st.set_bg_color(color(SURFACE))
        st.set_bg_opa(lv.OPA.COVER)
        st.set_border_width(1)
        st.set_border_side(lv.BORDER_SIDE.TOP)
        st.set_border_color(color(LINE))
        st.set_radius(0)
        st.set_pad_all(0)
    _styles[name] = st
    return st


def box(parent, w=None, h=None, flow=None, st="plain"):
    """A layout container without theme decoration."""
    o = lv.obj(parent)
    o.remove_style_all()
    o.add_style(style(st), lv.PART.MAIN)
    o.set_size(w if w is not None else lv.pct(100), h if h is not None else lv.SIZE_CONTENT)
    o.remove_flag(lv.obj.FLAG.SCROLLABLE)
    o.remove_flag(lv.obj.FLAG.CLICKABLE)    # taps go to the clickable() ancestor
    if flow is not None:
        o.set_flex_flow(flow)
    return o


def label(parent, text, role="body", col=TEXT, long_mode=None):
    lb = lv.label(parent)
    lb.set_text(text)
    lb.set_style_text_font(font(role), lv.PART.MAIN)
    lb.set_style_text_color(color(col), lv.PART.MAIN)
    if long_mode is not None:
        lb.set_long_mode(long_mode)
    return lb


def symbol(parent, sym, col=TEXT):
    lb = lv.label(parent)
    lb.set_text(sym)
    lb.set_style_text_font(SYMBOL_FONT, lv.PART.MAIN)
    lb.set_style_text_color(color(col), lv.PART.MAIN)
    return lb


def make_screen():
    scr = lv.obj()
    scr.remove_style_all()
    scr.add_style(style("screen"), lv.PART.MAIN)
    scr.set_size(W, H)
    scr.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return scr


def clickable(obj, on_click):
    obj.add_flag(lv.obj.FLAG.CLICKABLE)
    obj.add_style(style("pressed"), lv.PART.MAIN | lv.STATE.PRESSED)
    obj.add_event_cb(lambda e: on_click(), lv.EVENT.CLICKED, None)
    return obj


class Header:
    """Top bar: optional back arrow, title + subtitle, optional action button on the right.
    Occupies TOP_PAD + HEADER_H pixels."""

    def __init__(self, parent, title, subtitle=None, back=None, action=None):
        self.obj = box(parent, W, TOP_PAD + HEADER_H)
        self.obj.set_style_pad_top(TOP_PAD, lv.PART.MAIN)
        self.obj.set_style_pad_left(EDGE if back is None else 8, lv.PART.MAIN)
        self.obj.set_style_pad_right(12, lv.PART.MAIN)
        self.obj.set_flex_flow(lv.FLEX_FLOW.ROW)
        self.obj.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        if back is not None:
            b = box(self.obj, 44, 44)
            symbol(b, lv.SYMBOL.LEFT, ACCENT).center()
            clickable(b, back)
        col = box(self.obj, None, lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN)
        col.set_flex_grow(1)
        self.title = label(col, title, "title", TEXT, lv.label.LONG_MODE.DOTS)
        self.title.set_width(lv.pct(100))
        self.subtitle = label(col, subtitle or "", "small", MUTED, lv.label.LONG_MODE.DOTS)
        self.subtitle.set_width(lv.pct(100))
        if not subtitle:
            self.subtitle.add_flag(lv.obj.FLAG.HIDDEN)
        self.action = None
        if action is not None:
            text, cb = action
            self.action = Chip(self.obj, text, cb)

    def set_subtitle(self, text):
        self.subtitle.set_text(text or "")
        if text:
            self.subtitle.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.subtitle.add_flag(lv.obj.FLAG.HIDDEN)


class Chip:
    """A rounded 44 px button with a text label, optionally 'selected' (amber)."""

    def __init__(self, parent, text, on_click, selected=False, h=36):
        self.obj = lv.obj(parent)
        self.obj.remove_style_all()
        self.obj.add_style(style("chip"), lv.PART.MAIN)
        self.obj.add_style(style("chip_on"), lv.PART.MAIN | lv.STATE.CHECKED)
        self.obj.set_size(lv.SIZE_CONTENT, h)
        self.obj.remove_flag(lv.obj.FLAG.SCROLLABLE)
        self.label = label(self.obj, text, "strong", TEXT)
        self.label.center()
        clickable(self.obj, on_click)
        self.set_selected(selected)

    def set_text(self, text):
        self.label.set_text(text)

    def set_selected(self, on):
        if on:
            self.obj.add_state(lv.STATE.CHECKED)
            self.label.set_style_text_color(color(BG), lv.PART.MAIN)
        else:
            self.obj.remove_state(lv.STATE.CHECKED)
            self.label.set_style_text_color(color(TEXT), lv.PART.MAIN)


class TabBar:
    """The 56 px bottom bar of the main screen: one button per tab, the active one amber,
    with an optional count badge (Chats)."""

    def __init__(self, parent, labels, on_select):
        self.obj = box(parent, W, TABBAR_H, lv.FLEX_FLOW.ROW, "tabbar")
        self.obj.align(lv.ALIGN.BOTTOM_MID, 0, 0)
        self.obj.add_flag(lv.obj.FLAG.IGNORE_LAYOUT)
        self._labels = []
        self._badges = []
        for i, text in enumerate(labels):
            cell = box(self.obj, W // len(labels), TABBAR_H, lv.FLEX_FLOW.ROW)
            cell.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            cell.set_style_pad_column(6, lv.PART.MAIN)
            lb = label(cell, text, "strong", MUTED)
            badge = box(cell, lv.SIZE_CONTENT, lv.SIZE_CONTENT, None, "badge")
            label(badge, "", "small", BG)
            badge.add_flag(lv.obj.FLAG.HIDDEN)
            clickable(cell, lambda i=i: on_select(i))
            self._labels.append(lb)
            self._badges.append(badge)

    def set_active(self, idx):
        for i, lb in enumerate(self._labels):
            lb.set_style_text_color(color(ACCENT if i == idx else MUTED), lv.PART.MAIN)

    def set_badge(self, idx, count):
        badge = self._badges[idx]
        if count:
            badge.get_child(0).set_text(str(count))
            badge.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            badge.add_flag(lv.obj.FLAG.HIDDEN)


def badge(parent, text):
    b = box(parent, lv.SIZE_CONTENT, lv.SIZE_CONTENT, None, "badge")
    label(b, text, "small", BG)
    return b


def tz_offset_s():
    """Local time offset in seconds, from MicroPythonOS's timezone setting (0 if unknown)."""
    try:
        import time
        import mpos.time
        from ui_model import tz_offset
        return tz_offset(mpos.time.localtime(), time.gmtime())
    except Exception:
        return 0
