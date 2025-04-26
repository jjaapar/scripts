import socket
import struct
import argparse
import sys
import time
from prettytable import PrettyTable  # For pretty table output

# --- Constants ---

PNS_PRODUCT_ID = b'AB'

# Command Identifiers
PNS_RUN_CONTROL_COMMAND = b'S'
PNS_CLEAR_COMMAND = b'C'
PNS_GET_DATA_COMMAND = b'G'

# Response Codes
PNS_ACK = 0x06
PNS_NAK = 0x15

# LED Patterns Mapping
LED_PATTERNS = {
    0: "Off",
    1: "On",
    2: "Blinking (Slow)",
    3: "Blinking (Medium)",
    4: "Blinking (High)",
    5: "Flashing (Single)",
    6: "Flashing (Double)",
    7: "Flashing (Triple)",
    9: "No Change"
}

# Retry Settings
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds


# --- Data Classes ---

class PnsRunControlData:
    """Operation control data for LEDs."""

    def __init__(self, red, amber, green, blue, white):
        self.patterns = (red, amber, green, blue, white)

    def to_bytes(self) -> bytes:
        """Pack LED patterns into bytes."""
        return struct.pack('BBBBB', *self.patterns)


class PnsStatusData:
    """Parsed status data from device response."""

    def __init__(self, data: bytes):
        self.led_patterns = data[:5]


# --- Socket Communication Handler ---

class PnsClient:
    """Handles communication with the PNS device."""

    def __init__(self, ip: str, port: int, verbose: bool = False):
        self.ip = ip
        self.port = port
        self.verbose = verbose
        self.sock = None

    def __enter__(self):
        self.sock = socket.create_connection((self.ip, self.port))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sock:
            self.sock.close()

    def send_command(self, payload: bytes) -> bytes:
        """Send command and receive response with retry logic."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if self.verbose:
                    print(f"[>] Sending: {payload.hex()}")

                self.sock.sendall(payload)
                recv_data = self.sock.recv(1024)

                if self.verbose:
                    print(f"[<] Received: {recv_data.hex()}")

                return recv_data
            except (socket.timeout, socket.error) as e:
                print(f"[!] Attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY)

    def run_control(self, control_data: PnsRunControlData):
        """Send operation control command."""
        payload = struct.pack('>2ssxH', PNS_PRODUCT_ID, PNS_RUN_CONTROL_COMMAND, 5)
        payload += control_data.to_bytes()
        response = self.send_command(payload)

        if response[0] == PNS_NAK:
            raise ValueError('Negative Acknowledge')

    def clear(self):
        """Send clear command."""
        payload = struct.pack('>2ssxH', PNS_PRODUCT_ID, PNS_CLEAR_COMMAND, 0)
        response = self.send_command(payload)

        if response[0] == PNS_NAK:
            raise ValueError('Negative Acknowledge')

    def get_status(self) -> PnsStatusData:
        """Request and return device status."""
        payload = struct.pack('>2ssxH', PNS_PRODUCT_ID, PNS_GET_DATA_COMMAND, 0)
        response = self.send_command(payload)

        if response[0] == PNS_NAK:
            raise ValueError('Negative Acknowledge')

        return PnsStatusData(response)


# --- Argument Parsing ---

def build_parser():
    parser = argparse.ArgumentParser(
        description="Control LR5-LAN LEDs over TCP/IP"
    )

    parser.add_argument(
        "command", choices=['S', 'C', 'G'],
        help="Command to send: 'S' = Set, 'C' = Clear, 'G' = Get Status"
    )

    parser.add_argument("--red", type=int, choices=range(0, 10))
    parser.add_argument("--amber", type=int, choices=range(0, 10))
    parser.add_argument("--green", type=int, choices=range(0, 10))
    parser.add_argument("--blue", type=int, choices=range(0, 10))
    parser.add_argument("--white", type=int, choices=range(0, 10))

    parser.add_argument("--ip", default="192.168.10.1", help="Device IP address (default: 192.168.10.1)")
    parser.add_argument("--port", type=int, default=10000, help="Device port (default: 10000)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output (show raw sent/received data)")

    return parser


# --- Main Function ---

def main():
    parser = build_parser()
    args = parser.parse_args()

    with PnsClient(args.ip, args.port, verbose=args.verbose) as client:
        if args.command == 'S':
            if None in (args.red, args.amber, args.green, args.blue, args.white):
                parser.error("The 'S' command requires --red, --amber, --green, --blue, and --white options.")

            control_data = PnsRunControlData(
                args.red, args.amber, args.green, args.blue, args.white
            )
            client.run_control(control_data)
            print("Run control command sent successfully.")

        elif args.command == 'C':
            client.clear()
            print("Clear command sent successfully.")

        elif args.command == 'G':
            status = client.get_status()
            table = PrettyTable(["LED Color", "Status"])
            table.align = "l"
            
            # Add LED Patterns
            for color, pattern in zip(["Red", "Amber", "Green", "Blue", "White"], status.led_patterns):
                pattern_label = LED_PATTERNS.get(pattern, f"Unknown ({pattern})")
                table.add_row([f"{color}", pattern_label])

            print("Status received:")
            print(table)

# --- Entry Point ---

if __name__ == '__main__':
    main()
