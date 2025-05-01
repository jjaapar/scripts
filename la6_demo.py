#!/usr/bin/python3

#!/usr/bin/env python3

import time
import sys
from your_controller_module import PNSController, PnsRunControlData  # Adjust this import

# Spinner characters
SPINNER_FRAMES = ['|', '/', '-', '\\']

def spinner(delay=0.1, duration=2):
    """Show a spinner animation for a given duration."""
    end_time = time.time() + duration
    while time.time() < end_time:
        for frame in SPINNER_FRAMES:
            sys.stdout.write(f'\r{frame} Working...')
            sys.stdout.flush()
            time.sleep(delay)
    sys.stdout.write('\rDone!         \n')  # Clean line after spinner finishes

def main():
    """Enhanced test script for PNSController with spinner, delays, and loop test."""

    ip_address = "172.17.32.127"  # Replace with your device IP

    try:
        with PNSController(ip=ip_address) as controller:
            print("Connected to device.")
            time.sleep(1)

            # Test 1: Get device status
            print("Getting device status...")
            status = controller.pns_get_data_command()
            print("Device Status Retrieved Successfully!")
            print(f"Current Mode: {'Smart' if status.mode else 'LED'}")
            time.sleep(1)

            # Test 2: Send Mute ON
            print("Muting device...")
            controller.pns_mute_command(1)
            print("Device muted.")
            time.sleep(1)

            # Test 3: Send initial LED pattern
            print("Sending initial LED pattern...")
            control_data = PnsRunControlData(
                led1=2, led2=3, led3=1, led4=4, led5=5, buzzer=0
            )
            controller.pns_run_control_command(control_data)
            print("Initial LED pattern sent.")
            time.sleep(1)

            # Test 4: Loop test with spinner
            print("\nStarting LED pattern loop test...")
            patterns = [
                (1, 1, 1, 1, 1, 1),
                (2, 2, 2, 2, 2, 0),
                (3, 3, 3, 3, 3, 1),
                (4, 4, 4, 4, 4, 0),
                (5, 5, 5, 5, 5, 1),
            ]

            for cycle in range(3):  # Loop 3 times
                print(f"\nCycle {cycle+1}:")
                for led1, led2, led3, led4, led5, buzzer in patterns:
                    print(f"Setting LEDs: {led1}-{led2}-{led3}-{led4}-{led5}, Buzzer: {buzzer}")
                    control_data = PnsRunControlData(led1, led2, led3, led4, led5, buzzer)
                    controller.pns_run_control_command(control_data)
                    spinner(delay=0.1, duration=2)  # Show spinner for 2 seconds

            # Test 5: Unmute device at the end
            print("\nUnmuting device...")
            controller.pns_mute_command(0)
            print("Device unmuted.")
            time.sleep(1)

            print("\nTest completed successfully!")

    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    main()
