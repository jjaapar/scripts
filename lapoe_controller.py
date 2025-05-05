#!/usr/bin/env python3
"""
LA-POE Controller - A Python script to control LA-POE devices.

Provides an intuitive command-line interface to manage LEDs, buzzers, and monitor device status.
"""

import socket
import struct
import sys
import argparse
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_IP = "172.17.32.127"
DEFAULT_PORT = 10000
PNS_PRODUCT_ID = b'AB'

# Command constants
COMMAND_MAP = {
    'smart-mode': b'T',
    'mute': b'M',
    'run-control': b'S',
    'get-status': b'G'
}

PNS_NAK = 0x15
PNS_LED_MODE = 0
MIN_GROUP_NUMBER = 1
MAX_GROUP_NUMBER = 31
RESPONSE_TIMEOUT = 1.0

@dataclass
class PnsRunControlData:
    """Data class for LED and buzzer control patterns."""
    led1: int
    led2: int
    led3: int
    led4: int
    led5: int
    buzzer: int

@dataclass
class PnsSmartModeData:
    """Data class for smart mode configuration."""
    group_no: int = 0
    mute: int = 0
    stop_input: int = 0
    pattern_no: int = 0

class PnsStatusData:
    """Class to hold device status information."""
    def __init__(self):
        self.mode = PNS_LED_MODE
        self.input = [0] * 8
        self.led_mode_data = None
        self.smart_mode_data = None

class PNSController:
    """Main controller class for LA-POE device communication."""
    
    def __init__(self, ip: str = DEFAULT_IP, port: int = DEFAULT_PORT, timeout: float = 5.0) -> None:
        """
        Initialize the controller with device connection parameters.
        
        Args:
            ip: Device IP address
            port: Device port number
            timeout: Socket timeout in seconds
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        logger.debug(f"Initialized controller with {ip}:{port} and timeout {timeout}s")

    def __enter__(self) -> 'PNSController':
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def connect(self) -> None:
        """Establish a connection to the LA-POE device."""
        try:
            logger.debug(f"Connecting to {self.ip}:{self.port}")
            self.sock.connect((self.ip, self.port))
            logger.info("Successfully connected to device")
        except socket.error as e:
            raise ConnectionError(f"Unable to connect to {self.ip}:{self.port}") from e

    def close(self) -> None:
        """Close the connection to the device."""
        logger.debug("Closing connection")
        self.sock.close()

    def send_command(self, send_data: bytes) -> bytes:
        """
        Send a command to the device and return the response.
        
        Args:
            send_data: Bytes to send to the device
            
        Returns:
            Response from the device
        """
        try:
            logger.debug(f"Sending command: {send_data.hex()}")
            self.sock.sendall(send_data)
            recv_data = self.sock.recv(1024)
            logger.debug(f"Received response: {recv_data.hex()}")
            return recv_data
        except socket.timeout:
            raise ConnectionError("Socket operation timed out") from None
        except socket.error as e:
            raise ConnectionError(f"Communication error with device: {e}") from e

    def pns_smart_mode_command(self, group_number: int) -> None:
        """
        Configure the device in smart mode.
        
        Args:
            group_number: Smart mode group number (1-31)
        """
        if not MIN_GROUP_NUMBER <= group_number <= MAX_GROUP_NUMBER:
            raise ValueError(f"Group number must be between {MIN_GROUP_NUMBER} and {MAX_GROUP_NUMBER}")
            
        send_data = struct.pack('>2ssxHB', PNS_PRODUCT_ID, COMMAND_MAP['smart-mode'], 1, group_number)
        recv_data = self.send_command(send_data)
        
        if not recv_data:
            raise ConnectionError("No response received from device")
            
        if recv_data[0] == PNS_NAK:
            raise ValueError('Device returned NAK (Negative Acknowledge)')

    def pns_mute_command(self, mute: int) -> None:
        """
        Send mute ON/OFF command.
        
        Args:
            mute: 0 for OFF, 1 for ON
        """
        send_data = struct.pack('>2ssxHB', PNS_PRODUCT_ID, COMMAND_MAP['mute'], 1, mute)
        recv_data = self.send_command(send_data)
        
        if not recv_data:
            raise ConnectionError("No response received from device")
            
        if recv_data[0] == PNS_NAK:
            raise ValueError('Device returned NAK (Negative Acknowledge)')

    def pns_run_control_command(self, control_data: PnsRunControlData) -> None:
        """
        Send LED and buzzer control data.
        
        Args:
            control_data: Object containing LED and buzzer patterns
        """
        for field, value in control_data.__dict__.items():
            if not 0 <= value <= 255:
                raise ValueError(f"{field} must be between 0 and 255 inclusive")
                
        send_data = struct.pack(
            '>2ssx6B',
            PNS_PRODUCT_ID,
            COMMAND_MAP['run-control'],
            control_data.led1,
            control_data.led2,
            control_data.led3,
            control_data.led4,
            control_data.led5,
            control_data.buzzer
        )
        recv_data = self.send_command(send_data)
        
        if not recv_data:
            raise ConnectionError("No response received from device")
            
        if recv_data[0] == PNS_NAK:
            raise ValueError('Device returned NAK (Negative Acknowledge)')

    def pns_get_data_command(self) -> PnsStatusData:
        """Request and parse device status."""
        send_data = struct.pack('>2ssx', PNS_PRODUCT_ID, COMMAND_MAP['get-status'])
        recv_data = self.send_command(send_data)

        if not recv_data:
            raise ValueError("No response received from device")
            
        if len(recv_data) < 19:
            raise ValueError(f"Response too short ({len(recv_data)} bytes). Expected at least 19 bytes")

        status = PnsStatusData()
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
        epilog=f"""Examples:
  %(prog)s --ip 192.168.1.100 get-status          # Get device status
  %(prog)s --port 1234 run-control 1 1 1 1 1 1     # Run control command
  %(prog)s --timeout 2 mute 1                     # Enable mute with timeout
  %(prog)s --verbose smart-mode 5                 # Set smart mode with group 5 and verbose output
  %(prog)s --quiet                                # Run in interactive mode with minimal output
"""
    )

    parser.add_argument('--ip', default=DEFAULT_IP, 
                       help=f"Device IP (default: {DEFAULT_IP})")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, 
                       help=f"Device port (default: {DEFAULT_PORT})")
    parser.add_argument('--verbose', action='store_true', 
                       help='Enable debug logging')
    parser.add_argument('--quiet', action='store_true', 
                       help='Suppress all status messages')
    parser.add_argument('--timeout', type=float, default=5.0,
                       help='Connection timeout in seconds (default: 5.0)')

    subparsers = parser.add_subparsers(dest='command', required=False, title='Commands')

    smart_mode = subparsers.add_parser('smart-mode', aliases=['smart'], 
                                    help='Configure smart mode')
    smart_mode.add_argument('group', type=int, 
                           help=f'Group number ({MIN_GROUP_NUMBER}-{MAX_GROUP_NUMBER})')

    mute = subparsers.add_parser('mute', help='Control mute state')
    mute.add_argument('state', type=int, choices=[0, 1], 
                     help='Mute state: 0=OFF, 1=ON')

    run_control = subparsers.add_parser('run-control', aliases=['run', 'control'], 
                                    help='Manual LED/buzzer control')
    for led in range(1, 6):
        run_control.add_argument(f'led{led}', type=int, 
                               help=f'LED{led} pattern (0-255)')
    run_control.add_argument('buzzer', type=int, 
                           help='Buzzer pattern (0-255)')

    get_status = subparsers.add_parser('get-status', aliases=['status', 'monitor'], 
                                   help='Get device status')

    interactive = subparsers.add_parser('interactive', aliases=['i', 'wizard'], 
                                    help='Interactive mode with guided prompts')
    
    # Add a default command if none is specified
    if len(sys.argv) == 1:
        parser.print_help()
        print("\nNo command specified. Entering interactive mode...")
        return argparse.Namespace(command='interactive', quiet=False, verbose=False, 
                                 ip=DEFAULT_IP, port=DEFAULT_PORT, timeout=5.0)
    
    return parser.parse_args()

def display_status(status: PnsStatusData) -> None:
    """Print device status in human-readable format."""
    print("\nDevice Status\n-------------")
    print(f"Mode: {'Smart' if status.mode else 'LED'} mode")

    print("\nInputs:")
    for idx, val in enumerate(status.input):
        print(f"  Input {idx+1}: {'ACTIVE' if val else 'INACTIVE'}")

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
            print("\nSmart Mode Configuration:")
            print(f"  Group: {status.smart_mode_data.group_no}")
            print(f"  Mute: {'ENABLED' if status.smart_mode_data.mute else 'DISABLED'}")
            print(f"  STOP Input: {'ACTIVE' if status.smart_mode_data.stop_input else 'INACTIVE'}")
            print(f"  Pattern: {status.smart_mode_data.pattern_no}")

def interactive_mode() -> argparse.Namespace:
    """Guide the user through interactive command selection."""
    print("\nWelcome to LA-POE Interactive Controller")
    print("----------------------------------------")
    
    # Get IP address
    ip = input(f"Enter device IP (default: {DEFAULT_IP}) or press Enter: ") or DEFAULT_IP
    
    # Get command
    print("\nAvailable Commands:")
    print("  1. Get Device Status")
    print("  2. Run Control (Manual LED/Buzzer Control)")
    print("  3. Configure Smart Mode")
    print("  4. Toggle Mute")
    
    while True:
        choice = input("\nEnter command number (1-4): ")
        if choice in ['1', '2', '3', '4']:
            break
        print("Invalid choice. Please enter a number between 1 and 4.")
    
    args = argparse.Namespace()
    args.ip = ip
    args.quiet = False
    args.verbose = False
    
    if choice == '1':
        args.command = 'get-status'
    elif choice == '2':
        args.command = 'run-control'
        print("\nEnter pattern values (0-255):")
        args.led1 = int(input("LED1: "))
        args.led2 = int(input("LED2: "))
        args.led3 = int(input("LED3: "))
        args.led4 = int(input("LED4: "))
        args.led5 = int(input("LED5: "))
        args.buzzer = int(input("Buzzer: "))
    elif choice == '3':
        args.command = 'smart-mode'
        while True:
            try:
                args.group = int(input(f"Enter group number ({MIN_GROUP_NUMBER}-{MAX_GROUP_NUMBER}): "))
                if MIN_GROUP_NUMBER <= args.group <= MAX_GROUP_NUMBER:
                    break
                print(f"Please enter a number between {MIN_GROUP_NUMBER} and {MAX_GROUP_NUMBER}")
            except ValueError:
                print("Invalid input. Please enter a number.")
    elif choice == '4':
        args.command = 'mute'
        while True:
            state = input("Turn mute on? (y/n): ").lower()
            if state in ['y', 'yes']:
                args.state = 1
                break
            elif state in ['n', 'no']:
                args.state = 0
                break
            print("Please enter 'y' or 'n'")
    
    return args

def main() -> None:
    """Main function to handle command-line interface."""
    args = parse_arguments()
    
    # Handle quiet mode
    if args.quiet:
        logger.setLevel(logging.ERROR)
    elif args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Handle interactive mode
    if args.command in ['interactive', None]:
        args = interactive_mode()
    
    try:
        with PNSController(ip=args.ip, port=args.port, timeout=args.timeout) as controller:
            if args.command in ['smart-mode', 'smart']:
                controller.pns_smart_mode_command(args.group)
                if not args.quiet:
                    logger.info("Smart mode command sent successfully.")
            elif args.command in ['mute']:
                controller.pns_mute_command(args.state)
                if not args.quiet:
                    logger.info(f"Mute {'enabled' if args.state else 'disabled'}.")
            elif args.command in ['run-control', 'run', 'control']:
                control_data = PnsRunControlData(
                    args.led1, args.led2, args.led3, args.led4, args.led5, args.buzzer
                )
                controller.pns_run_control_command(control_data)
                if not args.quiet:
                    logger.info("Run control command sent.")
            elif args.command in ['get-status', 'status', 'monitor']:
                status = controller.pns_get_data_command()
                if not args.quiet:
                    display_status(status)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        sys.exit(1)

if __name__ == '__main__':
    main()
