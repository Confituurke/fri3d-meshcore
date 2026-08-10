"""Badge firmware / OS version requirements for MeshCore.

Hardware-independent, unit-testable off-badge -- deliberately free of `mpos` and `lvgl`
imports so the comparison logic can be tested in desktop CPython (the modules that talk to
the radio cannot be imported off-badge at all).

Why there is a minimum at all:

The SX1262's reset pin is wired only to the CH32 coprocessor, not to the ESP32-S3, so the
only way to hardware-reset a wedged radio is to write the CH32's config register (0x16)
twice -- assert reset, then release it.  Two consecutive I2C register writes is precisely
the pattern that crashes CH32 firmware v2.0.1: the coprocessor goes dark (black screen),
every subsequent I2C transaction returns ENODEV, and only a hard power-cycle recovers.
See MicroPythonOS#224 and Fri3dCamp/badge_2026_fw release v2.0.2, which fixes it.

MeshCore's watchdog resets the radio on its recovery path, so on v2.0.1 a badge that keeps
losing the radio can black-screen itself.  MicroPythonOS 0.16.2 auto-flashes coprocessor
2.0.2 at boot, so requiring the OS version and requiring the coprocessor version are two
views of the same requirement -- the coprocessor version is the one that actually matters
and the one we check, since a user can arrive at 2.0.2 by other routes.

There is no manifest field for any of this: mpos.app.App.from_manifest() parses only
name/publisher/descriptions/icon_url/download_url/fullname/version/category/activities/
services and silently drops everything else.  MicroPythonOS#223 is the open proposal.
Until it lands, the check has to happen at runtime -- see MeshCoreManager.coprocessor_status().
"""

# CH32 coprocessor firmware, read from mpos.io_expander.version (I2C register 0x00).
MIN_CH32_FW = (2, 0, 2)

# MicroPythonOS release, read from mpos.BuildInfo.version.release. Informational: it is the
# release that auto-flashes MIN_CH32_FW, so it is what we tell the user to install.
MIN_MPOS_RELEASE = (0, 16, 2)


def parse_release(s):
    """Parse a dotted version string into a tuple of ints; None if it is not one.

    Tolerates trailing junk on the last component ("0.16.2-dev" -> (0, 16, 2)) because
    MicroPythonOS development builds carry a suffix.
    """
    if isinstance(s, tuple):
        return s if all(isinstance(p, int) for p in s) else None
    if not isinstance(s, str):
        return None
    parts = []
    for chunk in s.strip().split("."):
        digits = ""
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        if not digits:
            return None
        parts.append(int(digits))
    return tuple(parts) if parts else None


def at_least(have, want):
    """True if version tuple `have` is >= `want`.

    Unknown (`have` is None) counts as NOT meeting the requirement: on a badge where the
    coprocessor version cannot be read we have no evidence the fix is present, and the
    consequence of guessing wrong is a black screen.  Callers decide whether "unknown"
    should even be asked about -- on non-fri3d hardware there is no coprocessor and the
    question does not apply.

    Tuples of different lengths compare as if the shorter were zero-padded, so
    (2, 0) < (2, 0, 2) and (2, 1) > (2, 0, 2).
    """
    if have is None:
        return False
    if isinstance(have, str):
        have = parse_release(have)
        if have is None:
            return False
    if not want:
        return True
    n = max(len(have), len(want))
    for i in range(n):
        h = have[i] if i < len(have) else 0
        w = want[i] if i < len(want) else 0
        if h != w:
            return h > w
    return True


def format_version(v):
    """Render a version tuple/string for display; '?' when unknown."""
    if v is None:
        return "?"
    if isinstance(v, str):
        return v
    return ".".join(str(p) for p in v)
