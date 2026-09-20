# File Integrity Checker (SHA256)

A modern, lightweight **Python desktop application** designed to verify **file integrity** using **SHA256 cryptographic hashing**.  
Built with a sleek **dark-mode GUI** powered by [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter), this tool helps ensure files remain authentic and untampered — an essential practice in **cybersecurity** and **digital forensics**.

Core hashing, batch verification, and the live monitor live in `integrity_core.py` so they can be tested with **pytest without a display**.

---

## Features

✅ **Modern UI** — Clean, dark-mode interface built with `customtkinter`  
✅ **File Hashing (SHA256)** — Quickly compute and display file hashes  
✅ **Integrity Verification** — Compare against a known hash for tamper detection  
✅ **Clipboard Support** — Copy computed hashes instantly  
✅ **Report Exporting** — Save results (with timestamps) to `report.txt`  
✅ **Threaded Processing** — Non-blocking performance for large files  
✅ **Drag-and-drop** — Drop one or many files onto the window (`tkinterdnd2`)  
✅ **Batch verification** — Hash many files; optional expected-hash list; status table + batch report export  
✅ **Live hash monitor** — Watch files/folder with `watchdog`; alert when SHA256 drifts from baseline  
✅ **Cross-Platform** — Works on Windows, macOS, and Linux  

---

## Changelog (2026-09-20)

### Added

1. **Drag-and-drop file support**  
   - Dependency: `tkinterdnd2`  
   - Drop files onto the main window. One file fills the Single File tab; multiple files queue on **Batch Verify**. Drops on the Live Monitor tab add monitor targets.

2. **Multiple file batch verification**  
   - **Batch Verify** tab: Add Files / clear list, optional expected-hash box, Verify Batch (threaded), side-by-side status table (`MATCH` / `MISMATCH` / `HASHED` / `ERROR`), Export Batch Report.  
   - Expected-hash lines accept: `SHA256  filename`, `file=hash`, or `file:hash` (`#` comments allowed).

3. **Real-time hash monitor**  
   - Dependency: `watchdog`  
   - **Live Monitor** tab: pick files and/or a folder, **Start Monitor** (baselines recorded), **Stop Monitor**. On change, SHA256 is recomputed; UI log + alert if the digest differs from baseline.

### Refactor / quality

- Extracted `integrity_core.py` (hash, compare, batch, `HashMonitor`) for headless pytest.  
- Added `requirements.txt`, `pytest.ini`, and `tests/test_integrity_core.py`.  
- GUI hashing/batch work stays on background threads so the UI remains responsive.

---

## Why It Matters

Verifying file integrity is a key step in:
- Detecting tampered or corrupted files  
- Validating software authenticity  
- Ensuring digital forensic accuracy  
- Demonstrating secure programming practices  

---

## Tech Stack

- **Language:** Python 3.9+
- **GUI:** [customtkinter](https://pypi.org/project/customtkinter/)
- **Libraries:**
  - `hashlib` — SHA256 hashing  
  - `pyperclip` — clipboard  
  - `threading` — non-blocking UI work  
  - `tkinterdnd2` — drag-and-drop  
  - `watchdog` — filesystem events for the live monitor  
  - `pytest` — headless unit tests  

---

## Installation

From this folder (`FileIntegrityCheckerSHA256/`):

```bash
python -m pip install -r requirements.txt
```

Dependencies (also listed in `requirements.txt`):

- `customtkinter`
- `pyperclip`
- `tkinterdnd2`
- `watchdog`
- `pytest` (for tests)

### Run the app

```bash
python File_Integrity_Checker__SHA256_.py
```

> If `tkinterdnd2` is missing, the app still runs; drag-and-drop is disabled and Browse / Add Files remain available.

### Run tests (no display required)

```bash
python -m pytest
```

---

## Usage

### Single file

1. **Browse** or drop a file.  
2. **Generate SHA256 Hash**.  
3. Optionally paste a known hash into **Reference Hash** → **Compare Hashes**.  
4. **Copy Hash** / **Export Report** (`report.txt`).

### Batch verify

1. Open **Batch Verify**, **Add Files…** or drop multiple files.  
2. Optionally paste an expected-hash list.  
3. **Verify Batch** — review the status table.  
4. **Export Batch Report** to save a timestamped summary.

### Live monitor

1. Open **Live Monitor**.  
2. **Pick Files…** and/or **Pick Folder…** (or drop onto the window while this tab is active).  
3. **Start Monitor** — baselines are hashed immediately.  
4. When a watched file changes, the log updates; a mismatch raises an alert.  
5. **Stop Monitor** when finished.

### Example single-file report

```
--- File Integrity Report ---
Date: 2026-09-20 17:45:00
File: /path/to/example.iso
SHA256: d2b2c8af3a6120a0d9c6d45d715baf9b1e2d6dcd83ef45fa9e5c0cc2b06d4a34
Status: Hashes match ✅ File integrity verified.
----------------------------------------
```

---

## Project layout

| Path | Role |
| --- | --- |
| `File_Integrity_Checker__SHA256_.py` | customtkinter GUI |
| `integrity_core.py` | Hash / batch / monitor (testable) |
| `tests/` | pytest suite (headless) |
| `requirements.txt` | Pinned runtime + test deps |
| `LICENSE` / `SECURITY.md` | License & security policy |

---

## Future ideas

- Standalone `.exe` build (Windows)
