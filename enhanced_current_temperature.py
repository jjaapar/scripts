#!/usr/bin/env python3

import serial
import time
import logging
import argparse
import os
import json

# Fixed configuration constants
BAUD_RATE = 115200
COMMAND = "R"
TIMEOUT = 1.0
RESPONSE_DELAY = 0.5
LOG_FILE = "serial_monitor.log"
SERIAL_INIT_DELAY = 2.0


def configure_logging() -> None:
    """Configures logging to file."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def read_serial_response(ser: serial.Serial) -> str:
    """Reads serial response with timeout handling."""
    response = bytearray()
    start_time = time.monotonic()
    
    while (time.monotonic() - start_time) < TIMEOUT:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            response.extend(data)
            start_time = time.monotonic()  # Reset timeout on new data
    
    return response.decode(errors="ignore").strip()


def send_command(ser: serial.Serial) -> str:
    """Sends command and reads response."""
    try:
        ser.write(COMMAND.encode() + b'\r\n')  # Send command with line terminator
        time.sleep(RESPONSE_DELAY)
        return read_serial_response(ser)
    except serial.SerialException as e:
        logging.error(f"Serial communication error: {e}")
        raise


def format_output(device: str, result: str) -> str:
    """Formats output in the requested JSON structure."""
    output = {
        "temperature_check": {
            "hardware": device,
            "Temperature": result,
            "Unit": "C"
        }
    }
    return json.dumps(output, indent=2)


def format_error(device: str, error: str) -> str:
    """Formats error output in a similar structure."""
    output = {
        "error": {
            "hardware": device,
            "message": error
        }
    }
    return json.dumps(output, indent=2)


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Serial Device Temperature Reader"
    )
    parser.add_argument("device", help="Serial device name (e.g. ttyACM0)")
    args = parser.parse_args()
    
    configure_logging()
    dev_path = f"/dev/{args.device}"
    
    if not os.path.exists(dev_path):
        error_msg = f"Device path not found: {dev_path}"
        logging.critical(error_msg)
        print(format_error(args.device, error_msg))
        return

    try:
        logging.info(f"Connecting to {dev_path} at {BAUD_RATE} baud")
        with serial.Serial(
            port=dev_path,
            baudrate=BAUD_RATE,
            timeout=TIMEOUT,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        ) as ser:
            logging.info(f"Connection established, waiting {SERIAL_INIT_DELAY}s")
            time.sleep(SERIAL_INIT_DELAY)  # Device initialization
            
            logging.info(f"Sending command: '{COMMAND}'")
            response = send_command(ser)
            logging.info(f"Received response: '{response}'")
            
            print(format_output(args.device, response))

    except Exception as e:
        error_msg = f"Operation failed: {type(e).__name__} - {str(e)}"
        logging.exception(error_msg)
        print(format_error(args.device, error_msg))


if __name__ == "__main__":
    main()
