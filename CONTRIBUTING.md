# Contributing

Short rules so the code stays easy to read and explain.

- Comments are single-line `#` comments, written in plain words, and only where the code alone doesn't say why.
- No decorative banners, no divider lines, no commented-out code.
- No multi-line string comments or docstring blocks. Use clear names instead.
- `core/` never imports `tkinter`, `customtkinter` or anything from `ui/`.
- Put type hints on every function in `core/`.
- One screen or widget per file. `main.py` only starts the app.
- Keep functions small. If a function needs a long explanation, split it.
- Before each commit, search the diff for `"""`, `# ====` and `# ----` and remove them.
- Make small commits, one idea each.
