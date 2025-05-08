#!/usr/bin/env python3
import serial
import subprocess
import time
import sys
from typing import Optional

def log(message: str) -> None:
    """Log with timestamp to stderr for systemd journal"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", file=sys.stderr)

def execute_controller(duration: str) -> None:
    """Execute the controller script with the specified duration"""
    try:
        subprocess.run([
            '/usr/bin/python3',
            '/home/jazzeryj/jazzeryj/new_la6.py',
            'T', duration
        ], check=True)
    except subprocess.CalledProcessError as e:
        log(f"Script execution failed: {e}")
    except Exception as e:
        log(f"Unexpected error during script execution: {e}")

def process_serial_data(serial_connection: serial.Serial) -> Optional[str]:
    """Process data from serial connection with error handling"""
    try:
        line = serial_connection.readline().decode().strip()
        return line if line else None
    except UnicodeDecodeError as e:
        log(f"Failed to decode serial data: {e}")
        return None

def main() -> None:
    serial_config = {
        'port': '/dev/ttyACM0',
        'baudrate': 9600,
        'timeout': 1,
        'bytesize': serial.EIGHTBITS,
        'parity': serial.PARITY_NONE,
        'stopbits': serial.STOPBITS_ONE
    }

    while True:
        try:
            with serial.Serial(**serial_config) as ser:
                log("Serial connection established")
                while True:
                    line = process_serial_data(ser)
                    if not line:
                        continue

                    if line == "Motion detected!":
                        log("Motion detected - Turning on the blue LED")
                        execute_controller('11')
                    elif line == "Motion ended!":
                        log("Motion ended - Turning off LED")
                        execute_controller('20')

        except serial.SerialException as e:
            log(f"Serial error: {e}. Retrying in 10s...")
            time.sleep(10)
        except KeyboardInterrupt:
            log("Program terminated by user")
            sys.exit(0)
        except Exception as e:
            log(f"Unexpected error: {e}. Restarting in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    main()
