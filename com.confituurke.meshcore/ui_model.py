"""View models for the screens: what each row and bubble says, in plain Python.

No LVGL here, so it runs (and is tested) on the desktop; the screens only turn these
dicts and strings into widgets. Times are Unix seconds; `tz_s` is the local offset.
"""

import time

import meshcore_presets

# Colours (0xRRGGBB), shared with ui_theme.
BG = 0x10151B
SURFACE = 0x19212A
SURFACE2 = 0x222C37
LINE = 0x2C3846
TEXT = 0xE9EEF3
MUTED = 0xA3B0BD
ACCENT = 0xF4A93B
OWN = 0x1E4B78
OK = 0x9BE0A8
WARN = 0xF2C98A
ERR = 0xF08A8A

MAX_TEXT_LEN = 160          # bytes of text in one MeshCore message (BaseChatMesh.h)
QUICK_REPLIES = ("copy", "on my way", "ETA 10 min", "signal report")

_EPOCH_2000 = 946684800
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_KINDS = {1: "chat", 2: "rptr", 3: "room", 4: "sensor"}


def _gmtime(unix_s):
    """time.gmtime() for Unix seconds, also on ports whose epoch is 2000."""
    if time.gmtime(0)[0] == 2000:
        unix_s -= _EPOCH_2000
    return time.gmtime(int(unix_s))


def _minus(s):
    return s.replace("-", "−")


def snr_text(snr):
    return _minus("%.1f" % snr)


def time_text(ts, now_s, tz_s=0):
    """'14:31' today, 'Wed' this week, '12 Sep' before that."""
    t = _gmtime(ts + tz_s)
    n = _gmtime(now_s + tz_s)
    if t[0:3] == n[0:3]:
        return "%02d:%02d" % (t[3], t[4])
    if 0 <= now_s - ts < 6 * 86400:
        return _DAYS[t[6]]
    return "%d %s" % (t[2], _MONTHS[t[1] - 1])


def tz_offset(local_tuple, utc_tuple):
    """Seconds the local clock is ahead of UTC, from the same instant read both ways
    (time tuples). Offsets are taken to lie within -12 h .. +14 h."""
    mins = (local_tuple[3] * 60 + local_tuple[4]) - (utc_tuple[3] * 60 + utc_tuple[4])
    while mins > 14 * 60:
        mins -= 24 * 60
    while mins < -12 * 60:
        mins += 24 * 60
    return mins * 60


def clock_text(ts, tz_s=0):
    t = _gmtime(ts + tz_s)
    return "%02d:%02d" % (t[3], t[4])


def initials(name):
    words = (name or "?").split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return words[0][:2].upper()


def _preview(msg, dm):
    if msg is None:
        return ""
    if not msg.get("incoming"):
        return "You: " + msg.get("text", "")
    if dm:
        return msg.get("text", "")
    return "%s: %s" % (msg.get("sender", "?"), msg.get("text", ""))


def chat_rows(mgr, now_s, filt="all", tz_s=0):
    """Rows for the Chats tab, newest activity first. filt: all, unread, direct, channels."""
    rows = []
    if filt != "direct":
        for name in mgr.get_channel_names():
            msgs = mgr.get_messages(name)
            last = msgs[-1] if msgs else None
            rows.append({"key": name, "kind": "channel", "title": name, "initials": "#",
                         "last": last})
    if filt != "channels":
        for c in mgr.get_contacts():
            msgs = mgr.get_dm_messages(c["pubkey"])
            last = msgs[-1] if msgs else None
            rows.append({"key": c["pubkey"], "kind": "dm", "title": c.get("name") or c["id"],
                         "initials": initials(c.get("name")), "last": last})
    for r in rows:
        last = r.pop("last")
        r["ts"] = last.get("ts", 0) if last else 0
        r["preview"] = _preview(last, r["kind"] == "dm")
        r["time"] = time_text(r["ts"], now_s, tz_s) if last else ""
        r["unread"] = mgr.get_unread(r["key"])
        r["mention"] = mgr.get_mention(r["key"])
    if filt == "unread":
        rows = [r for r in rows if r["unread"]]
    rows.sort(key=lambda r: r["ts"], reverse=True)
    return rows


def delivery(msg):
    """(glyph, text, colour) for an outgoing message's status line."""
    if not msg.get("tx"):
        return ("⏳", "sending", MUTED)
    if "ack" in msg or "delivered" in msg:          # a direct message
        if msg.get("delivered"):
            return ("✓", "delivered", OK)
        if msg.get("failed"):
            return ("✗", "no ack after 4 tries · tap to resend", ERR)
        return ("→", "sent", MUTED)
    if msg.get("heard"):
        return ("✓", "heard ×%d" % msg["heard"], OK)
    if msg.get("unheard"):
        return ("?", "not heard by a repeater · tap to resend", WARN)
    return ("→", "sent", MUTED)


def can_resend(msg):
    return not msg.get("incoming") and bool(msg.get("failed") or msg.get("unheard"))


def budget(text, channel_name=None, sender=None):
    """Bytes left in a message (negative = too long). A channel message carries
    'sender: ' in front of the text."""
    used = len((text or "").encode("utf-8"))
    if channel_name:
        used += len((sender or "").encode("utf-8")) + 2
    return MAX_TEXT_LEN - used


def age_text(seconds):
    if seconds < 60:
        return "now"
    if seconds < 3600:
        return "%d min" % (seconds // 60)
    if seconds < 86400:
        return "%d h" % (seconds // 3600)
    return "%d d" % (seconds // 86400)


def _age_color(seconds):
    if seconds < 30 * 60:
        return OK
    if seconds < 6 * 3600:
        return WARN
    return MUTED


def node_rows(nodes, now_ms, filt="all", contacts=()):
    """Rows for the Nodes tab. filt: all, chat, rptr, room, new (heard in the last hour and
    not a contact). `nodes` come most recent first, as the manager lists them."""
    rows = []
    for n in nodes:
        kind = _KINDS.get(n.get("type"), "other")
        age_s = max(0, (now_ms - n.get("heard_ms", now_ms)) // 1000)
        if filt == "new":
            if age_s >= 3600 or n.get("pubkey") in contacts:
                continue
        elif filt != "all" and kind != filt:
            continue
        hops = n.get("hops") or 0
        meta = "direct" if hops == 0 else ("1 hop" if hops == 1 else "%d hops" % hops)
        if n.get("snr") is not None:
            meta += " · SNR " + snr_text(n["snr"])
        rows.append({"pubkey": n.get("pubkey"), "hex": (n.get("id") or "??").upper(),
                     "kind": kind, "name": n.get("name") or "?", "age": age_text(age_s),
                     "age_color": _age_color(age_s), "meta": meta})
    return rows


def preset_summary(p, power):
    """(title, detail, airtime) for the Radio tab's preset card."""
    title = p.get("name") or "Custom"
    detail = "%s · %d dBm" % (meshcore_presets.describe(p), power)
    air = meshcore_presets.airtime_ms(p, 40) / 1000
    return (title, detail, "≈ %.2f s on air per 40-byte message" % air)


def signal_report(msg):
    hops = msg.get("hops") or 0
    s = "SNR " + snr_text(msg["snr"]) if msg.get("snr") is not None else "no SNR"
    return "%s · %d hop%s" % (s, hops, "" if hops == 1 else "s")
