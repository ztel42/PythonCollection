"""
File Integrity Checker (SHA256) — dark-mode customtkinter GUI.

Features: single-file hash/compare, clipboard, report export,
drag-and-drop, batch verification, and live hash monitor.
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import List, Optional

import customtkinter as ctk
import pyperclip

from integrity_core import (
    HashMonitor,
    batch_verify,
    compare_hashes,
    format_single_report,
    parse_expected_hash_list,
    sha256_file,
)

# Optional drag-and-drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _DND_AVAILABLE = True
except ImportError:  # pragma: no cover
    DND_FILES = None  # type: ignore
    TkinterDnD = None  # type: ignore
    _DND_AVAILABLE = False


def _parse_dnd_paths(data: str) -> List[str]:
    """Parse tkinterdnd2 file-drop payload into path strings."""
    paths: List[str] = []
    if not data:
        return paths
    # Brace-wrapped paths with spaces: {C:/path with space/file.txt} other.txt
    i = 0
    s = data.strip()
    while i < len(s):
        if s[i] == "{":
            j = s.find("}", i + 1)
            if j == -1:
                break
            paths.append(s[i + 1 : j])
            i = j + 1
        else:
            j = s.find(" ", i)
            if j == -1:
                paths.append(s[i:])
                break
            paths.append(s[i:j])
            i = j + 1
        while i < len(s) and s[i] == " ":
            i += 1
    return [p for p in paths if p]


if _DND_AVAILABLE:

    class _CTk(ctk.CTk, TkinterDnD.DnDWrapper):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)

else:

    class _CTk(ctk.CTk):  # type: ignore[no-redef]
        pass


class FileIntegrityChecker(_CTk):
    def __init__(self):
        super().__init__()

        self.title("File Integrity Checker (SHA256)")
        self.geometry("780x720")
        self.minsize(700, 640)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.file_path = ctk.StringVar()
        self.generated_hash = ctk.StringVar()
        self.reference_hash = ctk.StringVar()
        self.status_message = ctk.StringVar(value="Awaiting file...")
        self.monitor_status = ctk.StringVar(value="Monitor: stopped")
        self._batch_paths: List[str] = []
        self._monitor: Optional[HashMonitor] = None
        self._monitor_folder: Optional[str] = None

        self.create_widgets()
        self._setup_dnd()

    # -----------------------------
    #  UI Setup
    # -----------------------------
    def create_widgets(self):
        title_label = ctk.CTkLabel(
            self, text="🔒 File Integrity Checker", font=("Segoe UI", 24, "bold")
        )
        title_label.pack(pady=(12, 4))
        ctk.CTkLabel(
            self,
            text="Single · Batch · Live Monitor  |  Drop files anywhere on this window",
            font=("Segoe UI", 11),
            text_color="gray70",
        ).pack(pady=(0, 8))

        self.tabs = ctk.CTkTabview(self, width=740, height=560)
        self.tabs.pack(padx=16, pady=8, fill="both", expand=True)

        self.tab_single = self.tabs.add("Single File")
        self.tab_batch = self.tabs.add("Batch Verify")
        self.tab_monitor = self.tabs.add("Live Monitor")

        self._build_single_tab()
        self._build_batch_tab()
        self._build_monitor_tab()

        ctk.CTkLabel(
            self,
            text="Developed by Zachary Telford @ztel42",
            font=("Segoe UI", 10, "italic"),
        ).pack(side="bottom", pady=6)

    def _build_single_tab(self):
        file_frame = ctk.CTkFrame(self.tab_single)
        file_frame.pack(pady=10, padx=12, fill="x")

        ctk.CTkEntry(
            file_frame,
            textvariable=self.file_path,
            placeholder_text="Select or drop a file…",
            width=480,
        ).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(file_frame, text="Browse", command=self.select_file).pack(
            side="right", padx=10
        )

        ctk.CTkButton(
            self.tab_single, text="Generate SHA256 Hash", command=self.start_hash_thread
        ).pack(pady=8)
        ctk.CTkEntry(
            self.tab_single,
            textvariable=self.generated_hash,
            placeholder_text="Generated hash will appear here…",
            width=680,
        ).pack(pady=6)
        ctk.CTkEntry(
            self.tab_single,
            textvariable=self.reference_hash,
            placeholder_text="Enter reference hash for comparison…",
            width=680,
        ).pack(pady=6)
        ctk.CTkButton(
            self.tab_single, text="Compare Hashes", command=self.compare_hashes_ui
        ).pack(pady=8)

        self.status_label = ctk.CTkLabel(
            self.tab_single,
            textvariable=self.status_message,
            font=("Segoe UI", 14, "bold"),
        )
        self.status_label.pack(pady=10)

        btn_frame = ctk.CTkFrame(self.tab_single)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Copy Hash", command=self.copy_hash).pack(
            side="left", padx=10
        )
        ctk.CTkButton(btn_frame, text="Export Report", command=self.export_report).pack(
            side="left", padx=10
        )

    def _build_batch_tab(self):
        top = ctk.CTkFrame(self.tab_batch)
        top.pack(pady=8, padx=12, fill="x")
        ctk.CTkButton(top, text="Add Files…", command=self.batch_add_files).pack(
            side="left", padx=6, pady=8
        )
        ctk.CTkButton(top, text="Clear List", command=self.batch_clear).pack(
            side="left", padx=6, pady=8
        )
        ctk.CTkButton(
            top, text="Verify Batch", command=self.start_batch_thread, fg_color="#1f6aa5"
        ).pack(side="right", padx=6, pady=8)
        ctk.CTkButton(
            top, text="Export Batch Report", command=self.export_batch_report
        ).pack(side="right", padx=6, pady=8)

        ctk.CTkLabel(
            self.tab_batch,
            text="Optional expected hashes (one per line: SHA256  filename  |  file=hash  |  file:hash)",
            font=("Segoe UI", 11),
            anchor="w",
        ).pack(padx=14, fill="x")
        self.expected_box = ctk.CTkTextbox(self.tab_batch, height=80, width=680)
        self.expected_box.pack(padx=12, pady=4, fill="x")

        self.batch_table = ctk.CTkTextbox(self.tab_batch, height=280, width=680)
        self.batch_table.pack(padx=12, pady=8, fill="both", expand=True)
        self.batch_table.insert("1.0", "Drop or add files, then click Verify Batch.\n")
        self.batch_table.configure(state="disabled")
        self._last_batch_report: Optional[str] = None

    def _build_monitor_tab(self):
        info = ctk.CTkLabel(
            self.tab_monitor,
            text="Watch selected file(s) or a folder. On change, SHA256 is recomputed "
            "and compared to the baseline captured at Start.",
            font=("Segoe UI", 12),
            wraplength=680,
            justify="left",
        )
        info.pack(padx=14, pady=8, anchor="w")

        row = ctk.CTkFrame(self.tab_monitor)
        row.pack(padx=12, pady=6, fill="x")
        ctk.CTkButton(row, text="Pick Files…", command=self.monitor_pick_files).pack(
            side="left", padx=4, pady=8
        )
        ctk.CTkButton(row, text="Pick Folder…", command=self.monitor_pick_folder).pack(
            side="left", padx=4, pady=8
        )
        ctk.CTkButton(
            row, text="Start Monitor", command=self.start_monitor, fg_color="#2d8a4e"
        ).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(
            row, text="Stop Monitor", command=self.stop_monitor, fg_color="#a33"
        ).pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(
            self.tab_monitor,
            textvariable=self.monitor_status,
            font=("Segoe UI", 13, "bold"),
        ).pack(pady=4)

        self.monitor_targets = ctk.CTkTextbox(self.tab_monitor, height=80, width=680)
        self.monitor_targets.pack(padx=12, pady=4, fill="x")
        self.monitor_targets.insert("1.0", "(no targets)\n")

        self.monitor_log = ctk.CTkTextbox(self.tab_monitor, height=260, width=680)
        self.monitor_log.pack(padx=12, pady=8, fill="both", expand=True)
        self.monitor_log.insert("1.0", "Monitor log will appear here.\n")
        self.monitor_log.configure(state="disabled")

        self._monitor_file_list: List[str] = []

    # -----------------------------
    #  Drag and drop
    # -----------------------------
    def _setup_dnd(self):
        if not _DND_AVAILABLE:
            self.status_message.set("Awaiting file… (install tkinterdnd2 for drag-drop)")
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:  # noqa: BLE001
            pass

    def _on_drop(self, event):  # noqa: ANN001
        paths = _parse_dnd_paths(event.data)
        files = [p for p in paths if os.path.isfile(p)]
        dirs = [p for p in paths if os.path.isdir(p)]
        if not files and not dirs:
            return
        tab = self.tabs.get()
        if tab == "Batch Verify" or len(files) > 1:
            self.tabs.set("Batch Verify")
            for f in files:
                if f not in self._batch_paths:
                    self._batch_paths.append(f)
            self._refresh_batch_list_preview()
            self.status_message.set(f"Batch: {len(self._batch_paths)} file(s) ready.")
        elif tab == "Live Monitor":
            for f in files:
                if f not in self._monitor_file_list:
                    self._monitor_file_list.append(f)
            if dirs:
                self._monitor_folder = dirs[0]
            self._refresh_monitor_targets()
        else:
            if files:
                self.file_path.set(files[0])
                self.status_message.set("File dropped: Ready to hash.")
                if len(files) > 1:
                    for f in files[1:]:
                        if f not in self._batch_paths:
                            self._batch_paths.append(f)
                    self._refresh_batch_list_preview()

    # -----------------------------
    #  Single-file actions
    # -----------------------------
    def select_file(self):
        file = filedialog.askopenfilename()
        if file:
            self.file_path.set(file)
            self.status_message.set("File selected: Ready to hash.")

    def start_hash_thread(self):
        threading.Thread(target=self.generate_hash, daemon=True).start()

    def generate_hash(self):
        file = self.file_path.get()
        if not os.path.isfile(file):
            self.after(0, lambda: messagebox.showerror("Error", "Please select a valid file."))
            return
        self.after(0, lambda: self.status_message.set("Computing SHA256… ⏳"))
        try:
            computed = sha256_file(file)
            self.after(0, lambda: self.generated_hash.set(computed))
            self.after(0, lambda: self.status_message.set("Hash generated successfully ✅"))
        except Exception as e:  # noqa: BLE001
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.status_message.set("Hash generation failed ❌"))

    def compare_hashes_ui(self):
        gen_hash = self.generated_hash.get().strip()
        ref_hash = self.reference_hash.get().strip()
        if not gen_hash or not ref_hash:
            messagebox.showwarning("Warning", "Both hashes must be provided.")
            return
        if compare_hashes(gen_hash, ref_hash):
            self.status_label.configure(text_color="green")
            self.status_message.set("Hashes match ✅ File integrity verified.")
        else:
            self.status_label.configure(text_color="red")
            self.status_message.set("Hashes do not match ❌ Possible tampering detected.")

    def copy_hash(self):
        hash_val = self.generated_hash.get()
        if hash_val:
            pyperclip.copy(hash_val)
            messagebox.showinfo("Copied", "Hash copied to clipboard.")
        else:
            messagebox.showwarning("Warning", "No hash to copy.")

    def export_report(self):
        file = self.file_path.get()
        hash_val = self.generated_hash.get()
        status = self.status_message.get()
        if not file or not hash_val:
            messagebox.showwarning("Warning", "No file or hash to export.")
            return
        try:
            with open("report.txt", "a", encoding="utf-8") as report:
                report.write(format_single_report(file, hash_val, status))
            messagebox.showinfo("Exported", "Report saved as report.txt")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Error", f"Could not export report: {e}")

    # -----------------------------
    #  Batch
    # -----------------------------
    def batch_add_files(self):
        files = filedialog.askopenfilenames()
        for f in files:
            if f not in self._batch_paths:
                self._batch_paths.append(f)
        self._refresh_batch_list_preview()

    def batch_clear(self):
        self._batch_paths.clear()
        self._last_batch_report = None
        self._set_batch_table("List cleared. Add or drop files.\n")

    def _refresh_batch_list_preview(self):
        lines = [f"Queued ({len(self._batch_paths)}):\n"]
        for p in self._batch_paths:
            lines.append(f"  • {p}\n")
        lines.append("\nClick Verify Batch to hash / compare.\n")
        self._set_batch_table("".join(lines))

    def _set_batch_table(self, text: str):
        self.batch_table.configure(state="normal")
        self.batch_table.delete("1.0", "end")
        self.batch_table.insert("1.0", text)
        self.batch_table.configure(state="disabled")

    def start_batch_thread(self):
        if not self._batch_paths:
            messagebox.showwarning("Warning", "Add at least one file to the batch.")
            return
        threading.Thread(target=self._run_batch, daemon=True).start()

    def _run_batch(self):
        expected_text = self.expected_box.get("1.0", "end")
        expected = parse_expected_hash_list(expected_text)
        result = batch_verify(self._batch_paths, expected if expected else None)
        report = result.to_report_text()
        self._last_batch_report = report

        # Side-by-side status table
        header = f"{'Status':<10} {'File':<40} SHA256 / Expected\n"
        header += "-" * 90 + "\n"
        rows = []
        for r in result.results:
            name = Path(r.path).name
            if len(name) > 38:
                name = name[:35] + "…"
            detail = r.computed_hash or (r.error or "")
            if r.expected_hash:
                detail += f"\n{'':10} {'':40} expected: {r.expected_hash}"
            rows.append(f"{r.status:<10} {name:<40} {detail}\n")
        summary = (
            f"\nMatches: {result.match_count}  "
            f"Mismatches: {result.mismatch_count}  "
            f"Errors: {result.error_count}  "
            f"Hashed(no ref): {sum(1 for x in result.results if x.status == 'HASHED')}\n"
        )
        table = header + "".join(rows) + summary
        self.after(0, lambda: self._set_batch_table(table))

    def export_batch_report(self):
        if not self._last_batch_report:
            messagebox.showwarning("Warning", "Run Verify Batch before exporting.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile="batch_report.txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._last_batch_report)
            messagebox.showinfo("Exported", f"Batch report saved to:\n{path}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Error", str(e))

    # -----------------------------
    #  Live monitor
    # -----------------------------
    def monitor_pick_files(self):
        files = filedialog.askopenfilenames()
        for f in files:
            if f not in self._monitor_file_list:
                self._monitor_file_list.append(f)
        self._refresh_monitor_targets()

    def monitor_pick_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self._monitor_folder = folder
            self._refresh_monitor_targets()

    def _refresh_monitor_targets(self):
        lines = []
        if self._monitor_folder:
            lines.append(f"Folder: {self._monitor_folder}\n")
        if self._monitor_file_list:
            lines.append("Files:\n")
            for f in self._monitor_file_list:
                lines.append(f"  • {f}\n")
        if not lines:
            lines = ["(no targets)\n"]
        self.monitor_targets.configure(state="normal")
        self.monitor_targets.delete("1.0", "end")
        self.monitor_targets.insert("1.0", "".join(lines))
        self.monitor_targets.configure(state="normal")

    def _append_monitor_log(self, msg: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.monitor_log.configure(state="normal")
        self.monitor_log.insert("end", f"[{stamp}] {msg}\n")
        self.monitor_log.see("end")
        self.monitor_log.configure(state="disabled")

    def _on_monitor_alert(self, path: str, current: str, baseline: Optional[str], message: str):
        def ui():
            self._append_monitor_log(message)
            if baseline is not None and current and not compare_hashes(current, baseline):
                self.monitor_status.set(f"Monitor: ALERT — change detected")
                try:
                    messagebox.showwarning("Integrity Alert", message)
                except tk.TclError:
                    pass
            else:
                self.monitor_status.set("Monitor: running (event)")

        self.after(0, ui)

    def start_monitor(self):
        if not self._monitor_file_list and not self._monitor_folder:
            messagebox.showwarning(
                "Warning", "Pick at least one file or a folder to monitor."
            )
            return
        self.stop_monitor()
        try:
            mon = HashMonitor(on_alert=self._on_monitor_alert)
            mon.start(
                paths=self._monitor_file_list or None,
                folder=self._monitor_folder,
                establish_baselines=True,
            )
            self._monitor = mon
            n = len(mon.baselines)
            self.monitor_status.set(f"Monitor: running ({n} baseline(s))")
            self._append_monitor_log(f"Started — {n} baseline(s) recorded.")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Monitor Error", str(e))
            self.monitor_status.set("Monitor: error")

    def stop_monitor(self):
        if self._monitor is not None:
            self._monitor.stop()
            self._monitor = None
            self.monitor_status.set("Monitor: stopped")
            self._append_monitor_log("Stopped.")

    def destroy(self):
        self.stop_monitor()
        super().destroy()


if __name__ == "__main__":
    app = FileIntegrityChecker()
    app.mainloop()
