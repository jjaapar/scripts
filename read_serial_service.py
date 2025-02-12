import serial
import time
import logging
import boto3
import daemon
import os
import sys
from datetime import datetime

# -------------------- CONFIGURATION --------------------

# Define serial communication parameters
SERIAL_PORT = '/dev/ttyACM0'  # Change this to match your device's port
BAUD_RATE = 9600  # Ensure this matches the Arduino's baud rate
CHECK_INTERVAL = 60  # Time in seconds between sensor queries

# Define log file location
LOG_FILE = "/tmp/emperature_monitor.log"  # File where logs will be stored
DEVICE_NAME = "MLX90614"  # Unique identifier for this sensor

# AWS CloudWatch configuration
AWS_REGION = "us-west-2"  # AWS region for CloudWatch logs
LOG_GROUP = "TemperatureSensorLogs"  # Log group name in CloudWatch
LOG_STREAM = DEVICE_NAME  # Unique log stream for this device
AWS_PROFILE = "default"  # Specify the AWS profile to use from ~/.aws/credentials

# -------------------- SETUP LOGGING --------------------

# Configure logging to write to a file
logging.basicConfig(
    filemode='a', filename=LOG_FILE, level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s', force=True
)

# Redirect stdout and stderr to the log file
#sys.stdout = open(LOG_FILE, 'a')
#sys.stderr = open(LOG_FILE, 'a')

# Set AWS credentials profile
os.environ['AWS_PROFILE'] = AWS_PROFILE

# Initialize AWS CloudWatch client
cloudwatch = boto3.client('logs', region_name=AWS_REGION)

def create_log_stream():
    """
    Ensures a CloudWatch log stream exists for this device.
    If it doesn’t exist, it creates both the log group and stream.
    """
    try:
        response = cloudwatch.describe_log_streams(logGroupName=LOG_GROUP, logStreamNamePrefix=LOG_STREAM)
        if not response['logStreams']:
            cloudwatch.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    except cloudwatch.exceptions.ResourceNotFoundException:
        cloudwatch.create_log_group(logGroupName=LOG_GROUP)
        cloudwatch.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    logging.info(f"Log stream ensured: {LOG_STREAM}")

def send_to_cloudwatch(timestamp, ambient_temp, object_temp):
    """
    Sends temperature readings to AWS CloudWatch Logs and logs locally.
    """
    try:
        log_message = f"{DEVICE_NAME},{ambient_temp}°C,{object_temp}°C"
        log_event = {
            'timestamp': int(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').timestamp() * 1000),
            'message': log_message
        }
        response = cloudwatch.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[log_event]
        )
        logger.info(f"Sent log to CloudWatch and local file: {log_message}")
    except Exception as e:
        logging.error(f"Failed to send data to CloudWatch: {e}")

def read_temperature():
    """
    Continuously reads temperature data from the Arduino sensor,
    logs it locally, and uploads it to AWS CloudWatch.
    """
    create_log_stream()  # Ensure AWS log stream exists
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            while True:
                ser.flushInput()  # Clear the input buffer to prevent stale data
                ser.write(b'T\n')  # Request temperature data from Arduino
                time.sleep(2)  # Allow time for response
                raw_response = ser.read(ser.in_waiting or 128).decode('utf-8').strip()  # Read and decode response
                
                if raw_response:
                    lines = raw_response.split("\n")  # Split response into lines
                    try:
                        # Extract temperature values from response
                        ambient_temp = float(lines[1].split('|')[0].split(':')[1].strip().replace("°C", ""))
                        object_temp = float(lines[2].split('|')[0].split(':')[1].strip().replace("°C", ""))
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp
                        
                        # Log data locally and to CloudWatch
                        send_to_cloudwatch(timestamp, ambient_temp, object_temp)
                    except (IndexError, ValueError):
                        logging.error(f"Error parsing response: {raw_response}")
                
                time.sleep(CHECK_INTERVAL)  # Wait before the next query
    except serial.SerialException as e:
        logging.error(f"Serial connection error: {e}")

def run_as_service():
    """
    Runs the script as a background service using daemon mode.
    """
    with daemon.DaemonContext(
        stdout=sys.stdout, 
        stderr=sys.stderr
    ):
        read_temperature()

if __name__ == "__main__":
    run_as_service()
