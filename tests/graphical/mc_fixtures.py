"""Shared set-up for the app's graphical tests (copied next to MicroPythonOS's lib/ by
tools/run_graphical.sh). The manager runs in simulation mode on the desktop build; tests
seed its state directly and record the calls the screens make."""
import sys

APP = "com.confituurke.meshcore"
APP_DIR = "apps/" + APP
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)


def fresh_manager(setup_done=True, nickname="Kim"):
    """A new manager singleton with clean prefs, an identity and a name."""
    from mpos import SharedPreferences
    import meshcore_manager as mm
    for f in ("config.json", "dm_history.json", "channel_history.json", "unread.json"):
        ed = SharedPreferences(APP, filename=f).edit()
        ed.remove_all()
        ed.commit()
    mm.MeshCoreManager._instance = None
    m = mm.MeshCoreManager.get_instance()
    m.generate_identity()
    m.set_nickname(nickname)
    ed = SharedPreferences(APP).edit()
    ed.put_bool("setup_done", setup_done)
    ed.commit()
    return m


class Recorder:
    """Replaces manager methods with recorders: calls are kept in .calls."""

    def __init__(self, m, *names, result=True):
        self.calls = []
        for n in names:
            setattr(m, n, self._make(n, result))

    def _make(self, name, result):
        def f(*a, **kw):
            self.calls.append((name, a, kw))
            return result
        return f

    def names(self):
        return [c[0] for c in self.calls]
