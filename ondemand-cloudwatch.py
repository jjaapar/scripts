#!/usr/bin/python3

import serial
import time
import logging
from logging.handlers import RotatingFileHandler
import os
import boto3
import json
import sys
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# -------------------------------
# Configuration
# -------------------------------
AWS_ROLE = "arn:aws:iam::448355772178:role/plexus-venue-health-check-cloudwatch-role"
AWS_REGION = "us-west-2"
NAMESPACE = 'PlexusTemperatureMonitoring'


def setup_logging():
    """Set up separate loggers for different types of logs"""
    os.makedirs('logs', exist_ok=True)

    loggers = {}
    for name in ['error', 'metric', 'aws']:
        logger = logging.getLogger(f'{name}_logger')
        logger.setLevel(logging.INFO if name != 'error' else logging.ERROR)
        handler = RotatingFileHandler(f'logs/{name}.log', maxBytes=1024 * 1024, backupCount=5)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        loggers[name] = logger

    return loggers['error'], loggers['metric'], loggers['aws']


def run_command(cmd):
    """Execute a shell command and return the result"""
    return subprocess.run(cmd, text=True, capture_output=True)


class TemperatureMonitor:
    def __init__(self):
        self.error_logger, self.metric_logger, self.aws_logger = setup_logging()
        self.devices = {
            '1.400': 'Room 1.400',
            '1.401': 'Room 1.401'
        }
        self.cloudwatch = None
        self.setup_cloudwatch()

    def assume_role(self):
        """Assume the AWS role using STS assume-role"""
        self.aws_logger.info("Attempting to assume AWS role")
        print("Attempting to assume AWS role")

        # Generate timestamp for unique session name
        timestamp = int(datetime.now().timestamp())
        session_name = f'TempMonitor-{timestamp}'

        # Assume role using AWS STS
        cmd = [
            'aws', 'sts', 'assume-role',
            '--role-arn', AWS_ROLE,
            '--role-session-name', session_name,
            '--query', 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]',
            '--output', 'text',
            '--region', AWS_REGION,
        ]

        result = run_command(cmd)
        if result.returncode == 0:
            credentials = result.stdout.strip().split()
            os.environ['AWS_ACCESS_KEY_ID'] = credentials[0]
            os.environ['AWS_SECRET_ACCESS_KEY'] = credentials[1]
            os.environ['AWS_SESSION_TOKEN'] = credentials[2]
            return True
        return False

    def setup_cloudwatch(self):
        """Set up CloudWatch client"""
        try:
            if self.assume_role():
                self.cloudwatch = boto3.client('cloudwatch', region_name=AWS_REGION)
                self.aws_logger.info("CloudWatch client initialized successfully")
                print("CloudWatch client initialized successfully")
                return True
            return False
        except Exception as e:
            self.error_logger.error(f"CloudWatch setup failed: {e}")
            print(f"CloudWatch setup failed: {e}")
            return False

    def verify_cloudwatch_setup(self):
        """Verify CloudWatch setup and namespace"""
        try:
            if not self.cloudwatch:
                self.error_logger.error("CloudWatch client not initialized")
                print("CloudWatch client not initialized")
                return False

            response = self.cloudwatch.list_metrics(Namespace=NAMESPACE)
            self.aws_logger.info(f"Successfully connected to CloudWatch namespace: {NAMESPACE}")
            print(f"Successfully connected to CloudWatch namespace: {NAMESPACE}")

            metrics_count = len(response.get('Metrics', []))
            self.aws_logger.info(f"Found {metrics_count} metrics in namespace {NAMESPACE}")
            print(f"Found {metrics_count} metrics in namespace {NAMESPACE}")

            return True
        except Exception as e:
            self.error_logger.error(f"CloudWatch verification failed: {e}")
            print(f"CloudWatch verification failed: {e}")
            return False

    def read_temperature(self, device_name: str, room_name: str) -> Optional[float]:
        """Read temperature from a serial device"""
        device_path = f"/dev/{device_name}"

        if not os.path.exists(device_path):
            self.error_logger.error(f"Device {device_path} does not exist")
            return None

        for attempt in range(3):
            try:
                with serial.Serial(device_path, 115200, timeout=1) as ser:
                    time.sleep(2)
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()
                    ser.write("R\n".encode())
                    response = ser.readline().decode().strip()

                    if not response:
                        raise ValueError("Empty response received from device")

                    temp_c = float(response)

                    # Log temperatures outside valid range (10-45°C) but don't return them
                    if temp_c < 10 or temp_c > 45:
                        self.error_logger.error(
                            f"Temperature reading outside valid range for {room_name}: {temp_c}°C"
                        )
                        return None

                    temp_f = temp_c * 9 / 5 + 32
                    self.metric_logger.info(f"{room_name}: {temp_c:.2f}°C / {temp_f:.2f}°F")
                    print(f"{room_name}: {temp_c:.2f}°C / {temp_f:.2f}°F")
                    return temp_c

            except serial.SerialException as e:
                self.error_logger.error(f"Serial communication error on attempt {attempt + 1}/3: {e}")
                if attempt < 2:
                    time.sleep(1)

            except ValueError as e:
                self.error_logger.error(f"Invalid temperature data from {room_name}: {e}")
                return None

        print(f"Error: Failed to read from {room_name} after 3 attempts")
        return None

    def send_to_cloudwatch(self, room_name: str, temperature: float):
        """Send temperature data to CloudWatch"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=NAMESPACE,
                MetricData=[{
                    'MetricName': 'Temperature',
                    'Value': temperature,
                    'Unit': 'None',
                    'Timestamp': datetime.utcnow(),
                    'Dimensions': [
                        {'Name': 'Room', 'Value': room_name},
                        {'Name': 'Unit', 'Value': 'Celsius'},
                        {'Name': 'Environment', 'Value': 'Production'},
                        {'Name': 'System', 'Value': 'PlexusTemperature'}
                    ]
                }]
            )
            self.aws_logger.info(f"Sent temperature data to CloudWatch for {room_name}")
            print(f"Sent temperature data to CloudWatch for {room_name}")
        except Exception as e:
            self.error_logger.error(f"Failed to send data to CloudWatch: {e}")
            print(f"Failed to send data to CloudWatch: {e}")

    def get_cloudwatch_data(self, days: int = 10) -> Dict:
        """Retrieve temperature data from CloudWatch"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=[{
                    'Id': 'temp_data',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': NAMESPACE,
                            'MetricName': 'Temperature',
                            'Dimensions': [
                                {'Name': 'Unit', 'Value': 'Celsius'}
                            ]
                        },
                        'Period': 3600,  # 1 hour intervals
                        'Stat': 'Average'
                    },
                    'ReturnData': True
                }],
                StartTime=start_time,
                EndTime=end_time
            )

            self.aws_logger.info(f"Retrieved CloudWatch data for the past {days} days")
            return response
        except Exception as e:
            self.error_logger.error(f"Failed to retrieve CloudWatch data: {e}")
            print(f"Failed to retrieve CloudWatch data: {e}")
            return {}

    def run(self):
        """Main execution method"""
        print("\n=== Starting Temperature Monitoring ===")
        self.aws_logger.info("Starting temperature monitoring process")

        if not self.cloudwatch:
            self.error_logger.error("CloudWatch client not initialized")
            print("Error: CloudWatch client not initialized")
            return

        for device, room in self.devices.items():
            print(f"Checking device {device} for {room}...")
            device_path = f"/dev/{device}"
            if os.path.exists(device_path):
                temperature = self.read_temperature(device, room)
                # Only send to CloudWatch if temperature is valid (not None)
                if temperature is not None:
                    self.send_to_cloudwatch(room, temperature)
            else:
                self.error_logger.error(f"Device {device_path} for {room} does not exist.")
                print(f"Error: Device {device_path} for {room} does not exist.")

        print("\n=== Temperature Monitoring Complete ===")
        self.aws_logger.info("Temperature monitoring process complete")


def cleanup_old_logs(directory='logs', days=30):
    """Remove logs older than specified days"""
    cutoff = datetime.now() - timedelta(days=days)

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            if datetime.fromtimestamp(os.path.getmtime(filepath)) < cutoff:
                os.remove(filepath)
                print(f"Removed old log file: {filepath}")


def main():
    print("\n=== Starting Temperature Monitoring Setup ===")

    monitor = TemperatureMonitor()

    # Verify AWS setup
    print("\n=== Verifying AWS Setup ===")
    if monitor.cloudwatch:
        print("✅ AWS role assumption successful")
    else:
        print("❌ AWS role assumption failed")
        return

    # Verify CloudWatch setup
    print("\n=== Verifying CloudWatch Setup ===")
    if monitor.verify_cloudwatch_setup():
        print("✅ CloudWatch setup successful")
    else:
        print("❌ CloudWatch setup failed")
        return

    # Run temperature monitoring
    monitor.run()

    # Optional: Retrieve and display historical data
    print("\n=== Retrieving Historical Data ===")
    historical_data = monitor.get_cloudwatch_data()
    if historical_data:
        print("Historical Temperature Data:")
        print(json.dumps(historical_data, indent=2))
    else:
        print("No historical data found or error retrieving data")

    # Cleanup old logs
    cleanup_old_logs()


if __name__ == "__main__":
    main()
