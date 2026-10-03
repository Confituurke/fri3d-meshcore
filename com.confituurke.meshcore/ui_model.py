"""View models for the screens: what each row and bubble says, in plain Python.

No LVGL here, so it runs (and is tested) on the desktop; the screens only turn these
dicts and strings into widgets. Times are Unix seconds; `tz_s` is the local offset.
"""

import time

import meshcore_presets

# Colours (0xRRGGBB) of the design canvas, shared with ui_theme.
BG = 0x10151B         # app background; text on accent fills
BAR = 0x0D1217        # tab bar, composer bar
SURFACE = 0x19212A    # chips, pills, cards, incoming bubbles, inputs
SURFACE2 = 0x222C37   # pressed state
LINE = 0x222C37       # dividers
OUTLINE = 0x2C3846    # outlines, secondary buttons
TEXT = 0xE9EEF3
MUTED = 0xA3B0BD
ACCENT = 0xF4A93B
OWN = 0x1E4B78        # outgoing bubble
OWN_TEXT = 0xF2F7FC
CHAN_BG, CHAN_FG = 0x1F3A3F, 0x8FD3DA
DM_BG, DM_FG = 0x3A2E52, 0xCDB8F5
ROOM_BG = 0x2B3542
DELIVERED = 0x6CB4FF  # delivered check
FAIL = 0xFF9F7A       # failed bubble border
FAIL_TEXT = 0xFFB89C  # failed meta line
OK = 0x9BE0A8         # fresh age
WARN = 0xF2C98A       # older age, unheard
ERR = FAIL_TEXT
SENDER_COLORS = (CHAN_FG, DM_FG, 0xF2C98A, 0x9BE0A8, 0x6CB4FF, 0xFFB89C)

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
        return "No messages yet"
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


def delivery(msg, tz_s=0):
    """Status line of an outgoing message: {icon (None/"check"/"retry"), icon_color, text,
    color, dots (repeater echoes shown as dots, at most 6)}."""
    t = clock_text(msg.get("ts", 0), tz_s)
    if msg.get("failed"):
        return {"icon": "retry", "text": "no ack after 4 tries · tap to resend",
                "color": FAIL_TEXT, "dots": 0, "icon_color": FAIL_TEXT}
    if msg.get("unheard") and not msg.get("heard"):
        return {"icon": None, "text": "not heard by a repeater · tap to resend",
                "color": WARN, "dots": 0}
    if not msg.get("tx"):
        return {"icon": None, "text": t + " · sending", "color": MUTED, "dots": 0}
    if msg.get("delivered"):
        text = "delivered " + clock_text(msg.get("ack_ts") or msg.get("ts", 0), tz_s)
        if msg.get("ack_snr") is not None:
            text += " · SNR " + snr_text(msg["ack_snr"])
        return {"icon": "check", "text": text, "color": MUTED, "dots": 0, "icon_color": DELIVERED}
    if msg.get("heard"):
        return {"icon": None, "text": "%s · heard ×%d" % (t, msg["heard"]), "color": MUTED,
                "dots": min(msg["heard"], 6)}
    return {"icon": None, "text": t + " · sent", "color": MUTED, "dots": 0}


def sender_color(name):
    """A stable colour per sender name in channel threads."""
    h = 0
    for ch in name or "":
        h = (h * 31 + ord(ch)) & 0xFFFF
    return SENDER_COLORS[h % len(SENDER_COLORS)]


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


def _ticks_age_s(now_ms, then_ms):
    """Seconds between two ticks_ms() values, across the 2**30 ms wrap."""
    half = 1 << 29
    return max(0, ((now_ms - then_ms + half) % (1 << 30) - half) // 1000)


def _age_color(seconds):
    if seconds < 30 * 60:
        return OK
    if seconds < 6 * 3600:
        return WARN
    return MUTED


def node_rows(nodes, now_ms, filt="all", contacts=(), query=""):
    """Rows for the Nodes tab. filt: all, contacts (saved), chat, rptr, room, new (heard in
    the last hour and not a contact); query matches the name or hex id, any case. `nodes`
    come most recent first, as the manager lists them."""
    rows = []
    q = (query or "").strip().lower()
    for n in nodes:
        kind = _KINDS.get(n.get("type"), "other")
        age_s = _ticks_age_s(now_ms, n.get("heard_ms", now_ms))
        if filt == "new":
            if age_s >= 3600 or n.get("pubkey") in contacts:
                continue
        elif filt == "contacts":
            if n.get("pubkey") not in contacts:
                continue
        elif filt != "all" and kind != filt:
            continue
        if q and q not in (n.get("name") or "").lower() and not (n.get("id") or "").lower().startswith(q):
            continue
        hops = n.get("hops") or 0
        meta = "direct" if hops == 0 else ("1 hop" if hops == 1 else "%d hops" % hops)
        if n.get("snr") is not None:
            meta += " · SNR " + snr_text(n["snr"])
        rows.append({"pubkey": n.get("pubkey"), "hex": (n.get("id") or "??").upper(),
                     "kind": kind, "name": n.get("name") or "?", "age": age_text(age_s),
                     "age_color": _age_color(age_s), "meta": meta})
    return rows


_KIND_WORDS = {"chat": "companion", "rptr": "repeater", "room": "room server", "sensor": "sensor"}


def _via(path_hex, hops):
    """'3af1', 2 hops -> '3A › F1' (each repeater's hash prefix, in order)."""
    if not path_hex or not hops or len(path_hex) % hops:
        return ""
    step = len(path_hex) // hops
    return " › ".join(path_hex[i:i + step].upper() for i in range(0, len(path_hex), step))


def node_detail(n, now_ms):
    """Header, route line (lead, mono path, tail) and key-value fields for a node's
    detail screen."""
    kind = _KINDS.get(n.get("type"), "other")
    pk = (n.get("pubkey") or "").upper()
    hops = n.get("hops") or 0
    lead = "direct" if hops == 0 else ("1 hop" if hops == 1 else "%d hops" % hops)
    via = _via(n.get("path"), hops)
    tail = ""
    if n.get("snr") is not None:
        tail += " · SNR %s dB" % snr_text(n["snr"])
    age = age_text(_ticks_age_s(now_ms, n.get("heard_ms", now_ms)))
    tail += " · heard now" if age == "now" else " · heard %s ago" % age
    fields = [("Type", _KIND_WORDS.get(kind, kind)), ("Hops", str(hops))]
    if n.get("snr") is not None:
        fields.append(("Last SNR", snr_text(n["snr"]) + " dB"))
    if n.get("rssi") is not None:
        fields.append(("Last RSSI", _minus("%d" % n["rssi"]) + " dBm"))
    if n.get("lat") is not None and n.get("lon") is not None:
        fields.append(("Location", "%.4f, %.4f" % (n["lat"], n["lon"])))
    fields.append(("Signature", "verified" if n.get("verified") else "not checked"))
    return {"title": n.get("name") or pk[:8] or "?",
            "subtitle": "%s · %s…%s" % (_KIND_WORDS.get(kind, kind), pk[:4], pk[-4:]),
            "info": lead + tail,
            "route": (lead + " via " if via else lead, via, tail),
            "fields": fields, "pubkey": pk.lower()}


def radio_texts(st):
    """Strings for the Radio tab from manager.radio_stats()."""
    if not st.get("rx_on"):
        sub = "RX off"
    elif st.get("last_rx_s") is None:
        sub = "RX on · nothing heard yet"
    else:
        s = st["last_rx_s"]
        sub = "RX on · last packet %s ago" % ("%d s" % s if s < 60 else age_text(s))
    noise = st.get("noise_dbm")
    peak = st.get("peak_rssi_30m")
    return {"subtitle": sub,
            "noise": _minus("%d" % noise) if noise is not None else "—",
            "stats": [("Peak", _minus("%d" % peak) if peak is not None else "—"),
                      ("Packets", "%d/h" % st.get("packets_per_h", 0)),
                      ("TX air", "%.1f %%" % st.get("tx_air_pct", 0.0))]}


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
