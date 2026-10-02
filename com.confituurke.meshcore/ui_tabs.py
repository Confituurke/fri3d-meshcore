"""The four tabs of the main screen. Each is built when first shown and torn down when
another tab takes its place, so only one tab's widgets exist at a time."""

import lvgl as lv

import ui_theme as T


class Tab:
    title = ""

    def __init__(self):
        self.activity = None
        self.mgr = None
        self.root = None

    def build(self, parent, activity):
        """Fill `parent` (480 x 424, above the tab bar)."""
        self.activity = activity
        self.mgr = activity.mgr
        self.root = parent
        T.Header(parent, self.title)

    def on_event(self, event, data):
        """A manager event, already on the LVGL thread."""

    def destroy(self):
        """Called before the tab's widgets are deleted (stop timers here)."""


class ChatsTab(Tab):
    title = "Chats"


class NodesTab(Tab):
    title = "Nodes"


class RadioTab(Tab):
    title = "Radio"


class SettingsTab(Tab):
    title = "Settings"
