import socket
import struct
import argparse
import time

# Initialize the socket for communication with the device
_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Constants for PNS commands and responses
PNS_PRODUCT_ID = b'AB'
PNS_RUN_CONTROL_COMMAND = b'S'  # Operation control command
PNS_CLEAR_COMMAND = b'C'  # Clear command
PNS_GET_DATA_COMMAND = b'G'  # Get status command
PNS_ACK = 0x06  # Acknowledgement (normal response)
PNS_NAK = 0x15  # Negative Acknowledgement (abnormal response)

# Dictionary of possible LED patterns
LED_PATTERNS = {
    'off': 0x00,  # LED off
    'on': 0x01,  # LED on
    'blinking_slow': 0x02,  # LED blinking slow
    'blinking_medium': 0x03,  # LED blinking medium
    'blinking_high': 0x04,  # LED blinking fast
    'no_change': 0x09  # No change to current LED state
}

# Timeout constants (in seconds)
SOCKET_CONNECT_TIMEOUT = 5  # Timeout for connection attempts
SOCKET_RECEIVE_TIMEOUT = 10  # Timeout for receiving data

# Default IP address and port
DEFAULT_IP = '192.168.10.1'
DEFAULT_PORT = 10000

class PnsRunControlData:
    """
    This class handles the operation control data for LEDs.
    It stores LED patterns for red, amber, and green LEDs.
    """
    def __init__(self, led_patterns):
        # Initialize the patterns for red, amber, and green LEDs
        self._led_patterns = led_patterns

    def get_bytes(self) -> bytes:
        """
        Convert the LED patterns into bytes for communication with the device.
        
        Returns:
            bytes: The packed data of the LED patterns
        """
        return struct.pack(
            'BBBBB',  # Five LEDs (red, amber, green)
            *self._led_patterns  # LED patterns for red, amber, green
        )

class PnsStatusData:
    """
    This class processes the response data for the status command (LEDs and their states).
    """
    def __init__(self, data: bytes):
        # Extract only the first three LED patterns (Red, Amber, Green)
        self._ledPattern = data[0:3]

    @property
    def ledPattern(self) -> bytes:
        """Return the LED pattern (Red, Amber, Green)"""
        return self._ledPattern

def socket_open(ip: str, port: int):
    """
    Establish a socket connection to the device with a connection timeout.

    Parameters:
        ip (str): The IP address of the device.
        port (int): The port number to connect to.
    """
    _sock.settimeout(SOCKET_CONNECT_TIMEOUT)  # Set the connection timeout
    try:
        _sock.connect((ip, port))
        print(f"Connected to the device at {ip}:{port}.")
    except socket.timeout:
        raise ConnectionError(f"Connection to {ip}:{port} timed out.")
    except socket.error as e:
        raise ConnectionError(f"Error while connecting to the device: {e}")

def socket_close():
    """Close the socket connection."""
    _sock.close()

def send_command(send_data: bytes) -> bytes:
    """
    Send a command to the device and receive the response, with a timeout for receiving.

    Parameters:
        send_data (bytes): The data to be sent to the device.

    Returns:
        bytes: The response data from the device.
    """
    _sock.send(send_data)
    _sock.settimeout(SOCKET_RECEIVE_TIMEOUT)  # Set the receive timeout
    try:
        recv_data = _sock.recv(1024)
        return recv_data
    except socket.timeout:
        raise TimeoutError("The device did not respond in time.")
    except socket.error as e:
        raise ConnectionError(f"Error while receiving data: {e}")

def pns_run_control_command(run_control_data: PnsRunControlData):
    """
    Send the operation control command to set the LED patterns.

    Parameters:
        run_control_data (PnsRunControlData): The data object containing LED patterns.
    """
    send_data = struct.pack(
        '>2ssxH', 
        PNS_PRODUCT_ID, 
        PNS_RUN_CONTROL_COMMAND, 
        6
    ) + run_control_data.get_bytes()

    # Send the command and check the response
    try:
        recv_data = send_command(send_data)
        if recv_data[0] == PNS_NAK:
            raise ValueError('Negative Acknowledge (NAK) received')
    except (ConnectionError, TimeoutError) as e:
        print(f"Error: {e}")
        return

def pns_clear_command():
    """
    Send the clear command to turn off all LEDs and stop the buzzer.
    """
    send_data = struct.pack(
        '>2ssxH', 
        PNS_PRODUCT_ID, 
        PNS_CLEAR_COMMAND, 
        0
    )

    try:
        recv_data = send_command(send_data)
        if recv_data[0] == PNS_NAK:
            raise ValueError('Negative Acknowledge (NAK) received')
    except (ConnectionError, TimeoutError) as e:
        print(f"Error: {e}")
        return

def pns_get_data_command() -> PnsStatusData:
    """
    Send the status acquisition command to retrieve LED patterns and their statuses.

    Returns:
        PnsStatusData: The status data object containing LED patterns and their states.
    """
    send_data = struct.pack(
        '>2ssxH', 
        PNS_PRODUCT_ID, 
        PNS_GET_DATA_COMMAND, 
        0
    )

    try:
        recv_data = send_command(send_data)
        if recv_data[0] == PNS_NAK:
            raise ValueError('Negative Acknowledge (NAK) received')

        return PnsStatusData(recv_data)
    except (ConnectionError, TimeoutError) as e:
        print(f"Error: {e}")
        return None

def main():
    """
    Main function that processes command-line arguments, connects to the device,
    and sends the appropriate commands to control or query the device's LEDs.
    """
    parser = argparse.ArgumentParser(description="Control the LED lights on a device.")
    # Define command-line arguments
    parser.add_argument("command", choices=["S", "C", "G"], help="Command to send to the device (S: control, C: clear, G: get status)")
    parser.add_argument("--led-red", choices=LED_PATTERNS.keys(), help="LED Red pattern")
    parser.add_argument("--led-amber", choices=LED_PATTERNS.keys(), help="LED Amber pattern")
    parser.add_argument("--led-green", choices=LED_PATTERNS.keys(), help="LED Green pattern")
    parser.add_argument("--ip", default=DEFAULT_IP, help="IP address of the device (default: 192.168.10.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port of the device (default: 10000)")

    args = parser.parse_args()

    # Open socket connection to the device (use provided IP and port or defaults)
    socket_open(args.ip, args.port)

    try:
        if args.command == "S":
            # Operation control command: set the LED patterns
            led_patterns = [
                LED_PATTERNS.get(args.led_red, 0x00),  # Get the red LED pattern
                LED_PATTERNS.get(args.led_amber, 0x00),  # Get the amber LED pattern
                LED_PATTERNS.get(args.led_green, 0x00)  # Get the green LED pattern
            ]

            # Create the data object for the LED patterns and send control command
            run_control_data = PnsRunControlData(led_patterns)
            pns_run_control_command(run_control_data)
            print("Control command sent successfully.")

        elif args.command == "C":
            # Clear command: turn off all LEDs
            pns_clear_command()
            print("Clear command sent successfully.")

        elif args.command == "G":
            # Get status command: retrieve the current LED statuses
            status_data = pns_get_data_command()
            if status_data:
                print("Status retrieved successfully:")
                print(f"LED Red: {status_data.ledPattern[0]}")
                print(f"LED Amber: {status_data.ledPattern[1]}")
                print(f"LED Green: {status_data.ledPattern[2]}")

    except Exception as e:
        # Print error message if any exception occurs
        print(f"Error: {e}")

    finally:
        # Close the socket connection after the operation
        socket_close()

if __name__ == '__main__':
    main()
