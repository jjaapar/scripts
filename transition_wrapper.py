#!/usr/bin/env python3
"""
Patlite Smooth Transition Wrapper
================================
Gradually transitions from green to red over specified time using color mixing
for smooth brightness changes (no blinking patterns).
"""

import time
import math
from patlite_control import PatliteController

def calculate_intensity(step, total_steps, curve='sine'):
    """Calculate smooth intensity value (0-1) using different curve functions."""
    progress = step / total_steps
    if curve == 'linear':
        return progress
    elif curve == 'sine':
        return math.sin(progress * math.pi/2)
    elif curve == 'quadratic':
        return progress**2
    else:
        return progress

def gradual_transition(controller, transition_time=600):
    """
    Smooth transition from green to red using color mixing and brightness control.
    
    Args:
        controller: Initialized PatliteController
        transition_time: Total transition time in seconds
    """
    steps = 120  # Increased steps for smoother transition
    interval = transition_time / steps
    
    print(f"🎨 Beginning {transition_time//60} minute color transition")
    print(f"🖌️  Updating every {interval:.1f}s with mixed colors")

    try:
        for step in range(steps + 1):
            # Calculate normalized position (0-1)
            pos = step / steps
            
            # Green to Amber to Red color mixing
            if pos < 0.5:
                # Green to Amber (green fades, red increases)
                green = 1 - pos*2
                red = pos*2
                amber = pos*2
            else:
                # Amber to Red (amber fades, red dominates)
                green = 0
                red = 1
                amber = 1 - (pos-0.5)*2
            
            # Apply smooth intensity curves
            green_intensity = calculate_intensity(1-green, 1, 'sine')
            red_intensity = calculate_intensity(red, 1, 'quadratic')
            amber_intensity = calculate_intensity(amber, 1, 'sine')
            
            # Scale to 0-255 (8-bit brightness)
            green_val = int(green_intensity * 255)
            red_val = int(red_intensity * 255)
            amber_val = int(amber_intensity * 255)
            
            # Create mixed color command
            # (This assumes your patlite_control.py has been modified to accept RGB values)
            controller.set_leds_custom(
                red1=red_val,
                red2=int(red_val*0.8),  # Slightly dimmer second red
                amber=amber_val,
                green=green_val,
                blue=0  # Blue not used in transition
            )
            
            # Visual progress indicator
            print(f"⏳ {step*100/steps:.0f}% | "
                  f"RGB Mix: R{red_val:03d}/A{amber_val:03d}/G{green_val:03d} | "
                  f"Color: {'🟢' if green_val>150 else '🟠' if amber_val>150 else '🔴'}")
            
            time.sleep(interval)
        
        print("✅ Transition complete - Pure red achieved")
    
    except KeyboardInterrupt:
        print("\n🛑 Transition interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main execution with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Smooth color transition for Patlite LA6-POE",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--ip", default='192.168.1.100',
                       help="Device IP address")
    parser.add_argument("--port", type=int, default=10000,
                       help="Device port")
    parser.add_argument("--time", type=int, default=600,
                       help="Transition duration in seconds")
    
    args = parser.parse_args()
    
    controller = PatliteController()
    try:
        controller.connect(args.ip, args.port)
        print(f"💡 Starting smooth transition (CTRL+C to stop)")
        gradual_transition(controller, args.time)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        controller.disconnect()

if __name__ == '__main__':
    import argparse
    main()
