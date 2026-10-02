import tkinter as tk

import customtkinter as ctk

from core.visualizer import Timeline, scale_segments
from ui import theme

ROW_HEIGHT = 34
ROW_STEP = 44
LABEL_WIDTH = 90
PLOT_LEFT = 100
PLOT_RIGHT_MARGIN = 16
TOP_MARGIN = 8
AXIS_SPACE = 48
MIN_TEXT_WIDTH = 36
REDRAW_DELAY_MS = 50
RED_STRENGTH = 0.35

KIND_NAMES = {"G": "Green", "YR": "Yellow / All-Red", "R": "Red"}
KIND_LETTERS = {"G": "G", "YR": "Y/R", "R": "R"}


def blend(foreground: str, background: str, amount: float) -> str:
    # Tk has no transparency, so a "faded" color is mixed into the background by hand.
    def channel(color: str, start: int) -> int:
        return int(color[start:start + 2], 16)

    mixed = [
        round(channel(foreground, i) * amount + channel(background, i) * (1 - amount))
        for i in (1, 3, 5)
    ]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def tick_step(cycle: int) -> int:
    if cycle <= 60:
        return 5
    if cycle <= 150:
        return 10
    return 25


class TimelineCanvas(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent", height=0)
        self.columnconfigure(0, weight=1)
        self.timeline: Timeline | None = None
        # Each hit is (left, top, right, bottom, tooltip text) in canvas pixels.
        self.hits: list[tuple[int, int, int, int, str]] = []
        self._redraw_job: str | None = None

        self._build_legend()
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, height=ROW_STEP + AXIS_SPACE)
        self.canvas.grid(row=1, column=0, sticky="ew", pady=(theme.PAD_S, 0))
        self.canvas.bind("<Configure>", self._schedule_redraw)
        self.canvas.bind("<Motion>", self._show_tooltip)
        self.canvas.bind("<Leave>", lambda _: self.canvas.delete("tip"))

    def _build_legend(self) -> None:
        legend = ctk.CTkFrame(self, fg_color="transparent", height=0)
        legend.grid(row=0, column=0, sticky="w")
        for token, text in (
            ("signal_green", "Green"),
            ("signal_amber", "Yellow / All-Red"),
            ("signal_red", "Red"),
        ):
            ctk.CTkFrame(
                legend, width=12, height=12, corner_radius=3, fg_color=theme.color(token),
            ).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                legend, text=text, font=theme.font(11), text_color=theme.color("text_muted"),
            ).pack(side="left", padx=(0, theme.PAD_M))

    def draw(self, timeline: Timeline) -> None:
        self.timeline = timeline
        self.canvas.configure(height=len(timeline.rows) * ROW_STEP + AXIS_SPACE)
        self._redraw()

    def _schedule_redraw(self, _event=None) -> None:
        # Wait for the resize to settle so dragging the window stays smooth.
        if self._redraw_job:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(REDRAW_DELAY_MS, self._redraw)

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        self._redraw()

    def _redraw(self) -> None:
        self._redraw_job = None
        self.canvas.configure(bg=theme.resolve("surface"))
        self.canvas.delete("all")
        self.hits = []

        plot_width = self.canvas.winfo_width() - PLOT_LEFT - PLOT_RIGHT_MARGIN
        if self.timeline is None or plot_width < 50:
            return

        self._draw_rows(plot_width)
        self._draw_phase_starts(plot_width)
        self._draw_axis(plot_width)

    def _segment_colors(self, kind: str) -> tuple[str, str]:
        # Returns (fill color, text color) for a segment kind.
        if kind == "G":
            return theme.resolve("signal_green"), theme.resolve("on_accent")
        if kind == "YR":
            # Dark text reads much better than white on amber.
            return theme.resolve("signal_amber"), theme.resolve("text")
        faded = blend(theme.resolve("signal_red"), theme.resolve("surface"), RED_STRENGTH)
        return faded, theme.resolve("text")

    def _rows_bottom(self) -> int:
        return TOP_MARGIN + len(self.timeline.rows) * ROW_STEP - (ROW_STEP - ROW_HEIGHT)

    def _draw_rows(self, plot_width: int) -> None:
        cycle = self.timeline.cycle
        for index, row in enumerate(self.timeline.rows):
            top = TOP_MARGIN + index * ROW_STEP
            bottom = top + ROW_HEIGHT
            self.canvas.create_text(
                LABEL_WIDTH, (top + bottom) / 2, text=row.code, anchor="e",
                font=theme.font(12, mono=True), fill=theme.resolve("text"),
            )

            scaled = scale_segments(row, plot_width, cycle)
            for segment, (kind, x, width) in zip(row.segments, scaled):
                left = PLOT_LEFT + x
                right = left + width
                fill, text_color = self._segment_colors(kind)
                self.canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="")

                end = segment.start + segment.duration
                name = KIND_NAMES[kind]
                self.hits.append((
                    left, top, right, bottom,
                    f"{row.code}: {name} {segment.duration}s (t = {segment.start} to {end}s)",
                ))
                if width >= MIN_TEXT_WIDTH:
                    self.canvas.create_text(
                        (left + right) / 2, (top + bottom) / 2,
                        text=f"{KIND_LETTERS[kind]} {segment.duration}s",
                        font=theme.font(11, "bold"), fill=text_color,
                    )

    def _draw_phase_starts(self, plot_width: int) -> None:
        # A dashed line where each phase's green begins.
        for row in self.timeline.rows:
            green = next(s for s in row.segments if s.kind == "G")
            x = PLOT_LEFT + round(green.start / self.timeline.cycle * plot_width)
            self.canvas.create_line(
                x, TOP_MARGIN, x, self._rows_bottom(), dash=(3, 3), fill=theme.resolve("text_muted"),
            )

    def _draw_axis(self, plot_width: int) -> None:
        cycle = self.timeline.cycle
        step = tick_step(cycle)
        y = self._rows_bottom() + 6

        self.canvas.create_line(PLOT_LEFT, y, PLOT_LEFT + plot_width, y, fill=theme.resolve("border"))
        # Skip a regular tick that would sit right next to the final one at the cycle length.
        times = [t for t in range(0, cycle, step) if cycle - t >= step / 2] + [cycle]
        for t in times:
            x = PLOT_LEFT + round(t / cycle * plot_width)
            self.canvas.create_line(x, y, x, y + 5, fill=theme.resolve("text_muted"))
            self.canvas.create_text(
                x, y + 8, text=str(t), anchor="n",
                font=theme.font(10), fill=theme.resolve("text_muted"),
            )
        self.canvas.create_text(
            PLOT_LEFT + plot_width, y + 26, text="seconds", anchor="e",
            font=theme.font(10), fill=theme.resolve("text_muted"),
        )

    def _show_tooltip(self, event) -> None:
        self.canvas.delete("tip")
        for left, top, right, bottom, text in self.hits:
            if left <= event.x < right and top <= event.y <= bottom:
                self._draw_tooltip(event.x, event.y, text)
                return

    def _draw_tooltip(self, x: int, y: int, text: str) -> None:
        label = self.canvas.create_text(
            x + 12, y - 14, text=text, anchor="sw", tags="tip",
            font=theme.font(11), fill=theme.resolve("text"),
        )
        left, top, right, bottom = self.canvas.bbox(label)
        # Nudge it left if it would run off the right edge.
        shift = max(0, right + 6 - self.canvas.winfo_width())
        self.canvas.move(label, -shift, 0)
        box = self.canvas.create_rectangle(
            left - 6 - shift, top - 3, right + 6 - shift, bottom + 3, tags="tip",
            fill=theme.resolve("surface_alt"), outline=theme.resolve("border"),
        )
        self.canvas.tag_raise(label, box)
