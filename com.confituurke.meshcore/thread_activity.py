"""Conversation screens: a channel thread and a direct-message thread."""

from mpos import Activity

import ui_theme as T


class ThreadActivity(Activity):

    def onCreate(self):
        scr = T.make_screen()
        T.Header(scr, "Thread", back=self.finish)
        self.setContentView(scr)


class ChannelChatActivity(ThreadActivity):
    pass


class DMChatActivity(ThreadActivity):
    pass
