#!/usr/bin/env python3
"""
LED Cycle Launcher – Controls LA-POE LEDs with live progress bar and phase timing.

This script runs a full LED cycle from Green → Yellow → Amber → Red over a user-defined duration.
Each phase receives an equal portion of time. A live progress bar shows elapsed/remaining time.
"""

import subprocess
import time
import argparse
from typing import Tuple, List
import sys


# ========================
# Configuration
# ========================

COLOR_SEQUENCE: List[Tuple[str, int]] = [
    ("green", 10),
    ("yellow", 9),
    ("amber", 8),
    ("red", 7),
]

CONTROLLER_SCRIPT_PATH = "/home/labuser/jazzeryj/la6_controller.py"
DEFAULT_DURATION_MINUTES = 5
PROGRESS_BAR_LENGTH = 40


# ========================
# Helper Functions
# ========================

def run_led_command(color_code: int, verbose: bool) -> None:
    """Run the external controller script to change the LED color."""
    if verbose:
        print(f"Setting LED to code {color_code}...")

    try:
        result = subprocess.run(
            ["python3", CONTROLLER_SCRIPT_PATH, "T", str(color_code)],
            check=True,
            capture_output=verbose,
            text=verbose,
        )

        if verbose:
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"\nFailed to set LED to code {color_code}: {e}")
        sys.exit(1)


def format_time(seconds: float) -> str:
    """Format seconds into MM:SS string for display."""
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"


def update_progress_bar(elapsed: float, total: float, prefix: str = "Progress") -> None:
    """Update a live progress bar in the terminal."""
    percent = min(elapsed / total, 1.0)
    filled_length = int(percent * PROGRESS_BAR_LENGTH)
    bar = "█" * filled_length + "-" * (PROGRESS_BAR_LENGTH - filled_length)
    time_remaining = format_time(max(total - elapsed, 0))
    sys.stdout.write(f"\r{prefix} |{bar}| {percent * 100:.1f}% | Remaining: {time_remaining}")
    sys.stdout.flush()


def clear_line() -> None:
    """Clear the current line in the terminal."""
    sys.stdout.write("\r" + " " * (PROGRESS_BAR_LENGTH + 40) + "\r")
    sys.stdout.flush()


def log_phase(phase_num: int, color_name: str, color_code: int) -> None:
    """Log the start of a new LED phase."""
    print(f"\n[Phase {phase_num}] Setting LED to '{color_name}' ({color_code})")


def wait_with_progress(duration_seconds: float, verbose: bool) -> None:
    """Wait for a given duration while showing a live progress bar."""
    start_time = time.monotonic()
    while True:
        elapsed = time.monotonic() - start_time
        if elapsed >= duration_seconds:
            break
        update_progress_bar(elapsed, duration_seconds, prefix="⏳ Waiting")
        time.sleep(0.1)
    clear_line()


def exit_gracefully(*_) -> None:
    """Handle keyboard interrupt gracefully."""
    print("\n\nLED cycle interrupted by user. Exiting...")
    sys.exit(0)


# ========================
# Main Logic
# ========================

def run_led_cycle(duration_minutes: float, verbose: bool) -> None:
    """Run the full LED cycle with configurable timing and visual feedback."""
    total_seconds = duration_minutes * 60
    interval_seconds = total_seconds / len(COLOR_SEQUENCE)

    print(f"\nStarting LED cycle over {duration_minutes:.1f} minute(s):")
    print("Colors: Green (10) → Yellow (9) → Amber (8) → Red (7)\n")

    for i, (color_name, color_code) in enumerate(COLOR_SEQUENCE):
        log_phase(i + 1, color_name, color_code)
        run_led_command(color_code, verbose)

        if i < len(COLOR_SEQUENCE) - 1:
            print(f"Next change in {interval_seconds / 60:.1f} minutes:")
            wait_with_progress(interval_seconds, verbose)

    print("\nLED cycle complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Control LA-POE LEDs with a timed color cycle.")
    parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=DEFAULT_DURATION_MINUTES,
        help=f"Total cycle duration in minutes (default: {DEFAULT_DURATION_MINUTES})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed logging including script output",
    )
    args = parser.parse_args()

    try:
        run_led_cycle(args.duration, args.verbose)
    except KeyboardInterrupt:
        exit_gracefully()


if __name__ == "__main__":
    main()
