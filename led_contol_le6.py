#!/usr/bin/python3

#!/usr/bin/env python3
"""
Patlite LA6-POE Controller (LEDs Only)
======================================

A user-friendly Python script to control the LED tower on a Patlite LA6-POE device.
Provides simple commands to set, clear, and check the status of all 5 LEDs.
"""

import socket
import struct
import argparse
from typing import Dict, List

# =============================================================================
# CONSTANTS - Device Configuration
# =============================================================================

# Device Communication Settings
DEVICE_MODEL = "LA6-POE"
PRODUCT_CODE = b'LA'  # Patlite product identifier
DEFAULT_IP = '192.168.1.100'  # Common factory default IP
DEFAULT_PORT = 10000  # Standard port for Patlite devices

# Timeout Settings (in seconds)
CONNECTION_TIMEOUT = 5  # Max time to establish connection
RESPONSE_TIMEOUT = 10   # Max time to wait for device response

# Protocol Constants
ACKNOWLEDGE = 0x06  # Positive response from device
ERROR_RESPONSE = 0x15  # Negative response from device

# =============================================================================
# LED CONFIGURATION - Pattern Definitions
# =============================================================================

LED_PATTERNS: Dict[str, int] = {
    # Basic states
    'off': 0x00,       # LED completely off
    'on': 0x01,        # LED fully lit
    
    # Blinking patterns
    'slow': 0x02,      # Slow blink (0.5Hz - 2 seconds cycle)
    'medium': 0x03,    # Medium blink (1Hz - 1 second cycle)
    'fast': 0x04,      # Fast blink (2Hz - 0.5 second cycle)
    
    # Special state
    'no_change': 0x09  # Maintain current LED state
}

# =============================================================================
# DEVICE COMMANDS - Protocol Implementation
# =============================================================================

DEVICE_COMMANDS = {
    'set': b'S',    # Command to set LED states
    'clear': b'C',  # Command to turn all LEDs off
    'status': b'G'  # Command to check current states
}

class PatliteController:
    """
    Handles communication with the Patlite LA6-POE device.
    Manages the network connection and command execution.
    """
    
    def __init__(self):
        """Initialize a new controller instance."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def connect(self, ip: str = DEFAULT_IP, port: int = DEFAULT_PORT) -> None:
        """
        Establish connection to the Patlite device.
        
        Args:
            ip: Device IP address
            port: Network port number
            
        Raises:
            ConnectionError: If connection fails
        """
        self.socket.settimeout(CONNECTION_TIMEOUT)
        try:
            self.socket.connect((ip, port))
            print(f"✅ Connected to {DEVICE_MODEL} at {ip}:{port}")
        except socket.error as err:
            raise ConnectionError(f"🚨 Connection failed: {err}")
    
    def disconnect(self) -> None:
        """Safely close the network connection."""
        self.socket.close()
        print("🔌 Connection closed")
    
    def _execute_command(self, command: bytes, payload: bytes = b'') -> bytes:
        """
        Send a command to the device and receive the response.
        
        Args:
            command: The command byte to send
            payload: Additional data for the command
            
        Returns:
            The raw response from the device
            
        Raises:
            ConnectionError: If communication fails
            ValueError: If device returns an error
        """
        # Format: [ProductID][Command][Reserved][DataLength][Data]
        header = struct.pack('>2ssxH', PRODUCT_CODE, command, len(payload))
        
        try:
            # Send command and wait for response
            self.socket.send(header + payload)
            self.socket.settimeout(RESPONSE_TIMEOUT)
            response = self.socket.recv(1024)
            
            # Check for error response
            if response[0] == ERROR_RESPONSE:
                raise ValueError('⚠️ Device rejected command (NAK received)')
            return response
            
        except socket.error as err:
            raise ConnectionError(f"📡 Communication error: {err}")
    
    def set_leds(self, 
                red1: str = 'no_change',
                red2: str = 'no_change',
                amber: str = 'no_change',
                green: str = 'no_change',
                blue: str = 'no_change') -> None:
        """
        Set the state of all LEDs on the device.
        
        Args:
            red1:   Pattern for first red LED
            red2:   Pattern for second red LED
            amber:  Pattern for amber LED
            green:  Pattern for green LED
            blue:   Pattern for blue LED
        """
        # Convert pattern names to device codes
        led_states = [
            LED_PATTERNS.get(red1.lower(), 0x09),
            LED_PATTERNS.get(red2.lower(), 0x09),
            LED_PATTERNS.get(amber.lower(), 0x09),
            LED_PATTERNS.get(green.lower(), 0x09),
            LED_PATTERNS.get(blue.lower(), 0x09)
        ]
        
        # Send command with LED states
        self._execute_command(DEVICE_COMMANDS['set'], struct.pack('BBBBB', *led_states))
        print("💡 LEDs updated successfully")
    
    def clear_leds(self) -> None:
        """Turn off all LEDs on the device."""
        self._execute_command(DEVICE_COMMANDS['clear'])
        print("🌑 All LEDs turned off")
    
    def get_status(self) -> Dict[str, str]:
        """
        Get the current state of all LEDs.
        
        Returns:
            Dictionary mapping LED names to their current patterns
        """
        response = self._execute_command(DEVICE_COMMANDS['status'])
        
        # Convert numeric codes back to pattern names
        def pattern_name(code: int) -> str:
            for name, value in LED_PATTERNS.items():
                if value == code:
                    return name
            return 'unknown'
        
        return {
            'red1': pattern_name(response[1]),
            'red2': pattern_name(response[2]),
            'amber': pattern_name(response[3]),
            'green': pattern_name(response[4]),
            'blue': pattern_name(response[5])
        }

# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser."""
    parser = argparse.ArgumentParser(
        description=f"Patlite {DEVICE_MODEL} Controller - LED Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  Set LEDs:    ./patlite_control.py set --red1 fast --green on
  Clear LEDs:  ./patlite_control.py clear
  Check LEDs:  ./patlite_control.py status"""
    )
    
    # Main command selection
    parser.add_argument(
        "command",
        choices=['set', 'clear', 'status'],
        help="Operation to perform:\n"
             "  set    - Configure LED states\n"
             "  clear  - Turn all LEDs off\n"
             "  status - Check current LED states"
    )
    
    # LED pattern options
    led_help = "LED pattern (options: " + ", ".join(LED_PATTERNS.keys()) + ")"
    parser.add_argument("--red1", choices=LED_PATTERNS.keys(), help=f"First red LED - {led_help}")
    parser.add_argument("--red2", choices=LED_PATTERNS.keys(), help=f"Second red LED - {led_help}")
    parser.add_argument("--amber", choices=LED_PATTERNS.keys(), help=f"Amber LED - {led_help}")
    parser.add_argument("--green", choices=LED_PATTERNS.keys(), help=f"Green LED - {led_help}")
    parser.add_argument("--blue", choices=LED_PATTERNS.keys(), help=f"Blue LED - {led_help}")
    
    # Connection options
    parser.add_argument("--ip", default=DEFAULT_IP, 
                       help=f"Device IP address (default: {DEFAULT_IP})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                       help=f"Network port (default: {DEFAULT_PORT})")
    
    return parser

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main program execution."""
    parser = create_parser()
    args = parser.parse_args()
    controller = PatliteController()
    
    try:
        # Establish connection
        controller.connect(args.ip, args.port)
        
        # Execute requested command
        if args.command == "set":
            controller.set_leds(
                red1=args.red1,
                red2=args.red2,
                amber=args.amber,
                green=args.green,
                blue=args.blue
            )
        elif args.command == "clear":
            controller.clear_leds()
        elif args.command == "status":
            status = controller.get_status()
            print("\nCurrent LED Status:")
            print(f"  🔴 Red1:   {status['red1']}")
            print(f"  🔴 Red2:   {status['red2']}")
            print(f"  🟠 Amber:  {status['amber']}")
            print(f"  🟢 Green:  {status['green']}")
            print(f"  🔵 Blue:   {status['blue']}")
    
    except Exception as error:
        print(f"\n❌ Error: {error}")
    
    finally:
        # Ensure connection is closed
        controller.disconnect()

if __name__ == '__main__':
    main()
