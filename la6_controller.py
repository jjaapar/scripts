#!/usr/bin/env python3
"""
LA-POE Controller - A Python script to control LA-POE devices.

Provides a command-line interface to manage LEDs, buzzers, and monitor status.
"""

import socket
import struct
import sys
import argparse
from typing import Optional, Tuple, Union

# Constants
DEFAULT_IP = "172.18.3.200"
DEFAULT_PORT = 10000
PNS_PRODUCT_ID = b'AB'

# Command constants
PNS_SMART_MODE_COMMAND = b'T'
PNS_RUN_CONTROL_COMMAND = b'S'
PNS_MUTE_COMMAND = b'M'
PNS_GET_DATA_COMMAND = b'G'
PNS_NAK = 0x15
PNS_LED_MODE = 0

# Define Data Classes
class PnsRunControlData:
    def __init__(self, led1, led2, led3, led4, led5, buzzer):
        self.led1 = led1
        self.led2 = led2
        self.led3 = led3
        self.led4 = led4
        self.led5 = led5
        self.buzzer = buzzer

class PnsSmartModeData:
    def __init__(self, group_no=0, mute=0, stop_input=0, pattern_no=0):
        self.group_no = group_no
        self.mute = mute
        self.stop_input = stop_input
        self.pattern_no = pattern_no

class PnsStatusData:
    def __init__(self):
        self.mode = PNS_LED_MODE
        self.input = [0] * 8
        self.led_mode_data = PnsRunControlData(0, 0, 0, 0, 0, 0)
        self.smart_mode_data = PnsSmartModeData()

class PNSController:
    """Main controller class for LA-POE device communication."""

    def __init__(self, ip: str = DEFAULT_IP, port: int = DEFAULT_PORT) -> None:
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __enter__(self) -> 'PNSController':
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def connect(self) -> None:
        try:
            self.sock.connect((self.ip, self.port))
        except socket.error as e:
            raise ConnectionError(f"Unable to connect to {self.ip}:{self.port}") from e

    def close(self) -> None:
        self.sock.close()

    def send_command(self, send_data: bytes) -> bytes:
        try:
            self.sock.sendall(send_data)
            return self.sock.recv(1024)
        except socket.error as e:
            raise ConnectionError("Communication error with device.") from e

    def pns_smart_mode_command(self, run_data: int) -> None:
        send_data = struct.pack('>2ssxHB', PNS_PRODUCT_ID, PNS_SMART_MODE_COMMAND, 1, run_data)
        recv_data = self.send_command(send_data)
        if recv_data[0] == PNS_NAK:
            raise ValueError('Device returned NAK (Negative Acknowledge).')

    def pns_mute_command(self, mute: int) -> None:
        """Send mute ON/OFF command."""
        send_data = struct.pack('>2ssxHB', PNS_PRODUCT_ID, PNS_MUTE_COMMAND, 1, mute)
        recv_data = self.send_command(send_data)
        if recv_data[0] == PNS_NAK:
            raise ValueError('Device returned NAK (Negative Acknowledge).')

    def pns_run_control_command(self, control_data: PnsRunControlData) -> None:
        """Send LED and buzzer control data."""
        send_data = struct.pack(
            '>2ssx6B',
            PNS_PRODUCT_ID,
            PNS_RUN_CONTROL_COMMAND,
            control_data.led1,
            control_data.led2,
            control_data.led3,
            control_data.led4,
            control_data.led5,
            control_data.buzzer
        )
        recv_data = self.send_command(send_data)
        if recv_data[0] == PNS_NAK:
            raise ValueError('Device returned NAK (Negative Acknowledge).')

    def pns_get_data_command(self) -> PnsStatusData:
        """Request and parse device status."""
        send_data = struct.pack('>2ssx', PNS_PRODUCT_ID, PNS_GET_DATA_COMMAND)
        recv_data = self.send_command(send_data)

        if not recv_data:
            raise ValueError("No response received from device.")

        status = PnsStatusData()

        # Parse response (assuming a known layout)
        status.mode = recv_data[4]
        status.input = list(recv_data[5:13])

        if status.mode == PNS_LED_MODE:
            status.led_mode_data = PnsRunControlData(
                recv_data[13], recv_data[14], recv_data[15],
                recv_data[16], recv_data[17], recv_data[18]
            )
        else:
            status.smart_mode_data = PnsSmartModeData(
                group_no=recv_data[13],
                mute=recv_data[14],
                stop_input=recv_data[15],
                pattern_no=recv_data[16]
            )

        return status

def parse_arguments() -> argparse.Namespace:
    """Parse and validate command line arguments."""
    parser = argparse.ArgumentParser(
        description="LA-POE Controller - Control LA-POE devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --ip 192.168.1.100 G          # Get device status
  %(prog)s S 1 1 1 1 1 1                 # Run control command
  %(prog)s D 1 2 3 4 5 1 1               # Detailed control command
"""
    )

    parser.add_argument('--ip', default=DEFAULT_IP, help=f"Device IP (default: {DEFAULT_IP})")

    subparsers = parser.add_subparsers(dest='command', required=True, title='Commands')

    smart_mode = subparsers.add_parser('T', help='Smart mode control')
    smart_mode.add_argument('group', type=int, help='Group number (1-31)')

    mute = subparsers.add_parser('M', help='Mute control')
    mute.add_argument('state', type=int, choices=[0, 1], help='Mute state: 0=OFF, 1=ON')

    run_control = subparsers.add_parser('S', help='Run control')
    for led in range(1, 6):
        run_control.add_argument(f'led{led}', type=int, help=f'LED{led} pattern')
    run_control.add_argument('buzzer', type=int, help='Buzzer pattern')

    subparsers.add_parser('G', help='Get device status')

    return parser.parse_args()

def display_status(status: PnsStatusData) -> None:
    """Print device status."""
    print("\nDevice Status\n-------------")
    print(f"Mode: {'Smart' if status.mode else 'LED'} mode")

    print("\nInputs:")
    for idx, val in enumerate(status.input):
        print(f"  Input {idx+1}: {'ON' if val else 'OFF'}")

    if status.mode == PNS_LED_MODE:
        print("\nLED Patterns:")
        print(f"  LED1: {status.led_mode_data.led1}")
        print(f"  LED2: {status.led_mode_data.led2}")
        print(f"  LED3: {status.led_mode_data.led3}")
        print(f"  LED4: {status.led_mode_data.led4}")
        print(f"  LED5: {status.led_mode_data.led5}")
        print(f"  Buzzer: {status.led_mode_data.buzzer}")
    else:
        if status.smart_mode_data:
            print("\nSmart Mode Info:")
            print(f"  Group: {status.smart_mode_data.group_no}")
            print(f"  Mute: {'ON' if status.smart_mode_data.mute else 'OFF'}")
            print(f"  STOP Input: {'ON' if status.smart_mode_data.stop_input else 'OFF'}")
            print(f"  Pattern: {status.smart_mode_data.pattern_no}")

def main() -> None:
    args = parse_arguments()

    try:
        with PNSController(ip=args.ip) as controller:
            if args.command == 'T':
                controller.pns_smart_mode_command(args.group)
                print("Smart mode command sent successfully.")
            elif args.command == 'M':
                controller.pns_mute_command(args.state)
                print(f"Mute {'enabled' if args.state else 'disabled'}.")
            elif args.command == 'S':
                control_data = PnsRunControlData(
                    args.led1, args.led2, args.led3, args.led4, args.led5, args.buzzer
                )
                controller.pns_run_control_command(control_data)
                print("Run control command sent.")
            elif args.command == 'G':
                status = controller.pns_get_data_command()
                display_status(status)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
