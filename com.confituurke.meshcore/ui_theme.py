"""Look of the app: the design canvas's colours, fonts, icons and shared components.

MicroPythonOS keeps the top 24 px (status bar / drawer gesture) and a 24 px "back" strip
on the left, so every screen lays out from y 24 and keeps text clear of the left edge.
Components here are the canvas's building blocks: headers, chips, list rows, avatars,
badges, tab bar, cards, buttons, radio cards, step indicator, inputs and bubbles.
"""

import os

import lvgl as lv

from mpos import FontManager

import ui_model

from ui_model import (BG, SURFACE, SURFACE2, LINE, OUTLINE, TEXT, MUTED, ACCENT,  # noqa: F401
                      OWN, OWN_TEXT, BAR, CHAN_BG, CHAN_FG, DM_BG, DM_FG, ROOM_BG,
                      DELIVERED, FAIL, FAIL_TEXT, OK, WARN, ERR, ON_ACCENT, KEYBOARD,
                      PIN_RPTR, PIN_ROOM, SENDER_COLORS)
import ui_palette

palette = None          # the colours in use (ui_palette.resolve); None until apply()
theme_version = 0       # bumped by each apply() that changes the colours

W = 480
H = 480
TOP = 24            # MicroPythonOS status bar / drawer strip
HEADER_H = 48
TABBAR_H = 56
ROW_H = 77
CHIP_H = 36
COMPOSER_H = 52
KEYBOARD_H = 188

_DIR = os.path.dirname(os.path.abspath(__file__))
_FILES = {
    (False, 400): "ArchivoNarrow-Regular.ttf",
    (False, 600): "ArchivoNarrow-SemiBold.ttf",
    (False, 700): "ArchivoNarrow-Bold.ttf",
    (True, 400): "MeshMono-Regular.ttf",
    (True, 500): "MeshMono-Medium.ttf",
}
SYMBOL_FONT = lv.font_montserrat_14

_fonts = {}



def _has_emoji_image(cp):
    """Whether MicroPythonOS draws this emoji, itself or as a similar one it has."""
    try:
        return FontManager._get_emoji_src(cp, 16) is not None
    except Exception:
        return FontManager.isEmojiCodepoint(cp)


# Emoji MicroPythonOS has no image for are left out of displayed text (see ui_model.display).
ui_model.set_emoji_filter(_has_emoji_image)
_styles = {}


def color(c):
    return lv.color_hex(c)


# --- theme ------------------------------------------------------------------ #

def _os_look():
    """(light mode?, primary colour as 0xRRGGBB or None) from MicroPythonOS."""
    try:
        from mpos import AppearanceManager
        light = bool(AppearanceManager.is_light_mode())
        c = AppearanceManager.get_primary_color()
    except Exception:
        return False, None
    if c is None:
        return light, None
    try:
        return light, rgb(c)
    except Exception:
        return light, None


def rgb(c):
    """An lv.color_t as 0xRRGGBB."""
    return (c.red << 16) | (c.green << 8) | c.blue


def wanted_palette():
    """The colours the settings ask for now: the app's own Appearance choice, or the OS's."""
    from mpos import SharedPreferences
    from meshcore_manager import MESHCORE_APP
    prefs = SharedPreferences(MESHCORE_APP)
    light, accent = _os_look()
    return ui_palette.resolve(prefs.get_string("theme", "system") or "system",
                              prefs.get_string("accent", "system") or "system", light, accent)


def apply(p=None):
    """Use palette `p` (default: wanted_palette()) for everything built from now on. True when
    the colours changed: screens already built then have to be rebuilt."""
    global palette, theme_version
    if p is None:
        p = wanted_palette()
    if palette is not None and all(palette.get(k) == v for k, v in p.items()):
        return False
    p = dict(p)
    p["ERR"] = p["FAIL_TEXT"]
    g = globals()
    for k, v in p.items():
        if k.isupper():
            g[k] = v
            setattr(ui_model, k, v)
    _styles.clear()             # cached styles hold the old colours
    palette = p
    theme_version += 1
    return True


def font(size, weight=400, mono=False, emoji=False):
    """A bundled font. Kept per (size, weight, family): FontManager.getFont() costs more
    than building a widget, and a font that is held stays valid (it is never destroyed).
    emoji=True puts MicroPythonOS's emoji images in front of it, for text people wrote
    (names, messages): node names on the mesh often carry emoji."""
    key = (size, weight, mono, emoji)
    f = _fonts.get(key)
    if f is None:
        path = "M:%s/fonts/%s" % (_DIR, _FILES[(mono, weight)])
        base = FontManager.getFont(size=size, ttf=path)
        _no_kerning(base)
        f = FontManager.getFont(size=size, ttf=path, emoji=True) if emoji else base
        _fonts[key] = f
    return f


def _no_kerning(f):
    """LVGL 9.4's tiny_ttf kerning cache orders its entries with an 8-bit compare of glyph
    index differences: once it holds 256 letter pairs and has to evict, a lookup fails and
    eviction loops forever (the UI freezes). Without kerning that cache is never used."""
    try:
        lv.font_set_kerning(f, lv.FONT_KERNING.NONE)
    except AttributeError:
        f.kerning = lv.FONT_KERNING.NONE


# --- basic building blocks ------------------------------------------------- #

def box(parent, w=None, h=None, flow=None):
    """A layout container with no decoration and no click handling of its own."""
    o = lv.obj(parent)
    o.remove_style_all()
    o.set_size(w if w is not None else lv.pct(100), h if h is not None else lv.SIZE_CONTENT)
    o.remove_flag(lv.obj.FLAG.SCROLLABLE)
    o.remove_flag(lv.obj.FLAG.CLICKABLE)    # taps go to the clickable() ancestor
    if flow is not None:
        o.set_flex_flow(flow)
    return o


def row(parent, w=None, h=None, gap=0, align=lv.FLEX_ALIGN.START):
    o = box(parent, w, h, lv.FLEX_FLOW.ROW)
    o.set_flex_align(align, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    o.set_style_pad_column(gap, lv.PART.MAIN)
    return o


def column(parent, w=None, h=None, gap=0):
    o = box(parent, w, h, lv.FLEX_FLOW.COLUMN)
    o.set_style_pad_row(gap, lv.PART.MAIN)
    return o


def fill(o, bg, radius=0, border=None, border_w=1):
    o.set_style_bg_color(color(bg), lv.PART.MAIN)
    o.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    o.set_style_radius(radius, lv.PART.MAIN)
    if border is not None:
        o.set_style_border_color(color(border), lv.PART.MAIN)
        o.set_style_border_width(border_w, lv.PART.MAIN)
    return o


def outline(o, border, radius, width=1):
    o.set_style_border_color(color(border), lv.PART.MAIN)
    o.set_style_border_width(width, lv.PART.MAIN)
    o.set_style_radius(radius, lv.PART.MAIN)
    return o


def divider(o, side=None):
    """1 px #222C37 line on the bottom (default) or top of an object."""
    o.set_style_border_color(color(LINE), lv.PART.MAIN)
    o.set_style_border_width(1, lv.PART.MAIN)
    o.set_style_border_side(side or lv.BORDER_SIDE.BOTTOM, lv.PART.MAIN)
    return o


def label(parent, text, size=16, weight=400, col=None, mono=False, long_mode=None, width=None,
          emoji=False):
    lb = lv.label(parent)
    lb.set_text(text)
    lb.set_style_text_font(font(size, weight, mono, emoji), lv.PART.MAIN)
    lb.set_style_text_color(color(TEXT if col is None else col), lv.PART.MAIN)
    if long_mode is not None:
        lb.set_long_mode(long_mode)
    if width is not None:
        lb.set_width(width)
    return lb


def icon(parent, name, col=None):
    img = lv.image(parent)
    img.set_src("M:%s/icons/%s.png" % (_DIR, name))
    tint(img, TEXT if col is None else col)
    return img


def tint(img, col):
    img.set_style_image_recolor(color(col), lv.PART.MAIN)
    img.set_style_image_recolor_opa(lv.OPA.COVER, lv.PART.MAIN)


def symbol(parent, sym, col=None):
    lb = lv.label(parent)
    lb.set_text(sym)
    lb.set_style_text_font(SYMBOL_FONT, lv.PART.MAIN)
    lb.set_style_text_color(color(TEXT if col is None else col), lv.PART.MAIN)
    return lb


def _pressed_style():
    st = _styles.get("pressed")
    if st is None:
        st = lv.style_t()
        st.init()
        st.set_bg_color(color(SURFACE2))
        st.set_bg_opa(lv.OPA.COVER)
        _styles["pressed"] = st
    return st


def clickable(obj, on_click, feedback=True):
    obj.add_flag(lv.obj.FLAG.CLICKABLE)
    if feedback:
        obj.add_style(_pressed_style(), lv.PART.MAIN | lv.STATE.PRESSED)
    obj.add_event_cb(lambda e: on_click(), lv.EVENT.CLICKED, None)
    return obj


def make_screen():
    if palette is None:
        apply()                 # first screen of the app (a notification can open any)
    scr = lv.obj()
    scr.remove_style_all()
    fill(scr, BG)
    scr.set_style_text_color(color(TEXT), lv.PART.MAIN)
    scr.set_size(W, H)
    scr.remove_flag(lv.obj.FLAG.SCROLLABLE)
    scr.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    scr.set_style_pad_top(TOP, lv.PART.MAIN)
    return scr


def scroll_area(parent, pad_hor=0, gap=0):
    """The flexible middle of a screen: takes the remaining height and scrolls."""
    a = column(parent, W, 1, gap)
    a.set_flex_grow(1)
    a.add_flag(lv.obj.FLAG.SCROLLABLE)
    a.set_scroll_dir(lv.DIR.VER)
    a.set_scrollbar_mode(lv.SCROLLBAR_MODE.ACTIVE)
    a.set_style_pad_hor(pad_hor, lv.PART.MAIN)
    return a


def icon_button(parent, name, on_click, w=48, h=48, col=None):
    b = box(parent, w, h)
    b.set_style_radius(h // 2, lv.PART.MAIN)
    icon(b, name, col).center()
    clickable(b, on_click)
    return b


# --- headers ---------------------------------------------------------------- #

class HeaderTop:
    """Top-level tab header: 48 px, 22/700 title at x 16, actions on the right."""

    def __init__(self, parent, title, pad_right=8, gap=8):
        self.obj = row(parent, W, HEADER_H, gap)
        self.obj.set_style_pad_left(16, lv.PART.MAIN)
        self.obj.set_style_pad_right(pad_right, lv.PART.MAIN)
        self.title = label(self.obj, title, 22, 700)
        self.title.set_flex_grow(1)


class HeaderSub:
    """Sub-page header: back button, 20/700 title with a subtitle (Archivo 14 or mono 12),
    optional kebab menu and bottom divider."""

    def __init__(self, parent, title, subtitle=None, back=None, mono_subtitle=False,
                 border=False, menu=None):
        self.obj = row(parent, W, HEADER_H, 4)
        self.obj.set_style_pad_hor(4, lv.PART.MAIN)
        if border:
            divider(self.obj)
            self.obj.set_height(HEADER_H + 1)
        if back is not None:
            icon_button(self.obj, "back", back)
        col = column(self.obj, 1)
        col.set_flex_grow(1)
        self.title = label(col, title, 20, 700, long_mode=lv.label.LONG_MODE.DOTS, width=lv.pct(100),
                           emoji=True)
        self.subtitle = label(col, subtitle or "", 12 if mono_subtitle else 14, 400, MUTED,
                              mono=mono_subtitle, long_mode=lv.label.LONG_MODE.DOTS, width=lv.pct(100))
        if not subtitle:
            self.subtitle.add_flag(lv.obj.FLAG.HIDDEN)
        if menu is not None:
            icon_button(self.obj, "kebab", menu)

    def set_subtitle(self, text):
        self.subtitle.set_text(text or "")
        if text:
            self.subtitle.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.subtitle.add_flag(lv.obj.FLAG.HIDDEN)


class HeaderCompact:
    """Direct-thread header: 44 px + divider, back at x 0, 20/700 title, a pill on the right."""

    def __init__(self, parent, title, back, pill_text, on_pill):
        self.obj = row(parent, W, 45, 4)
        divider(self.obj)
        self.obj.set_style_pad_right(8, lv.PART.MAIN)
        icon_button(self.obj, "back", back, 48, 44)
        self.title = label(self.obj, title, 20, 700, long_mode=lv.label.LONG_MODE.DOTS, emoji=True)
        self.title.set_flex_grow(1)
        self.pill = row(self.obj, lv.SIZE_CONTENT, 32, 6)
        fill(self.pill, SURFACE, 16)
        self.pill.set_style_pad_hor(12, lv.PART.MAIN)
        self.pill_label = label(self.pill, pill_text, 13, mono=True)
        icon(self.pill, "chevron_down")
        clickable(self.pill, on_pill)


def preset_pill(parent, text, on_click):
    """Chats header pill: accent dot + mono 12 preset name on a surface pill."""
    p = row(parent, lv.SIZE_CONTENT, 28, 6)
    fill(p, SURFACE, 14)
    p.set_style_pad_hor(10, lv.PART.MAIN)
    dot = box(p, 8, 8)
    fill(dot, ACCENT, 4)
    label(p, text, 12, mono=True, col=MUTED)
    clickable(p, on_click)
    return p


# --- chips and badges ------------------------------------------------------ #

class Chip:
    """A 36 px filter chip: accent with dark 600 text when selected, surface otherwise."""

    def __init__(self, parent, text, on_click, selected=False, pad_on=16, pad_off=14, icon_name=None):
        self.pad_on, self.pad_off = pad_on, pad_off
        self.obj = row(parent, lv.SIZE_CONTENT, CHIP_H, 0, lv.FLEX_ALIGN.CENTER)
        self.obj.set_style_radius(18, lv.PART.MAIN)
        self.obj.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
        self.icon = None
        self.label = None
        if icon_name:
            self.obj.set_width(44)
            self.icon = icon(self.obj, icon_name)
        else:
            self.label = label(self.obj, text, 16)
        clickable(self.obj, on_click, feedback=False)
        self.set_selected(selected)

    def set_text(self, text):
        if self.label is not None:
            self.label.set_text(text)

    def set_selected(self, on):
        self.selected = on
        self.obj.set_style_bg_color(color(ACCENT if on else SURFACE), lv.PART.MAIN)
        if self.label is not None:
            self.obj.set_style_pad_hor(self.pad_on if on else self.pad_off, lv.PART.MAIN)
            self.label.set_style_text_color(color(ON_ACCENT if on else TEXT), lv.PART.MAIN)
            self.label.set_style_text_font(font(16, 600 if on else 400), lv.PART.MAIN)
        if self.icon is not None:
            tint(self.icon, ON_ACCENT if on else TEXT)


def chip_bar(parent, gap=8):
    bar = row(parent, W, 44, gap)
    bar.set_style_pad_hor(12, lv.PART.MAIN)
    bar.add_flag(lv.obj.FLAG.SCROLLABLE)
    bar.set_scroll_dir(lv.DIR.HOR)
    bar.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    return bar


def quick_chip(parent, text, on_click):
    c = row(parent, lv.SIZE_CONTENT, CHIP_H)
    outline(c, OUTLINE, 18)
    c.set_style_pad_hor(14, lv.PART.MAIN)
    label(c, text, 16)
    clickable(c, on_click)
    return c


class Badge:
    """Row badge: filled accent count, or an outlined "@" for a mention."""

    def __init__(self, parent):
        self.obj = row(parent, lv.SIZE_CONTENT, 24, 0, lv.FLEX_ALIGN.CENTER)
        self.obj.set_style_radius(12, lv.PART.MAIN)
        self.obj.set_style_min_width(24, lv.PART.MAIN)
        self.label = label(self.obj, "", 14, 700, ON_ACCENT)

    def show(self, count=0, mention=False):
        if mention:
            self.obj.set_style_bg_opa(lv.OPA.TRANSP, lv.PART.MAIN)
            outline(self.obj, ACCENT, 12, 2)
            self.obj.set_style_pad_hor(8, lv.PART.MAIN)
            self.label.set_text("@")
            self.label.set_style_text_color(color(ACCENT), lv.PART.MAIN)
        elif count:
            fill(self.obj, ACCENT, 12)
            self.obj.set_style_border_width(0, lv.PART.MAIN)
            self.obj.set_style_pad_hor(7, lv.PART.MAIN)
            self.label.set_text(str(count))
            self.label.set_style_text_color(color(ON_ACCENT), lv.PART.MAIN)
        if mention or count:
            self.obj.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.obj.add_flag(lv.obj.FLAG.HIDDEN)


# --- avatars ---------------------------------------------------------------- #

def avatar(parent, kind, text=""):
    """44 px avatar. kind: channel (circle, '#'), dm (circle, initials), room (square with
    the chat icon), node (bordered square: "hex\\nkind" as two lines)."""
    a = box(parent, 44, 44)
    if kind == "channel":
        fill(a, CHAN_BG, 22)
        label(a, "#", 22, 700, CHAN_FG).center()
    elif kind == "dm":
        fill(a, DM_BG, 22)
        label(a, text, 17, 700, DM_FG).center()
    elif kind == "room":
        fill(a, ROOM_BG, 12)
        icon(a, "chat").center()
    else:
        fill(a, SURFACE, 10, OUTLINE)
        col = column(a, lv.SIZE_CONTENT, lv.SIZE_CONTENT, 1)
        col.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        parts = (text.split("\n") + [""])[:2]
        label(col, parts[0], 15, 500, mono=True)
        kind_label = label(col, parts[1].upper(), 10, 400, MUTED)
        kind_label.set_style_text_letter_space(1, lv.PART.MAIN)
        col.center()
    return a


# --- list rows ------------------------------------------------------------- #

class ListRow:
    """77 px row with a 1 px divider: avatar, title (19/600) + right text (mono 13), and a
    second line (16, muted) with an optional badge."""

    def __init__(self, parent, on_click):
        self.obj = row(parent, W, ROW_H + 1, 12)
        self.obj.set_style_pad_hor(14, lv.PART.MAIN)
        divider(self.obj)
        clickable(self.obj, on_click)
        self.avatar_slot = box(self.obj, 44, 44)
        text = column(self.obj, 1, lv.SIZE_CONTENT, 3)
        text.set_flex_grow(1)
        top = row(text, lv.pct(100), lv.SIZE_CONTENT, 8)
        self.title = label(top, "", 19, 600, long_mode=lv.label.LONG_MODE.DOTS, emoji=True)
        self.title.set_flex_grow(1)
        self.right = label(top, "", 13, mono=True, col=MUTED)
        bottom = row(text, lv.pct(100), 24, 8)
        self.line2 = label(bottom, "", 16, col=MUTED, long_mode=lv.label.LONG_MODE.DOTS, emoji=True)
        self.line2.set_flex_grow(1)
        self.badge = Badge(bottom)
        self.badge.show()
        self._avatar_key = None

    def set_avatar(self, kind, text):
        key = (kind, text)
        if key == self._avatar_key:
            return
        self._avatar_key = key
        self.avatar_slot.clean()
        avatar(self.avatar_slot, kind, text)


# --- tab bar --------------------------------------------------------------- #

class TabBar:
    """56 px bar with a top divider: icon (22) over label (13), accent + 600 when active."""

    def __init__(self, parent, tabs, on_select):
        self.obj = row(parent, W, TABBAR_H + 1)
        fill(self.obj, BAR)
        divider(self.obj, lv.BORDER_SIDE.TOP)
        self._icons = []
        self._labels = []
        self._names = []
        for i, (name, icon_name) in enumerate(tabs):
            cell = column(self.obj, W // len(tabs), TABBAR_H, 2)
            cell.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self._icons.append(icon(cell, icon_name, MUTED))
            self._labels.append(label(cell, name, 13, col=MUTED))
            self._names.append(name)
            clickable(cell, lambda i=i: on_select(i), feedback=False)

    def set_active(self, idx):
        for i, lb in enumerate(self._labels):
            on = i == idx
            c = ACCENT if on else MUTED
            lb.set_style_text_color(color(c), lv.PART.MAIN)
            lb.set_style_text_font(font(13, 600 if on else 400), lv.PART.MAIN)
            tint(self._icons[i], c)

    def set_count(self, idx, count):
        """'Chats 3': the count is part of the label, not a separate badge."""
        self._labels[idx].set_text("%s %d" % (self._names[idx], count) if count else self._names[idx])


# --- cards, settings rows, key-value grid ----------------------------------- #

def card(parent, filled=True, pad_ver=12, pad_hor=14, gap=6, radius=12):
    c = column(parent, lv.pct(100), lv.SIZE_CONTENT, gap)
    if filled:
        fill(c, SURFACE, radius)
    else:
        outline(c, OUTLINE, radius)
    c.set_style_pad_ver(pad_ver, lv.PART.MAIN)
    c.set_style_pad_hor(pad_hor, lv.PART.MAIN)
    return c


def section_label(parent, text):
    lb = label(parent, text, 15, col=MUTED)
    lb.set_style_pad_top(6, lv.PART.MAIN)
    return lb


class SettingRow:
    """A row inside an outline card: label (16) on the left, an optional mono value and a
    chevron on the right. Rows after the first get a divider on top."""

    def __init__(self, parent, title, value=None, on_click=None, first=False, chevron=True):
        self.obj = row(parent, lv.pct(100), 52, 8)
        if not first:
            divider(self.obj, lv.BORDER_SIDE.TOP)
        self.title = label(self.obj, title, 16, long_mode=lv.label.LONG_MODE.DOTS)
        self.title.set_flex_grow(1)
        self.value = None
        if value is not None:
            self.value = label(self.obj, value, 13, mono=True, col=MUTED)
        if on_click is not None:
            if chevron:
                icon(self.obj, "chevron_right", MUTED)
            clickable(self.obj, on_click)


def kv_grid(parent, pairs):
    """Two columns of key (15, muted) / value (mono 14, right-aligned) cells."""
    grid = box(parent, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW_WRAP)
    grid.set_style_pad_column(16, lv.PART.MAIN)
    grid.set_style_pad_row(8, lv.PART.MAIN)
    for k, v in pairs:
        cell = row(grid, 218, 22, 8, lv.FLEX_ALIGN.SPACE_BETWEEN)
        label(cell, k, 15, col=MUTED)
        label(cell, v, 14, mono=True)
    return grid


# --- buttons ---------------------------------------------------------------- #

def button(parent, text, on_click, kind="primary", h=52, sub=None, width=None, size=18):
    """primary: accent fill, dark text. outline: 2 px #2C3846. filled: #2C3846 fill.
    An optional sublabel (13) below the text."""
    b = column(parent, width if width is not None else lv.SIZE_CONTENT, h, 0)
    b.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    b.set_style_pad_hor(16, lv.PART.MAIN)
    radius = 12 if h >= 52 else (10 if h >= 44 else 8)
    if kind == "primary":
        fill(b, ACCENT, radius)
        fg, sub_fg, weight = ON_ACCENT, ON_ACCENT, 700 if h >= 52 else 600
    elif kind == "tile":
        fill(b, SURFACE, 10, OUTLINE)
        fg, sub_fg, weight = TEXT, MUTED, 400
    elif kind == "outline":
        outline(b, OUTLINE, radius, 2)
        fg, sub_fg, weight = TEXT, MUTED, 600 if sub else 400
    else:
        fill(b, OUTLINE, radius)
        fg, sub_fg, weight = TEXT, MUTED, 400
    label(b, text, size, weight, fg)
    if sub:
        label(b, sub, 13, col=sub_fg)
    clickable(b, on_click, feedback=kind != "primary")
    return b


def disable(b):
    """A button that is shown but does nothing yet: muted text, no taps."""
    b.remove_flag(lv.obj.FLAG.CLICKABLE)
    for i in range(b.get_child_count()):
        b.get_child(i).set_style_text_color(color(MUTED), lv.PART.MAIN)
        b.get_child(i).set_style_text_opa(lv.OPA._50, lv.PART.MAIN)


class Segmented:
    """A 44 px segmented control: the selected segment is #2C3846 with 600 text."""

    def __init__(self, parent, labels, on_select, selected=0):
        self.obj = row(parent, lv.pct(100), 44, 0)
        fill(self.obj, SURFACE, 10)
        self.obj.set_style_pad_all(3, lv.PART.MAIN)
        self._segs = []
        for i, text in enumerate(labels):
            seg = row(self.obj, 1, 38, 0, lv.FLEX_ALIGN.CENTER)
            seg.set_flex_grow(1)
            seg.set_style_radius(8, lv.PART.MAIN)
            lb = label(seg, text, 16, col=MUTED)
            clickable(seg, lambda i=i: on_select(i), feedback=False)
            lb.add_flag(lv.obj.FLAG.EVENT_BUBBLE)
            self._segs.append((seg, lb))
        self.set_selected(selected)

    def set_selected(self, idx):
        for i, (seg, lb) in enumerate(self._segs):
            on = i == idx
            seg.set_style_bg_color(color(OUTLINE), lv.PART.MAIN)
            seg.set_style_bg_opa(lv.OPA.COVER if on else lv.OPA.TRANSP, lv.PART.MAIN)
            lb.set_style_text_color(color(TEXT if on else MUTED), lv.PART.MAIN)
            lb.set_style_text_font(font(16, 600 if on else 400), lv.PART.MAIN)


def advert_button(parent, on_click):
    """Nodes header: 'Advert' in accent with the advert icon, 2 px accent outline."""
    b = row(parent, lv.SIZE_CONTENT, 40, 6)
    outline(b, ACCENT, 20, 2)
    b.set_style_pad_hor(14, lv.PART.MAIN)
    icon(b, "advert", ACCENT)
    label(b, "Advert", 16, 600, ACCENT)
    clickable(b, on_click)
    return b


# --- setup pieces ---------------------------------------------------------- #

def step_indicator(parent, step, total):
    r = row(parent, lv.pct(100), 21, 8)
    label(r, "Step %d of %d" % (step, total), 15, col=MUTED)
    track = box(r, 1, 4)
    track.set_flex_grow(1)
    fill(track, LINE, 2)
    bar = box(track, lv.pct(100 * step // total), 4)
    fill(bar, ACCENT, 2)
    return r


class RadioCard:
    """Setup option: 2 px border card with a 22 px radio dot, name (18/600), detail (mono 12)
    and an optional accent tag."""

    def __init__(self, parent, name, detail, tag, on_click):
        self.obj = row(parent, lv.pct(100), lv.SIZE_CONTENT, 12)
        self.obj.set_style_min_height(56, lv.PART.MAIN)
        self.obj.set_style_pad_ver(6, lv.PART.MAIN)
        self.obj.set_style_pad_hor(14, lv.PART.MAIN)
        self.obj.set_style_radius(12, lv.PART.MAIN)
        self.obj.set_style_border_width(2, lv.PART.MAIN)
        self.obj.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
        self.dot = box(self.obj, 22, 22)
        outline(self.dot, OUTLINE, 11, 2)
        self.inner = box(self.dot, 10, 10)
        fill(self.inner, ACCENT, 5)
        self.inner.center()
        text = column(self.obj, 1, lv.SIZE_CONTENT, 2)
        text.set_flex_grow(1)
        label(text, name, 18, 600)
        label(text, detail, 12, mono=True, col=MUTED)
        if tag:
            label(self.obj, tag, 14, 600, ACCENT)
        clickable(self.obj, on_click, feedback=False)
        self.set_selected(False)

    def set_selected(self, on):
        self.obj.set_style_border_color(color(ACCENT if on else OUTLINE), lv.PART.MAIN)
        self.obj.set_style_bg_color(color(SURFACE if on else BG), lv.PART.MAIN)
        self.dot.set_style_border_color(color(ACCENT if on else OUTLINE), lv.PART.MAIN)
        if on:
            self.inner.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.inner.add_flag(lv.obj.FLAG.HIDDEN)


# --- inputs ---------------------------------------------------------------- #

def text_input(parent, text="", placeholder="", width=None):
    ta = lv.textarea(parent)
    ta.set_one_line(True)
    ta.set_text(text)
    ta.set_placeholder_text(placeholder)
    ta.set_size(width if width is not None else lv.pct(100), 40)
    ta.set_style_text_font(font(17), lv.PART.MAIN)
    ta.set_style_text_color(color(TEXT), lv.PART.MAIN)
    # LV_PART_TEXTAREA_PLACEHOLDER is LV_PART_CUSTOM_FIRST; the binding only has the latter.
    ta.set_style_text_color(color(MUTED), lv.PART.CUSTOM_FIRST)
    fill(ta, SURFACE, 20, OUTLINE)
    ta.set_style_border_color(color(ACCENT), lv.PART.MAIN | lv.STATE.FOCUSED)
    ta.set_style_pad_hor(14, lv.PART.MAIN)
    ta.set_style_pad_ver(9, lv.PART.MAIN)
    ta.set_style_bg_color(color(ACCENT), lv.PART.CURSOR)
    ta.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    return ta


def switch(parent, on, on_change):
    """48x28 switch: accent track when on, #2C3846 when off, light knob."""
    sw = lv.switch(parent)
    sw.set_size(48, 28)
    sw.set_style_bg_color(color(OUTLINE), lv.PART.MAIN)
    sw.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    sw.set_style_bg_color(color(ACCENT), lv.PART.INDICATOR | lv.STATE.CHECKED)
    sw.set_style_bg_color(color(TEXT), lv.PART.KNOB)
    sw.set_style_pad_all(-3, lv.PART.KNOB)
    sw.set_style_opa(lv.OPA._50, lv.PART.MAIN | lv.STATE.DISABLED)   # locked: greyed
    if on:
        sw.add_state(lv.STATE.CHECKED)
    sw.add_event_cb(lambda e: on_change(sw.has_state(lv.STATE.CHECKED)), lv.EVENT.VALUE_CHANGED, None)
    return sw


def dropdown(parent, options, selected=0):
    """A 40 px dropdown in the input's look; the open list uses the surface colours."""
    dd = lv.dropdown(parent)
    dd.set_options("\n".join(options))
    dd.set_selected(selected)
    dd.set_size(lv.pct(100), 40)
    dd.set_style_text_font(font(17), lv.PART.MAIN)
    dd.set_style_text_color(color(TEXT), lv.PART.MAIN)
    fill(dd, SURFACE, 10, OUTLINE)
    dd.set_style_pad_hor(14, lv.PART.MAIN)
    dd.set_style_pad_ver(9, lv.PART.MAIN)
    lst = dd.get_list()
    if lst is not None:
        lst.set_style_text_font(font(17), lv.PART.MAIN)
        lst.set_style_text_color(color(TEXT), lv.PART.MAIN)
        fill(lst, SURFACE, 10, OUTLINE)
        lst.set_style_bg_color(color(ACCENT), lv.PART.SELECTED | lv.STATE.CHECKED)
        lst.set_style_text_color(color(ON_ACCENT), lv.PART.SELECTED | lv.STATE.CHECKED)
    return dd


def keyboard(scr, ta=None, on_show=None, on_hide=None, floating=False):
    """MicroPythonOS's keyboard in the canvas colours, hidden until its textarea is tapped.
    In a column screen it takes its place at the bottom; floating, it covers the bottom."""
    from mpos import MposKeyboard
    kb = MposKeyboard(scr)
    if floating:
        kb.add_flag(lv.obj.FLAG.FLOATING)
        kb.align(lv.ALIGN.BOTTOM_MID, 0, 0)
    kb.set_size(W, KEYBOARD_H)
    style_keyboard(kb)
    kb.add_flag(lv.obj.FLAG.HIDDEN)
    if ta is not None:
        kb.set_textarea(ta, on_show=on_show, on_hide=on_hide)
    return kb


def style_keyboard(kb):
    """The canvas keyboard colours on MicroPythonOS's keyboard."""
    kb.set_style_bg_color(color(KEYBOARD), lv.PART.MAIN)
    kb.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    kb.set_style_border_width(0, lv.PART.MAIN)
    kb.set_style_pad_all(4, lv.PART.MAIN)
    kb.set_style_pad_gap(5, lv.PART.MAIN)
    kb.set_style_bg_color(color(LINE), lv.PART.ITEMS)
    kb.set_style_bg_color(color(OUTLINE), lv.PART.ITEMS | lv.STATE.CHECKED)
    kb.set_style_text_color(color(TEXT), lv.PART.ITEMS)
    kb.set_style_radius(6, lv.PART.ITEMS)
    kb.set_style_border_width(0, lv.PART.ITEMS)
    kb.set_style_shadow_width(0, lv.PART.ITEMS)


def tz_offset_s():
    """Local time offset in seconds, from MicroPythonOS's timezone setting (0 if unknown)."""
    try:
        import time
        import mpos.time
        from ui_model import tz_offset
        return tz_offset(mpos.time.localtime(), time.gmtime())
    except Exception:
        return 0
