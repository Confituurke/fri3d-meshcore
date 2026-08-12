"""Desktop CPython tests for meshcore_version.

Run:  PYTHONPATH=org.fri3d.meshcore python3 tests/test_meshcore_version.py
"""

from meshcore_version import (
    MIN_CH32_FW, MIN_MPOS_RELEASE,
    parse_release, at_least, format_version,
)


def _assert(c, m=""):
    if not c:
        raise AssertionError(m)


def test_minimums_are_the_documented_ones():
    # The CH32 release that fixed "2 consecutive i2c register writes" (badge_2026_fw v2.0.2).
    _assert(MIN_CH32_FW == (2, 0, 2), MIN_CH32_FW)
    # A semantic floor, deliberately not a downloadable release: 0.16.1 carried coprocessor
    # 2.0.1 and 0.17.0 carried 2.0.3, so the first OS that could carry a fixed one sits
    # between them. What matters is which real releases clear it -- see the at_least tests.
    _assert(MIN_MPOS_RELEASE == (0, 16, 2), MIN_MPOS_RELEASE)


def test_parse_release_basic():
    _assert(parse_release("0.16.2") == (0, 16, 2))
    _assert(parse_release("2.0.1") == (2, 0, 1))
    _assert(parse_release("1") == (1,))
    _assert(parse_release(" 0.16.1 ") == (0, 16, 1))


def test_parse_release_dev_suffix():
    # MicroPythonOS development builds carry a suffix on the last component.
    _assert(parse_release("0.16.2-dev") == (0, 16, 2), parse_release("0.16.2-dev"))
    _assert(parse_release("0.17.0rc1") == (0, 17, 0))


def test_parse_release_rejects_garbage():
    for bad in ("", "   ", "abc", "0..2", ".1.2", None, 3, 4.2, b"0.16.2"):
        _assert(parse_release(bad) is None, repr(bad))


def test_parse_release_passes_through_tuples():
    _assert(parse_release((2, 0, 2)) == (2, 0, 2))
    _assert(parse_release((2, "0", 2)) is None)


def test_at_least_equal_and_newer():
    _assert(at_least((2, 0, 2), MIN_CH32_FW))
    _assert(at_least((2, 0, 3), MIN_CH32_FW))
    _assert(at_least((2, 1, 0), MIN_CH32_FW))
    _assert(at_least((3, 0, 0), MIN_CH32_FW))


def test_at_least_older():
    # The firmware that black-screens the badge on back-to-back config writes.
    _assert(not at_least((2, 0, 1), MIN_CH32_FW))
    _assert(not at_least((2, 0, 0), MIN_CH32_FW))
    _assert(not at_least((1, 2, 2), MIN_CH32_FW))
    _assert(not at_least((0, 0, 0), MIN_CH32_FW))


def test_at_least_unknown_is_not_supported():
    # Unknown must not count as meeting the requirement: the cost of guessing wrong is a
    # black screen. Callers decide whether the question applies at all.
    _assert(not at_least(None, MIN_CH32_FW))


def test_at_least_accepts_version_strings():
    _assert(at_least("0.16.2", MIN_MPOS_RELEASE))
    _assert(at_least("0.17.0", MIN_MPOS_RELEASE))
    _assert(not at_least("0.16.1", MIN_MPOS_RELEASE))
    _assert(not at_least("nonsense", MIN_MPOS_RELEASE))


def test_at_least_uneven_lengths():
    # Short tuples compare as if zero-padded.
    _assert(not at_least((2, 0), (2, 0, 2)))
    _assert(at_least((2, 1), (2, 0, 2)))
    _assert(at_least((2, 0, 2), (2, 0)))
    _assert(at_least((2, 0, 2, 1), (2, 0, 2)))
    _assert(at_least((2, 0, 2), ()))


def test_format_version():
    _assert(format_version((2, 0, 2)) == "2.0.2")
    _assert(format_version(None) == "?")
    _assert(format_version("0.16.2") == "0.16.2")


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print("ok   %s" % t.__name__)
    print("\n%d/%d tests passed" % (len(tests), len(tests)))


if __name__ == "__main__":
    _run_all()
