"""Radio tab: is the radio listening, how noisy is the channel, adverts, and the preset."""

import lvgl as lv

from mpos import Intent

import ui_model
import ui_theme as T
import setup_activity
from meshcore_presets import DEFAULT_POWER
from ui_tabs import Tab

REFRESH_MS = 5000
CHART_POINTS = 180


class RadioTab(Tab):
    title = "Radio"

    def build(self, parent, activity):
        self.activity = activity
        self.mgr = activity.mgr
        self.header = T.Header(parent, "Radio", "")
        body = T.box(parent, T.W, 1, lv.FLEX_FLOW.COLUMN)
        body.set_flex_grow(1)
        body.add_flag(lv.obj.FLAG.SCROLLABLE)
        body.set_scroll_dir(lv.DIR.VER)
        body.set_style_pad_hor(T.EDGE, lv.PART.MAIN)
        body.set_style_pad_bottom(16, lv.PART.MAIN)
        body.set_style_pad_row(12, lv.PART.MAIN)

        card = T.box(body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN, "surface")
        card.set_style_pad_all(14, lv.PART.MAIN)
        top = T.box(card, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW)
        top.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.END, lv.FLEX_ALIGN.END)
        top.set_style_pad_column(10, lv.PART.MAIN)
        self.noise = T.label(top, "—", "big", T.TEXT)
        T.label(top, "dBm noise floor", "small", T.MUTED).set_style_pad_bottom(8, lv.PART.MAIN)
        self.chart = lv.chart(card)
        self.chart.set_size(lv.pct(100), 70)
        self.chart.set_type(lv.chart.TYPE.LINE)
        self.chart.set_point_count(CHART_POINTS)
        self.chart.set_div_line_count(0, 0)
        self.chart.set_axis_range(lv.chart.AXIS.PRIMARY_Y, -125, -60)
        self.chart.set_style_bg_opa(lv.OPA.TRANSP, lv.PART.MAIN)
        self.chart.set_style_border_width(0, lv.PART.MAIN)
        self.chart.set_style_size(0, 0, lv.PART.INDICATOR)
        self.chart.set_style_line_width(2, lv.PART.ITEMS)
        self.series = self.chart.add_series(T.color(T.ACCENT), lv.chart.AXIS.PRIMARY_Y)
        T.label(card, "last 30 min", "small", T.MUTED)

        chips = T.box(body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW)
        chips.set_style_pad_column(8, lv.PART.MAIN)
        self.peak = T.Chip(chips, "", lambda: None)
        self.packets = T.Chip(chips, "", lambda: None)
        self.tx_air = T.Chip(chips, "", lambda: None)

        self._advert_button(body, "Zero-hop advert", "neighbours only", False)
        self._advert_button(body, "Flood advert", "whole mesh", True)

        preset = T.box(body, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.COLUMN, "surface")
        preset.set_style_pad_all(14, lv.PART.MAIN)
        preset.set_style_pad_row(4, lv.PART.MAIN)
        title, detail, air = ui_model.preset_summary(self.mgr.radio_preset(), DEFAULT_POWER)
        row = T.box(preset, lv.pct(100), lv.SIZE_CONTENT, lv.FLEX_FLOW.ROW)
        row.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        T.label(row, title, "strong", T.TEXT)
        T.Chip(row, "Change", self.change_preset)
        T.label(preset, detail, "mono", T.MUTED, lv.label.LONG_MODE.WRAP).set_width(lv.pct(100))
        T.label(preset, air, "small", T.MUTED)

        self._timer = lv.timer_create(lambda t: self.refresh(), REFRESH_MS, None)
        self.refresh()

    def _advert_button(self, parent, title, hint, flood):
        b = T.box(parent, lv.pct(100), 52, lv.FLEX_FLOW.ROW, "surface")
        b.set_style_pad_hor(14, lv.PART.MAIN)
        b.set_style_pad_column(10, lv.PART.MAIN)
        b.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        T.symbol(b, lv.SYMBOL.WIFI, T.ACCENT)
        T.label(b, title, "strong", T.TEXT)
        T.label(b, hint, "small", T.MUTED)
        T.clickable(b, lambda: self.advert(flood))

    def advert(self, flood):
        ok, err = self.mgr.advertise(flood=flood)
        if ok:
            self.header.set_subtitle("Flood advert sent" if flood else "Zero-hop advert sent")
        else:
            self.header.set_subtitle(err or "Advert failed")

    def change_preset(self):
        intent = Intent(activity_class=setup_activity.SetupActivity)
        intent.putExtra("step", 2)
        self.activity.startActivity(intent)

    def refresh(self):
        st = self.mgr.radio_stats()
        t = ui_model.radio_texts(st)
        self.header.set_subtitle(t["subtitle"])
        self.noise.set_text(t["noise"])
        self.peak.set_text(t["peak"])
        self.packets.set_text(t["packets"])
        self.tx_air.set_text(t["tx_air"])
        series = st.get("noise_series") or []
        self.chart.set_all_values(self.series, lv.CHART_POINT_NONE)
        for v in series[-CHART_POINTS:]:
            self.chart.set_next_value(self.series, int(v))
        self.chart.refresh()

    def destroy(self):
        if self._timer is not None:
            self._timer.delete()
            self._timer = None
