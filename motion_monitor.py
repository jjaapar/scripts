#!/usr/bin/env python3
import serial
import subprocess
import sys
import os
import time
import logging
from typing import Optional
from logging.handlers import RotatingFileHandler

# Configuration Constants
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
SCRIPT_PATH = '/home/jazzeryj/jazzeryj/new_la6.py'
BLUE_ON = '11'
GREEN_ON = '10'
MAX_RECONNECT_ATTEMPTS = 5
RETRY_DELAY = 10  # seconds

# Configure logging to both stderr and a rotating log file
LOG_FILENAME = '/home/jazzeryj/jazzeryj/controller_app.log'

file_handler = RotatingFileHandler(LOG_FILENAME, maxBytes=5*1024*1024, backupCount=3)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stderr),
        file_handler
    ]
)
def execute_controller(duration: str) -> None:
    """Execute the controller script with the specified duration"""
    if not os.path.exists(SCRIPT_PATH):
        logging.error(f"Controller script not found at {SCRIPT_PATH}")
        return
    
    try:
        result = subprocess.run([
            sys.executable,
            SCRIPT_PATH,
            'T', duration
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30  # Add timeout for subprocess
        )
        logging.debug(f"Script output: {result.stdout}")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Script execution failed (exit code {e.returncode}): {e.stderr}")
    except subprocess.TimeoutExpired:
        logging.error("Script execution timed out")
    except Exception as e:
        logging.exception(f"Unexpected error during script execution: {e}")

def process_serial_data(serial_connection: serial.Serial) -> Optional[str]:
    """Process data from serial connection with error handling"""
    try:
        line = serial_connection.readline().decode().strip()
        if line:
            logging.debug(f"Received serial data: {line}")
            return line
        return None
    except UnicodeDecodeError as e:
        logging.warning(f"Failed to decode serial data: {e}")
        return None
    except serial.SerialTimeoutException:
        logging.debug("Serial read timeout")
        return None

def establish_serial_connection() -> Optional[serial.Serial]:
    """Establish serial connection with retry mechanism"""
    reconnect_attempts = 0
    while reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
        try:
            ser = serial.Serial(
                port=SERIAL_PORT,
                baudrate=BAUD_RATE,
                timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            logging.info("Serial connection established successfully")
            return ser
        except serial.SerialException as e:
            reconnect_attempts += 1
            logging.error(f"Connection attempt {reconnect_attempts} failed: {e}")
            if reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
                logging.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
    
    logging.critical("Maximum reconnect attempts reached - exiting")
    return None

def main() -> None:
    """Main application loop"""
    try:
        while True:
            serial_conn = establish_serial_connection()
            if not serial_conn:
                break
                
            try:
                while True:
                    line = process_serial_data(serial_conn)
                    
                    if line == "Motion detected!":
                        logging.info("Motion detected - Activating Blue LED")
                        execute_controller(BLUE_ON)
                        
                    elif line == "Motion ended!":
                        logging.info("Motion ended - Activating Green LED")
                        execute_controller(GREEN_ON)
                        
                    elif line is not None:
                        logging.debug(f"Received unexpected serial message: {line}")
                        
            except serial.SerialException:
                logging.warning("Lost serial connection - attempting to reconnect")
            finally:
                serial_conn.close()
                
    except KeyboardInterrupt:
        logging.info("Program terminated by user")
    except Exception as e:
        logging.exception(f"Critical error in main loop: {e}")
    finally:
        logging.info("Application shutdown complete")

if __name__ == "__main__":
    main()
