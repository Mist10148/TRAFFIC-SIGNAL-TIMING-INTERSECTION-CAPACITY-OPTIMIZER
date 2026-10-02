import customtkinter as ctk

from core.calculator import compute_timing
from core.models import MODELS
from core.validation import parse_number, validate_inputs
from ui import theme
from ui.widgets.banner import Banner
from ui.widgets.labeled_entry import LabeledEntry
from ui.widgets.y_meter import YMeter

STACK_BELOW_WIDTH = 760
RELAYOUT_DELAY_MS = 100
GLOBAL_KEYS = ("saturation_flow", "lost_time")

# One filled-in example per model, so people can see the app work in one click.
# These are the reference cases from the PRD. Phases not listed get 0.
EXAMPLES = {
    "2": {"NS": "850", "EW": "600"},
    "3": {"MajThru": "800", "MajLeft": "300", "MinStem": "450"},
    "4": {"NSL": "200", "NST": "700", "EWL": "150", "EWT": "600"},
    "6": {"NBL": "250", "ArtThru": "900", "MinEB": "500"},
    "8": {"NBL": "150", "SBT": "600", "EBL": "150", "WBT": "500"},
}
EXAMPLE_SATURATION = "1900"
EXAMPLE_LOST_TIME = "4"


class InputFormScreen(ctk.CTkFrame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.built_for: str | None = None
        self.entries: dict[str, LabeledEntry] = {}
        self.stacked: bool | None = None
        self._relayout_job: str | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._build_footer()
        for key in GLOBAL_KEYS:
            self._wire_entry(self.entries[key])
        self.bind("<Configure>", self._on_resize)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_M))
        header.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Model / Inputs", anchor="w",
            font=theme.font(11), text_color=theme.color("text_muted"),
        ).grid(row=0, column=0, sticky="w")
        self.title = ctk.CTkLabel(
            header, text="", anchor="w",
            font=theme.font(28, serif=True), text_color=theme.color("text"),
        )
        self.title.grid(row=1, column=0, sticky="w")
        ctk.CTkButton(
            header, text="Change model", width=0, height=32, font=theme.font(13),
            fg_color="transparent", hover_color=theme.color("surface_alt"),
            text_color=theme.color("accent"),
            command=lambda: self.app.show("model"),
        ).grid(row=0, column=1, rowspan=2, sticky="e")

    def _build_body(self) -> None:
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=(theme.PAD_L, theme.PAD_S))

        self.card_a = self._card("Intersection parameters")
        self.entries["saturation_flow"] = LabeledEntry(
            self.card_a, "Saturation flow rate", "veh/hr/lane",
            "Typical 1800 to 1900", placeholder="1900",
        )
        self.entries["lost_time"] = LabeledEntry(
            self.card_a, "Lost time per phase", "s",
            "Amber + all-red, whole seconds", placeholder="4",
        )
        for row, key in enumerate(GLOBAL_KEYS, start=1):
            self.entries[key].grid(row=row, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))

        self.card_b = self._card("Traffic volumes")
        self.volume_grid = ctk.CTkFrame(self.card_b, fg_color="transparent")
        self.volume_grid.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M)
        for column in range(2):
            self.volume_grid.columnconfigure(column, weight=1, uniform="volumes")

    def _card(self, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self.body, corner_radius=theme.RADIUS_CARD, border_width=1, height=0,
            fg_color=theme.color("surface"), border_color=theme.color("border"),
        )
        card.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card, text=title, anchor="w",
            font=theme.font(18, serif=True), text_color=theme.color("text"),
        ).grid(row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=theme.PAD_M)
        return card

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(
            self, corner_radius=theme.RADIUS_CARD, border_width=1, height=0,
            fg_color=theme.color("surface"), border_color=theme.color("border"),
        )
        footer.grid(row=2, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_M)
        footer.columnconfigure(0, weight=1)

        self.meter = YMeter(footer)
        self.meter.grid(row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_M, 0))
        self.count_label = ctk.CTkLabel(
            footer, text="", anchor="w",
            font=theme.font(12), text_color=theme.color("text_muted"),
        )
        self.count_label.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M)

        self.banner = Banner(footer, "error", "")
        self.banner.grid(row=2, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_S, 0))
        self.banner.hide()

        self.buttons = ctk.CTkFrame(footer, fg_color="transparent")
        self.buttons.grid(row=3, column=0, sticky="ew", padx=theme.PAD_M, pady=theme.PAD_M)
        ctk.CTkButton(
            self.buttons, text="Calculate", width=130, height=36, font=theme.font(13, "bold"),
            corner_radius=theme.RADIUS_INPUT, fg_color=theme.color("accent"),
            hover_color=theme.color("accent_hover"), text_color=theme.color("on_accent"),
            command=self._on_calculate,
        ).pack(side="right")
        ctk.CTkButton(
            self.buttons, text="Reset", width=90, height=36, font=theme.font(13),
            corner_radius=theme.RADIUS_INPUT, fg_color="transparent", border_width=1,
            border_color=theme.color("border"), hover_color=theme.color("surface_alt"),
            text_color=theme.color("text"), command=self._on_reset,
        ).pack(side="left", padx=(0, theme.PAD_S))
        ctk.CTkButton(
            self.buttons, text="Fill example", width=0, height=36, font=theme.font(13),
            fg_color="transparent", hover_color=theme.color("surface_alt"),
            text_color=theme.color("accent"), command=self._on_fill_example,
        ).pack(side="left")

    # Showing the screen and building the fields

    def on_show(self) -> None:
        model = MODELS[self.app.model_key]
        self.title.configure(text=f"{model.name} inputs")
        if self.built_for != model.key:
            self._rebuild_volumes(model.key)
        self._restore_values()
        self._clear_feedback()
        self._update_live_feedback()
        self._layout_cards(force=True)

    def _rebuild_volumes(self, model_key: str) -> None:
        for key in [k for k in self.entries if k not in GLOBAL_KEYS]:
            self.entries.pop(key).destroy()

        for index, phase in enumerate(MODELS[model_key].phases):
            entry = LabeledEntry(self.volume_grid, phase.label, "veh/hr", phase.hint)
            row, column = divmod(index, 2)
            entry.grid(row=row, column=column, sticky="ew", padx=theme.PAD_S, pady=(0, theme.PAD_M))
            self.entries[phase.code] = entry
            self._wire_entry(entry)
        self.built_for = model_key

    def _wire_entry(self, entry: LabeledEntry) -> None:
        entry.bind_change(self._on_change)
        entry.bind_enter(self._on_calculate)

    def _restore_values(self) -> None:
        # Global values survive a model switch; keys that no longer exist are simply dropped.
        for key, entry in self.entries.items():
            entry.set(self.app.form_values.get(key, ""))

    # Layout

    def _on_resize(self, _event) -> None:
        if self._relayout_job:
            self.after_cancel(self._relayout_job)
        self._relayout_job = self.after(RELAYOUT_DELAY_MS, self._layout_cards)

    def _layout_cards(self, force: bool = False) -> None:
        self._relayout_job = None
        stacked = self.winfo_width() < STACK_BELOW_WIDTH
        if stacked == self.stacked and not force:
            return
        self.stacked = stacked

        self.card_a.grid_forget()
        self.card_b.grid_forget()
        self.body.columnconfigure(0, weight=1)
        self.body.columnconfigure(1, weight=0 if stacked else 1)
        if stacked:
            self.card_a.grid(row=0, column=0, sticky="new", pady=(0, theme.PAD_M))
            self.card_b.grid(row=1, column=0, sticky="new")
        else:
            self.card_a.grid(row=0, column=0, sticky="new", padx=(0, theme.PAD_S))
            self.card_b.grid(row=0, column=1, sticky="new", padx=(theme.PAD_S, 0))

    # Live feedback

    def _on_change(self) -> None:
        self.app.form_values = {key: entry.get() for key, entry in self.entries.items()}
        # Any edit makes an old result out of date, so Results waits for the next Calculate.
        if self.app.result is not None:
            self.app.result = None
            self.app.update_nav()
        self._update_live_feedback()

    def _update_live_feedback(self) -> None:
        saturation = parse_number(self.entries["saturation_flow"].get())
        phases = MODELS[self.built_for].phases

        volumes = []
        for phase in phases:
            value = parse_number(self.entries[phase.code].get())
            if value is not None:
                volumes.append(max(value, 0))

        active = sum(1 for v in volumes if v > 0)
        self.count_label.configure(text=f"{active} of {len(phases)} phases active")

        if saturation and saturation > 0 and volumes:
            self.meter.set(sum(v / saturation for v in volumes))
        else:
            self.meter.set_error()

    def _clear_feedback(self) -> None:
        self.banner.hide()
        for entry in self.entries.values():
            entry.clear_error()

    # Buttons

    def _on_reset(self) -> None:
        for entry in self.entries.values():
            entry.set("")
        self._clear_feedback()
        self._on_change()

    def _on_fill_example(self) -> None:
        example = EXAMPLES[self.built_for]
        self.entries["saturation_flow"].set(EXAMPLE_SATURATION)
        self.entries["lost_time"].set(EXAMPLE_LOST_TIME)
        for phase in MODELS[self.built_for].phases:
            self.entries[phase.code].set(example.get(phase.code, "0"))
        self._clear_feedback()
        self._on_change()

    # Calculate and the two retry loops

    def _on_calculate(self) -> None:
        self._clear_feedback()
        try:
            self._calculate()
        except (ValueError, ZeroDivisionError):
            # Safety net only. Validation should already have caught anything odd.
            self._show_error("Unexpected input problem. Check the values and try again.")

    def _calculate(self) -> None:
        raw = {key: entry.get() for key, entry in self.entries.items()}
        timing_input, errors = validate_inputs(self.app.model_key, raw)

        if errors:
            self._show_field_errors(errors)
            return

        result = compute_timing(timing_input)
        if result.oversaturated:
            self._show_oversaturation(result)
            return

        self.app.timing_input = timing_input
        self.app.result = result
        self.app.show("results")

    def _show_field_errors(self, errors) -> None:
        # Nothing is cleared here: the user keeps everything they typed and just fixes the marked fields.
        volume_keys = [k for k in self.entries if k not in GLOBAL_KEYS]
        for error in errors:
            targets = volume_keys if error.field == "volumes" else [error.field]
            for key in targets:
                self.entries[key].set_error(error.message)

        marked = {key for error in errors for key in (volume_keys if error.field == "volumes" else [error.field])}
        first = next(key for key in self.entries if key in marked)
        self.entries[first].focus()
        self._show_error(f"Please fix {len(errors)} field(s) to continue.")

    def _show_oversaturation(self, result) -> None:
        busiest = sorted(result.phases, key=lambda p: p.flow_ratio, reverse=True)[:2]
        names = ", ".join(f"{p.code} ({p.flow_ratio:.3f})" for p in busiest)
        self._show_error(
            f"{result.message} Largest demand: {names}. "
            "Reduce volumes or add capacity, then try again."
        )
        self.meter.set(result.total_flow_ratio)
        for phase in busiest:
            self.entries[phase.code].set_highlight()

    def _show_error(self, text: str) -> None:
        self.banner.set("error", text)
        self.banner.show()
