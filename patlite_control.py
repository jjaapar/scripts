#!/usr/bin/env python3
"""
Patlite LA6-POE Controller - A human-friendly interface for controlling and monitoring Patlite signal lights.
"""

import socket
import time
import argparse
from enum import Enum, auto
from typing import Optional, Tuple, Dict
from contextlib import contextmanager
from dataclasses import dataclass

class LightState(Enum):
    """Enumeration for light states."""
    OFF = 0
    ON = 1
    FLASH = 2
    
    def __str__(self):
        return self.name.lower()

class BuzzerState(Enum):
    """Enumeration for buzzer states."""
    OFF = 0
    ON = 1
    FLASH = 2
    
    def __str__(self):
        return self.name.lower()

class FlashSpeed(Enum):
    """Enumeration for flash speeds."""
    SLOW = 1
    MEDIUM = 2
    FAST = 3
    
    def __str__(self):
        return self.name.lower()

@dataclass
class DeviceStatus:
    """Dataclass to hold device status information."""
    red: LightState
    yellow: LightState
    green: LightState
    buzzer: BuzzerState
    flash_speed: FlashSpeed
    device_model: str
    firmware_version: str

    def __str__(self):
        status_lines = [
            f"Device Model: {self.device_model}",
            f"Firmware Version: {self.firmware_version}",
            f"Red Light: {self.red}",
            f"Yellow Light: {self.yellow}",
            f"Green Light: {self.green}",
            f"Buzzer: {self.buzzer}",
            f"Flash Speed: {self.flash_speed}"
        ]
        return "\n".join(status_lines)

class PatliteController:
    """A human-friendly controller for Patlite LA6-POE signal lights with status monitoring."""
    
    DEFAULT_PORT = 10000
    SOCKET_TIMEOUT = 2  # seconds
    STATUS_COMMAND = b"$SR\r"
    MODEL_COMMAND = b"$SM\r"
    VERSION_COMMAND = b"$SV\r"
    
    def __init__(self, ip_address: str, port: int = DEFAULT_PORT):
        """
        Initialize the controller with device connection details.
        
        Args:
            ip_address: The IP address of the Patlite device
            port: The network port (default 10000)
        """
        self.ip_address = ip_address
        self.port = port
    
    @contextmanager
    def _connection(self):
        """Context manager for socket connection."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.SOCKET_TIMEOUT)
        try:
            sock.connect((self.ip_address, self.port))
            yield sock
        except socket.timeout:
            raise ConnectionError(f"Timeout connecting to Patlite at {self.ip_address}:{self.port}")
        except ConnectionRefusedError:
            raise ConnectionError(f"Connection refused by Patlite at {self.ip_address}:{self.port}")
        finally:
            sock.close()
    
    def _send_command(self, command: bytes) -> str:
        """
        Send a command to the Patlite device and return response.
        
        Args:
            command: The command bytes to send
            
        Returns:
            str: The response from the device
            
        Raises:
            ConnectionError: If communication with the device fails
        """
        try:
            with self._connection() as conn:
                conn.sendall(command)
                response = conn.recv(1024).decode('ascii').strip()
                return response
        except Exception as e:
            raise ConnectionError(f"Failed to communicate with Patlite: {str(e)}")
    
    def get_status(self) -> DeviceStatus:
        """
        Get the current status of the Patlite device.
        
        Returns:
            DeviceStatus: An object containing all status information
            
        Raises:
            ValueError: If the status response is malformed
        """
        try:
            # Get device model and version first
            model = self._send_command(self.MODEL_COMMAND)
            version = self._send_command(self.VERSION_COMMAND)
            
            # Get current status
            status_response = self._send_command(self.STATUS_COMMAND)
            
            if not status_response.startswith("$SR") or len(status_response) < 8:
                raise ValueError("Invalid status response format")
            
            # Parse status response: $SRRRYYGG*F
            red = LightState(int(status_response[3]))
            yellow = LightState(int(status_response[4]))
            green = LightState(int(status_response[5]))
            buzzer = BuzzerState(int(status_response[7]))
            flash_speed = FlashSpeed(int(status_response[8]))
            
            return DeviceStatus(
                red=red,
                yellow=yellow,
                green=green,
                buzzer=buzzer,
                flash_speed=flash_speed,
                device_model=model.replace("$SM", "").strip(),
                firmware_version=version.replace("$SV", "").strip()
            )
            
        except (IndexError, ValueError) as e:
            raise ValueError(f"Failed to parse device status: {str(e)}")
    
    def control_lights(
        self,
        red: LightState,
        yellow: LightState,
        green: LightState,
        buzzer: Optional[BuzzerState] = None,
        flash_speed: FlashSpeed = FlashSpeed.MEDIUM
    ) -> bool:
        """
        Control the lights and buzzer of the Patlite.
        
        Args:
            red: State for the red light
            yellow: State for the yellow light
            green: State for the green light
            buzzer: State for the buzzer (None leaves unchanged)
            flash_speed: Speed for flashing lights/buzzer
            
        Returns:
            bool: True if command succeeded, False otherwise
        """
        # Build command string
        cmd = f"$KE{red.value}{yellow.value}{green.value}"
        cmd += f"{buzzer.value}" if buzzer is not None else "*"
        cmd += f"{flash_speed.value}\r"
        
        print(f"Setting lights: Red {red}, Yellow {yellow}, Green {green}", end="")
        if buzzer is not None:
            print(f", Buzzer {buzzer}", end="")
        print(f", Flash speed {flash_speed}")
        
        response = self._send_command(cmd.encode('ascii'))
        return response == cmd.strip()
    
    def turn_all_off(self) -> bool:
        """Turn all lights and buzzer off."""
        print("Turning all lights and buzzer off")
        return self.control_lights(
            red=LightState.OFF,
            yellow=LightState.OFF,
            green=LightState.OFF,
            buzzer=BuzzerState.OFF
        )
    
    def test_sequence(self, duration: float = 1.0) -> bool:
        """Run a test sequence of all lights and buzzer."""
        print("Running test sequence...")
        try:
            self.turn_all_off()
            time.sleep(duration)
            
            states = [
                (LightState.ON, LightState.OFF, LightState.OFF, "Red light on"),
                (LightState.OFF, LightState.ON, LightState.OFF, "Yellow light on"),
                (LightState.OFF, LightState.OFF, LightState.ON, "Green light on"),
                (LightState.FLASH, LightState.FLASH, LightState.FLASH, "All lights flashing with buzzer")
            ]
            
            for red, yellow, green, description in states:
                print(description)
                if not self.control_lights(red, yellow, green, BuzzerState.ON if "buzzer" in description else None):
                    return False
                time.sleep(duration)
            
            return self.turn_all_off()
        except Exception as e:
            print(f"Test sequence failed: {str(e)}")
            return False

def parse_arguments() -> argparse.Namespace:
    """Parse and validate command line arguments."""
    parser = argparse.ArgumentParser(
        description="Patlite LA6-POE Controller - Control and monitor your signal lights",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Connection parameters
    connection_group = parser.add_argument_group('Connection Settings')
    connection_group.add_argument(
        '--ip',
        required=True,
        help="IP address of your Patlite device"
    )
    connection_group.add_argument(
        '--port',
        type=int,
        default=PatliteController.DEFAULT_PORT,
        help="Network port of the Patlite device"
    )
    
    # Light control
    light_group = parser.add_argument_group('Light Control')
    for color in ['red', 'yellow', 'green']:
        light_group.add_argument(
            f'--{color}',
            type=str.lower,
            choices=['off', 'on', 'flash'],
            help=f"Set {color} light state"
        )
    
    # Buzzer control
    buzzer_group = parser.add_argument_group('Buzzer Control')
    buzzer_group.add_argument(
        '--buzzer',
        type=str.lower,
        choices=['off', 'on', 'flash'],
        help="Set buzzer state"
    )
    
    # Flash control
    flash_group = parser.add_argument_group('Flash Control')
    flash_group.add_argument(
        '--flash-speed',
        type=str.lower,
        choices=['slow', 'medium', 'fast'],
        default='medium',
        help="Set flash speed"
    )
    
    # Actions
    action_group = parser.add_argument_group('Actions')
    action_group.add_argument(
        '--test',
        action='store_true',
        help="Run a visual test sequence"
    )
    action_group.add_argument(
        '--off',
        action='store_true',
        help="Turn all lights and buzzer off"
    )
    action_group.add_argument(
        '--status',
        action='store_true',
        help="Check current device status"
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    try:
        # Create controller instance
        controller = PatliteController(args.ip, args.port)
        print(f"Connected to Patlite at {args.ip}:{args.port}")
        
        # Map string arguments to enums
        state_map = {
            'off': LightState.OFF,
            'on': LightState.ON,
            'flash': LightState.FLASH
        }
        speed_map = {
            'slow': FlashSpeed.SLOW,
            'medium': FlashSpeed.MEDIUM,
            'fast': FlashSpeed.FAST
        }
        
        # Execute requested action
        if args.status:
            status = controller.get_status()
            print("\nCurrent Device Status:")
            print("---------------------")
            print(status)
        elif args.test:
            if not controller.test_sequence():
                print("Test sequence completed with errors")
        elif args.off:
            if not controller.turn_all_off():
                print("Failed to turn lights off")
        elif any(getattr(args, color) for color in ['red', 'yellow', 'green']):
            # Set specific light states
            success = controller.control_lights(
                red=state_map.get(args.red, LightState.OFF),
                yellow=state_map.get(args.yellow, LightState.OFF),
                green=state_map.get(args.green, LightState.OFF),
                buzzer=BuzzerState[args.buzzer.upper()] if args.buzzer else None,
                flash_speed=speed_map[args.flash_speed]
            )
            if not success:
                print("Failed to set light states")
        else:
            print("No action specified. Use --help for usage information.")
        
    except ConnectionError as e:
        print(f"Connection error: {str(e)}")
    except ValueError as e:
        print(f"Status error: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
