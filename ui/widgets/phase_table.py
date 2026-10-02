import customtkinter as ctk

from core.models import TimingResult
from ui import theme

# Phase code, label, then the four number columns.
HEADERS = ("Phase", "Volume (veh/hr)", "Flow ratio Yi", "Green (s)", "Share of Te")
# Each row gets its own dot color so the table can match the legend elsewhere.
DOT_TOKENS = (
    "accent", "signal_green", "signal_amber", "signal_red",
    "text_muted", "accent_hover", "border", "text",
)


class PhaseTable(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent", height=0)
        self.columnconfigure(0, weight=3)
        for column in range(1, len(HEADERS)):
            self.columnconfigure(column, weight=1)

    def set(self, result: TimingResult) -> None:
        for child in self.winfo_children():
            child.destroy()

        self._row(0, HEADERS, "surface_alt", bold=True)
        for index, phase in enumerate(result.phases):
            shade = "surface" if index % 2 == 0 else "surface_alt"
            cells = (
                None,
                f"{phase.volume:g}",
                f"{phase.flow_ratio:.4f}",
                str(phase.green),
                f"{phase.green_share * 100:.1f}%",
            )
            self._row(index + 1, cells, shade, phase=phase, dot=DOT_TOKENS[index % len(DOT_TOKENS)])

        totals = (
            "Total",
            f"{sum(p.volume for p in result.phases):g}",
            f"{result.total_flow_ratio:.4f}",
            str(result.effective_green),
            "100.0%",
        )
        self._row(len(result.phases) + 1, totals, "surface_alt", bold=True)

    def _row(self, row: int, cells, shade: str, bold: bool = False, phase=None, dot: str | None = None) -> None:
        for column, text in enumerate(cells):
            holder = ctk.CTkFrame(self, corner_radius=0, height=34, fg_color=theme.color(shade))
            holder.grid(row=row, column=column, sticky="nsew")
            holder.grid_propagate(False)
            holder.columnconfigure(1 if column == 0 else 0, weight=1)

            if column == 0:
                self._phase_cell(holder, text, phase, dot, bold)
                continue

            ctk.CTkLabel(
                holder, text=text, anchor="e",
                font=theme.font(12, "bold" if bold else "normal", mono=True),
                text_color=theme.color("text"),
            ).grid(row=0, column=0, sticky="e", padx=theme.PAD_M)

    def _phase_cell(self, holder, text, phase, dot, bold) -> None:
        if phase is None:
            # Header and totals rows have no dot, so the text starts where the dot would.
            ctk.CTkLabel(
                holder, text=text, anchor="w",
                font=theme.font(12, "bold"), text_color=theme.color("text"),
            ).grid(row=0, column=0, columnspan=2, sticky="w", padx=theme.PAD_M)
            return

        ctk.CTkFrame(
            holder, width=8, height=8, corner_radius=4, fg_color=theme.color(dot),
        ).grid(row=0, column=0, padx=(theme.PAD_M, 6))
        ctk.CTkLabel(
            holder, text=f"{phase.code}  {phase.label}", anchor="w",
            font=theme.font(12), text_color=theme.color("text"),
        ).grid(row=0, column=1, sticky="w")
