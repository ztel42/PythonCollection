# FileIntegrityCheckerSHA256
Python application used to compare SHA256 hashes in files and export to and append to .txt reports 

# File Integrity Checker (SHA256)

A modern, lightweight **Python desktop application** designed to verify **file integrity** using **SHA256 cryptographic hashing**.  
Built with a sleek **dark-mode GUI** powered by [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter), this tool helps ensure files remain authentic and untampered — an essential practice in **cybersecurity** and **digital forensics**.

---

## Features

✅ **Modern UI** — Clean, dark-mode interface built with `customtkinter`  
✅ **File Hashing (SHA256)** — Quickly compute and display file hashes  
✅ **Integrity Verification** — Compare against a known hash for tamper detection  
✅ **Clipboard Support** — Copy computed hashes instantly  
✅ **Report Exporting** — Save results (with timestamps) to `report.txt`  
✅ **Threaded Processing** — Non-blocking performance for large files  
✅ **Cross-Platform** — Works on Windows, macOS, and Linux  

---

## Why It Matters

Verifying file integrity is a key step in:
- Detecting tampered or corrupted files  
- Validating software authenticity  
- Ensuring digital forensic accuracy  
- Demonstrating secure programming practices  

This project showcases cybersecurity awareness, practical cryptographic implementation, and secure software design principles.

---

## Tech Stack

- **Language:** Python 3.8+
- **GUI Framework:** [customtkinter](https://pypi.org/project/customtkinter/)
- **Libraries Used:**
  - `hashlib` — for SHA256 hashing  
  - `pyperclip` — for clipboard operations  
  - `threading` — for async processing  
  - `datetime`, `os` — for system utilities

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/<yourusername>/file-integrity-checker.git
   cd file-integrity-checker
Install dependencies:

bash

pip install customtkinter pyperclip
Run the app:

bash

python file_integrity_checker.py
Usage
Click Browse to select a file.

Click Generate SHA256 Hash — the hash will appear instantly.

Optionally, paste a known hash into the Reference Hash field.

Click Compare Hashes to verify file integrity.

Use Copy Hash to copy it to your clipboard.

Use Export Report to save a timestamped report to report.txt.

Example Output:

--- File Integrity Report ---
Date: 2025-11-04 14:22:58
File: C:\Users\Admin\Downloads\example.iso
SHA256: d2b2c8af3a6120a0d9c6d45d715baf9b1e2d6dcd83ef45fa9e5c0cc2b06d4a34
Status: Hashes match ✅ File integrity verified.
----------------------------------------
Future Enhancements
Drag-and-drop file support

Multiple file batch verification

Real-time hash monitor

Standalone .exe build (for Windows users)
