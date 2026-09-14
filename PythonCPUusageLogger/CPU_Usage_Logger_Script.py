import psutil
import csv
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

class CPUUsageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CPU Usage Logger")
        self.is_running = False
        self.filename = "cpu_usage.csv"
        self.interval_seconds = 2  # How often to record CPU usage

        # Buttons
        self.start_button = tk.Button(root, text="Start Logging", command=self.start_logging, width=20)
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(root, text="Stop Logging", command=self.stop_logging, width=20, state=tk.DISABLED)
        self.stop_button.pack(pady=10)

        self.status_label = tk.Label(root, text="Status: Idle", fg="blue")
        self.status_label.pack(pady=10)

    def start_logging(self):
        if not self.is_running:
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="Status: Logging...", fg="green")
            threading.Thread(target=self.collect_cpu_usage, daemon=True).start()

    def stop_logging(self):
        if self.is_running:
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Stopped", fg="red")
            messagebox.showinfo("Stopped", "CPU usage logging stopped.")

    def collect_cpu_usage(self):
        # Create or append to CSV file
        with open(self.filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "CPU Usage (%)"])

            while self.is_running:
                cpu_usage = psutil.cpu_percent(interval=None)
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([timestamp, cpu_usage])
                print(f"{timestamp} | CPU Usage: {cpu_usage}%")
                time.sleep(self.interval_seconds)

if __name__ == "__main__":
    root = tk.Tk()
    app = CPUUsageApp(root)
    root.mainloop()
