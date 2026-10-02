import customtkinter as ctk

from ui import theme


class StatCard(ctk.CTkFrame):
    def __init__(self, parent, caption: str, value: str, subtitle: str, accent: str | None = None) -> None:
        super().__init__(
            parent, corner_radius=theme.RADIUS_CARD, border_width=1, height=0,
            fg_color=theme.color("surface"), border_color=theme.color("border"),
        )
        self.columnconfigure(0, weight=1)

        # A thin colored bar along the top marks the headline number.
        if accent:
            ctk.CTkFrame(
                self, height=3, corner_radius=0, fg_color=theme.color(accent),
            ).grid(row=0, column=0, sticky="ew", padx=theme.PAD_M)

        ctk.CTkLabel(
            self, text=caption.upper(), anchor="w",
            font=theme.font(11), text_color=theme.color("text_muted"),
        ).grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_M, 0))

        self.value = ctk.CTkLabel(
            self, text=value, anchor="w",
            font=theme.font(32, "bold", mono=True),
            text_color=theme.color(accent or "text"),
        )
        self.value.grid(row=2, column=0, sticky="ew", padx=theme.PAD_M)

        self.subtitle = ctk.CTkLabel(
            self, text=subtitle, anchor="w", justify="left",
            font=theme.font(12), text_color=theme.color("text_muted"),
        )
        self.subtitle.grid(row=3, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))
        self.bind("<Configure>", self._wrap_subtitle)

        # Other widgets (like the Y meter) can be dropped in here, under the subtitle.
        self.extra = ctk.CTkFrame(self, fg_color="transparent", height=0)

    def update_values(self, value: str, subtitle: str) -> None:
        self.value.configure(text=value)
        self.subtitle.configure(text=subtitle)

    def add_extra(self, widget_factory):
        # Pass a function that builds the widget inside self.extra.
        self.extra.grid(row=4, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))
        widget = widget_factory(self.extra)
        widget.pack(fill="x")
        self.subtitle.grid_configure(pady=(0, theme.PAD_S))
        return widget

    def _wrap_subtitle(self, event) -> None:
        # Wrap against the card width; the label's own width would feed back on itself.
        self.subtitle.configure(wraplength=max(self.winfo_width() - 2 * theme.PAD_M, 80))
