import customtkinter as ctk

from core.models import TimingResult
from core.visualizer import build_timeline, render_report, render_text
from ui import theme
from ui.widgets.banner import Banner
from ui.widgets.card import Card
from ui.widgets.phase_table import PhaseTable
from ui.widgets.stat_card import StatCard
from ui.widgets.timeline_canvas import TimelineCanvas
from ui.widgets.y_meter import YMeter

TWO_BY_TWO_BELOW_WIDTH = 760
RELAYOUT_DELAY_MS = 100
COPIED_MESSAGE_MS = 1500
TEXT_LINE_HEIGHT = 20


def formula_lines(result: TimingResult, saturation_flow: float, lost_time: int) -> list[str]:
    # The same numbers the app used, written out so a student can check them by hand.
    lines = []
    for p in result.phases:
        lines.append(f"Y({p.code}) = {p.volume:g} / {saturation_flow:g} = {p.flow_ratio:.4f}")

    ratios = " + ".join(f"{p.flow_ratio:.4f}" for p in result.phases)
    lines.append(f"Y = {ratios} = {result.total_flow_ratio:.4f}")
    lines.append(f"L = {result.active_count} x {lost_time} = {result.total_lost_time} s")
    lines.append(
        f"Co = (1.5 x {result.total_lost_time} + 5) / (1 - {result.total_flow_ratio:.4f})"
        f" = {result.raw_cycle:.2f} s"
    )
    lines.append(f"C = {result.cycle} s (rounded up to the next 5 s)")
    lines.append(f"Te = {result.cycle} - {result.total_lost_time} = {result.effective_green} s")
    for p in result.phases:
        exact = p.flow_ratio / result.total_flow_ratio * result.effective_green
        lines.append(
            f"g({p.code}) = ({p.flow_ratio:.4f} / {result.total_flow_ratio:.4f})"
            f" x {result.effective_green} = {exact:.2f} -> {p.green} s"
        )
    return lines


class ResultsScreen(ctk.CTkFrame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.report_text = ""
        self.stat_columns: int | None = None
        self._relayout_job: str | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=0, column=0, sticky="nsew", padx=(theme.PAD_L, theme.PAD_S), pady=(theme.PAD_S, 0))
        self.body.columnconfigure(0, weight=1)

        self._build_header()
        self.warning_area = ctk.CTkFrame(self.body, fg_color="transparent", height=0)
        self.warning_area.grid(row=1, column=0, sticky="ew")
        self.warning_area.columnconfigure(0, weight=1)
        self._build_stat_cards()
        self._build_cards()
        self._build_actions()

        self.bind("<Configure>", self._on_resize)
        # Keyboard shortcuts live on the window, but only act while this screen is showing.
        window = self.winfo_toplevel()
        window.bind("<Escape>", self._on_escape, add="+")
        window.bind("<Control-c>", self._on_ctrl_c, add="+")

    # Building the pieces

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.body, fg_color="transparent", height=0)
        header.grid(row=0, column=0, sticky="ew", pady=(theme.PAD_S, theme.PAD_M))
        ctk.CTkLabel(
            header, text="Model / Inputs / Results", anchor="w",
            font=theme.font(11), text_color=theme.color("text_muted"),
        ).pack(fill="x")
        self.title = ctk.CTkLabel(
            header, text="", anchor="w",
            font=theme.font(28, serif=True), text_color=theme.color("text"),
        )
        self.title.pack(fill="x")
        self.subtitle = ctk.CTkLabel(
            header, text="", anchor="w",
            font=theme.font(13), text_color=theme.color("text_muted"),
        )
        self.subtitle.pack(fill="x")

    def _build_stat_cards(self) -> None:
        self.stat_area = ctk.CTkFrame(self.body, fg_color="transparent", height=0)
        self.stat_area.grid(row=2, column=0, sticky="ew", pady=(theme.PAD_M, 0))

        self.cycle_card = StatCard(self.stat_area, "Optimal cycle length (Co)", "", "", accent="accent")
        self.green_card = StatCard(self.stat_area, "Total effective green (Te)", "", "")
        self.flow_card = StatCard(self.stat_area, "Total flow ratio (Y)", "", "")
        self.meter: YMeter = self.flow_card.add_extra(YMeter)
        self.lost_card = StatCard(self.stat_area, "Total lost time (L)", "", "")
        self.stat_cards = [self.cycle_card, self.green_card, self.flow_card, self.lost_card]

    def _build_cards(self) -> None:
        table_card = Card(self.body, "Phase green times")
        table_card.grid(row=3, column=0, sticky="ew", pady=(theme.PAD_M, 0))
        self.table = PhaseTable(table_card)
        self.table.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))

        timeline_card = Card(self.body, "Phase timeline")
        timeline_card.grid(row=4, column=0, sticky="ew", pady=(theme.PAD_M, 0))
        self.timeline_view = TimelineCanvas(timeline_card)
        self.timeline_view.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))

        text_card = Card(self.body, "Text diagram")
        text_card.grid(row=5, column=0, sticky="ew", pady=(theme.PAD_M, 0))
        self.diagram = ctk.CTkTextbox(
            text_card, wrap="none", font=theme.font(12, mono=True),
            fg_color=theme.color("surface_alt"), text_color=theme.color("text"),
            corner_radius=theme.RADIUS_INPUT,
        )
        self.diagram.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))

        formula_card = Card(self.body, "Formulas used")
        formula_card.grid(row=6, column=0, sticky="ew", pady=theme.PAD_M)
        self.formulas = ctk.CTkLabel(
            formula_card, text="", anchor="w", justify="left",
            font=theme.font(12, mono=True), text_color=theme.color("text"),
        )
        self.formulas.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))

    def _build_actions(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_M)

        self.copy_button = ctk.CTkButton(
            bar, text="Copy results", width=140, height=36, font=theme.font(13, "bold"),
            corner_radius=theme.RADIUS_INPUT, fg_color=theme.color("accent"),
            hover_color=theme.color("accent_hover"), text_color=theme.color("on_accent"),
            command=self._copy_report,
        )
        self.copy_button.pack(side="left", padx=(0, theme.PAD_S))
        ctk.CTkButton(
            bar, text="Edit inputs", width=110, height=36, font=theme.font(13),
            corner_radius=theme.RADIUS_INPUT, fg_color="transparent", border_width=1,
            border_color=theme.color("border"), hover_color=theme.color("surface_alt"),
            text_color=theme.color("text"), command=lambda: self.app.show("inputs"),
        ).pack(side="left", padx=(0, theme.PAD_S))
        ctk.CTkButton(
            bar, text="New calculation", width=0, height=36, font=theme.font(13),
            fg_color="transparent", hover_color=theme.color("surface_alt"),
            text_color=theme.color("accent"), command=self.app.reset,
        ).pack(side="left")

    # Showing the screen

    def on_show(self) -> None:
        result = self.app.result
        data = self.app.timing_input
        if result is None or data is None:
            self.app.show("inputs")
            return

        timeline = build_timeline(result, data.lost_time)
        self.report_text = render_report(result, timeline, data.saturation_flow, data.lost_time)

        self.title.configure(text=f"{result.model.name} results")
        self.subtitle.configure(
            text=f"Saturation flow {data.saturation_flow:g} veh/hr/lane, "
                 f"lost time {data.lost_time} s per phase"
        )
        self._show_warnings(result.warnings)
        self._fill_stat_cards(result, data.lost_time)
        self.table.set(result)
        self.timeline_view.draw(timeline)
        self._fill_diagram(timeline, render_text(timeline))
        self.formulas.configure(text="\n".join(formula_lines(result, data.saturation_flow, data.lost_time)))
        self._layout_stat_cards(force=True)

    def _show_warnings(self, warnings: list[str]) -> None:
        for child in self.warning_area.winfo_children():
            child.destroy()
        for row, text in enumerate(warnings):
            Banner(self.warning_area, "warning", text).grid(
                row=row, column=0, sticky="ew", pady=(0, theme.PAD_S),
            )

    def _fill_stat_cards(self, result: TimingResult, lost_time: int) -> None:
        self.cycle_card.update_values(
            f"{result.cycle} s", f"Webster raw: {result.raw_cycle:.2f} s, rounded up to 5 s",
        )
        self.green_card.update_values(
            f"{result.effective_green} s", f"Cycle minus {result.total_lost_time} s lost time",
        )
        self.flow_card.update_values(
            f"{result.total_flow_ratio:.4f}", f"{result.active_count} active phases",
        )
        self.meter.set(result.total_flow_ratio)
        self.lost_card.update_values(
            f"{result.total_lost_time} s", f"{result.active_count} phases x {lost_time} s",
        )

    def _fill_diagram(self, timeline, text: str) -> None:
        self.diagram.configure(state="normal", height=(len(timeline.rows) + 1) * TEXT_LINE_HEIGHT + 16)
        self.diagram.delete("1.0", "end")
        self.diagram.insert("1.0", text)
        self.diagram.configure(state="disabled")

    # Layout

    def _on_resize(self, _event) -> None:
        if self._relayout_job:
            self.after_cancel(self._relayout_job)
        self._relayout_job = self.after(RELAYOUT_DELAY_MS, self._layout_stat_cards)

    def _layout_stat_cards(self, force: bool = False) -> None:
        self._relayout_job = None
        columns = 2 if self.winfo_width() < TWO_BY_TWO_BELOW_WIDTH else 4
        if columns == self.stat_columns and not force:
            return
        self.stat_columns = columns

        # Columns that are no longer used must drop out of the equal-width group too.
        for index in range(4):
            used = index < columns
            self.stat_area.columnconfigure(
                index, weight=1 if used else 0, uniform="stats" if used else "",
            )
        for index, card in enumerate(self.stat_cards):
            row, column = divmod(index, columns)
            card.grid(row=row, column=column, sticky="nsew", padx=theme.PAD_S // 2, pady=theme.PAD_S // 2)

    # Actions

    def _copy_report(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.report_text)
        self.copy_button.configure(text="Copied")
        self.after(COPIED_MESSAGE_MS, lambda: self.copy_button.configure(text="Copy results"))

    def _on_escape(self, _event) -> None:
        if self.app.current == "results":
            self.app.show("inputs")

    def _on_ctrl_c(self, _event) -> None:
        if self.app.current != "results":
            return
        # If the user selected some text in the diagram, let the normal copy happen.
        if self.diagram.tag_ranges("sel"):
            return
        self._copy_report()
