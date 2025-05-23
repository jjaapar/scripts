#!/usr/bin/env python3

import serial
import time
import logging
import argparse
import os
import json
from typing import Optional, Dict, Any


# ----------------------
# Configuration Section
# ----------------------
LOG_FILE = "serial_log.txt"
BAUD_RATE = 115200
DEFAULT_COMMAND = "R"
TIMEOUT = 1
RESPONSE_DELAY = 1  # seconds to wait after sending a command

# ----------------------
# Logging Setup
# ----------------------
def setup_logging() -> None:
    """Set up timestamped logging to file."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ----------------------
# Serial Communication
# ----------------------
def send_command(ser: serial.Serial, command: str) -> str:
    """
    Send a command over the serial connection and read the response.

    Args:
        ser: Open serial port object.
        command: The command string to send.

    Returns:
        The device's trimmed response as a string.

    Raises:
        serial.SerialException: If communication fails.
    """
    try:
        ser.write(command.encode())
        time.sleep(RESPONSE_DELAY)

        response = ""
        while ser.in_waiting > 0:
            response += ser.read(ser.in_waiting).decode()

        return response.strip()

    except serial.SerialException as e:
        logging.error(f"Serial communication error: {e}")
        raise


# ----------------------
# Output Formatting
# ----------------------
def create_output(
    device_name: str,
    result: Optional[str] = None,
    status: str = "success",
    error: Optional[str] = None,
) -> str:
    """
    Generate structured JSON output for success or error cases.

    Args:
        device_name: Device identifier (e.g., 'TXPA1').
        result: Response from the device (if successful).
        status: 'success' or 'error'.
        error: Error message (if any).

    Returns:
        A JSON-formatted string.
    """
    if status == "error":
        return json.dumps({"status": "error", "error": str(error)}, indent=2)

    return json.dumps(
        {
            "status": "success",
            "device": device_name,
            "data": {
                "temperature_check": {
                    "hardware": device_name,
                    "Temperature": result,
                    "Unit": "C",
                }
            },
        },
        indent=2,
    )


# ----------------------
# Main Logic
# ----------------------
def main(device_name: str) -> None:
    """
    Main function to communicate with the serial device and handle results.

    Args:
        device_name: Name of the serial device (e.g., 'ttyACM0').
    """
    setup_logging()
    device_path = f"/dev/{device_name}"

    if not os.path.exists(device_path):
        error_msg = f"Device {device_path} does not exist."
        logging.error(error_msg)
        print(create_output(device_name, status="error", error=error_msg))
        return

    try:
        with serial.Serial(port=device_path, baudrate=BAUD_RATE, timeout=TIMEOUT) as ser:
            logging.info(f"Opened serial port: {device_path}")
            time.sleep(2)  # Allow device to initialize

            result = send_command(ser, DEFAULT_COMMAND)
            logging.info(f"{device_name}: {result}")
            print(create_output(device_name, result=result))

    except serial.SerialException as e:
        error_msg = f"Failed to open or communicate with {device_path}: {e}"
        logging.error(error_msg)
        print(create_output(device_name, status="error", error=error_msg))

    except Exception as e:
        error_msg = f"Unexpected error occurred: {e}"
        logging.exception(error_msg)
        print(create_output(device_name, status="error", error=error_msg))


# ----------------------
# Entry Point
# ----------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send a command to a serial device and receive a response.",
        epilog="Example usage: ./script.py ttyACM0",
    )
    parser.add_argument("device", help="Name of the serial device (e.g., ttyACM0 or TXPA1)")
    args = parser.parse_args()

    main(args.device)
