#!/usr/bin/env python3
import subprocess
import logging
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    filename='temperature_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_ondemand(port):
    try:
        # Run ondemand.py and capture output
        result = subprocess.check_output(['python3', 'ondemand.py', port], universal_newlines=True)
        return result.strip()
    except subprocess.CalledProcessError as e:
        error_msg = f"Error running ondemand.py: {str(e)}"
        print(error_msg)
        logging.error(error_msg)
        return None

def power_cycle():
    try:
        # Run power cycle command
        subprocess.run(['powercycle', 'txpaa', '--power-off'], check=True)
        message = "Power cycle executed successfully"
        print(message)
        logging.info(message)
    except subprocess.CalledProcessError as e:
        error_msg = f"Error during power cycle: {str(e)}"
        print(error_msg)
        logging.error(error_msg)

def main():
    port = 'ttyACM0'
    temp_threshold = 180

    # Get temperature reading
    temperature_output = run_ondemand(port)

    if temperature_output is None:
        return

    try:
        # Extract temperature value (assuming it's a number in the output)
        temperature = float(temperature_output)

        # Create timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Save to results file
        with open('temperature_results.txt', 'a') as f:
            f.write(f"{timestamp} - Temperature: {temperature}°C\n")

        # Print current temperature
        message = f"Current temperature: {temperature}°C"
        print(message)
        logging.info(message)

        # Check if temperature exceeds threshold
        if temperature > temp_threshold:
            warning_msg = f"Temperature ({temperature}°C) exceeds threshold ({temp_threshold}°C)!"
            print(warning_msg)
            logging.warning(warning_msg)
            power_cycle()

    except ValueError as e:
        error_msg = f"Error parsing temperature value: {str(e)}"
        print(error_msg)
        logging.error(error_msg)

if __name__ == "__main__":
    main()
