#!/usr/bin/python3

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
    Connects to the serial port, sends a command, and returns the response.

    Args:
        device_name (str): Short device name (e.g., 'ttyACM0')
        command (str): Command to send (default is 'R\\n')
        baudrate (int): Baud rate for communication
        timeout (int): Timeout in seconds

    Returns:
        str or None: Response from the device or None if an error occurred
    """
    device_path = f"/dev/{device_name}"

    try:
        with serial.Serial(device_path, baudrate, timeout=timeout) as ser:
            time.sleep(2)  # Wait for the device to initialize

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
        description="Send a command to a serial device and get a response."
    )
    parser.add_argument(
        "device_name",
        help="Serial device name (e.g., ttyACM0)"
    )
    args = parser.parse_args()

    # Check if the device exists
    device_path = f"/dev/{args.device_name}"
    if not os.path.exists(device_path):
        error_msg = f"Device {device_path} does not exist."
        print(error_msg)
        logging.error(error_msg)
        return

    # Communicate with the device using just the device name
    communicate(args.device_name)

if __name__ == "__main__":
    main()
