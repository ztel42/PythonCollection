# PythonCPUusageLogger
Basic cpu usage logger using Python automatically saves results in a .csv file
CPU Usage Logger
A simple Python application that records your computer's CPU usage over time and saves the data into a .csv file.
Includes a basic GUI with Start and Stop buttons to control when logging happens.

Features
Live CPU Monitoring using psutil

CSV Export with timestamps and CPU usage percentages

Start/Stop Control via a simple tkinter GUI

Non-freezing GUI thanks to background threading

CSV file automatically created (cpu_usage.csv) in the working directory

Installation
Clone or Download the project files.

Install Required Python Package:

bash
Copy
Edit
pip install psutil
tkinter is included with standard Python installations (Windows, Mac, Linux).
If for some reason you don't have it, install Python from python.org.

How to Run
In your terminal or command prompt, navigate to the project folder and run:

bash
Copy
Edit
python cpu_usage_logger.py
(Replace cpu_usage_logger.py with the actual filename if it's different.)

How It Works
Press Start Logging to begin recording CPU usage every 2 seconds.

Press Stop Logging to end the recording.

The data will be saved in a file called cpu_usage.csv, formatted like:


Timestamp	CPU Usage (%)
2025-04-29 12:00:01	15.4
2025-04-29 12:00:03	20.1

Future Improvements
Add "Save As" option to choose custom filename/location

Live graph of CPU usage (like a mini Task Manager)

Adjustable interval settings via GUI

Requirements
Python 3.7+

psutil library

tkinter (included with Python)

License
This project is free to use and modify.

