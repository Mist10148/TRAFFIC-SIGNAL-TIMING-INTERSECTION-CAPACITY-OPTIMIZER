# QA record

Checked on 2026-10-02 on Windows 11 with Python 3.13. "Scripted" means a throwaway script drove the real app and checked the result (or took a screenshot that was read by eye). "Not run" means nobody has done it yet and it still needs a person at the keyboard.

| Test | Steps | Expected | Result | Date |
|---|---|---|---|---|
| Full flow, all five models | Pick the model, Fill example, Calculate | Cycle, Te, Y and L match PRD section 11 for each case | Pass (scripted) | 2026-10-02 |
| Retry loop: invalid input | Empty form, `abc`, lost time `3.5`, all-zero volumes, Calculate | Inline messages, banner count, values kept | Pass (scripted) | 2026-10-02 |
| Retry loop: oversaturation | 2-phase NS 1200, EW 800, Calculate; then 850 and 600 | Banner with Y = 1.0526, two fields outlined, stays on form; fixed values reach Results | Pass (scripted) | 2026-10-02 |
| Edge: Y = 1.0 exactly | NS 950, EW 950 | Oversaturated | Pass (scripted) | 2026-10-02 |
| Edge: Y = 0.99 | NS 1000, EW 881 | Cycle above 150 s, impractical warning | Pass (scripted) | 2026-10-02 |
| Edge: tiny volume | EW `0.0001` | Accepted, 0 s green, minimum-green warning | Pass (scripted) | 2026-10-02 |
| Edge: number formats | `1,5`, `  850  `, `1e3` | 1.5, 850 and 1000 | Pass (scripted) | 2026-10-02 |
| Edge: bad numbers | `nan`, `inf`, `-inf`, 200 characters of text | "Enter a number", no crash | Pass (scripted) | 2026-10-02 |
| Model switch | 2-phase to 4-phase | Saturation flow and lost time kept, volumes rebuilt | Pass (scripted) | 2026-10-02 |
| Appearance Light and Dark | Screenshots of every screen in both | Readable, no leftover wrong colors | Pass (screenshots read by eye) | 2026-10-02 |
| Written sections | 4-Phase example, Light and Dark, 1120 x 720 | Summary, Description, Results and Discussion readable and wrapped | Pass (screenshots read by eye) | 2026-10-02 |
| Appearance switching on each screen | Use the sidebar control while on each screen | Screen recolors without a glitch | Not run | |
| Window size 960 x 640 | Screenshots of all three screens, both themes | Nothing cut off without a scrollbar | Pass (screenshots read by eye) | 2026-10-02 |
| Window size 1120 x 720 | Screenshots of all three screens | Layout as designed | Pass (screenshots read by eye) | 2026-10-02 |
| Window size 1600 x 900 and maximized | Resize and maximize | Layout adapts | Not run | |
| Windows scaling 100, 125, 150 percent | Change display scaling and relaunch | Fonts and padding stay proportional | Not run | |
| Keyboard-only run | Tab through the form, Enter to calculate, Esc back | Whole flow works without the mouse | Not run | |
| Copy results | Click Copy results, check the clipboard | Five sections in order; button shows "Copied" | Pass (scripted); pasting into Notepad Not run | 2026-10-02 |
| Rapid Calculate | 20 Calculate presses in a row | No extra widgets, no crash | Pass (scripted, widget count stayed at 574) | 2026-10-02 |
| 50 trips around the app | Model, Inputs, Calculate, Results, 50 times | Widget count stays flat | Pass (scripted); memory in Task Manager Not run | 2026-10-02 |
| Speed | Time `compute_timing` for an 8-phase case | Under 5 ms | Pass (about 0.008 ms per call) | 2026-10-02 |
| Tooltip on the timeline | Hover over bars | Tooltip with phase, kind and times | Not run | |
| Close from every screen | Close the window on each screen | Exits cleanly | Not run | |

## Contrast

Text and signal colors were measured against WCAG AA (4.5 to 1) in both themes. Muted text, accent text, white or dark text on the accent button, and the signal colors on their surfaces all pass after the palette was adjusted in Phase 6.
