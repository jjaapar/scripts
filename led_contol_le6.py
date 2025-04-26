#!/usr//bin/python3

import socket
import struct
import argparse
from typing import Optional, List, Dict

# Constants for Patlite LA6-POE
PNS_PRODUCT_ID = b'LA'
PNS_COMMANDS = {
    'control': b'S',  # Operation control command
    'clear': b'C',    # Clear command
    'status': b'G'    # Get status command
}
PNS_ACK = 0x06
PNS_NAK = 0x15

# LA6-POE has 5 LEDs (Red1, Red2, Amber, Green, Blue) and a buzzer
LED_PATTERNS: Dict[str, int] = {
    'off': 0x00,
    'on': 0x01,
    'slow': 0x02,      # 0.5Hz blinking
    'medium': 0x03,    # 1Hz blinking
    'fast': 0x04,      # 2Hz blinking
    'no_change': 0x09
}

BUZZER_PATTERNS: Dict[str, int] = {
    'off': 0x00,
    'on': 0x01,
    'intermittent': 0x02,  # 0.5Hz beeping
    'continuous': 0x03,    # Continuous sound
    'no_change': 0x09
}

DEFAULT_IP = '192.168.1.100'  # Typical default IP for Patlite LA6-POE
DEFAULT_PORT = 10000
CONNECT_TIMEOUT = 5
RECEIVE_TIMEOUT = 10

class PatliteLA6:
    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def connect(self, ip: str = DEFAULT_IP, port: int = DEFAULT_PORT) -> None:
        """Connect to the Patlite device"""
        self._sock.settimeout(CONNECT_TIMEOUT)
        try:
            self._sock.connect((ip, port))
            print(f"Connected to Patlite LA6-POE at {ip}:{port}")
        except socket.error as e:
            raise ConnectionError(f"Connection failed: {e}")
    
    def close(self) -> None:
        """Close the connection"""
        self._sock.close()
    
    def _send_command(self, command: bytes, data: bytes = b'') -> bytes:
        """Send command to device and return response"""
        # LA6-POE command format: [ProductID(2)][Command(1)][Reserved(1)][DataLength(2)][Data(n)]
        header = struct.pack('>2ssxH', PNS_PRODUCT_ID, command, len(data))
        
        try:
            self._sock.send(header + data)
            self._sock.settimeout(RECEIVE_TIMEOUT)
            response = self._sock.recv(1024)
            
            if response[0] == PNS_NAK:
                raise ValueError('Device returned NAK (Negative Acknowledge)')
            return response
        except socket.error as e:
            raise ConnectionError(f"Communication error: {e}")
    
    def set_leds_buzzer(self, 
                       red1: str = 'no_change',
                       red2: str = 'no_change',
                       amber: str = 'no_change',
                       green: str = 'no_change',
                       blue: str = 'no_change',
                       buzzer: str = 'no_change') -> None:
        """Set the state of LEDs and buzzer"""
        patterns = [
            LED_PATTERNS.get(red1, 0x09),
            LED_PATTERNS.get(red2, 0x09),
            LED_PATTERNS.get(amber, 0x09),
            LED_PATTERNS.get(green, 0x09),
            LED_PATTERNS.get(blue, 0x09),
            BUZZER_PATTERNS.get(buzzer, 0x09)
        ]
        
        data = struct.pack('BBBBBB', *patterns)
        self._send_command(PNS_COMMANDS['control'], data)
        print("LEDs and buzzer updated successfully")
    
    def clear_all(self) -> None:
        """Turn off all LEDs and buzzer"""
        self._send_command(PNS_COMMANDS['clear'])
        print("All LEDs and buzzer turned off")
    
    def get_status(self) -> Dict[str, int]:
        """Get current status of LEDs and buzzer"""
        response = self._send_command(PNS_COMMANDS['status'])
        # Response format: [ACK][LED1][LED2][Amber][Green][Blue][Buzzer]
        return {
            'red1': response[1],
            'red2': response[2],
            'amber': response[3],
            'green': response[4],
            'blue': response[5],
            'buzzer': response[6]
        }

def main():
    parser = argparse.ArgumentParser(
        description="Control Patlite LA6-POE signal tower",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Command selection
    parser.add_argument("command", 
                       choices=['set', 'clear', 'status'],
                       help="Command to execute:\n"
                            "  set - Control LEDs and buzzer\n"
                            "  clear - Turn off all LEDs and buzzer\n"
                            "  status - Get current status")
    
    # LED and buzzer options
    parser.add_argument("--red1", choices=LED_PATTERNS.keys(),
                       help="Red1 LED pattern")
    parser.add_argument("--red2", choices=LED_PATTERNS.keys(),
                       help="Red2 LED pattern")
    parser.add_argument("--amber", choices=LED_PATTERNS.keys(),
                       help="Amber LED pattern")
    parser.add_argument("--green", choices=LED_PATTERNS.keys(),
                       help="Green LED pattern")
    parser.add_argument("--blue", choices=LED_PATTERNS.keys(),
                       help="Blue LED pattern")
    parser.add_argument("--buzzer", choices=BUZZER_PATTERNS.keys(),
                       help="Buzzer pattern")
    
    # Connection options
    parser.add_argument("--ip", default=DEFAULT_IP,
                       help=f"IP address (default: {DEFAULT_IP})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                       help=f"Port number (default: {DEFAULT_PORT})")
    
    args = parser.parse_args()
    patlite = PatliteLA6()
    
    try:
        patlite.connect(args.ip, args.port)
        
        if args.command == "set":
            patlite.set_leds_buzzer(
                red1=args.red1,
                red2=args.red2,
                amber=args.amber,
                green=args.green,
                blue=args.blue,
                buzzer=args.buzzer
            )
        elif args.command == "clear":
            patlite.clear_all()
        elif args.command == "status":
            status = patlite.get_status()
            print("Current status:")
            print(f"Red1 LED: {list(LED_PATTERNS.keys())[list(LED_PATTERNS.values()).index(status['red1'])]}")
            print(f"Red2 LED: {list(LED_PATTERNS.keys())[list(LED_PATTERNS.values()).index(status['red2'])}")
            print(f"Amber LED: {list(LED_PATTERNS.keys())[list(LED_PATTERNS.values()).index(status['amber'])]}")
            print(f"Green LED: {list(LED_PATTERNS.keys())[list(LED_PATTERNS.values()).index(status['green'])]}")
            print(f"Blue LED: {list(LED_PATTERNS.keys())[list(LED_PATTERNS.values()).index(status['blue'])]}")
            print(f"Buzzer: {list(BUZZER_PATTERNS.keys())[list(BUZZER_PATTERNS.values()).index(status['buzzer'])}")
    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        patlite.close()

if __name__ == '__main__':
    main()
