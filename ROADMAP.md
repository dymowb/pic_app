# Roadmap — pic_app

Delivery is organised into 7 phases. Each phase produces a working increment
that can be tested end-to-end before the next phase begins.

---

## Phase 1 — Foundation
**Goal:** Working project scaffold; empty app window launches on Windows.

- [ ] Initialise Git repo and branch strategy (`main` + feature branches)
- [ ] Create Python virtual environment (`python -m venv .venv`)
- [ ] Add `requirements.txt` and `requirements-dev.txt`
- [ ] Scaffold `src/` directory layout (ui, analysis, grouping, export packages)
- [ ] Create `src/main.py` — bootstraps PyQt6 `QApplication` and shows an empty `QMainWindow`
- [ ] Add `assets/icons/` placeholder
- [ ] Add `build.bat` (PyInstaller skeleton)
- [ ] Add `tests/` with a smoke test (`pytest` passes)
- [ ] Verify the app window opens and closes cleanly on Windows

**Exit criteria:** `python src/main.py` opens an empty window; `pytest` passes.

---

## Phase 2 — Image Loading & Thumbnail Grid
**Goal:** User can select a folder and see all images as thumbnails.

- [ ] Toolbar with "Open Folder" button (`QFileDialog.getExistingDirectory`)
- [ ] Recursive folder scan for supported extensions (JPEG, PNG, WEBP, BMP, TIFF)
- [ ] Background `QThread` worker for scanning and thumbnail generation
- [ ] Progress bar shown during scan
- [ ] `ThumbnailGrid` widget — scrollable grid of image cards (filename, size label)
- [ ] Click a thumbnail → open full-size preview panel (right pane)
- [ ] "Unique" images (no duplicates) shown in a separate collapsible section
- [ ] Handle corrupt/unreadable image files gracefully (log and skip)

**Exit criteria:** Open a folder of 100 mixed images; all thumbnails render; clicking shows preview.

---

## Phase 3 — Similarity Detection & Grouping
**Goal:** Images are automatically clustered into duplicate groups.

- [ ] `analysis/hasher.py` — compute pHash (64-bit) for each image using `imagehash`
- [ ] Hashing runs in background thread; progress bar updates per image
- [ ] `analysis/clusterer.py` — group images by pHash Hamming distance ≤ threshold
  - Use a union-find (disjoint set) structure for efficient clustering
- [ ] `ui/group_panel.py` — horizontal strip widget showing a duplicate group
  - Thumbnails side-by-side with filename and file size beneath each
- [ ] Groups sorted by size (largest first)
- [ ] Similarity threshold exposed as a slider in Settings; changing it re-clusters live
- [ ] "Groups found: N | Unique: M" summary label in status bar

**Exit criteria:** A folder of 50 burst-shot images produces correct groups; threshold slider changes group count live.

---

## Phase 4 — Quality Analysis Engine
**Goal:** Each image in a group gets quality metrics computed.

- [ ] `analysis/quality.py` — compute per-image metrics:
  - `sharpness(img)` — Laplacian variance via OpenCV
  - `exposure_score(img)` — histogram mean ± std-dev penalty for clipping
  - `noise_score(img)` — high-frequency residual estimation
  - `resolution(img)` — total pixel count
- [ ] Analysis runs in background thread after clustering completes
- [ ] Per-image metrics displayed in a tooltip or detail panel on hover
- [ ] Raw metric values shown as labelled bars (mini bar chart per metric)

**Exit criteria:** Hover any image in a group → see sharpness, exposure, noise, resolution values.

---

## Phase 5 — Scoring & Recommendation Engine
**Goal:** App picks the best 1–2 images per group and explains why.

- [ ] `analysis/scorer.py` — normalise each metric across the group, apply weights, sum to composite score (0–100)
- [ ] Default weights: sharpness 50%, exposure 30%, resolution 20%
- [ ] Top-1 image in each group gets a **"Best — Keep"** badge (green border)
- [ ] Top-2 image gets a **"Runner-up"** badge (blue border) if group size ≥ 3
- [ ] Recommendation reason generated from dominant metric, e.g.:
  - "Sharpest image in this group"
  - "Best exposure — well-balanced brightness"
  - "Highest resolution"
- [ ] Reason displayed beneath the recommended thumbnail
- [ ] User can click any other image to manually override the recommendation
- [ ] Weight sliders in Settings → scores and badges recalculate immediately

**Exit criteria:** Groups show correct badges; changing weights updates recommendations live; manual override works.

---

## Phase 6 — Actions & Export
**Goal:** User can act on recommendations to clean up their library.

- [ ] Each non-recommended image shows a "Mark for Deletion" checkbox (pre-checked after "Apply Recommendations")
- [ ] "Apply Recommendations" toolbar button — marks all non-top images for deletion across all groups
- [ ] Confirmation dialog listing all files to be moved before any action
- [ ] "Move Duplicates" action — moves marked files to `<source_folder>/_duplicates/`
- [ ] "Export Keep List" action — writes one file path per line to a `.txt` file
- [ ] Summary panel: groups found, duplicates marked, space to reclaim (MB)
- [ ] Status bar updates after action: "Moved 42 files — 1.2 GB reclaimed"
- [ ] Undo: re-scan restores the original state (files are never permanently deleted)

**Exit criteria:** Apply recommendations on a test folder → correct files moved to `_duplicates/`; keep list exports correctly.

---

## Phase 7 — Polish & Packaging
**Goal:** Production-ready Windows `.exe` with a polished UI.

- [ ] App icon (`assets/icons/app.ico`) added to window and taskbar
- [ ] Stylesheet / theming — clean, modern look consistent with Windows 11 style
- [ ] Settings persisted to `%APPDATA%\pic_app\settings.json` between sessions
- [ ] Last-used folder restored on launch
- [ ] Error handling — friendly error dialogs for permission errors, out-of-memory, etc.
- [ ] About dialog with version, license, and acknowledgements
- [ ] `build.bat` — full PyInstaller command: `--onefile --windowed --icon=assets/icons/app.ico`
- [ ] Smoke-test the `.exe` on a clean Windows VM
- [ ] Tag `v1.0.0` release

**Exit criteria:** Single `.exe` runs on a clean Windows 10/11 machine with no Python installed; all Phase 1–6 features work.

---

## Future Phases (v2+)

| Feature | Notes |
|---------|-------|
| AI aesthetic scoring | Integrate a lightweight model for composition, subject, rule-of-thirds |
| Face-based grouping | Group by detected faces in addition to visual similarity |
| HEIC / RAW support | Add `pyheif` and `rawpy` dependencies |
| Batch rename | Rename kept images in a consistent naming scheme |
| Video deduplication | Extend hashing to video key-frames |
