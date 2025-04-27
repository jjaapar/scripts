#!/usr/bin/env python3
"""
Patlite Transition Wrapper - Gradually transitions lights from green to amber to red.
(Buzzer-free version)
"""

import subprocess
import time
import argparse
from datetime import datetime, timedelta

# Default configuration
DEFAULT_IP = "192.168.1.100"  # Default Patlite IP
SCRIPT_PATH = "./patlite_controller.py"  # Path to the control script
DEFAULT_DURATION = 10  # Default duration in minutes
UPDATE_INTERVAL = 5  # Seconds between updates

def run_command(args):
    """Run the patlite control command and return success status."""
    try:
        result = subprocess.run(
            [SCRIPT_PATH] + args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.stderr}")
        return False

def calculate_transition_progress(start_time, duration):
    """Calculate the transition progress (0.0 to 1.0)."""
    elapsed = datetime.now() - start_time
    return min(1.0, elapsed.total_seconds() / duration.total_seconds())

def set_transition_state(progress, ip_address):
    """
    Set the light state based on transition progress.
    0.0 = fully green
    0.5 = fully amber
    1.0 = fully red
    """
    if progress <= 0.5:
        # Transition from green to amber
        amber_intensity = progress * 2  # 0.0 to 1.0
        green_intensity = 1 - amber_intensity
        args = [
            f"--ip={ip_address}",
            f"--red=off",
            f"--yellow={'on' if amber_intensity > 0.1 else 'off'}",
            f"--green={'on' if green_intensity > 0.1 else 'off'}"
        ]
    else:
        # Transition from amber to red
        red_intensity = (progress - 0.5) * 2  # 0.0 to 1.0
        amber_intensity = 1 - red_intensity
        args = [
            f"--ip={ip_address}",
            f"--red={'on' if red_intensity > 0.1 else 'off'}",
            f"--yellow={'on' if amber_intensity > 0.1 else 'off'}",
            f"--green=off"
        ]
    
    return run_command(args)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Patlite Transition Wrapper - Gradually transitions lights from green to amber to red",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--ip",
        default=DEFAULT_IP,
        help="IP address of the Patlite device"
    )
    
    parser.add_argument(
        "--transition-duration",
        type=int,
        default=DEFAULT_DURATION,
        help="Transition duration in minutes"
    )
    
    return parser.parse_args()

def main():
    """Run the full transition sequence."""
    args = parse_arguments()
    transition_duration = timedelta(minutes=args.transition_duration)
    
    print(f"Starting {transition_duration} transition from green to red")
    print(f"Current time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Will complete at: {(datetime.now() + transition_duration).strftime('%H:%M:%S')}")
    
    # Initial state - green only
    if not run_command([f"--ip={args.ip}", "--red=off", "--yellow=off", "--green=on"]):
        return
    
    start_time = datetime.now()
    
    try:
        while True:
            progress = calculate_transition_progress(start_time, transition_duration)
            print(f"\nProgress: {progress:.1%} | Time remaining: "
                  f"{transition_duration - (datetime.now() - start_time)}")
            
            if not set_transition_state(progress, args.ip):
                print("Transition aborted due to error")
                return
            
            if progress >= 1.0:
                print("\nTransition complete!")
                break
                
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nTransition interrupted by user")
        run_command([f"--ip={args.ip}", "--off"])
    
    # Final state - red only
    run_command([f"--ip={args.ip}", "--red=on", "--yellow=off", "--green=off"])

if __name__ == "__main__":
    main()
