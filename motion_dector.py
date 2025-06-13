#!/usr/bin/env python3

import serial
import subprocess
from datetime import datetime
import time

# Serial port configuration
SERIAL_PORT = '/dev/ttyACM2'
BAUD_RATE = 9600
USERNAME = 'labuser'

def send_wall_message(message):
    """Send a wall message to the specified user."""
    try:
        subprocess.run(['wall', '-n', f'/dev/pts/[0-9]*'])
        subprocess.run(['write', USERNAME], input=message.encode(), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error sending wall message: {e}")

def monitor_motion():
    """Monitor the serial port for motion detection messages."""
    try:
        # Open serial port
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"Monitoring {SERIAL_PORT} for motion detection...")
            
            while True:
                if ser.in_waiting:
                    # Read line from serial port
                    line = ser.readline().decode('utf-8').strip()
                    
                    # Check for motion detection message
                    if "Motion detected!" in line:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        message = f"\nMOTION ALERT: Movement detected at {timestamp}\n"
                        send_wall_message(message)
                        print(message)
                
                time.sleep(0.1)  # Small delay to prevent CPU hogging

    except serial.SerialException as e:
        print(f"Error opening serial port {SERIAL_PORT}: {e}")
        exit(1)

if __name__ == "__main__":
    try:
        monitor_motion()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        exit(0)
