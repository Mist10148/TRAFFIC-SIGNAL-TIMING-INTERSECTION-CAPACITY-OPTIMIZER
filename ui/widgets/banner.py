import customtkinter as ctk

from ui import theme

# kind -> (background token, bar and icon token, icon letter)
KINDS = {
    "info": ("info_bg", "text_muted", "i"),
    "warning": ("warning_bg", "signal_amber", "!"),
    "error": ("error_bg", "signal_red", "x"),
}


# Space taken by the bar, icon and padding to the left and right of the text.
BANNER_TEXT_INSET = 80


class Banner(ctk.CTkFrame):
    def __init__(self, parent, kind: str, text: str) -> None:
        # height=0 lets the banner shrink to its text instead of the 200 px default.
        super().__init__(parent, corner_radius=theme.RADIUS_INPUT, height=0)
        self.columnconfigure(2, weight=1)

        self.bar = ctk.CTkFrame(self, width=4, height=1, corner_radius=0)
        self.bar.grid(row=0, column=0, sticky="ns")

        self.icon = ctk.CTkLabel(
            self, text="", width=22, height=22, corner_radius=11,
            font=theme.font(12, "bold"), text_color=theme.color("on_accent"),
        )
        self.icon.grid(row=0, column=1, padx=(theme.PAD_M, theme.PAD_S), pady=theme.PAD_M, sticky="n")

        self.message = ctk.CTkLabel(
            self, text="", anchor="w", justify="left",
            font=theme.font(13), text_color=theme.color("text"),
        )
        self.message.grid(row=0, column=2, padx=(0, theme.PAD_M), pady=theme.PAD_M, sticky="ew")
        # Wrap against the banner's own width. Using the label's width would feed
        # back on itself, since wrapping changes the label's size.
        self.bind("<Configure>", self._wrap_to_width)

        self.set(kind, text)

    def set(self, kind: str, text: str) -> None:
        background, accent, letter = KINDS[kind]
        self.configure(fg_color=theme.color(background))
        self.bar.configure(fg_color=theme.color(accent))
        self.icon.configure(text=letter, fg_color=theme.color(accent))
        self.message.configure(text=text)

    def show(self) -> None:
        self.grid()

    def hide(self) -> None:
        self.grid_remove()

    def _wrap_to_width(self, event) -> None:
        self.message.configure(wraplength=max(event.width - BANNER_TEXT_INSET, 100))
