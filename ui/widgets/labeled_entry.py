import re
from typing import Callable

import customtkinter as ctk

from core.validation import parse_number
from ui import theme

# Digits with at most one . or , and an optional minus at the front.
NUMBER_SHAPE = re.compile(r"^-?[0-9]*[.,]?[0-9]*$")
ENTRY_HEIGHT = 38


class LabeledEntry(ctk.CTkFrame):
    def __init__(self, parent, label: str, unit: str, hint: str, placeholder: str = "0") -> None:
        super().__init__(parent, fg_color="transparent", height=0)
        self.hint = hint
        self.columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent", height=0)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            top, text=label, anchor="w",
            font=theme.font(13), text_color=theme.color("text"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            top, text=unit, anchor="e",
            font=theme.font(11), text_color=theme.color("text_muted"),
        ).grid(row=0, column=1, sticky="e")

        self.entry = ctk.CTkEntry(
            self, height=ENTRY_HEIGHT, corner_radius=theme.RADIUS_INPUT, border_width=1,
            placeholder_text=placeholder, font=theme.font(13),
            fg_color=theme.color("surface"), border_color=theme.color("border"),
            text_color=theme.color("text"), placeholder_text_color=theme.color("text_muted"),
        )
        self.entry.grid(row=1, column=0, sticky="ew", pady=(4, 2))

        self.note = ctk.CTkLabel(
            self, text=hint, anchor="w", justify="left",
            font=theme.font(11), text_color=theme.color("text_muted"),
        )
        self.note.grid(row=2, column=0, sticky="ew")
        # Wrap against the whole field width, not the label itself, to avoid a resize loop.
        self.bind("<Configure>", lambda e: self.note.configure(wraplength=max(e.width - 8, 80)))

        self.status = "normal"
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<KeyRelease>", self._check_shape, add="+")

    def get(self) -> str:
        return self.entry.get()

    def set(self, text: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def focus(self) -> None:
        self.entry.focus_set()

    def bind_change(self, callback: Callable[[], None]) -> None:
        self.entry.bind("<KeyRelease>", lambda _: callback(), add="+")

    def bind_enter(self, callback: Callable[[], None]) -> None:
        self.entry.bind("<Return>", lambda _: callback())

    def set_error(self, message: str) -> None:
        self.status = "error"
        self._paint_border(focused=False)
        self.note.configure(text=message, text_color=theme.color("signal_red"))

    def set_highlight(self) -> None:
        # A softer amber outline: "this one is part of the problem", not "this is invalid".
        self.status = "highlight"
        self._paint_border(focused=False)

    def clear_error(self) -> None:
        self.status = "normal"
        self._paint_border(focused=False)
        self.note.configure(text=self.hint, text_color=theme.color("text_muted"))

    def _paint_border(self, focused: bool) -> None:
        # Errors keep their color while focused, so the focus ring never hides a problem.
        colors = {"error": "signal_red", "highlight": "signal_amber"}
        if self.status in colors:
            token = colors[self.status]
        else:
            token = "accent" if focused else "border"
        self.entry.configure(border_color=theme.color(token), border_width=2 if focused else 1)

    def _on_focus_in(self, _event) -> None:
        self.entry.select_range(0, "end")
        self._paint_border(focused=True)

    def _on_focus_out(self, _event) -> None:
        self._paint_border(focused=False)
        self._trim()

    def _trim(self) -> None:
        text = self.entry.get()
        # Only trim stray spaces; never rewrite what the user typed.
        if parse_number(text) is not None and text != text.strip():
            self.set(text.strip())

    def _check_shape(self, _event) -> None:
        # Editing means they're fixing it, so drop the old message first.
        self.clear_error()
        self._paint_border(focused=True)
        text = self.entry.get().strip()
        if not NUMBER_SHAPE.match(text):
            self.set_error("Numbers only")
            self._paint_border(focused=True)
