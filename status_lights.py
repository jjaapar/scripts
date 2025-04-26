#!/usr/bin/python3

import socket
import struct
import argparse
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Tuple
from prettytable import PrettyTable


# Enum to define possible LED patterns
class LEDPattern(IntEnum):
    OFF = 0
    ON = 1
    BLINK_SLOW = 2
    BLINK_MEDIUM = 3
    BLINK_FAST = 4
    NO_CHANGE = 9

    # Convert pattern number to a readable string
    def label(self):
        return {
            self.OFF: "Off",
            self.ON: "On",
            self.BLINK_SLOW: "Blinking (Slow)",
            self.BLINK_MEDIUM: "Blinking (Medium)",
            self.BLINK_FAST: "Blinking (Fast)",
            self.NO_CHANGE: "No Change"
        }.get(self, f"Unknown ({self})")

    # Helper method to get the LED pattern from a name (e.g., 'off', 'on', etc.)
    @classmethod
    def from_name(cls, name: str) -> 'LEDPattern':
        name_to_value = {
            'off': cls.OFF,
            'on': cls.ON,
            'blinking_slow': cls.BLINK_SLOW,
            'blinking_medium': cls.BLINK_MEDIUM,
            'blinking_fast': cls.BLINK_FAST,
            'no_change': cls.NO_CHANGE
        }
        try:
            return name_to_value[name.lower()]
        except KeyError:
            raise ValueError(f"Invalid pattern name: {name}")


# Data class to store the LED patterns for each color (Red, Amber, Green, Blue, White)
@dataclass
class PnsRunControlData:
    red: LEDPattern
    amber: LEDPattern
    green: LEDPattern
    blue: LEDPattern
    white: LEDPattern

    # Convert the LED data to a byte format for sending over the network
    def to_bytes(self) -> bytes:
        return struct.pack('BBBBB', self.red, self.amber, self.green, self.blue, self.white)


# Data class to store the status data of the LEDs received from the device
@dataclass
class PnsStatusData:
    led_patterns: Tuple[LEDPattern, LEDPattern, LEDPattern, LEDPattern, LEDPattern]

    # Convert the received byte data into human-readable LED patterns
    @classmethod
    def from_bytes(cls, data: bytes) -> 'PnsStatusData':
        return cls(tuple(LEDPattern(p) for p in data[:5]))


# Client class to handle communication with the LR5-LAN device over the network
class PnsClient:
    PRODUCT_ID = b'AB'
    COMMAND_RUN = b'S'
    COMMAND_CLEAR = b'C'
    COMMAND_GET = b'G'
    ACK = 0x06
    NAK = 0x15
    MAX_RETRIES = 3  # Number of retries for network failure
    RETRY_DELAY = 1.0  # Delay between retries

    def __init__(self, ip: str, port: int, verbose: bool = False):
        """Initialize the client with the device's IP and port"""
        self.ip, self.port = ip, port
        self.verbose = verbose
        self.sock = None

    # Establish a connection to the device
    def __enter__(self):
        self.sock = socket.create_connection((self.ip, self.port))
        return self

    # Close the connection when done
    def __exit__(self, *_):
        self.sock and self.sock.close()

    # Method to send data to the device and receive the response
    def _send(self, payload: bytes) -> bytes:
        """Send the payload to the device and handle retries on failure."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                if self.verbose:
                    print(f"[>] Sending: {payload.hex()}")

                self.sock.sendall(payload)
                response = self.sock.recv(1024)

                if self.verbose:
                    print(f"[<] Received: {response.hex()}")

                return response
            except Exception as e:
                print(f"[!] Retry {attempt}/{self.MAX_RETRIES} - {e}")
                if attempt == self.MAX_RETRIES:
                    raise
                time.sleep(self.RETRY_DELAY)

    # Command to control the LED patterns
    def run_control(self, data: PnsRunControlData):
        """Send the 'run control' command to set LED patterns."""
        payload = struct.pack('>2ssxH', self.PRODUCT_ID, self.COMMAND_RUN, 5) + data.to_bytes()
        if self._send(payload)[0] == self.NAK:
            raise ValueError("Device responded with NAK")

    # Command to clear (turn off) the LEDs
    def clear(self):
        """Send the 'clear' command to turn off the LEDs."""
        payload = struct.pack('>2ssxH', self.PRODUCT_ID, self.COMMAND_CLEAR, 0)
        if self._send(payload)[0] == self.NAK:
            raise ValueError("Device responded with NAK")

    # Command to get the current status of the LEDs
    def get_status(self) -> PnsStatusData:
        """Send the 'get status' command to retrieve the current LED patterns."""
        payload = struct.pack('>2ssxH', self.PRODUCT_ID, self.COMMAND_GET, 0)
        response = self._send(payload)
        if response[0] == self.NAK:
            raise ValueError("Device responded with NAK")
        return PnsStatusData.from_bytes(response)


# Function to build and return the command-line argument parser
def build_parser():
    parser = argparse.ArgumentParser(description="Control the LEDs of an LR5-LAN device")

    # Define the available command options: S (set), C (clear), G (get)
    parser.add_argument("command", choices=['S', 'C', 'G'],
                        help="Command to be sent to the device:\n"
                             "  S: Set LEDs to specified patterns\n"
                             "  C: Clear LEDs\n"
                             "  G: Get the current status of LEDs")

    # Define the available LED patterns for each color (Red, Amber, Green, Blue, White)
    for color in ['red', 'amber', 'green', 'blue', 'white']:
        parser.add_argument(f"--{color}", type=str, choices=['off', 'on', 'blinking_slow', 'blinking_medium', 'blinking_fast', 'no_change'],
                             help=f"LED {color.capitalize()} pattern")

    # Define IP and port settings for the device
    parser.add_argument("--ip", default="192.168.10.1", help="IP address of the device (default: 192.168.10.1)")
    parser.add_argument("--port", type=int, default=10000, help="Port number (default: 10000)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging")

    return parser


# Function to print the LED status in a human-readable table format
def print_status(status: PnsStatusData):
    table = PrettyTable(["Color", "Pattern"])
    colors = ["Red", "Amber", "Green", "Blue", "White"]
    for color, pattern in zip(colors, status.led_patterns):
        table.add_row([color, pattern.label()])
    print(table)


# Main function to parse arguments and perform the requested action
def main():
    args = build_parser().parse_args()

    # Convert the string-based LED patterns to enum values (e.g., 'off' -> LEDPattern.OFF)
    led_data = {color: LEDPattern.from_name(getattr(args, color)) if getattr(args, color) else LEDPattern.OFF
                for color in ["red", "amber", "green", "blue", "white"]}

    # Open a connection to the device and perform the requested command
    with PnsClient(args.ip, args.port, verbose=args.verbose) as client:
        if args.command == 'S':
            # If the command is 'S' (Set), we must specify all LED patterns
            if any(value is None for value in led_data.values()):
                raise ValueError("All LED colors must be specified for the 'S' command.")
            control = PnsRunControlData(**led_data)
            client.run_control(control)
            print("LED patterns have been updated.")
        elif args.command == 'C':
            # If the command is 'C' (Clear), turn off all LEDs
            client.clear()
            print("All LEDs have been turned off.")
        elif args.command == 'G':
            # If the command is 'G' (Get), retrieve the current LED status and display it
            status = client.get_status()
            print("Current LED Status:")
            print_status(status)


# Run the main function if the script is executed directly
if __name__ == '__main__':
    main()
