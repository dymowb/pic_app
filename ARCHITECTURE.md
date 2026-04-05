# Architecture — pic_app

## 1. Overview

`pic_app` is a Windows-only desktop application built in Python. It follows a
layered architecture: the UI layer delegates all heavy work (hashing, analysis,
scoring) to background worker threads, keeping the interface responsive at all
times. Results flow back to the UI via Qt signals.

```
┌─────────────────────────────────────────────────────┐
│                     UI Layer (PyQt6)                │
│  MainWindow → ThumbnailGrid → GroupPanel → Badges  │
└────────────────────┬────────────────────────────────┘
                     │ signals / slots
┌────────────────────▼────────────────────────────────┐
│               Worker Threads (QThread)              │
│   ScanWorker   HashWorker   AnalysisWorker          │
└────────────────────┬────────────────────────────────┘
                     │ calls
┌────────────────────▼────────────────────────────────┐
│              Analysis Layer (pure Python)           │
│   hasher.py  clusterer.py  quality.py  scorer.py   │
└────────────────────┬────────────────────────────────┘
                     │ uses
┌────────────────────▼────────────────────────────────┐
│                 Third-Party Libraries               │
│   Pillow   imagehash   OpenCV (headless)   NumPy   │
└─────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack

| Concern | Choice | Reason |
|---------|--------|--------|
| Language | Python 3.11+ | Rich imaging ecosystem; fast iteration |
| UI framework | PyQt6 | Native Windows look, mature threading, rich widgets |
| Image I/O | Pillow (PIL) | Broad format support; simple API |
| Perceptual hashing | `imagehash` | pHash / dHash; returns Hamming-comparable hash objects |
| Quality analysis | `opencv-python-headless` | Laplacian sharpness, histogram ops; no GUI dependency |
| Numerics | NumPy | Required by OpenCV; used for metric normalisation |
| Settings persistence | `json` (stdlib) | Simple; stored in `%APPDATA%\pic_app\settings.json` |
| Packaging | PyInstaller | Produces single `.exe`; no Python install required |
| Testing | pytest + pytest-qt | Unit tests for analysis layer; widget smoke tests |

---

## 3. Project Layout

```
pic_app/
├── src/
│   ├── main.py                   # QApplication bootstrap; launches MainWindow
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py        # Top-level QMainWindow; toolbar, status bar, layout
│   │   ├── thumbnail_grid.py     # QScrollArea grid of ImageCard widgets
│   │   ├── group_panel.py        # Horizontal strip for one duplicate group + badges
│   │   ├── image_card.py         # Single thumbnail card (image, filename, size, badge)
│   │   ├── preview_panel.py      # Full-size image preview (right pane)
│   │   ├── summary_bar.py        # Bottom bar: groups, duplicates, space-saved stats
│   │   └── settings_dialog.py    # QDialog: threshold slider, weight sliders
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── hasher.py             # compute_phash(path) → imagehash.ImageHash
│   │   ├── clusterer.py          # cluster(hashes, threshold) → List[List[Path]]
│   │   ├── quality.py            # sharpness / exposure / noise / resolution metrics
│   │   └── scorer.py             # score_group(images, weights) → List[ImageScore]
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── scan_worker.py        # QThread: enumerate files, emit path per file
│   │   ├── hash_worker.py        # QThread: hash each file, emit progress
│   │   └── analysis_worker.py    # QThread: quality metrics per group, emit results
│   │
│   └── export/
│       ├── __init__.py
│       └── actions.py            # move_to_duplicates(), export_keep_list()
│
├── assets/
│   └── icons/
│       └── app.ico               # Application icon
│
├── tests/
│   ├── conftest.py               # Shared fixtures (sample images)
│   ├── test_hasher.py
│   ├── test_clusterer.py
│   ├── test_quality.py
│   └── test_scorer.py
│
├── requirements.txt
├── requirements-dev.txt
├── build.bat                     # PyInstaller build command
├── README.md
├── REQUIREMENTS.md
├── ROADMAP.md
└── ARCHITECTURE.md
```

---

## 4. Key Module Contracts

### 4.1 `analysis/hasher.py`
```python
def compute_phash(path: Path) -> imagehash.ImageHash:
    """Return the 64-bit pHash for the image at path.
    Raises ValueError if the file cannot be opened as an image."""
```

### 4.2 `analysis/clusterer.py`
```python
def cluster(
    hashes: dict[Path, imagehash.ImageHash],
    threshold: int = 10,
) -> list[list[Path]]:
    """Group paths into clusters where every pair has Hamming distance ≤ threshold.
    Returns list of groups; groups with one member are 'unique' images."""
```
Implementation note: use union-find (disjoint set union) for O(n²) pairwise
comparison — acceptable for n ≤ 500.

### 4.3 `analysis/quality.py`
```python
@dataclass
class ImageMetrics:
    sharpness: float    # Laplacian variance; higher = sharper
    exposure: float     # 0–1; 1 = perfect exposure
    noise: float        # 0–1; 1 = very noisy (inverted for scoring)
    resolution: int     # total pixel count

def compute_metrics(path: Path) -> ImageMetrics:
    """Compute all quality metrics for a single image."""
```

### 4.4 `analysis/scorer.py`
```python
@dataclass
class ScoringWeights:
    sharpness: float = 0.50
    exposure: float  = 0.30
    resolution: float = 0.20

@dataclass
class ImageScore:
    path: Path
    score: float          # 0–100
    rank: int             # 1 = best in group
    reason: str           # plain-English explanation

def score_group(
    metrics: dict[Path, ImageMetrics],
    weights: ScoringWeights,
) -> list[ImageScore]:
    """Normalise metrics within the group, apply weights, return ranked scores."""
```

### 4.5 `export/actions.py`
```python
def move_to_duplicates(paths: list[Path], source_root: Path) -> None:
    """Move each path to <source_root>/_duplicates/, preserving sub-folder structure."""

def export_keep_list(keep_paths: list[Path], output_file: Path) -> None:
    """Write one absolute path per line to output_file."""
```

---

## 5. Threading Model

```
Main Thread (UI)
│
├── ScanWorker (QThread)
│     signal: file_found(path)       → adds card to ThumbnailGrid
│     signal: scan_complete(paths)   → triggers HashWorker
│
├── HashWorker (QThread)
│     signal: progress(n, total)     → updates progress bar
│     signal: hash_complete(hashes)  → triggers clusterer + AnalysisWorker
│
└── AnalysisWorker (QThread)
      signal: group_ready(group, scores)  → GroupPanel renders badges + reasons
      signal: analysis_complete(summary)  → SummaryBar updates stats
```

All signals are connected with `Qt.ConnectionType.QueuedConnection` to ensure
thread safety. Worker objects are never accessed from the main thread after
`start()`.

---

## 6. Settings Persistence

Settings are stored as JSON at:
```
%APPDATA%\pic_app\settings.json
```

Schema:
```json
{
  "similarity_threshold": 10,
  "weights": {
    "sharpness": 0.50,
    "exposure": 0.30,
    "resolution": 0.20
  },
  "show_unique": true,
  "last_folder": "C:\\Users\\..."
}
```

---

## 7. Packaging (PyInstaller)

`build.bat` runs:
```bat
pyinstaller src/main.py ^
  --name pic_app ^
  --onefile ^
  --windowed ^
  --icon assets/icons/app.ico ^
  --add-data "assets;assets"
```

Output: `dist/pic_app.exe` — a single self-contained executable for Windows.

---

## 8. Design Decisions & Trade-offs

| Decision | Rationale |
|----------|-----------|
| pHash over exact MD5 | Catches near-duplicates (re-saves, crops, slight edits), not just byte-identical files |
| Union-find clustering | O(n²) pairwise — fine for n ≤ 500; avoids complex graph libraries |
| Move to `_duplicates/` instead of delete | Safety first; user can always recover files |
| Weights configurable by user | Different use cases (wildlife vs portrait) have different "best shot" definitions |
| OpenCV headless build | Avoids bundling Qt's OpenCV GUI, reducing `.exe` size |
| Settings in `%APPDATA%` | Standard Windows practice; survives app reinstall |
