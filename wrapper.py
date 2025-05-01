#!/usr/bin/env python3
"""
LED Cycle Controller - A script to control LA-POE LEDs with a gradual transition
from Green to Yellow to Amber to Red over 10 minutes.
"""

import time
import subprocess

# LED Pattern Mapping (based on your system, these values may need to be updated)
LED_PATTERNS = {
    'green': 1,
    'yellow': 2,
    'amber': 3,
    'red': 4,
}

# Total cycle time in seconds (10 minutes)
TOTAL_CYCLE_TIME = 10 * 60  # 10 minutes

# Interval to change LED colors (2.5 minutes per change)
INTERVAL = TOTAL_CYCLE_TIME / 4

def set_led_color(color: str):
    """Set the LED color using the controller script."""
    led_pattern = LED_PATTERNS.get(color)
    if led_pattern is None:
        print(f"Error: Invalid LED color '{color}'")
        return
    
    # Call the controller script to send the LED control command
    try:
        print(f"Setting LED color to {color}...")
        subprocess.run([
            "python3", "controller.py", "S", str(led_pattern), str(led_pattern), str(led_pattern), str(led_pattern), str(led_pattern), "1"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error setting LED color to {color}: {e}")

def cycle_leds():
    """Cycle the LEDs through Green, Yellow, Amber, and Red over 10 minutes."""
    colors = ['green', 'yellow', 'amber', 'red']
    
    for color in colors:
        set_led_color(color)
        print(f"Waiting for {INTERVAL / 60} minutes before changing to next color...\n")
        time.sleep(INTERVAL)

def main():
    """Main function to start the LED cycle."""
    print("Starting LED cycle (Green -> Yellow -> Amber -> Red) over 10 minutes...\n")
    cycle_leds()
    print("\nLED cycle complete!")

if __name__ == '__main__':
    main()
