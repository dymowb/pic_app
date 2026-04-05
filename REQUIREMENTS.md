# Requirements — pic_app

## 1. Purpose

`pic_app` helps users clean up bloated photo libraries by automatically finding
groups of similar or duplicate photos and recommending the best 1–2 images to
keep in each group. Users can then safely delete or archive the rest.

---

## 2. Functional Requirements

### 2.1 Image Loading

| ID | Requirement |
|----|-------------|
| F-01 | User can select a folder to scan (recursive scan of all sub-folders included) |
| F-02 | Supported formats: JPEG, PNG, WEBP, BMP, TIFF; HEIC and RAW as best-effort |
| F-03 | App displays a thumbnail grid of all scanned images with filename and file size |
| F-04 | User can rescann a different folder without restarting the app |
| F-05 | App shows a progress indicator during scanning |

### 2.2 Similarity Detection (Grouping)

| ID | Requirement |
|----|-------------|
| F-06 | Each image is fingerprinted using perceptual hashing (pHash, 64-bit) |
| F-07 | Images whose pHash Hamming distance is ≤ threshold are placed in the same group |
| F-08 | Default similarity threshold: distance ≤ 10 (configurable by user, range 0–20) |
| F-09 | Images not similar to any other image are listed as "unique" (no action needed) |
| F-10 | Each duplicate group is displayed as a horizontal strip of thumbnails |
| F-11 | Groups are sorted by size descending (largest groups first) |

### 2.3 Quality Analysis

| ID | Requirement |
|----|-------------|
| F-12 | For each image in a duplicate group, compute: |
|      | • **Sharpness** — Laplacian variance (higher = sharper) |
|      | • **Exposure** — histogram mean and std-dev; penalise over/under-exposure |
|      | • **Noise** — estimated via high-frequency residual |
|      | • **Resolution** — total pixel count (width × height) |
|      | • **File size** — bytes on disk |
| F-13 | Raw metric values are displayed per image on hover / detail panel |

### 2.4 Scoring & Recommendation

| ID | Requirement |
|----|-------------|
| F-14 | Each image receives a composite quality score (0–100) computed as a weighted sum of normalised metrics |
| F-15 | Default weights: sharpness 50%, exposure 30%, resolution 20% |
| F-16 | The image with the highest score in a group is labelled **"Best — Keep"** |
| F-17 | The image with the second-highest score is optionally labelled **"Runner-up"** |
| F-18 | Each recommendation includes a plain-English reason, e.g.: |
|      | • "Sharpest image in this group" |
|      | • "Best exposure — well-balanced brightness" |
|      | • "Highest resolution" |
| F-19 | User can override the recommendation by clicking a different image in the group |
| F-20 | User can adjust scoring weights via a Settings panel; scores recalculate live |

### 2.5 Actions & Export

| ID | Requirement |
|----|-------------|
| F-21 | User can mark individual images for deletion within each group |
| F-22 | "Apply Recommendations" button automatically marks all non-recommended images for deletion across all groups |
| F-23 | Before any destructive action, user sees a confirmation dialog listing files to be affected |
| F-24 | Deletion action: move files to a `_duplicates` subfolder (safe; not permanent delete) |
| F-25 | User can also export a plain-text "keep list" (one file path per line) |
| F-26 | Summary panel shows: groups found, images analysed, duplicates to remove, space to reclaim (MB) |

### 2.6 Settings

| ID | Requirement |
|----|-------------|
| F-27 | Similarity threshold slider (0–20) with live preview of group count change |
| F-28 | Scoring weight sliders for sharpness, exposure, resolution (must sum to 100%) |
| F-29 | Option: show/hide "unique" images (those with no duplicates) |
| F-30 | Settings persisted to a local config file between sessions |

---

## 3. Non-Functional Requirements

### 3.1 Platform

| ID | Requirement |
|----|-------------|
| NF-01 | Target OS: Windows 10 (64-bit) and Windows 11 only |
| NF-02 | Distributed as a standalone `.exe` — no Python or dependency installation required |
| NF-03 | Single-file PyInstaller build |

### 3.2 Performance

| ID | Requirement |
|----|-------------|
| NF-04 | Handle sessions of up to 500 images without crashing or excessive memory use |
| NF-05 | Hashing and quality analysis run in background threads; UI remains responsive at all times |
| NF-06 | Thumbnail generation completes within 5 seconds for 100 images on a mid-range Windows PC |
| NF-07 | Full analysis (hash + quality) completes within 30 seconds for 100 images |

### 3.3 Usability

| ID | Requirement |
|----|-------------|
| NF-08 | First-time user can load a folder and get recommendations within 3 clicks |
| NF-09 | Recommendations include plain-English explanations (no technical jargon) |
| NF-10 | All destructive actions require explicit confirmation |
| NF-11 | UI scales correctly on 100%, 125%, and 150% Windows display scaling |

### 3.4 Reliability & Safety

| ID | Requirement |
|----|-------------|
| NF-12 | App never permanently deletes files — only moves to a `_duplicates` subfolder |
| NF-13 | Errors during analysis of a single image are logged and skipped; they do not crash the session |
| NF-14 | App state (selected folder, settings) is restored on next launch |

---

## 4. Out of Scope (v1)

- Cloud sync or remote library support
- AI/ML-based aesthetic scoring (planned for v2)
- Face detection or subject-recognition grouping
- Video deduplication
- macOS / Linux support
