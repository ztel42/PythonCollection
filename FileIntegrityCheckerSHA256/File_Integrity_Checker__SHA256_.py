import customtkinter as ctk
from tkinter import filedialog, messagebox
import hashlib
import pyperclip
import threading
import os
from datetime import datetime

# -----------------------------
#  File Integrity Checker (SHA256)
# -----------------------------

class FileIntegrityChecker(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("File Integrity Checker (SHA256)")
        self.geometry("650x480")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Variables
        self.file_path = ctk.StringVar()
        self.generated_hash = ctk.StringVar()
        self.reference_hash = ctk.StringVar()
        self.status_message = ctk.StringVar(value="Awaiting file...")

        # UI Layout
        self.create_widgets()

    # -----------------------------
    #  UI Setup
    # -----------------------------
    def create_widgets(self):
        title_label = ctk.CTkLabel(self, text="🔒 File Integrity Checker", font=("Segoe UI", 24, "bold"))
        title_label.pack(pady=15)

        # File Selection
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkEntry(file_frame, textvariable=self.file_path, placeholder_text="Select a file...", width=400).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(file_frame, text="Browse", command=self.select_file).pack(side="right", padx=10)

        # Hash Generation
        ctk.CTkButton(self, text="Generate SHA256 Hash", command=self.start_hash_thread).pack(pady=8)
        ctk.CTkEntry(self, textvariable=self.generated_hash, placeholder_text="Generated hash will appear here...", width=580).pack(pady=6)

        # Reference Hash
        ctk.CTkEntry(self, textvariable=self.reference_hash, placeholder_text="Enter reference hash for comparison...", width=580).pack(pady=6)
        ctk.CTkButton(self, text="Compare Hashes", command=self.compare_hashes).pack(pady=8)

        # Status Label
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_message, font=("Segoe UI", 14, "bold"))
        self.status_label.pack(pady=10)

        # Action Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Copy Hash", command=self.copy_hash).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Export Report", command=self.export_report).pack(side="left", padx=10)

        # Footer
        ctk.CTkLabel(self, text="Developed by Zachary Telford @ztel42", font=("Segoe UI", 10, "italic")).pack(side="bottom", pady=8)

    # -----------------------------
    #  File Selection
    # -----------------------------
    def select_file(self):
        file = filedialog.askopenfilename()
        if file:
            self.file_path.set(file)
            self.status_message.set("File selected: Ready to hash.")

    # -----------------------------
    #  Threaded Hash Generation
    # -----------------------------
    def start_hash_thread(self):
        thread = threading.Thread(target=self.generate_hash)
        thread.start()

    # -----------------------------
    #  SHA256 Computation
    # -----------------------------
    def generate_hash(self):
        file = self.file_path.get()
        if not os.path.isfile(file):
            messagebox.showerror("Error", "Please select a valid file.")
            return

        self.status_message.set("Computing SHA256... ⏳")

        sha256_hash = hashlib.sha256()
        try:
            with open(file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            computed = sha256_hash.hexdigest()
            self.generated_hash.set(computed)
            self.status_message.set("Hash generated successfully ✅")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_message.set("Hash generation failed ❌")

    # -----------------------------
    #  Compare Hashes
    # -----------------------------
    def compare_hashes(self):
        gen_hash = self.generated_hash.get().strip()
        ref_hash = self.reference_hash.get().strip()

        if not gen_hash or not ref_hash:
            messagebox.showwarning("Warning", "Both hashes must be provided.")
            return

        if gen_hash.lower() == ref_hash.lower():
            self.status_label.configure(text_color="green")
            self.status_message.set("Hashes match ✅ File integrity verified.")
        else:
            self.status_label.configure(text_color="red")
            self.status_message.set("Hashes do not match ❌ Possible tampering detected.")

    # -----------------------------
    #  Copy Hash
    # -----------------------------
    def copy_hash(self):
        hash_val = self.generated_hash.get()
        if hash_val:
            pyperclip.copy(hash_val)
            messagebox.showinfo("Copied", "Hash copied to clipboard.")
        else:
            messagebox.showwarning("Warning", "No hash to copy.")

    # -----------------------------
    #  Export Report
    # -----------------------------
    def export_report(self):
        file = self.file_path.get()
        hash_val = self.generated_hash.get()
        status = self.status_message.get()

        if not file or not hash_val:
            messagebox.showwarning("Warning", "No file or hash to export.")
            return

        try:
            with open("report.txt", "a", encoding="utf-8") as report:
                report.write(f"\n--- File Integrity Report ---\n")
                report.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                report.write(f"File: {file}\n")
                report.write(f"SHA256: {hash_val}\n")
                report.write(f"Status: {status}\n")
                report.write("-" * 40 + "\n")
            messagebox.showinfo("Exported", "Report saved as report.txt")
        except Exception as e:
            messagebox.showerror("Error", f"Could not export report: {e}")

# -----------------------------
#  Run Application
# -----------------------------
if __name__ == "__main__":
    app = FileIntegrityChecker()
    app.mainloop()