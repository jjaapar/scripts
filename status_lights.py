#!/usr/bin/python3

import socket
import struct
import argparse
import sys
from enum import IntEnum
from dataclasses import dataclass
from typing import Tuple
import time
from prettytable import PrettyTable


class LEDPattern(IntEnum):
    OFF = 0
    ON = 1
    BLINK_SLOW = 2
    BLINK_MEDIUM = 3
    BLINK_FAST = 4
    NO_CHANGE = 9

    def label(self):
        return {
            self.OFF: "Off",
            self.ON: "On",
            self.BLINK_SLOW: "Blink (Slow)",
            self.BLINK_MEDIUM: "Blink (Medium)",
            self.BLINK_FAST: "Blink (Fast)",
            self.NO_CHANGE: "No Change"
        }.get(self, f"Unknown ({self})")

    @classmethod
    def from_name(cls, name: str):
        return {
            'off': cls.OFF,
            'on': cls.ON,
            'blinking_slow': cls.BLINK_SLOW,
            'blinking_medium': cls.BLINK_MEDIUM,
            'blinking_fast': cls.BLINK_FAST,
            'no_change': cls.NO_CHANGE
        }.get(name.lower(), cls.OFF)


@dataclass
class PnsRunControlData:
    red: LEDPattern
    amber: LEDPattern
    green: LEDPattern

    def to_bytes(self) -> bytes:
        return struct.pack('BBB', self.red, self.amber, self.green)


@dataclass
class PnsStatusData:
    patterns: Tuple[LEDPattern, LEDPattern, LEDPattern]

    @classmethod
    def from_bytes(cls, data: bytes):
        return cls(tuple(LEDPattern(p) for p in data[:3]))


class PnsClient:
    def __init__(self, ip, port):
        self.ip, self.port = ip, port

    def __enter__(self):
        self.sock = socket.create_connection((self.ip, self.port))
        return self

    def __exit__(self, *args):
        self.sock.close()

    def send(self, command, payload=b''):
        header = struct.pack('>2ssxH', b'AB', command.encode(), len(payload))
        self.sock.sendall(header + payload)
        return self.sock.recv(1024)

    def set_leds(self, data: PnsRunControlData):
        self.send('S', data.to_bytes())

    def clear_leds(self):
        self.send('C')

    def get_status(self) -> PnsStatusData:
        response = self.send('G')
        return PnsStatusData.from_bytes(response)


def alert(message: str):
    """Alert function for when the condition is not met."""
    print(f"🚨 {message}")


def print_examples():
    print("""
📘 Usage Examples:

🔴🟠🟢 Set LED Patterns
  python3 led_control.py S --red on --amber blinking_slow --green off

🧹 Clear All LEDs
  python3 led_control.py C

🔍 Get Current LED Status
  python3 led_control.py G

🌐 Using Custom IP and Port
  python3 led_control.py S --red blinking_fast --amber off --green on --ip 192.168.0.50 --port 12345
""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=['S', 'C', 'G'], help="Command: S=Set, C=Clear, G=Get")
    for color in ['red', 'amber', 'green']:
        parser.add_argument(f"--{color}", choices=[
            'off', 'on', 'blinking_slow', 'blinking_medium', 'blinking_fast', 'no_change'
        ])
    parser.add_argument("--ip", default="192.168.10.1")
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--examples", action="store_true", help="Show usage examples and exit")

    # Show examples if no args are provided or --examples is passed
    if len(sys.argv) == 1:
        print_examples()
        return

    args = parser.parse_args()

    if args.examples:
        print_examples()
        return

    with PnsClient(args.ip, args.port) as client:
        if args.command == 'S':
            led_data = {
                color: LEDPattern.from_name(getattr(args, color)) for color in ['red', 'amber', 'green']
            }
            client.set_leds(PnsRunControlData(**led_data))
            print("LEDs updated.")
        elif args.command == 'C':
            client.clear_leds()
            print("LEDs cleared.")
        elif args.command == 'G':
            status = client.get_status()
            table = PrettyTable(["Color", "Pattern"])
            for color, pattern in zip(['Red', 'Amber', 'Green'], status.patterns):
                table.add_row([color, pattern.label()])
            print(table)

        # Now, implement the new operation
        # Check if light is green
        status = client.get_status()
        
        # If the light is not green, stop and alert
        if status.patterns[2] != LEDPattern.ON:
            alert("The light is not green! Stopping the operation.")
            return

        # Change the LED to slow blinking yellow (amber)
        print("Changing light to slow blinking yellow for 10 minutes...")
        client.set_leds(PnsRunControlData(red=LEDPattern.OFF, amber=LEDPattern.BLINK_SLOW, green=LEDPattern.OFF))
        
        # Wait for 10 minutes (600 seconds)
        time.sleep(600)

        # After 10 minutes, change the light to solid red
        print("Changing light to solid red...")
        client.set_leds(PnsRunControlData(red=LEDPattern.ON, amber=LEDPattern.OFF, green=LEDPattern.OFF))

        print("Operation completed.")


if __name__ == "__main__":
    main()
