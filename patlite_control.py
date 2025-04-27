#!/usr/bin/env python3
"""
Patlite LA6-POE Smart Controller (Deluxe Version)
==================================================

Features:
- Simple pattern and brightness control
- Auto-reconnect if communication fails
- Pretty terminal output using Rich
"""

import socket
import struct
import argparse
from typing import Dict, Optional
from rich import print
from rich.console import Console

# --------------------------
# Device Configuration
# --------------------------

DEFAULT_IP = '192.168.1.100'
DEFAULT_PORT = 10000
CONNECT_TIMEOUT = 5
RESPONSE_TIMEOUT = 10

PRODUCT_CODE = b'LA'
ACK = 0x06
NAK = 0x15

LED_PATTERNS = {
    'off': 0x00,
    'on': 0x01,
    'slow': 0x02,
    'medium': 0x03,
    'fast': 0x04,
    'no_change': 0x09
}

LED_ORDER = ['red1', 'red2', 'amber', 'green', 'blue']

console = Console()

# --------------------------
# Core Controller Class
# --------------------------

class PatliteController:
    """Smart controller for Patlite LA6-POE signal towers."""

    def __init__(self) -> None:
        self.socket: Optional[socket.socket] = None
        self.ip = DEFAULT_IP
        self.port = DEFAULT_PORT

    def __enter__(self) -> 'PatliteController':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def connect(self, ip: Optional[str] = None, port: Optional[int] = None) -> None:
        """Establish connection to the Patlite device."""
        if ip:
            self.ip = ip
        if port:
            self.port = port

        self.disconnect()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(CONNECT_TIMEOUT)
        try:
            self.socket.connect((self.ip, self.port))
            console.print(f"🔌 [green]Connected to Patlite at {self.ip}:{self.port}[/green]")
        except socket.error as e:
            self.socket = None
            raise ConnectionError(f"❌ [red]Connection failed:[/red] {e}")

    def disconnect(self) -> None:
        """Close the connection if open."""
        if self.socket:
            self.socket.close()
            self.socket = None
            console.print("[blue]🔌 Connection closed[/blue]")

    def _send_command(self, command: str, data: bytes = b'') -> bytes:
        """Send a command to the device and return the response."""
        if not self.socket:
            raise ConnectionError("Not connected to device")
        try:
            header = struct.pack('>2ssxH', PRODUCT_CODE, command.encode(), len(data))
            self.socket.sendall(header + data)
            self.socket.settimeout(RESPONSE_TIMEOUT)
            response = self.socket.recv(1024)
            if not response:
                raise ConnectionError("📡 No response received")
            if response[0] == NAK:
                raise ValueError("Device rejected command (NAK received)")
            return response
        except (socket.error, ConnectionError):
            console.print("[yellow]⚠️ Communication error - attempting reconnect...[/yellow]")
            self.connect()  # Auto-reconnect once
            # Retry sending once
            try:
                header = struct.pack('>2ssxH', PRODUCT_CODE, command.encode(), len(data))
                self.socket.sendall(header + data)
                self.socket.settimeout(RESPONSE_TIMEOUT)
                response = self.socket.recv(1024)
                if not response or response[0] == NAK:
                    raise ValueError("Device rejected command (after reconnect)")
                return response
            except socket.error as e:
                raise ConnectionError(f"❌ Communication failed even after reconnect: {e}")

    def set_patterns(self, **led_patterns: str) -> None:
        """Set LEDs using named patterns."""
        patterns = {led: 'no_change' for led in LED_ORDER}
        patterns.update(led_patterns)
        try:
            led_codes = [LED_PATTERNS[patterns[led].lower()] for led in LED_ORDER]
        except KeyError as e:
            raise ValueError(f"Invalid LED pattern: {e}")

        self._send_command('s', struct.pack('BBBBB', *led_codes))
        console.print("[cyan]💡 LED patterns updated[/cyan]")

    def set_brightness(self, **brightness_levels: int) -> None:
        """Set custom brightness levels (0-255) for LEDs."""
        def _scale(value: int) -> int:
            value = max(0, min(255, value))
            if value == 0: return 0x00
            if value < 51: return 0x01
            if value < 102: return 0x02
            if value < 204: return 0x03
            return 0x04

        levels = {led: 0 for led in LED_ORDER}
        levels.update(brightness_levels)

        scaled = [_scale(levels[led]) for led in LED_ORDER]
        self._send_command('s', struct.pack('BBBBB', *scaled))
        console.print("[magenta]🌈 Brightness levels set[/magenta]")

    def all_off(self) -> None:
        """Turn all LEDs off."""
        self._send_command('c')
        console.print("[dim]🌑 All LEDs turned off[/dim]")

    def get_status(self) -> Dict[str, str]:
        """Get current status of all LEDs."""
        response = self._send_command('t')
        status = {}
        for i, led in enumerate(LED_ORDER):
            code = response[i+1]
            status[led] = next((name for name, val in LED_PATTERNS.items() if val == code), 'unknown')
        return status

# --------------------------
# Command Line Interface
# --------------------------

def run_cli() -> int:
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

    parser.add_argument(
        'command',
        choices=['set', 'brightness', 'clear', 'status'],
        help="Operation to perform"
    )

    for led in LED_ORDER:
        parser.add_argument(f'--{led}', help=f"{led} pattern or brightness (depending on command)")

    parser.add_argument('--ip', default=DEFAULT_IP, help="Device IP address")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help="Device port")

    args = parser.parse_args()

    try:
        with PatliteController() as controller:
            controller.connect(args.ip, args.port)

            led_args = {led: getattr(args, led) for led in LED_ORDER if getattr(args, led) is not None}

            if args.command == 'set':
                controller.set_patterns(**led_args)
            elif args.command == 'brightness':
                brightness = {led: int(val) for led, val in led_args.items()}
                controller.set_brightness(**brightness)
            elif args.command == 'clear':
                controller.all_off()
            elif args.command == 'status':
                status = controller.get_status()
                console.print("\n[b]Current Status:[/b]\n")
                for led, state in status.items():
                    console.print(f"  [bold cyan]{led:>6}[/bold cyan]: [green]{state}[/green]")

    except Exception as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        return 1

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(run_cli())
