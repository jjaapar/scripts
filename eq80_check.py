#!/usr/bin/env python3
"""
Temperature Monitoring Service with Multiple Device Support

Monitors three serial-connected temperature devices: txpaa1, txpaa2, txpaa3.
If any device reports a temperature above the safe limit,
this script will run a system power-cycle command.

Logs:
- Main log: /var/log/temperature_monitor.log
- Temperature history: /var/log/temperature_results.txt
"""

import serial
import subprocess
import logging
from datetime import datetime
import time
import signal
import sys
import re

# ==============================================================================
# 🛠️ Configuration Section
# ==============================================================================

# Log files where the program records its actions
LOG_FILE = '/var/log/temperature_monitor.log'        # Logs what the service does
RESULTS_FILE = '/var/log/temperature_results.txt'    # Stores historical readings

# List of temperature sensors to monitor
# These correspond to serial ports under /dev/
DEVICES = ["txpaa1", "txpaa2", "txpaa3"]

# Communication settings for talking to the devices
BAUD_RATE = 115200                   # Speed of communication
DEVICE_COMMAND = 'R\n'               # Command to request temperature reading

# Safety settings
TEMPERATURE_THRESHOLD = 180.0        # Max safe temperature in degrees Celsius
CHECK_INTERVAL = 300                 # How often to check (in seconds, default: 5 minutes)

# System command to run if any device gets too hot
POWER_CYCLE_COMMAND = ['/usr/sbin/powercycle', 'chroma', '--power-off']


# ==============================================================================
# 📜 Logging Setup
# ==============================================================================
# Set up logging so we can track everything the script does
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# ==============================================================================
# ⚠️ Graceful Shutdown Handling
# ==============================================================================
def handle_termination_signal(signum, frame):
    """
    If someone tries to stop the script (like pressing Ctrl+C or sending a kill signal),
    this function handles it cleanly and logs the shutdown.
    
    Args:
        signum: Signal number (e.g., SIGINT, SIGTERM)
        frame: Current stack frame (not used here)
    """
    logging.info(f"Received termination signal {signum}. Shutting down service.")
    sys.exit(0)

# Register handlers for keyboard interrupt and system terminate signals
signal.signal(signal.SIGTERM, handle_termination_signal)
signal.signal(signal.SIGINT, handle_termination_signal)


# ==============================================================================
# 💬 Communicating with the Devices
# ==============================================================================
def query_temperature_sensor(device_name):
    """
    Connects to a single serial device and asks for its current temperature.
    
    Args:
        device_name: Name of the device (e.g., txpaa1)
    
    Returns:
        The raw string response from the device, or None if something went wrong.
    """

    port_path = f"/dev/{device_name}"  # Full path to serial port

    try:
        # Open serial connection
        with serial.Serial(port_path, BAUD_RATE, timeout=1) as serial_connection:
            time.sleep(2)  # Give the device time to initialize

            # Clear old data before starting
            serial_connection.reset_input_buffer()
            serial_connection.reset_output_buffer()

            # Send command to get temperature
            serial_connection.write(DEVICE_COMMAND.encode())

            # Read the device's reply
            response = serial_connection.readline().decode().strip()

        # For debugging: log the raw response
        logging.debug(f"{device_name} raw response: {response}")
        return response

    except serial.SerialException as e:
        logging.error(f"Serial communication failure on {device_name}: {str(e)}")
        return None
    except Exception as e:
        logging.exception(f"Unexpected error with {device_name}: {str(e)}")
        return None


# ==============================================================================
# ⚙️ Power Cycle Trigger
# ==============================================================================
def initiate_power_cycle():
    """
    Runs the power-cycle command to shut off power if an overheat is detected.
    This helps prevent damage from overheating hardware.
    """
    try:
        # Run the power-cycle silently without showing output
        subprocess.run(
            POWER_CYCLE_COMMAND,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logging.info("Successfully initiated system power cycle")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to execute power cycle: {str(e)}")


# ==============================================================================
# 🔍 Main Monitoring Logic
# ==============================================================================
def process_temperature_reading():
    """
    Checks the temperature of each connected device.
    If any device goes above the safe limit, prepares to trigger a power cycle.
    """

    high_temp_detected = False  # Start with assumption that everything is okay

    # Loop through all devices
    for device in DEVICES:
        raw_response = query_temperature_sensor(device)

        if not raw_response:
            logging.warning(f"No valid response from {device}")
            continue  # Skip to next device

        try:
            # Extract numbers from text (handles responses like "Temp: 75.3°C")
            numeric_match = re.search(r'[-+]?\d*\.\d+|\d+', raw_response)

            if not numeric_match:
                raise ValueError(f"Could not find numeric value in response: '{raw_response}'")

            # Convert text to actual temperature number
            current_temp = float(numeric_match.group())

            # Format timestamp for logging
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"{timestamp} - [{device}] Temperature: {current_temp}°C"

            # Save this result to file
            with open(RESULTS_FILE, 'a') as results_file:
                results_file.write(log_entry + '\n')

            # Log the temperature to the main log file
            logging.info(f"[{device}] Current temperature: {current_temp:.2f}°C")

            # Check if it's too hot
            if current_temp > TEMPERATURE_THRESHOLD:
                logging.warning(f"[{device}] High temp: {current_temp:.2f}°C (threshold: {TEMPERATURE_THRESHOLD}°C)")
                high_temp_detected = True  # We'll need to power cycle later

        except ValueError as e:
            logging.error(f"[{device}] Invalid temperature reading: {str(e)}")
        except Exception as e:
            logging.exception(f"[{device}] Error processing temperature: {str(e)}")

    # After checking all devices, decide whether to power cycle
    if high_temp_detected:
        initiate_power_cycle()


# ==============================================================================
# 🕒 Continuous Monitoring Loop
# ==============================================================================
def start_monitoring_service():
    """
    Starts the background monitoring loop.
    Keeps running until manually stopped or system shuts down.
    """

    logging.info("Temperature monitoring service started")

    try:
        while True:
            try:
                process_temperature_reading()  # Do the actual work
            except Exception as e:
                logging.exception(f"Monitoring iteration error: {str(e)}")

            # Wait for the configured amount of time before next check
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logging.info("User requested service shutdown via keyboard interrupt")
    except Exception as e:
        logging.critical(f"Critical service failure: {str(e)}", exc_info=True)
        sys.exit(1)


# ==============================================================================
# 🚀 Entry Point – Start the Program
# ==============================================================================
if __name__ == "__main__":
    start_monitoring_service()
