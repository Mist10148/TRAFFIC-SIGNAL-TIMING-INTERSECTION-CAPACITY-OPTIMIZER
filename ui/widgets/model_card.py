import tkinter as tk
from typing import Callable

import customtkinter as ctk

from core.models import PhaseModel
from ui import theme

DIAGRAM_WIDTH = 120
DIAGRAM_HEIGHT = 56
# The mini diagram just repeats green, amber, red to hint at how many phases there are.
BAR_TOKENS = ("signal_green", "signal_amber", "signal_red")


class ModelCard(ctk.CTkFrame):
    def __init__(self, parent, model: PhaseModel, on_select: Callable[[str], None]) -> None:
        super().__init__(
            parent,
            corner_radius=theme.RADIUS_CARD,
            height=0,
            border_width=1,
            fg_color=theme.color("surface"),
            border_color=theme.color("border"),
        )
        self.model = model
        self.on_select = on_select
        self.highlighted = False

        self.diagram = tk.Canvas(
            self, width=DIAGRAM_WIDTH, height=DIAGRAM_HEIGHT, highlightthickness=0, bd=0,
        )
        self.diagram.pack(anchor="w", padx=theme.PAD_M, pady=(theme.PAD_M, theme.PAD_S))

        self.name = ctk.CTkLabel(
            self, text=model.name, anchor="w",
            font=theme.font(18, serif=True), text_color=theme.color("text"),
        )
        self.name.pack(fill="x", padx=theme.PAD_M)

        self.description = ctk.CTkLabel(
            self, text=model.description, anchor="w", justify="left", wraplength=220,
            font=theme.font(13), text_color=theme.color("text_muted"),
        )
        self.description.pack(fill="x", padx=theme.PAD_M, pady=(4, theme.PAD_S))

        self.inputs = ctk.CTkLabel(
            self, text=f"{model.phase_count} volume inputs", anchor="w",
            font=theme.font(12, "bold"), text_color=theme.color("accent"),
        )
        self.inputs.pack(fill="x", padx=theme.PAD_M, pady=(0, theme.PAD_M))

        self._draw_diagram()
        self._wire_events()

    def _wire_events(self) -> None:
        # Clicks and hovers land on the labels and canvas too, so wire them all.
        for widget in (self, self.diagram, self.name, self.description, self.inputs):
            widget.bind("<Button-1>", self._select)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            # A hand cursor tells people the whole card can be clicked.
            widget.configure(cursor="hand2")

        # Make the card reachable with Tab, and selectable with Enter or Space.
        tk.Frame.configure(self, takefocus=True)
        self.bind("<FocusIn>", lambda _: self._highlight(True))
        self.bind("<FocusOut>", lambda _: self._highlight(False))
        self.bind("<Return>", self._select)
        self.bind("<space>", self._select)

    def _select(self, _event=None) -> None:
        self.focus_set()
        self.on_select(self.model.key)

    def _on_enter(self, _event) -> None:
        self._highlight(True)

    def _on_leave(self, event) -> None:
        # Moving onto a child label also fires Leave on the card; ignore that.
        under_pointer = self.winfo_containing(event.x_root, event.y_root)
        if under_pointer is not None and str(under_pointer).startswith(str(self)):
            return
        if self.focus_get() is not self:
            self._highlight(False)

    def _highlight(self, on: bool) -> None:
        self.highlighted = on
        self.configure(
            border_color=theme.color("accent" if on else "border"),
            border_width=2 if on else 1,
        )

    def _draw_diagram(self) -> None:
        self.diagram.configure(bg=theme.resolve("surface"))
        self.diagram.delete("all")

        count = self.model.phase_count
        gap = 3
        bar_width = (DIAGRAM_WIDTH - gap * (count - 1)) / count
        for i in range(count):
            left = i * (bar_width + gap)
            token = BAR_TOKENS[i % len(BAR_TOKENS)]
            self.diagram.create_rectangle(
                left, 8, left + bar_width, DIAGRAM_HEIGHT - 8,
                fill=theme.resolve(token), outline="",
            )

    def _set_appearance_mode(self, mode_string: str) -> None:
        # The canvas can't switch colors on its own, so redraw when the theme flips.
        super()._set_appearance_mode(mode_string)
        self._draw_diagram()
