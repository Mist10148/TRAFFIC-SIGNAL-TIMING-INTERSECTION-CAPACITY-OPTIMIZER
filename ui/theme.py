from functools import lru_cache
from tkinter import font as tkfont

import customtkinter as ctk

LIGHT = {
    "bg": "#FAF9F5",
    "surface": "#FFFFFF",
    "surface_alt": "#F0EEE6",
    "border": "#E3DFD3",
    "text": "#29261F",
    "text_muted": "#6B665B",
    "accent": "#C15F3C",
    "accent_hover": "#A9502F",
    "on_accent": "#FFFFFF",
    "signal_green": "#3F8F5B",
    "signal_amber": "#C98A1B",
    "signal_red": "#C2453D",
    "error_bg": "#FBEAE6",
    "warning_bg": "#FBF1DB",
    "info_bg": "#EEF1F6",
}

DARK = {
    "bg": "#1F1E1D",
    "surface": "#2A2926",
    "surface_alt": "#34322E",
    "border": "#403D38",
    "text": "#F0EEE6",
    "text_muted": "#A8A294",
    "accent": "#D97757",
    "accent_hover": "#E58A6A",
    "on_accent": "#1F1E1D",
    "signal_green": "#5BB57A",
    "signal_amber": "#E0A93B",
    "signal_red": "#E0645C",
    "error_bg": "#3D2623",
    "warning_bg": "#3A3022",
    "info_bg": "#26292E",
}

RADIUS_CARD = 12
RADIUS_INPUT = 8

PAD_S = 8
PAD_M = 16
PAD_L = 24

SANS_FAMILIES = ("Segoe UI Variable", "Segoe UI", "Arial")
SERIF_FAMILIES = ("Georgia", "Cambria", "Times New Roman")
MONO_FAMILIES = ("Cascadia Mono", "Consolas", "Courier New")


def color(name: str) -> tuple[str, str]:
    # CustomTkinter takes (light, dark) and switches by itself with the theme.
    return (LIGHT[name], DARK[name])


def resolve(name: str) -> str:
    # Plain tk widgets (like Canvas) can't take a (light, dark) pair,
    # so they ask for the hex of whichever mode is on screen right now.
    tokens = DARK if ctk.get_appearance_mode() == "Dark" else LIGHT
    return tokens[name]


@lru_cache(maxsize=1)
def _installed_families() -> frozenset[str]:
    return frozenset(tkfont.families())


def _pick_family(candidates: tuple[str, ...]) -> str:
    installed = _installed_families()
    for name in candidates:
        if name in installed:
            return name
    return candidates[-1]


@lru_cache(maxsize=None)
def font(size: int, weight: str = "normal", serif: bool = False, mono: bool = False) -> ctk.CTkFont:
    if mono:
        family = _pick_family(MONO_FAMILIES)
    elif serif:
        family = _pick_family(SERIF_FAMILIES)
    else:
        family = _pick_family(SANS_FAMILIES)
    return ctk.CTkFont(family=family, size=size, weight=weight)
