import customtkinter as ctk

from core.models import TimingInput, TimingResult
from ui import theme
from ui.screens.model_select import ModelSelectScreen

WINDOW_WIDTH = 1120
WINDOW_HEIGHT = 720
SIDEBAR_WIDTH = 220
NAV_HEIGHT = 36


class FlowApp(ctk.CTk):
    def __init__(self) -> None:
        # Both of these have to be set before the window exists.
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=theme.color("bg"))

        self.title("FLOW | Traffic Signal Timing Optimizer")
        self.minsize(960, 640)
        self._center_window()

        # State shared by every screen.
        self.model_key: str | None = None
        self.form_values: dict[str, str] = {}
        self.result: TimingResult | None = None
        self.timing_input: TimingInput | None = None

        self.columnconfigure(0, weight=0, minsize=SIDEBAR_WIDTH)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.current: str | None = None
        self._build_sidebar()
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.screens: dict[str, ctk.CTkFrame] = {
            "model": ModelSelectScreen(self.content, self),
            "inputs": self._placeholder("Inputs: coming in Phase 4"),
            "results": self._placeholder("Results: coming in Phase 5"),
        }
        self.show("model")

    def _center_window(self) -> None:
        x = (self.winfo_screenwidth() - WINDOW_WIDTH) // 2
        y = (self.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{max(x, 0)}+{max(y, 0)}")

    def _placeholder(self, text: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(
            frame, text=text, font=theme.font(18, serif=True), text_color=theme.color("text_muted"),
        ).place(relx=0.5, rely=0.5, anchor="center")
        return frame

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(
            self, width=SIDEBAR_WIDTH, corner_radius=0, fg_color=theme.color("surface_alt"),
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.rowconfigure(2, weight=1)

        ctk.CTkLabel(
            sidebar, text="FLOW", anchor="w",
            font=theme.font(24, "bold", serif=True), text_color=theme.color("accent"),
        ).grid(row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_L, 0))
        ctk.CTkLabel(
            sidebar, text="Signal Timing Optimizer", anchor="w",
            font=theme.font(11), text_color=theme.color("text_muted"),
        ).grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_L))

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.grid(row=2, column=0, sticky="new", padx=theme.PAD_S)
        nav.columnconfigure(0, weight=1)
        self.nav_buttons = {
            "model": self._nav_button(nav, "New calculation", self.reset),
            "inputs": self._nav_button(nav, "Inputs", lambda: self.show("inputs")),
            "results": self._nav_button(nav, "Results", lambda: self.show("results")),
        }
        for row, button in enumerate(self.nav_buttons.values()):
            button.grid(row=row, column=0, sticky="ew", pady=2)

        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=theme.PAD_M, pady=theme.PAD_M)
        bottom.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            bottom, text="Appearance", anchor="w",
            font=theme.font(11), text_color=theme.color("text_muted"),
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        appearance = ctk.CTkSegmentedButton(
            bottom, values=["Light", "Dark", "System"], font=theme.font(11),
            command=lambda mode: ctk.set_appearance_mode(mode.lower()),
            fg_color=theme.color("border"),
            selected_color=theme.color("accent"),
            selected_hover_color=theme.color("accent_hover"),
            unselected_color=theme.color("border"),
            unselected_hover_color=theme.color("surface"),
            text_color=theme.color("text"),
        )
        appearance.grid(row=1, column=0, sticky="ew")
        # set() only picks the starting option; it doesn't fire the callback.
        appearance.set("System")
        ctk.CTkLabel(
            bottom, text="ENGG 1035 | Webster's Method", anchor="w",
            font=theme.font(10), text_color=theme.color("text_muted"),
        ).grid(row=2, column=0, sticky="ew", pady=(theme.PAD_M, 0))

    def _nav_button(self, parent, text: str, command) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent, text=text, command=command, anchor="w", height=NAV_HEIGHT,
            corner_radius=theme.RADIUS_INPUT, font=theme.font(13),
            fg_color="transparent", hover_color=theme.color("border"),
            text_color=theme.color("text"), text_color_disabled=theme.color("text_muted"),
        )

    def show(self, name: str) -> None:
        if self.current:
            self.screens[self.current].grid_remove()
        self.current = name
        screen = self.screens[name]
        screen.grid(row=0, column=0, sticky="nsew")
        if hasattr(screen, "on_show"):
            screen.on_show()
        self._update_nav()

    def reset(self) -> None:
        self.model_key = None
        self.form_values = {}
        self.result = None
        self.timing_input = None
        self.show("model")

    def _update_nav(self) -> None:
        # Inputs need a chosen model; Results need a finished calculation.
        enabled = {
            "model": True,
            "inputs": self.model_key is not None,
            "results": self.result is not None,
        }
        for name, button in self.nav_buttons.items():
            is_active = name == self.current
            button.configure(
                state="normal" if enabled[name] else "disabled",
                fg_color=theme.color("surface") if is_active else "transparent",
                text_color=theme.color("accent") if is_active else theme.color("text"),
            )
