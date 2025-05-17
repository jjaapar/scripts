#!/usr/bin/env python3
"""
LED Cycle Launcher - Controls LA-POE LEDs via la6_controller.py with live progress bar.

Cycles through Green → Yellow → Amber → Red over a configurable duration,
with optional verbose mode, accurate timing, and real-time progress display.
"""

import subprocess
import time
import argparse
import sys


# ========================
# Configuration
# ========================

COLOR_SEQUENCE = [
    ('green', 10),
    ('yellow', 9),
    ('amber', 8),
    ('red', 7)
]

CONTROLLER_SCRIPT = "/home/labuser/jazzeryj/la6_controller.py"
DEFAULT_DURATION_MINUTES = 5
PROGRESS_BAR_LENGTH = 40


# ========================
# Helper Functions
# ========================

def run_led_command(color_code: int, verbose: bool):
    """Run the controller script with the given color code."""
    if verbose:
        print(f"🔧 Running command: {CONTROLLER_SCRIPT} T {color_code}")
    try:
        result = subprocess.run([
            "python3", CONTROLLER_SCRIPT, "T", str(color_code)
        ], check=True, capture_output=verbose, text=verbose)

        if verbose and result.stdout:
            print("STDOUT:", result.stdout)
        if verbose and result.stderr:
            print("STDERR:", result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running command for color code {color_code}: {e}")
        sys.exit(1)


def update_progress_bar(elapsed: float, total: float, prefix: str = 'Progress'):
    """Display or update a console progress bar."""
    fraction = min(elapsed / total, 1.0)
    filled_length = int(fraction * PROGRESS_BAR_LENGTH)
    bar = '█' * filled_length + '-' * (PROGRESS_BAR_LENGTH - filled_length)
    percent = f"{fraction * 100:.1f}%"
    time_left = format_time(max(total - elapsed, 0))
    sys.stdout.write(f"\r{prefix} |{bar}| {percent} | Remaining: {time_left}")
    sys.stdout.flush()


def format_time(seconds: float) -> str:
    """Format seconds into MM:SS string."""
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"


def log_phase(phase_num: int, color_name: str, color_code: int):
    """Log current LED phase."""
    print(f"\n[Phase {phase_num}] Setting LED to '{color_name}' ({color_code})")


def exit_gracefully(signum=None, frame=None):
    """Handle keyboard interrupts cleanly."""
    print("\n\n🛑 LED cycle interrupted by user. Exiting...")
    sys.exit(0)


# ========================
# Main Logic
# ========================

def wait_with_progress(duration_seconds: float, verbose: bool):
    """Wait for a given duration while showing a progress bar."""
    start_time = time.monotonic()
    while True:
        elapsed = time.monotonic() - start_time
        if elapsed >= duration_seconds:
            break
        update_progress_bar(elapsed, duration_seconds, prefix="⏳ Waiting")
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * (PROGRESS_BAR_LENGTH + 30) + "\r")  # Clear line
    sys.stdout.flush()


def cycle_leds(duration_minutes: float, verbose: bool):
    """
    Run the full LED cycle over the specified duration.
    Each phase gets equal time.
    """
    total_seconds = duration_minutes * 60
    interval_seconds = total_seconds / len(COLOR_SEQUENCE)

    print(f"\n🔄 Starting LED cycle over {duration_minutes:.1f} minute(s):")
    print("Colors: Green (10) → Yellow (9) → Amber (8) → Red (7)\n")

    for i, (color_name, color_code) in enumerate(COLOR_SEQUENCE):
        log_phase(i + 1, color_name, color_code)
        run_led_command(color_code, verbose)

        if i < len(COLOR_SEQUENCE) - 1:
            print(f"⏳ Next change in {interval_seconds / 60:.1f} minutes:")
            wait_with_progress(interval_seconds, verbose)

    print("\n✅ LED cycle complete.")


def main():
    parser = argparse.ArgumentParser(description="Control LA-POE LEDs with a timed color cycle.")
    parser.add_argument("--duration", "-d", type=float, default=DEFAULT_DURATION_MINUTES,
                        help=f"Duration of the full LED cycle in minutes (default: {DEFAULT_DURATION_MINUTES} min)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable detailed logging (including script output)")

    args = parser.parse_args()

    try:
        cycle_leds(args.duration, args.verbose)
    except KeyboardInterrupt:
        exit_gracefully()


if __name__ == "__main__":
    main()
