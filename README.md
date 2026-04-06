# pic_app — Duplicate Photo Finder & Cleaner

A Windows desktop application that scans your photo library, detects groups of
near-duplicate or similar images, and recommends which 1–2 photos to **keep**
per group — so you can confidently delete the rest.

## Problem it solves

Modern cameras and phones shoot bursts, HDR stacks, and accidental duplicates.
Over time, photo libraries balloon with nearly-identical shots that are hard to
review manually. `pic_app` automates the tedious work:

1. Scans a folder recursively for images
2. Groups visually similar photos using perceptual hashing
3. Ranks each image in a group by sharpness, exposure quality, and resolution
4. Tells you exactly which one to keep — and why

## Key Features

- Near-duplicate detection using perceptual hashing (pHash)
- Per-group quality scoring: sharpness, exposure, noise, resolution
- Clear recommendations: "Keep this one — sharpest image in group"
- Manual override — you always have the final say
- Move duplicates to a subfolder or export a "keep" list
- Space-saved summary
- Configurable similarity threshold (strict → relaxed)
- Runs entirely offline — no cloud, no account needed

## Tech Stack

| Component | Library |
|-----------|---------|
| UI | PyQt6 |
| Image I/O | Pillow |
| Similarity | imagehash (pHash) |
| Quality analysis | OpenCV (headless) |
| Numerics | NumPy |
| Packaging | PyInstaller (.exe) |

## Requirements

- Windows 10 or Windows 11 (64-bit)
- Python 3.11+ (for development)
- No Python needed for the packaged `.exe`

## Getting Started (Development)

```bat
git clone https://github.com/dymowb/pic_app.git
cd pic_app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python src/main.py
```

## Building the Windows .exe

```bat
.venv\Scripts\activate
build.bat
```

The output `.exe` will be in `dist/pic_app.exe`.

## One-Click Setup + Build (first time)

```bat
setup_and_build.bat
```

This creates the virtual environment, installs all dependencies, runs tests,
and builds the `.exe` in one step.

## Project Structure

```
pic_app/
├── src/
│   ├── main.py               # Entry point
│   ├── ui/                   # PyQt6 windows and widgets
│   ├── analysis/             # Hashing, clustering, quality metrics, scoring
│   └── export/               # File actions (move, export list)
├── assets/icons/
├── tests/
├── requirements.txt
├── requirements-dev.txt
├── build.bat
├── REQUIREMENTS.md
├── ROADMAP.md
└── ARCHITECTURE.md
```

## License

MIT
