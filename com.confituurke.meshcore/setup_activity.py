"""First-run setup: name, radio preset, first advert."""

from mpos import Activity

import ui_theme as T


class SetupActivity(Activity):

    def onCreate(self):
        scr = T.make_screen()
        T.Header(scr, "Set up MeshCore")
        self.setContentView(scr)
