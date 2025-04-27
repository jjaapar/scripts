#!/usr/bin/env python3
"""
Patlite Transition Wrapper - Gradually transitions lights from green to amber to red.
(Buzzer-free version)
"""

import subprocess
import time
from datetime import datetime, timedelta

# Configuration
PATLITE_IP = "192.168.1.100"  # Change to your Patlite's IP
SCRIPT_PATH = "./patlite_controller.py"  # Path to the control script
TRANSITION_DURATION = timedelta(minutes=10)  # Total transition time
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

def calculate_transition_progress(start_time):
    """Calculate the transition progress (0.0 to 1.0)."""
    elapsed = datetime.now() - start_time
    return min(1.0, elapsed.total_seconds() / TRANSITION_DURATION.total_seconds())

def set_transition_state(progress):
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
            f"--ip={PATLITE_IP}",
            f"--red=off",
            f"--yellow={'on' if amber_intensity > 0.1 else 'off'}",
            f"--green={'on' if green_intensity > 0.1 else 'off'}"
        ]
    else:
        # Transition from amber to red
        red_intensity = (progress - 0.5) * 2  # 0.0 to 1.0
        amber_intensity = 1 - red_intensity
        args = [
            f"--ip={PATLITE_IP}",
            f"--red={'on' if red_intensity > 0.1 else 'off'}",
            f"--yellow={'on' if amber_intensity > 0.1 else 'off'}",
            f"--green=off"
        ]
    
    return run_command(args)

def main():
    """Run the full transition sequence."""
    print(f"Starting {TRANSITION_DURATION} transition from green to red")
    print(f"Current time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Will complete at: {(datetime.now() + TRANSITION_DURATION).strftime('%H:%M:%S')}")
    
    # Initial state - green only
    if not run_command([f"--ip={PATLITE_IP}", "--red=off", "--yellow=off", "--green=on"]):
        return
    
    start_time = datetime.now()
    
    try:
        while True:
            progress = calculate_transition_progress(start_time)
            print(f"\nProgress: {progress:.1%} | Time remaining: "
                  f"{TRANSITION_DURATION - (datetime.now() - start_time)}")
            
            if not set_transition_state(progress):
                print("Transition aborted due to error")
                return
            
            if progress >= 1.0:
                print("\nTransition complete!")
                break
                
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nTransition interrupted by user")
        run_command([f"--ip={PATLITE_IP}", "--off"])
    
    # Final state - red only
    run_command([f"--ip={PATLITE_IP}", "--red=on", "--yellow=off", "--green=off"])

if __name__ == "__main__":
    main()
