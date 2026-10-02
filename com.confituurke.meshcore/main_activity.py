"""Main screen: four tabs (Chats, Nodes, Radio, Settings) over a bottom tab bar.

Every screen module is imported here, at load time: the app directory is only on sys.path
while MicroPythonOS imports this entrypoint."""

import lvgl as lv

from mpos import Activity, Intent, SharedPreferences

import ui_theme as T
import ui_tabs
import tab_chats
import tab_nodes
import tab_radio
import thread_activity  # noqa: F401  (notification intents name its classes)
import setup_activity
from meshcore_manager import MeshCoreManager, MESHCORE_APP


class MeshCoreHome(Activity):
    TAB_LABELS = ("Chats", "Nodes", "Radio", "Settings")

    def tab_classes(self):
        return (tab_chats.ChatsTab, tab_nodes.NodesTab, tab_radio.RadioTab, ui_tabs.SettingsTab)

    def onCreate(self):
        self.mgr = MeshCoreManager.get_instance()
        self._tab = None
        self._tab_index = -1
        if not SharedPreferences(MESHCORE_APP).get_bool("setup_done", False):
            self.startActivity(Intent(activity_class=setup_activity.SetupActivity))
            self.finish()
            return
        if not self.mgr.is_running():
            self.mgr.start()           # listen while the app is open
        scr = T.make_screen()
        self.content = T.box(scr, T.W, T.H - T.TABBAR_H, lv.FLEX_FLOW.COLUMN)
        self.tabbar = T.TabBar(scr, self.TAB_LABELS, self.select)
        extras = self.getIntent().extras if self.getIntent() else None
        start = (extras or {}).get("tab", 0) if isinstance(extras, dict) else 0
        self.select(start)
        self.setContentView(scr)

    def select(self, idx):
        if idx == self._tab_index:
            return
        if self._tab is not None:
            try:
                self._tab.destroy()
            except Exception as e:
                print("MeshCoreHome: tab destroy error:", repr(e))
        self.content.clean()
        self._tab_index = idx
        self._tab = self.tab_classes()[idx]()
        self._tab.build(self.content, self)
        self.tabbar.set_active(idx)
        self.refresh_badge()

    def refresh_badge(self):
        total = 0
        for name in self.mgr.get_channel_names():
            total += self.mgr.get_unread(name)
        for c in self.mgr.get_contacts():
            total += self.mgr.get_unread(c["pubkey"])
        self.tabbar.set_badge(0, total)

    def onResume(self, screen):
        super().onResume(screen)
        self.mgr.add_subscriber(self._on_event)

    def onPause(self, screen):
        self.mgr.remove_subscriber(self._on_event)
        super().onPause(screen)

    def onDestroy(self, screen):
        if self._tab is not None:
            self._tab.destroy()
        if not self.mgr.is_service_enabled():
            self.mgr.stop()            # no background service: the radio rests

    def _on_event(self, event, data):
        self.update_ui_threadsafe_if_foreground(self._dispatch, event, data)

    def _dispatch(self, event, data):
        if event in ("message", "dm", "unread", "contacts", "channels"):
            self.refresh_badge()
        if self._tab is not None:
            self._tab.on_event(event, data)
