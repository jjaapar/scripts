#!/usr/bin/env python3
"""
LED Cycle Launcher - Launches la6_controller.py with different color codes
to simulate a gradual LED transition from Green → Yellow → Amber → Red
over a configurable time period.
"""

import subprocess
import time
import argparse

# Color code mapping
COLOR_SEQUENCE = [
    ('green', 10),
    ('yellow', 9),
    ('amber', 8),
    ('red', 7)
]

CONTROLLER_SCRIPT = "/home/labuser/jazzeryj/la6_controller.py"

DEFAULT_CYCLE_DURATION_MINUTES = 5  # Default cycle duration in minutes

def run_led_command(color_code: int):
    """Run the controller script with the given color code."""
    print(f"Running: {CONTROLLER_SCRIPT} T {color_code}")
    try:
        subprocess.run([
            "python3", CONTROLLER_SCRIPT, "T", str(color_code)
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command for color code {color_code}: {e}")

def cycle_leds(duration_minutes: float):
    """
    Cycle through the LED colors over the specified duration.
    Each color gets an equal amount of time.
    """
    total_seconds = duration_minutes * 60
    interval_seconds = total_seconds / len(COLOR_SEQUENCE)

    print(f"\nStarting LED cycle over {duration_minutes:.1f} minute(s):")
    print("Colors: Green (10) → Yellow (9) → Amber (8) → Red (7)\n")

    for i, (color_name, color_code) in enumerate(COLOR_SEQUENCE):
        print(f"[Phase {i+1}/{len(COLOR_SEQUENCE)}] Setting LED to '{color_name}' ({color_code})")
        run_led_command(color_code)

        if i < len(COLOR_SEQUENCE) - 1:
            print(f"Waiting for {interval_seconds / 60:.2f} minutes before next change...")
            time.sleep(interval_seconds)
            print()

    print("\n✅ LED cycle complete.")

def main():
    parser = argparse.ArgumentParser(description="Control LA-POE LEDs with a timed color cycle.")
    parser.add_argument("--duration", "-d", type=float, default=DEFAULT_CYCLE_DURATION_MINUTES,
                        help=f"Duration of the full LED cycle in minutes (default: {DEFAULT_CYCLE_DURATION_MINUTES} min)")

    args = parser.parse_args()

    cycle_leds(args.duration)

if __name__ == "__main__":
    main()
