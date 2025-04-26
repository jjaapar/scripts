#!/usr/bin/env python3
"""
Patlite LA6-POE Smart Controller
================================

A human-friendly Python interface for controlling Patlite signal towers.
Provides both simple pattern-based and smooth brightness control for all LEDs.

Features:
- Simple commands for normal operation
- Fine-grained brightness control (0-255)
- Automatic connection handling
- Clear status reporting
"""

import socket
import struct
import argparse
from typing import Dict, List, Optional

# --------------------------
# Device Configuration
# --------------------------

# Network settings (defaults for LA6-POE)
DEFAULT_IP = '192.168.1.100'  # Common factory default IP
DEFAULT_PORT = 10000          # Standard control port
CONNECT_TIMEOUT = 5           # Seconds to wait for connection
RESPONSE_TIMEOUT = 10         # Seconds to wait for responses

# Protocol constants
PRODUCT_CODE = b'LA'          # Patlite's product identifier
ACK = 0x06                    # Positive acknowledgment
NAK = 0x15                    # Negative acknowledgment

# Available LED patterns
LED_PATTERNS = {
    # Basic states
    'off': 0x00,        # LED completely off
    'on': 0x01,         # LED fully on
    
    # Blinking patterns
    'slow': 0x02,       # Slow blink (0.5Hz)
    'medium': 0x03,     # Medium blink (1Hz)
    'fast': 0x04,       # Fast blink (2Hz)
    
    # Special
    'no_change': 0x09   # Maintain current state
}

# --------------------------
# Core Controller Class
# --------------------------

class PatliteController:
    """Smart controller for Patlite LA6-POE signal towers."""
    
    def __init__(self):
        """Initialize a new controller instance."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(CONNECT_TIMEOUT)
    
    def __enter__(self):
        """Support context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure connection is closed when leaving context."""
        self.disconnect()
    
    def connect(self, ip: str = DEFAULT_IP, port: int = DEFAULT_PORT) -> None:
        """
        Establish connection to the Patlite device.
        
        Args:
            ip: Device IP address
            port: Network port number
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.socket.connect((ip, port))
            print(f"🔌 Connected to Patlite at {ip}:{port}")
        except socket.error as e:
            raise ConnectionError(f"❌ Connection failed: {e}")
    
    def disconnect(self) -> None:
        """Safely close the connection."""
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
            print("🔌 Connection closed")
    
    def _send_command(self, command: str, data: bytes = b'') -> bytes:
        """
        Send a command to the device and return the response.
        
        Args:
            command: One of 'set', 'clear', or 'status'
            data: Optional payload data
            
        Returns:
            The raw response bytes
            
        Raises:
            ConnectionError: If communication fails
            ValueError: If device rejects command
        """
        try:
            # Format: [ProductID][Command][Reserved][DataLength][Data]
            header = struct.pack('>2ssxH', PRODUCT_CODE, command, len(data))
            self.socket.send(header + data)
            
            self.socket.settimeout(RESPONSE_TIMEOUT)
            response = self.socket.recv(1024)
            
            if response[0] == NAK:
                raise ValueError("Device rejected command (NAK received)")
            return response
            
        except socket.error as e:
            raise ConnectionError(f"📡 Communication error: {e}")
    
    def set_patterns(self, **led_patterns) -> None:
        """
        Set LEDs using named patterns.
        
        Args:
            red1: Pattern for first red LED
            red2: Pattern for second red LED
            amber: Pattern for amber LED
            green: Pattern for green LED
            blue: Pattern for blue LED
            
        Example:
            controller.set_patterns(red1='on', green='slow')
        """
        # Default to 'no_change' for unspecified LEDs
        patterns = {
            'red1': 'no_change',
            'red2': 'no_change',
            'amber': 'no_change',
            'green': 'no_change',
            'blue': 'no_change',
            **led_patterns
        }
        
        # Convert to device codes
        led_codes = [LED_PATTERNS[p.lower()] for p in patterns.values()]
        self._send_command('set', struct.pack('BBBBB', *led_codes))
        print("💡 LED patterns updated")
    
    def set_brightness(self, **brightness_levels) -> None:
        """
        Set custom brightness levels (0-255) for LEDs.
        
        Args:
            red1: Brightness for first red LED (0-255)
            red2: Brightness for second red LED (0-255)
            amber: Brightness for amber LED (0-255)
            green: Brightness for green LED (0-255)
            blue: Brightness for blue LED (0-255)
            
        Example:
            controller.set_brightness(red1=255, green=128)
        """
        def _scale_brightness(value: int) -> int:
            """Convert 0-255 to device's 5 brightness levels."""
            value = max(0, min(255, value))
            if value == 0: return 0x00
            if value < 51: return 0x01
            if value < 102: return 0x02
            if value < 204: return 0x03
            return 0x04
        
        # Default to 0 (off) for unspecified LEDs
        levels = {
            'red1': 0,
            'red2': 0,
            'amber': 0,
            'green': 0,
            'blue': 0,
            **brightness_levels
        }
        
        # Convert and send
        scaled = [_scale_brightness(v) for v in levels.values()]
        self._send_command('set', struct.pack('BBBBB', *scaled))
        print("🌈 Brightness levels set")
    
    def all_off(self) -> None:
        """Turn all LEDs off."""
        self._send_command('clear')
        print("🌑 All LEDs turned off")
    
    def get_status(self) -> Dict[str, str]:
        """
        Get current status of all LEDs.
        
        Returns:
            Dictionary mapping LED names to their current patterns
        """
        response = self._send_command('status')
        
        # Convert response codes to pattern names
        status = {}
        for i, led in enumerate(['red1', 'red2', 'amber', 'green', 'blue']):
            status[led] = next(
                (name for name, code in LED_PATTERNS.items() if code == response[i+1]),
                'unknown'
            )
        
        return status

# --------------------------
# Command Line Interface
# --------------------------

def run_cli():
    """Handle command line execution."""
    parser = argparse.ArgumentParser(
        description="Patlite LA6-POE Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  Set patterns:   ./patlite.py set --red1 on --green slow
  Set brightness: ./patlite.py brightness --red1 255 --amber 128
  Clear all:      ./patlite.py clear
  Check status:   ./patlite.py status"""
    )
    
    # Main command
    parser.add_argument(
        'command',
        choices=['set', 'brightness', 'clear', 'status'],
        help="Operation to perform"
    )
    
    # LED options
    led_group = parser.add_argument_group('LED settings')
    for led in ['red1', 'red2', 'amber', 'green', 'blue']:
        if parser.parse_args().command == 'brightness':
            led_group.add_argument(
                f'--{led}', type=int, default=0,
                help=f"{led} brightness (0-255)"
            )
        else:
            led_group.add_argument(
                f'--{led}', choices=LED_PATTERNS.keys(),
                help=f"{led} pattern"
            )
    
    # Network options
    net_group = parser.add_argument_group('Network settings')
    net_group.add_argument('--ip', default=DEFAULT_IP, help="Device IP address")
    net_group.add_argument('--port', type=int, default=DEFAULT_PORT, help="Device port")
    
    args = parser.parse_args()
    
    # Execute command
    with PatliteController() as controller:
        try:
            controller.connect(args.ip, args.port)
            
            if args.command == 'set':
                controller.set_patterns(**{
                    k: v for k, v in vars(args).items()
                    if k in ['red1', 'red2', 'amber', 'green', 'blue'] and v is not None
                })
            elif args.command == 'brightness':
                controller.set_brightness(**{
                    k: v for k, v in vars(args).items()
                    if k in ['red1', 'red2', 'amber', 'green', 'blue']
                })
            elif args.command == 'clear':
                controller.all_off()
            elif args.command == 'status':
                status = controller.get_status()
                print("\nCurrent Status:")
                for led, state in status.items():
                    print(f"  {led:>6}: {state}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return 1
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(run_cli())
