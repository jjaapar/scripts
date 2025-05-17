#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time


# Configuration
COLOR_SEQUENCE = [
    ('green', 10),
    ('yellow', 9),
    ('amber', 8),
    ('red', 7)
]

CONTROLLER_SCRIPT = "/home/labuser/jazzeryj/la6_controller.py"
DEFAULT_DURATION_MINUTES = 5


class LEDCycleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LA-POE LED Cycle Controller")
        self.root.geometry("500x400")
        self.running = False
        self.stop_flag = False

        # UI Elements
        self.create_widgets()

    def create_widgets(self):
        # Title Label
        title_label = tk.Label(self.root, text="LED Cycle Controller", font=("Helvetica", 16))
        title_label.pack(pady=10)

        # Duration Entry
        duration_frame = tk.Frame(self.root)
        duration_frame.pack(pady=10)

        tk.Label(duration_frame, text="Duration (minutes):").pack(side=tk.LEFT)
        self.duration_entry = tk.Entry(duration_frame, width=10)
        self.duration_entry.insert(0, str(DEFAULT_DURATION_MINUTES))
        self.duration_entry.pack(side=tk.LEFT, padx=5)

        # Start Button
        self.start_button = tk.Button(self.root, text="Start Cycle", command=self.start_cycle)
        self.start_button.pack(pady=10)

        # Stop Button
        self.stop_button = tk.Button(self.root, text="Stop Cycle", command=self.stop_cycle, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        # Current Color Box
        self.color_box = tk.Canvas(self.root, width=200, height=100, bg="gray")
        self.color_box.pack(pady=10)

        # Phase Progress Bar
        tk.Label(self.root, text="Current Phase Progress").pack()
        self.phase_progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.phase_progress.pack(pady=5)

        # Total Cycle Progress Bar
        tk.Label(self.root, text="Total Cycle Progress").pack()
        self.total_progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.total_progress.pack(pady=5)

        # Status Label
        self.status_label = tk.Label(self.root, text="Ready", fg="blue")
        self.status_label.pack(pady=10)

    def start_cycle(self):
        try:
            self.duration_minutes = float(self.duration_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for duration.")
            return

        if self.duration_minutes <= 0:
            messagebox.showerror("Invalid Input", "Duration must be greater than zero.")
            return

        self.running = True
        self.stop_flag = False
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Running...", fg="green")

        self.cycle_thread = threading.Thread(target=self.run_cycle)
        self.cycle_thread.start()

    def stop_cycle(self):
        self.stop_flag = True
        self.status_label.config(text="Stopping...", fg="orange")

    def update_color_display(self, color_name):
        color_map = {
            'green': '#00FF00',
            'yellow': '#FFFF00',
            'amber': '#FFA500',
            'red': '#FF0000'
        }
        self.color_box.configure(bg=color_map.get(color_name.lower(), 'gray'))

    def run_cycle(self):
        total_seconds = self.duration_minutes * 60
        interval_seconds = total_seconds / len(COLOR_SEQUENCE)
        total_start = time.monotonic()

        for i, (color_name, color_code) in enumerate(COLOR_SEQUENCE):
            if self.stop_flag:
                break

            self.root.after(0, self.update_color_display, color_name)
            self.root.after(0, self.status_label.config, {'text': f"Phase {i+1}/{len(COLOR_SEQUENCE)}: {color_name.capitalize()}", 'fg': 'black'})

            self.run_led_command(color_code)

            if i < len(COLOR_SEQUENCE) - 1:
                self.run_phase_timer(interval_seconds, total_seconds, i + 1)

        if not self.stop_flag:
            self.root.after(0, self.status_label.config, {'text': "✅ Cycle complete!", 'fg': 'green'})
        else:
            self.root.after(0, self.status_label.config, {'text': "🛑 Stopped by user.", 'fg': 'red'})

        self.root.after(0, self.start_button.config, {'state': tk.NORMAL})
        self.root.after(0, self.stop_button.config, {'state': tk.DISABLED})

        self.running = False

    def run_phase_timer(self, interval_seconds, total_seconds, phase_number):
        start_time = time.monotonic()
        while True:
            elapsed = time.monotonic() - start_time
            total_elapsed = time.monotonic() - total_start

            if elapsed >= interval_seconds or self.stop_flag:
                break

            phase_percent = min(elapsed / interval_seconds, 1.0) * 100
            total_percent = min(total_elapsed / total_seconds, 1.0) * 100

            self.root.after(0, self.phase_progress["value"].__setattr__, phase_percent)
            self.root.after(0, self.total_progress["value"].__setattr__, total_percent)

            time.sleep(0.1)

        self.root.after(0, self.phase_progress["value"].__setattr__, 0)

    def run_led_command(self, color_code):
        try:
            subprocess.run([
                "python3", CONTROLLER_SCRIPT, "T", str(color_code)
            ], check=True)
        except subprocess.CalledProcessError as e:
            self.stop_flag = True
            self.root.after(0, messagebox.showerror, "Error", f"Failed to set LED color code {color_code}: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LEDCycleApp(root)
    root.mainloop()
