# FLOW Design Guide

How FLOW should look and feel. The goal is a calm, warm, readable tool, in the spirit of Claude's own interface: paper-like surfaces, one clay-colored accent, a little serif for personality, and lots of breathing room. This file is the source of truth for `ui/theme.py` and every widget.

It replaces the teal color tokens in PRD section 10.1. Layout, screens and components in the PRD still apply.

## Principles

1. **Calm over flashy.** Numbers are the star. Chrome stays quiet.
2. **Warm, not stark.** Cream and warm charcoal instead of pure white and pure black.
3. **One accent.** Clay/terracotta marks the primary action and the current selection. Nothing else competes with it.
4. **Say it in words.** Color never carries meaning alone. Signal bars always print G, Y/R and R.
5. **Forgiving.** Errors are gentle and specific, and they never wipe what the user typed.

## Color tokens

Defined once in `ui/theme.py` as a light and a dark set. Widgets read tokens by name, never raw hex.

| Token | Light | Dark | Used for |
|---|---|---|---|
| `bg` | `#FAF9F5` | `#1F1E1D` | window background |
| `surface` | `#FFFFFF` | `#2A2926` | cards, inputs |
| `surface_alt` | `#F0EEE6` | `#34322E` | sidebar, table stripes, hover |
| `border` | `#E3DFD3` | `#403D38` | card and input outlines |
| `text` | `#29261F` | `#F0EEE6` | body text, numbers |
| `text_muted` | `#6B665B` | `#A8A294` | labels, hints, units |
| `accent` | `#C15F3C` | `#D97757` | primary button, selected card, meter fill |
| `accent_hover` | `#A9502F` | `#E58A6A` | primary button hover |
| `on_accent` | `#FFFFFF` | `#1F1E1D` | text on accent |
| `signal_green` | `#3F8F5B` | `#5BB57A` | green phase bar |
| `signal_amber` | `#C98A1B` | `#E0A93B` | Y/R (lost time) bar |
| `signal_red` | `#C2453D` | `#E0645C` | red phase bar |
| `error_bg` | `#FBEAE6` | `#3D2623` | error banner background |
| `warning_bg` | `#FBF1DB` | `#3A3022` | warning banner background |
| `info_bg` | `#EEF1F6` | `#26292E` | info banner background |

Contrast: `text` on `bg`/`surface` and `on_accent` on `accent` must pass WCAG AA (4.5:1). Check again if any hex changes.

The app follows the system theme at launch and can be switched from the sidebar.

## Typography

| Role | Font | Fallback | Size / weight |
|---|---|---|---|
| Screen title | Georgia | Cambria, serif | 28 / regular |
| Section heading | Georgia | Cambria, serif | 18 / regular |
| Stat number | Georgia | Cambria, serif | 34 / regular |
| Body and labels | Segoe UI | Arial, sans-serif | 13 / regular |
| Small hints and units | Segoe UI | Arial, sans-serif | 11 / regular, `text_muted` |
| Buttons | Segoe UI | Arial, sans-serif | 13 / semibold |
| Text timeline and readouts | Cascadia Mono | Consolas, monospace | 12 / regular |

Serif is used only for titles and big numbers. Everything you read or type is sans.

## Spacing and shape

- Spacing scale (px): 4, 8, 12, 16, 24, 32. Use these and nothing in between.
- Window padding 24. Gap between cards 16. Padding inside a card 16 to 20.
- Corner radius: cards 12, inputs and buttons 8, small chips 6.
- Borders are 1 px in `border`. No heavy drop shadows; separation comes from border and surface color.
- Sidebar width 220. Content area is scrollable and capped near 960 px wide so lines stay short.

## Components

| Component | Notes |
|---|---|
| `ModelCard` | Surface card with a small phase diagram, name, one-line description. Hover lifts the border to `accent`; selected card gets a 2 px `accent` border. |
| `LabeledEntry` | Label above, entry, unit on the right inside the field, hint below in muted text. Error state: border and message in `signal_red`, text below the field. |
| `StatCard` | Muted label on top, big serif number, small muted unit beneath. |
| `Banner` | Rounded strip with a tinted background (`error_bg`, `warning_bg`, `info_bg`), a short title and one sentence. |
| `YMeter` | Thin horizontal bar from 0 to 1.0. Fill is `accent` below 0.85, `signal_amber` from 0.85, `signal_red` at 1.0 or more. Shows the number beside it. |
| `PhaseTable` | Rows separated by 1 px borders, alternate rows use `surface_alt`, numbers right-aligned in mono. |
| `TimelineCanvas` | One row per phase. Green, Y/R and red segments use the signal tokens, with the letters G, Y/R, R printed inside when the segment is wide enough. A thin time axis sits underneath. |
| Primary button | Filled `accent`, `on_accent` text. One per screen. |
| Secondary button | Transparent with a `border` outline and `text` color. |

## Screens

1. **Model select.** Serif title "Choose a phase model", short subtitle, five cards in a responsive grid.
2. **Input form.** Two columns. Left: saturation flow, lost time, and the live `YMeter`. Right: volume fields in a two-column grid. Calculate is primary, Reset is secondary. Errors show inline plus one banner at the top.
3. **Results.** Four stat cards, then the phase table, then the graphical timeline, then the text timeline in a mono box. Actions at the bottom: Copy results, Edit inputs, New calculation.
4. **Oversaturation.** An `error_bg` banner on the input form with the actual Y, one plain sentence of explanation and the top contributing phases. The form keeps every value.

## Voice

Friendly, short, specific. Say what happened and what to do next.

- Good: "Demand is higher than capacity (Y = 1.05). Lower the busiest volumes and try again."
- Avoid: "Error: invalid input." or all-caps shouting.
- Buttons are verbs: Calculate, Reset, Copy results, Edit inputs, New calculation.

## Accessibility

- AA contrast for text in both themes.
- Every signal color is paired with a letter or label.
- Tab order follows reading order; Enter in any field triggers Calculate.
- Minimum click target about 32 px tall.
