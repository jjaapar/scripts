#!/usr/bin/env python3

# Standard imports
import serial
import subprocess
import sys
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

# -----------------------------
# Configuration Section
# -----------------------------

# Serial port connected to Arduino or motion sensor device
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600  # Communication speed with the device

# Path to the LED control script (ensure this exists)
SCRIPT_PATH = '/home/jazzeryj/jazzeryj/new_la6.py'

# LED command codes used by the controller script:
LED_BLUE = '11'   # Code to activate blue LED
LED_GREEN = '10'  # Code to activate green LED

# Reconnection settings in case the serial connection drops
MAX_RECONNECT_ATTEMPTS = 5
RETRY_DELAY = 10  # Wait 10 seconds before retrying

# Log file path
LOG_FILENAME = '/home/jazzeryj/logs/controller_app.log'

# Delay between full reconnection attempts when everything fails
FULL_RESTART_DELAY = 30  # Seconds

# -----------------------------
# Logging Setup
# -----------------------------
# Set up logs to go both to console and a rotating file (up to 5MB each, 3 backups)
os.makedirs(os.path.dirname(LOG_FILENAME), exist_ok=True)

file_handler = RotatingFileHandler(LOG_FILENAME, maxBytes=5 * 1024 * 1024, backupCount=3)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Output logs to stdout (for systemd journal)
        file_handler                        # Also write logs to file
    ]
)

# -----------------------------
# Function Definitions
# -----------------------------

def run_led_script(command_code: str) -> None:
    """
    Runs the LED control script with the specified command code.
    
    The script expects a command code like '10' or '11' to determine which LED to turn on.

    Args:
        command_code (str): A string representing the LED action.
    """
    if not os.path.exists(SCRIPT_PATH):
        logging.error(f"LED control script not found at: {SCRIPT_PATH}")
        return

    try:
        result = subprocess.run([
            sys.executable, SCRIPT_PATH, 'T', command_code
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30  # Fail if the script doesn't finish within 30 seconds
        )

        logging.debug(f"Script output: {result.stdout}")

    except subprocess.CalledProcessError as e:
        logging.error(f"LED script failed (exit code {e.returncode}): {e.stderr}")
    except subprocess.TimeoutExpired:
        logging.error("LED script execution timed out")
    except Exception as e:
        logging.exception(f"Unexpected error occurred: {e}")


def read_serial_data(connection: serial.Serial) -> Optional[str]:
    """
    Read one line from the serial device.

    Returns:
        Optional[str]: A decoded message string, or None if an error occurred.
    """
    try:
        line = connection.readline().decode().strip()
        if line:
            logging.debug(f"Serial received: {line}")
        return line

    except UnicodeDecodeError as e:
        logging.warning(f"Failed to decode serial data: {e}")
        return None
    except serial.SerialTimeoutException:
        logging.debug("Serial read timeout - no new data.")
        return None


def connect_to_serial() -> Optional[serial.Serial]:
    """
    Attempt to connect to the serial device.
    
    Will retry up to MAX_RECONNECT_ATTEMPTS times if initial connection fails.

    Returns:
        Optional[serial.Serial]: A working serial connection or None if failed.
    """
    attempts = 0
    while attempts < MAX_RECONNECT_ATTEMPTS:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            logging.info("Successfully connected to the serial device.")
            return ser
        except serial.SerialException as e:
            attempts += 1
            logging.error(f"Connection attempt {attempts} failed: {e}")
            if attempts < MAX_RECONNECT_ATTEMPTS:
                logging.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)

    logging.warning("Unable to connect after maximum retries. Retrying later...")
    return None


# -----------------------------
# Main Application Logic
# -----------------------------

def main() -> None:
    """
    Main loop of the application.
    
    - Connects to the serial device
    - Listens for motion detection events
    - Triggers appropriate LED actions
    - Handles disconnections and reconnects automatically
    
    Designed to run forever like a service.
    """
    logging.info("Starting motion detection LED service...")

    while True:
        serial_connection = connect_to_serial()
        if not serial_connection:
            logging.warning(f"Waiting {FULL_RESTART_DELAY} seconds before trying again...")
            time.sleep(FULL_RESTART_DELAY)
            continue

        try:
            while True:
                line = read_serial_data(serial_connection)

                if line == "Motion detected!":
                    logging.info("Motion detected - Activating Blue LED")
                    run_led_script(LED_BLUE)

                elif line == "Motion ended!":
                    logging.info("Motion ended - Activating Green LED")
                    run_led_script(LED_GREEN)

                elif line:
                    logging.debug(f"Received unknown serial message: {line}")

        except serial.SerialException:
            logging.warning("Lost connection to serial device. Restarting connection...")
        finally:
            serial_connection.close()


# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    main()
