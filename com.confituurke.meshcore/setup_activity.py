"""First-run setup in three steps (name, radio preset, first advert), in one activity whose
content is swapped per step. Opened with extra step=2 it only changes the radio preset."""

import lvgl as lv

from mpos import Activity, Intent, MposKeyboard, SharedPreferences

import meshcore_presets
import ui_theme as T
from meshcore_manager import MeshCoreManager, MESHCORE_APP

FOOTNOTE = ("Everyone you want to reach must use the same frequency, bandwidth, "
            "spreading factor and coding rate.")
BWS = ("62.5", "125", "250", "500")
SFS = ("7", "8", "9", "10", "11", "12")
CRS = ("5", "6", "7", "8")


class SetupActivity(Activity):

    def onCreate(self):
        self.mgr = MeshCoreManager.get_instance()
        if not self.mgr.has_identity():
            self.mgr.generate_identity()
        extras = self.getIntent().extras if self.getIntent() else None
        self._only_preset = bool(extras and extras.get("step") == 2)
        current = self.mgr.radio_preset()
        self._preset = current.get("id") or meshcore_presets.DEFAULT_PRESET
        self._custom = dict(current) if self._preset == "custom" else None
        self._nick = self.mgr.nickname()
        self._advert = True
        self._step = 2 if self._only_preset else 1
        scr = T.make_screen()
        scr.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        top = T.box(scr, T.W, lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN)
        top.set_style_pad_top(T.TOP_PAD + 8, lv.PART.MAIN)
        top.set_style_pad_hor(T.EDGE, lv.PART.MAIN)
        self.step_label = T.label(top, "", "small", T.ACCENT)
        self.title = T.label(top, "", "title", T.TEXT)
        self.body = T.box(scr, T.W, 1, lv.FLEX_FLOW.COLUMN)
        self.body.set_flex_grow(1)
        self.body.add_flag(lv.obj.FLAG.SCROLLABLE)
        self.body.set_scroll_dir(lv.DIR.VER)
        self.body.set_style_pad_hor(T.EDGE, lv.PART.MAIN)
        self.body.set_style_pad_row(10, lv.PART.MAIN)
        self.body.set_style_pad_top(12, lv.PART.MAIN)
        foot = T.box(scr, T.W, 64, lv.FLEX_FLOW.ROW)
        foot.set_style_pad_hor(T.EDGE, lv.PART.MAIN)
        foot.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        self.back_chip = T.Chip(foot, "Back", self.back, h=44)
        self.next_chip = T.Chip(foot, "Next", self.next, selected=True, h=44)
        self._kb = MposKeyboard(scr)
        self._kb.set_size(T.W, 188)
        self._kb.add_flag(lv.obj.FLAG.HIDDEN)
        self._name = None
        self.show()
        self.setContentView(scr)

    # --- steps ----------------------------------------------------------- #
    def show(self):
        self.body.clean()
        self._name = None
        if self._only_preset:
            self.step_label.set_text("Radio")
        else:
            self.step_label.set_text("Step %d of 3" % self._step)
        if self._step == 1:
            self._show_name()
        elif self._step == 2:
            self._show_preset()
        else:
            self._show_hello()
        if self._only_preset or self._step == 1:
            self.back_chip.obj.add_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.back_chip.obj.remove_flag(lv.obj.FLAG.HIDDEN)
        self.next_chip.set_text("Save" if self._only_preset else ("Finish" if self._step == 3 else "Next"))

    def _textarea(self, parent, text, placeholder=""):
        ta = lv.textarea(parent)
        ta.set_one_line(True)
        ta.set_text(text)
        ta.set_placeholder_text(placeholder)
        ta.set_width(lv.pct(100))
        ta.set_style_text_font(T.font("body"), lv.PART.MAIN)
        ta.set_style_bg_color(T.color(T.SURFACE2), lv.PART.MAIN)
        ta.set_style_text_color(T.color(T.TEXT), lv.PART.MAIN)
        ta.set_style_border_width(0, lv.PART.MAIN)
        ta.set_style_radius(10, lv.PART.MAIN)
        ta.add_event_cb(lambda e: self._kb.set_textarea(ta), lv.EVENT.FOCUSED, None)
        return ta

    def _show_name(self):
        self.title.set_text("What should others see?")
        T.label(self.body, "Your name on the mesh", "small", T.MUTED)
        self._name = self._textarea(self.body, self._nick)
        self._kb.set_textarea(self._name)
        T.label(self.body, "You can change it later in Settings.", "small", T.MUTED)

    def _show_preset(self):
        self.title.set_text("Which mesh are you on?")
        T.label(self.body, "Radio preset", "small", T.MUTED)
        self._cards = {}
        options = [(p["id"], p["name"], meshcore_presets.describe(p),
                    "Recommended" if p["id"] == meshcore_presets.DEFAULT_PRESET else "")
                   for p in meshcore_presets.PRESETS]
        options.append(("custom", "Custom…", "set every value yourself", ""))
        for pid, name, detail, tag in options:
            card = T.box(self.body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN, "surface")
            card.set_style_pad_all(12, lv.PART.MAIN)
            card.set_style_border_width(2, lv.PART.MAIN)
            row = T.box(card, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW)
            row.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            T.label(row, name, "strong", T.TEXT)
            if tag:
                T.label(row, tag, "small", T.ACCENT)
            T.label(card, detail, "mono", T.MUTED)
            T.clickable(card, lambda pid=pid: self.pick(pid))
            self._cards[pid] = card
        self._custom_box = T.box(self.body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN)
        self._custom_box.set_style_pad_row(6, lv.PART.MAIN)
        c = self._custom or {"freq": 869.618, "bw": 62.5, "sf": 8, "cr": 8}
        T.label(self._custom_box, "Frequency (MHz)", "small", T.MUTED)
        self._freq = self._textarea(self._custom_box, "%.3f" % float(c["freq"]))
        self._bw = self._dropdown("Bandwidth (kHz)", BWS, str(c["bw"]).rstrip("0").rstrip(".") if "." in str(c["bw"]) else str(c["bw"]))
        self._sf = self._dropdown("Spreading factor", SFS, str(c["sf"]))
        self._cr = self._dropdown("Coding rate 4/…", CRS, str(c["cr"]))
        T.label(self.body, FOOTNOTE, "small", T.MUTED, lv.label.LONG_MODE.WRAP).set_width(lv.pct(100))
        self.pick(self._preset)

    def _dropdown(self, title, options, value):
        T.label(self._custom_box, title, "small", T.MUTED)
        dd = lv.dropdown(self._custom_box)
        dd.set_options("\n".join(options))
        dd.set_width(lv.pct(100))
        if value in options:
            dd.set_selected(options.index(value))
        return dd

    def pick(self, pid):
        self._preset = pid
        for k, card in self._cards.items():
            card.set_style_border_color(T.color(T.ACCENT if k == pid else T.LINE), lv.PART.MAIN)
        if pid == "custom":
            self._custom_box.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            self._custom_box.add_flag(lv.obj.FLAG.HIDDEN)

    def _show_hello(self):
        self.title.set_text("Say hello")
        T.label(self.body, "An advert tells nodes around you who you are, so they can "
                "message you.", "body", T.TEXT, lv.label.LONG_MODE.WRAP).set_width(lv.pct(100))
        cb = lv.checkbox(self.body)
        cb.set_text("Send a flood advert now")
        cb.set_style_text_font(T.font("body"), lv.PART.MAIN)
        cb.set_style_text_color(T.color(T.TEXT), lv.PART.MAIN)
        if self._advert:
            cb.add_state(lv.STATE.CHECKED)
        cb.add_event_cb(lambda e: self._set_advert(cb.has_state(lv.STATE.CHECKED)),
                        lv.EVENT.VALUE_CHANGED, None)

    def _set_advert(self, on):
        self._advert = on

    # --- navigation ------------------------------------------------------ #
    def _collect(self):
        if self._name is not None:
            self._nick = self._name.get_text().strip() or self._nick
        if self._step == 2 and self._preset == "custom":
            try:
                self._custom = {"freq": float(self._freq.get_text()),
                                "bw": float(BWS[self._bw.get_selected()]),
                                "sf": int(SFS[self._sf.get_selected()]),
                                "cr": int(CRS[self._cr.get_selected()])}
            except ValueError:
                self._custom = None

    def _preset_value(self):
        if self._preset == "custom":
            return self._custom
        return self._preset

    def next(self):
        self._collect()
        if self._only_preset:
            if self._preset_value():
                self.mgr.set_radio_preset(self._preset_value())
            self.finish()
            return
        if self._step < 3:
            self._step += 1
            self.show()
            return
        self.mgr.set_nickname(self._nick)
        if self._preset_value():
            self.mgr.set_radio_preset(self._preset_value())
        ed = SharedPreferences(MESHCORE_APP).edit()
        ed.put_bool("setup_done", True)
        ed.commit()
        if not self.mgr.is_running():
            self.mgr.start()
        if self._advert:
            self.mgr.advertise(flood=True)
        import main_activity
        self.startActivity(Intent(activity_class=main_activity.MeshCoreHome))
        self.finish()

    def back(self):
        self._collect()
        if self._step > 1 and not self._only_preset:
            self._step -= 1
            self.show()

    def onBackPressed(self, screen):
        if self._step > 1 and not self._only_preset:
            self.back()
            return True
        return False
