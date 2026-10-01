# Phase 7: Packaging and Submission

**Goal:** a one-file Windows build, a final documentation pass and a ready-to-present submission.
**Prerequisites:** Phase 6 merged and green.
**Deadline:** submission on **October 16, 2026**. Target finishing this phase by October 14 to leave a buffer day.
**Output:** `dist/FLOW.exe`, final README, release tag, demo script, submission checklist.

---

## Tasks

### 7.1 Branch
`git checkout -b phase-7-packaging`

### 7.2 Prepare the build
1. Confirm `assets/flow.ico` exists (Phase 6.7).
2. Add a `flow.spec` build configuration or use the command in 7.3. Prefer the command for simplicity.
3. CustomTkinter ships theme JSON and font files that PyInstaller does not detect automatically. Find the package path:
   ```bash
   python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"
   ```

### 7.3 Build the executable
From the repo root with the virtual environment active (replace `<CTK_PATH>` with the printed path):

```bash
pyinstaller --noconfirm --onefile --windowed --name FLOW --icon assets/flow.ico --add-data "<CTK_PATH>;customtkinter/" main.py
```

Notes:
- `--windowed` removes the console window; `--onefile` produces `dist/FLOW.exe`.
- If startup is slow, rebuild with `--onedir` and zip the folder instead.

### 7.4 Test the build
1. Run `dist/FLOW.exe` by double-click. It must open without a console window.
2. Run the full flow with all five models and both retry loops.
3. Copy `FLOW.exe` to a different folder and to a different Windows user or machine without Python installed; confirm it runs.
4. If Windows SmartScreen warns about an unknown publisher, that is expected for unsigned builds; note it in the README troubleshooting section.
5. If it crashes silently, rebuild without `--windowed` to see the traceback in a console.

### 7.5 Final README pass
1. Replace "Status: Planning" with the real status and version `1.0.0`.
2. Verify the install, run and test commands by following them literally on a clean clone in a new folder.
3. Add a "Download" line pointing to the GitHub release.
4. Add a "Troubleshooting" section: Python version, Tk not found, SmartScreen warning, blurry text on high-DPI screens.
5. Confirm every link in the README and in `docs/` resolves.
6. Update the PRD status line from "Planning" to "Implemented" and note any deviations in a short "Changes from plan" list at the bottom.

### 7.6 Release
1. `git checkout main` and `git merge phase-7-packaging`.
2. Run `pytest` one last time; all green.
3. `git tag v1.0.0`
4. `git push origin main --tags`
5. Create a GitHub release for `v1.0.0` and attach `FLOW.exe`.

### 7.7 Demo script (5 minutes)
1. **Intro (30 s):** what FLOW does and the formulas, one slide or the README table.
2. **Case 1 live (60 s):** 2-phase, "Fill example", Calculate. Point out the cycle (75 s), greens (39 and 28) and the timeline.
3. **Show the math (45 s):** the "Formulas used" card, matching a hand calculation.
4. **Bigger model (60 s):** 4-phase example. Point out the cycle of 225 s and the impractical-cycle warning.
5. **Retry loop 1 (45 s):** enter `abc` and a negative value; show inline errors; fix and recalculate.
6. **Retry loop 2 (45 s):** 2-phase with `NS 1200`, `EW 800`; show the oversaturation warning, then lower the volumes and succeed.
7. **Wrap-up (15 s):** copy results, switch theme, mention the tests and what was recomputed from the proposal (PRD decision D1).

Prepare answers for likely questions:
- Why does the cycle round up to 5 s? Standard practice, and rounding up never shortens the effective green.
- Why do the proposal sample numbers differ? The sample cycles for scenarios 2 to 5 do not follow Webster's formula; the app follows the formula.
- Why drop zero-volume phases? They need no green, so counting their lost time would lengthen the cycle for nothing.
- Why largest-remainder rounding? It guarantees the greens add up to the effective green, so the timeline closes exactly on the cycle.

### 7.8 Submission checklist
- [ ] Repository is public or shared with the instructor as required
- [ ] `v1.0.0` tag and release exist, `FLOW.exe` attached
- [ ] README complete with screenshots and run instructions
- [ ] PRD and phase docs included in `docs/`
- [ ] `pytest` passes on a fresh clone
- [ ] Final proposal document references updated (project title, FLOW name, formulas)
- [ ] Demo rehearsed at least twice, under 5 minutes
- [ ] Backup: executable and a short screen recording on a USB drive or cloud folder
- [ ] Submitted before **October 16, 2026**

---

## Checklist
- [ ] `FLOW.exe` builds and runs on a clean machine
- [ ] README final and verified from a clean clone
- [ ] Tag and release published
- [ ] Demo rehearsed
- [ ] Submission checklist complete

## Definition of done
Anyone can download `FLOW.exe` or clone the repo, follow the README and get the same results as the demo, and the submission is in on time.
