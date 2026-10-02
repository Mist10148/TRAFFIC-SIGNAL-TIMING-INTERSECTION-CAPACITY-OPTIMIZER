import customtkinter as ctk

from ui import theme


class Card(ctk.CTkFrame):
    # A bordered surface with a serif title. Put your own content in row 1 and below.
    def __init__(self, parent, title: str) -> None:
        super().__init__(
            parent, corner_radius=theme.RADIUS_CARD, border_width=1, height=0,
            fg_color=theme.color("surface"), border_color=theme.color("border"),
        )
        self.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self, text=title, anchor="w",
            font=theme.font(18, serif=True), text_color=theme.color("text"),
        ).grid(row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=theme.PAD_M)
