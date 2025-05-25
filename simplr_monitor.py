#!/usr/bin/env python3
"""
Simple Temperature Monitor

Checks temperature on 3 devices every 5 minutes.
Powers off system if any device gets too hot.
"""

import serial
import subprocess
import logging
import time
import signal
import sys
import re
from datetime import datetime

# Settings
DEVICES = ["txpaa1", "txpaa2", "txpaa3"]
MAX_TEMP = 180.0
CHECK_EVERY = 300  # seconds (5 minutes)

# Files
LOG_FILE = '/var/log/temperature_monitor.log'
TEMP_FILE = '/var/log/temperature_results.txt'

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# Handle Ctrl+C gracefully
def shutdown(signum, frame):
    logging.info("Shutting down")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)


def get_temperature(device):
    """Get temperature from one device"""
    
    try:
        with serial.Serial(f"/dev/{device}", 115200, timeout=1) as conn:
            time.sleep(1)  # Let device wake up
            conn.write(b'R\n')  # Ask for temperature
            response = conn.readline().decode().strip()
            
            # Find the number in the response
            match = re.search(r'\d+\.?\d*', response)
            if match:
                return float(match.group())
            else:
                logging.warning(f"No temperature found in {device} response: {response}")
                return None
                
    except Exception as e:
        logging.error(f"Failed to read {device}: {e}")
        return None


def power_off():
    """Emergency power off"""
    
    try:
        subprocess.run(['/usr/sbin/powercycle', 'chroma', '--power-off'], 
                      check=True, capture_output=True)
        logging.critical("SYSTEM POWERED OFF DUE TO OVERHEATING")
    except Exception as e:
        logging.error(f"Power off failed: {e}")


def check_all_devices():
    """Check temperature on all devices"""
    
    emergency = False
    
    for device in DEVICES:
        temp = get_temperature(device)
        
        if temp is None:
            continue  # Skip failed readings
            
        # Log the temperature
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save to results file
        with open(TEMP_FILE, 'a') as f:
            f.write(f"{timestamp} - [{device}] {temp}°C\n")
        
        # Log to main log
        logging.info(f"[{device}] {temp}°C")
        
        # Check if too hot
        if temp > MAX_TEMP:
            logging.warning(f"[{device}] TOO HOT: {temp}°C (max: {MAX_TEMP}°C)")
            emergency = True
    
    # Power off if any device is overheating
    if emergency:
        power_off()


def main():
    """Main monitoring loop"""
    
    logging.info("Temperature monitor started")
    
    try:
        while True:
            check_all_devices()
            time.sleep(CHECK_EVERY)
            
    except KeyboardInterrupt:
        logging.info("Stopped by user")
    except Exception as e:
        logging.critical(f"Critical error: {e}")


if __name__ == "__main__":
    main()
