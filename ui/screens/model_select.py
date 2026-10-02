import customtkinter as ctk

from core.models import MODELS
from ui import theme
from ui.widgets.banner import Banner
from ui.widgets.model_card import ModelCard

WIDE_LAYOUT_MIN_WIDTH = 900
RELAYOUT_DELAY_MS = 100


class ModelSelectScreen(ctk.CTkFrame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.columns = 0
        self._relayout_job: str | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        ctk.CTkLabel(
            self, text="Choose a phase model", anchor="w",
            font=theme.font(28, serif=True), text_color=theme.color("text"),
        ).grid(row=0, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_L, 0))
        ctk.CTkLabel(
            self, text="Pick the signal phasing that matches your intersection.", anchor="w",
            font=theme.font(13), text_color=theme.color("text_muted"),
        ).grid(row=1, column=0, sticky="ew", padx=theme.PAD_L, pady=(4, theme.PAD_M))

        self.grid_area = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_area.grid(row=2, column=0, sticky="nsew", padx=theme.PAD_L)
        self.cards = [ModelCard(self.grid_area, model, self._choose) for model in MODELS.values()]

        Banner(
            self, "info", "Phases with a volume of 0 are left out of the cycle.",
        ).grid(row=3, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_M)

        self.bind("<Configure>", self._on_resize)
        self._layout_cards(3)

    def _choose(self, model_key: str) -> None:
        # Keep what the user typed if they pick the same model again.
        if model_key != self.app.model_key:
            self.app.form_values = {}
        self.app.model_key = model_key
        self.app.show("inputs")

    def _on_resize(self, _event) -> None:
        # Wait for the resize to settle so we don't re-grid on every pixel.
        if self._relayout_job:
            self.after_cancel(self._relayout_job)
        self._relayout_job = self.after(RELAYOUT_DELAY_MS, self._relayout)

    def _relayout(self) -> None:
        self._relayout_job = None
        wide = self.winfo_width() >= WIDE_LAYOUT_MIN_WIDTH
        self._layout_cards(3 if wide else 2)

    def _layout_cards(self, columns: int) -> None:
        if columns == self.columns:
            return
        self.columns = columns
        for index in range(3):
            self.grid_area.columnconfigure(index, weight=0, uniform="")
        for index in range(columns):
            self.grid_area.columnconfigure(index, weight=1, uniform="cards")
        for index, card in enumerate(self.cards):
            row, column = divmod(index, columns)
            card.grid(
                row=row, column=column, sticky="nsew",
                padx=theme.PAD_S, pady=theme.PAD_S,
            )
