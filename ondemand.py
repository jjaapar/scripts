#!/usr/bin/env python3

import serial
import time
import logging
import argparse
import os

# -------------------------------
# Configure logging to file
# -------------------------------
logging.basicConfig(
    filename='serial_communication.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def communicate(device_name, command="R\n", baudrate=115200, timeout=1):
    """
    Connects to a serial port, sends a command, and returns the response.

    Args:
        device_name (str): Short device name (e.g., 'txpaa1')
        command (str): Command to send (default is 'R\\n')
        baudrate (int): Communication speed
        timeout (int): Timeout in seconds

    Returns:
        str or None: Response from the device or None if an error occurred
    """
    device_path = f"/dev/{device_name}"

    try:
        with serial.Serial(device_path, baudrate, timeout=timeout) as ser:
            time.sleep(2)  # Allow time for device to initialize

            ser.reset_input_buffer()
            ser.reset_output_buffer()

            ser.write(command.encode())     # Send command
            response = ser.readline().decode().strip()  # Read response

        # Print and log using device_name
        print(f"{device_name}: {response}")
        logging.info(f"{device_name}: {response}")
        return response

    except serial.SerialException as e:
        error_msg = f"Error with {device_name}: {e}"
        print(error_msg)
        logging.error(error_msg)
        return None

def main():
    # -------------------------------
    # Parse command-line arguments
    # -------------------------------
    parser = argparse.ArgumentParser(
        description="Send a command to one or more serial devices and get a response."
    )
    parser.add_argument(
        "device_name",
        nargs='?',  # Makes this argument optional
        help="Serial device name (e.g., txpaa1). If not provided, defaults to checking txpaa1, txpaa2, txpaa3"
    )
    args = parser.parse_args()

    # Determine which devices to check
    if args.device_name:
        devices_to_check = [args.device_name]
    else:
        devices_to_check = ["txpaa1", "txpaa2", "txpaa3"]
        print("No device specified. Checking default devices:", ", ".join(devices_to_check))

    # Loop through each device and communicate
    for device in devices_to_check:
        device_path = f"/dev/{device}"

        if not os.path.exists(device_path):
            error_msg = f"Device {device_path} does not exist."
            print(error_msg)
            logging.error(error_msg)
            continue

        communicate(device)

if __name__ == "__main__":
    main()
