#!/usr/bin/env python3
"""
Temperature Monitoring Service

Monitors temperature readings from a serial device and initiates power cycling
if temperature exceeds safe thresholds. Maintains detailed logs and stores
historical temperature data.
"""

import serial
import subprocess
import logging
from datetime import datetime
import time
import signal
import sys
import re

# ============================================================================
# Configuration Section
# ============================================================================

# Log files configuration
LOG_FILE = '/var/log/temperature_monitor.log'        # Service activity log
RESULTS_FILE = '/var/log/temperature_results.txt'    # Temperature history storage

# Device communication settings
SERIAL_PORT = 'ttyACM0'              # Serial port name for temperature sensor
BAUD_RATE = 115200                   # Communication speed (bits per second)
DEVICE_COMMAND = 'R\n'               # Command to request temperature reading

# Monitoring parameters
TEMPERATURE_THRESHOLD = 180.0        # °C - Maximum safe operating temperature
CHECK_INTERVAL = 300                 # Seconds between temperature checks

# System control commands
POWER_CYCLE_COMMAND = ['/usr/sbin/powercycle', 'txpaa', '--power-off']

# ============================================================================
# Logging Configuration
# ============================================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ============================================================================
# Signal Handling
# ============================================================================

def handle_termination_signal(signum, frame):
    """
    Gracefully handle termination signals
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logging.info(f"Received termination signal {signum}. Shutting down service.")
    sys.exit(0)

# Register signal handlers for clean shutdown
signal.signal(signal.SIGTERM, handle_termination_signal)
signal.signal(signal.SIGINT, handle_termination_signal)

# ============================================================================
# Device Communication Layer
# ============================================================================

def query_temperature_sensor(port_name):
    """
    Communicate with temperature sensor over serial connection
    
    Args:
        port_name: Name of serial port to use (e.g., 'ttyACM0')
    
    Returns:
        str: Raw response from device, or None if communication failed
    """
    port_path = f"/dev/{port_name}"
    
    try:
        # Establish serial connection
        with serial.Serial(port_path, BAUD_RATE, timeout=1) as serial_connection:
            # Allow device time to initialize
            time.sleep(2)
            
            # Clear communication buffers
            serial_connection.reset_input_buffer()
            serial_connection.reset_output_buffer()
            
            # Send temperature reading command
            serial_connection.write(DEVICE_COMMAND.encode())
            
            # Read response (expecting single line)
            response = serial_connection.readline().decode().strip()

        logging.debug(f"Raw sensor response: {response}")
        return response

    except serial.SerialException as e:
        logging.error(f"Serial communication failure on {port_name}: {str(e)}")
        return None
    except Exception as e:
        logging.exception(f"Unexpected error with {port_name}: {str(e)}")
        return None

# ============================================================================
# System Control Functions
# ============================================================================

def initiate_power_cycle():
    """
    Execute power cycle command to reset hardware
    
    Typically used when temperature exceeds safe thresholds
    """
    try:
        # Execute power cycle command silently
        subprocess.run(
            POWER_CYCLE_COMMAND,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logging.info("Successfully initiated system power cycle")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to execute power cycle: {str(e)}")

# ============================================================================
# Monitoring Logic
# ============================================================================

def process_temperature_reading():
    """
    Main temperature monitoring workflow:
    1. Query sensor for current temperature
    2. Parse and validate response
    3. Log results
    4. Initiate safety measures if needed
    """
    raw_response = query_temperature_sensor(SERIAL_PORT)
    
    if not raw_response:
        logging.warning("No valid response from temperature sensor")
        return

    try:
        # Extract numeric value from response (handles formats like "Temp: 123.45°C")
        numeric_match = re.search(r'[-+]?\d*\.\d+|\d+', raw_response)
        
        if not numeric_match:
            raise ValueError(f"Could not find numeric value in response: '{raw_response}'")

        # Convert to floating point temperature
        current_temp = float(numeric_match.group())

        # Create timestamped record
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} - Temperature: {current_temp}°C"
        
        # Store in results file
        with open(RESULTS_FILE, 'a') as results_file:
            results_file.write(log_entry + '\n')

        # Log to main service log
        logging.info(f"Current temperature: {current_temp:.2f}°C")

        # Safety check: compare against threshold
        if current_temp > TEMPERATURE_THRESHOLD:
            logging.warning(f"High temperature detected! {current_temp:.2f}°C vs threshold {TEMPERATURE_THRESHOLD}°C")
            initiate_power_cycle()

    except ValueError as e:
        logging.error(f"Invalid temperature reading: {str(e)}")
    except Exception as e:
        logging.exception(f"Error processing temperature: {str(e)}")

# ============================================================================
# Service Management
# ============================================================================

def start_monitoring_service():
    """
    Main service loop that periodically checks temperature
    
    Handles periodic execution and error recovery for the monitoring process
    """
    logging.info("Temperature monitoring service started")
    
    try:
        while True:
            try:
                process_temperature_reading()
            except Exception as e:
                logging.exception(f"Monitoring iteration error: {str(e)}")
            
            # Wait until next check interval
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logging.info("User requested service shutdown via keyboard interrupt")
    except Exception as e:
        logging.critical(f"Critical service failure: {str(e)}", exc_info=True)
        sys.exit(1)

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    start_monitoring_service()
