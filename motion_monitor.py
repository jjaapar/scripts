#!/usr/bin/env python3
import serial
import subprocess
import time
import sys

def log(message):
    """Log with timestamp to stderr for systemd journal"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", file=sys.stderr)

def main():
    while True:
        try:
            with serial.Serial(
                port='/dev/ttyACM0',
                baudrate=9600,
                timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            ) as ser:
                log("Serial connection established")
                while True:
                    line = ser.readline().decode().strip()
                    if line == "Motion detected!":
                        log("Executing lapoe_controller.py")
                        try:
                            subprocess.run([
                                '/usr/bin/python3',
                                '/path/to/lapoe_controller.py',
                                'smart-mode', '5'
                            ], check=True)
                        except subprocess.CalledProcessError as e:
                            log(f"Script execution failed: {e}")
        except serial.SerialException as e:
            log(f"Serial error: {e}. Retrying in 10s...")
            time.sleep(10)
        except Exception as e:
            log(f"Unexpected error: {e}. Restarting...")
            time.sleep(5)

if __name__ == "__main__":
    main()
