import customtkinter as ctk

from ui import theme

HEAVY_MARK = 0.85
TRACK_HEIGHT = 14


class YMeter(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent", height=0)
        self.columnconfigure(0, weight=1)

        self.caption = ctk.CTkLabel(
            self, text="Y = --", anchor="w",
            font=theme.font(13, "bold", mono=True), text_color=theme.color("text"),
        )
        self.caption.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            self, text="Capacity", anchor="e",
            font=theme.font(11), text_color=theme.color("text_muted"),
        ).grid(row=0, column=1, sticky="e")

        self.track = ctk.CTkFrame(
            self, height=TRACK_HEIGHT, corner_radius=TRACK_HEIGHT // 2,
            fg_color=theme.color("surface_alt"),
        )
        self.track.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.fill = ctk.CTkFrame(self.track, corner_radius=TRACK_HEIGHT // 2)

        # A small tick where the intersection starts to get heavy.
        marks = ctk.CTkFrame(self, fg_color="transparent", height=24)
        marks.grid(row=2, column=0, columnspan=2, sticky="ew")
        ctk.CTkFrame(
            marks, width=2, height=6, corner_radius=0, fg_color=theme.color("text_muted"),
        ).place(relx=HEAVY_MARK, y=0, anchor="n")
        ctk.CTkLabel(
            marks, text="heavy", height=16, font=theme.font(10), text_color=theme.color("text_muted"),
        ).place(relx=HEAVY_MARK, y=8, anchor="n")

        self.set_error()

    def set(self, value: float) -> None:
        self.caption.configure(text=f"Y = {value:.4f}")
        self._draw_fill(min(value, 1.0), self._color_for(value))

    def set_error(self) -> None:
        # Not enough valid numbers yet, so show an empty bar.
        self.caption.configure(text="Y = --")
        self._draw_fill(0, "signal_green")

    def _draw_fill(self, fraction: float, token: str) -> None:
        if fraction <= 0:
            self.fill.place_forget()
            return
        self.fill.configure(fg_color=theme.color(token))
        self.fill.place(x=0, y=0, relheight=1, relwidth=fraction)

    @staticmethod
    def _color_for(value: float) -> str:
        if value >= 0.95:
            return "signal_red"
        if value >= 0.70:
            return "signal_amber"
        return "signal_green"
