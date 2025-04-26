#!/usr/bin/python3

import serial
import time
import logging
import argparse
import os
import json

def setup_logging():
    """
    Set up logging to 'serial_log.txt' with timestamped entries.
    """
    logging.basicConfig(
        filename='serial_log.txt',
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def send_command(ser, command):
    """
    Send a command via serial port and return the device's response.

    Args:
        ser (serial.Serial): An open serial port.
        command (str): The command string to send.

    Returns:
        str: Response from the device (whitespace-trimmed).
    """
    try:
        ser.write(command.encode())
        time.sleep(1)  # Allow device time to respond

        response = ""
        while ser.in_waiting:
            response += ser.read(ser.in_waiting).decode()

        return response.strip()

    except serial.SerialException as e:
        logging.error(f"Serial communication error: {e}")
        raise

def create_json_output(device_name, result=None, status="success", error=None):
    """
    Format the result or error as a JSON string.

    Args:
        device_name (str): Device name (e.g., 'TXPA1').
        result (str): Response from the device.
        status (str): 'success' or 'error'.
        error (str): Error message if any.

    Returns:
        str: Formatted JSON string.
    """
    if status == "error":
        return json.dumps({"error": str(error)}, indent=2)

    output = {
        "temperature_check": {
            "hardware": device_name,
            "Temperature": result,
            "Unit": "C"
        }
    }

    return json.dumps(output, indent=2)

def main(device_name):
    """
    Main routine to communicate with a serial device and handle response/errors.

    Args:
        device_name (str): Device name (e.g., 'ttyACM0').
    """
    setup_logging()

    device_path = f"/dev/{device_name}"
    command = "R"

    if not os.path.exists(device_path):
        error_msg = f"Device {device_path} does not exist"
        print(create_json_output(device_name, status="error", error=error_msg))
        logging.error(error_msg)
        return

    try:
        with serial.Serial(device_path, 115200, timeout=1) as ser:
            time.sleep(2)

            result = send_command(ser, command)

            print(create_json_output(device_name, result))
            logging.info(f"{device_name}: {result}")

    except serial.SerialException as e:
        error_msg = f"Error opening serial port {device_path}: {e}"
        print(create_json_output(device_name, status="error", error=error_msg))
        logging.error(error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(create_json_output(device_name, status="error", error=error_msg))
        logging.error(error_msg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send a command to a serial device and receive a response.",
        epilog="Example usage: ./script.py ttyACM0"
    )
    parser.add_argument(
        "device",
        help="Serial device name (e.g., ttyACM0 or TXPA1)"
    )
    args = parser.parse_args()
    main(args.device)
