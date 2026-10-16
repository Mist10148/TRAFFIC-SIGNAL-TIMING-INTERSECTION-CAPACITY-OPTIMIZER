# Phase 0: Project Setup

**Goal:** a runnable empty project: environment, folders, dependencies, conventions and a window that opens.
**Prerequisites:** Python 3.11+ installed, Git configured, repo cloned.
**Output:** project skeleton, `requirements.txt`, `requirements-dev.txt`, `Main.py` that opens a blank CustomTkinter window, first commit on a feature branch.
**Read first:** [PRD](../PRD.md) sections 12 (architecture) and 14 (conventions).

---

## Tasks

### 0.1 Verify tooling
1. Run `python --version`. It must print 3.11 or higher. If not, install Python 3.11+ from python.org and tick "Add to PATH".
2. Run `git --version` and `git status`. The tree must be clean on `main`.
3. Confirm Tk is bundled: run `python -c "import tkinter; print(tkinter.TkVersion)"`. It must print 8.6 or higher.

### 0.2 Create a working branch
1. Run `git checkout -b phase-0-setup`.
2. Branch naming for the rest of the project: `phase-N-short-name`. One branch per phase, merged into `main` after the phase checklist is complete.

### 0.3 Create the virtual environment
1. In the repo root run `python -m venv .venv`.
2. Activate: `.venv\Scripts\activate` (PowerShell: `.venv\Scripts\Activate.ps1`; if blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once).
3. Confirm `.venv` is already ignored: open `.gitignore` and search for `.venv`. If missing, add the line `.venv/`.

### 0.4 Declare dependencies
1. Create `requirements.txt` with exactly:
   ```
   customtkinter>=5.2.2
   ```
2. Create `requirements-dev.txt` with exactly:
   ```
   -r requirements.txt
   pytest>=8.0
   pytest-cov>=5.0
   pyinstaller>=6.0
   ```
3. Run `pip install -r requirements-dev.txt`.
4. Verify: `python -c "import customtkinter; print(customtkinter.__version__)"` prints a version.

### 0.5 Create the project skeleton
The whole app lives in one file, `Main.py`, in the repo root. Tests go in a `tests/` folder with an empty `tests/__init__.py` (empty means zero bytes, no comments).

Later phases add their code to `Main.py` as sections, each starting with a plain `# Section` comment, in this order:

```
Models
Validation
Calculator
Narrative
Visualizer
Theme
Widgets
Screens
App
```

### 0.6 Add pytest configuration
1. Create `pytest.ini` in the repo root:
   ```
   [pytest]
   testpaths = tests
   addopts = -q
   ```
2. Run `pytest`. Expected: "no tests ran" and exit without import errors.

### 0.7 Create the entry point
Create `Main.py` with a minimal App section and the entry point so the window opens:

```python
import customtkinter as ctk


# App

class FlowApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FLOW | Traffic Signal Timing Optimizer")
        self.geometry("1120x720")
        self.minsize(960, 640)


def main() -> None:
    app = FlowApp()
    app.mainloop()


if __name__ == "__main__":
    main()
```

### 0.8 Smoke test
1. Run `python Main.py`. A blank window titled "FLOW | Traffic Signal Timing Optimizer" must open at 1120 x 720 and must not shrink below 960 x 640.
2. Close the window. The process must exit cleanly with no traceback.

### 0.9 Record the conventions
1. Create `CONTRIBUTING.md` (short, about 15 lines) copying the rules from PRD section 14: single-line `#` comments, no decorative comments, no multi-line string comments, the logic sections of `Main.py` have no GUI imports, type hints in the logic sections, one class per screen or widget.
2. Add a short "Conventions" check to your own review routine: before every commit, search the diff for `"""` and for `# ====` or `# ----`; remove any that are not required.

### 0.10 Commit and merge
1. `git add .`
2. `git status` and confirm `.venv/` is not staged.
3. `git commit -m "Phase 0: project skeleton, dependencies and empty window"`
4. `git checkout main` then `git merge phase-0-setup`.

---

## Checklist
- [x] `python --version` is 3.11 or higher
- [x] `.venv` created and ignored by git
- [x] `requirements.txt` and `requirements-dev.txt` exist and install cleanly
- [x] Project layout matches PRD section 12
- [x] `pytest` runs without errors (no tests yet)
- [x] `python Main.py` opens the blank window and closes cleanly
- [x] `CONTRIBUTING.md` written
- [x] Phase committed and merged

## Definition of done
A fresh clone can follow the README, install dependencies and see the empty FLOW window. Nothing else is implemented yet.
