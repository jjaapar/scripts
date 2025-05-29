#!/usr/bin/env python3
"""
Advanced Temperature Monitor
Monitors multiple devices concurrently with configurable thresholds.
Implements hysteresis to prevent false positives and graceful shutdown.
"""

import argparse
import concurrent.futures
import json
import logging
import os
import re
import serial
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Default configuration (overridden by config file)
DEFAULT_CONFIG = {
    "devices": ["txpaa1", "txpaa2", "txpaa3"],
    "max_temp": 180.0,
    "check_interval": 300,
    "hysteresis_threshold": 2,
    "retry_count": 3,
    "retry_delay": 0.5,
    "log_file": "/var/log/temperature_monitor.log",
    "temp_file": "/var/log/temperature_results.txt",
    "power_off_command": ["/usr/sbin/powercycle", "chroma", "--power-off"],
    "serial_settings": {
        "baudrate": 115200,
        "timeout": 1.0,
        "wakeup_delay": 0.5
    }
}

# Global state
config = None
over_temp_counts = {}
last_shutdown_attempt = None
logger = logging.getLogger()

def load_config(config_path: str) -> dict:
    """Load configuration from JSON file with fallback to defaults"""
    conf = DEFAULT_CONFIG.copy()
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                user_conf = json.load(f)
            conf.update(user_conf)
            logger.info(f"Loaded configuration from {config_path}")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Config error: {e}. Using defaults.")
    return conf

def setup_logging(log_file: str) -> None:
    """Configure logging system"""
    global logger
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger()
    # Add console logging for critical errors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.CRITICAL)
    logger.addHandler(console_handler)

def shutdown_handler(signum: int, frame) -> None:
    """Handle graceful shutdown signals"""
    logger.info("Shutdown signal received. Exiting cleanly.")
    sys.exit(0)

def get_temperature(device: str) -> Optional[float]:
    """Read temperature from serial device with error handling and retries"""
    serial_settings = config["serial_settings"]
    for attempt in range(config["retry_count"]):
        try:
            with serial.Serial(
                port=f"/dev/{device}",
                baudrate=serial_settings["baudrate"],
                timeout=serial_settings["timeout"]
            ) as conn:
                time.sleep(serial_settings["wakeup_delay"])
                conn.write(b'R\n')
                response = conn.readline().decode().strip()
                
                # Improved temperature parsing
                match = re.search(r'(\d{1,3}\.?\d*)', response)
                if match:
                    return float(match.group(1))
                logger.warning(f"Invalid response from {device}: '{response}'")

        except (serial.SerialException, UnicodeDecodeError) as e:
            logger.warning(f"Attempt {attempt+1} failed on {device}: {str(e)}")
        
        if attempt < config["retry_count"] - 1:
            time.sleep(config["retry_delay"])
    
    logger.error(f"All attempts failed for {device}")
    return None

def check_temperatures() -> bool:
    """Check all devices concurrently and process results"""
    global over_temp_counts, last_shutdown_attempt
    
    emergency = False
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    results = []

    # Concurrent temperature reading
    with concurrent.futures.ThreadPoolExecutor() as executor:
        device_temps = {
            executor.submit(get_temperature, device): device
            for device in config["devices"]
        }
        
        for future in concurrent.futures.as_completed(device_temps):
            device = device_temps[future]
            try:
                temp = future.result()
                results.append((device, temp))
            except Exception as e:
                logger.exception(f"Unexpected error with {device}: {e}")
                results.append((device, None))

    # Process results
    with open(config["temp_file"], "a") as temp_log:
        for device, temp in results:
            # Handle failed reads
            if temp is None:
                logger.warning(f"[{device}] Read failure")
                temp_log.write(f"{timestamp} - [{device}] READ_ERROR\n")
                continue
            
            # Log temperature
            log_entry = f"[{device}] {temp}°C"
            logger.info(log_entry)
            temp_log.write(f"{timestamp} - {log_entry}\n")
            
            # Check temperature threshold
            if temp > config["max_temp"]:
                over_temp_counts[device] = over_temp_counts.get(device, 0) + 1
                logger.warning(
                    f"[{device}] OVERHEAT: {temp}°C "
                    f"(Count: {over_temp_counts[device]}/{config['hysteresis_threshold']})"
                )
                
                if over_temp_counts[device] >= config["hysteresis_threshold"]:
                    emergency = True
            else:
                # Reset counter if below threshold
                over_temp_counts[device] = 0

    return emergency

def power_off_system() -> None:
    """Execute power-off command with safety checks"""
    global last_shutdown_attempt
    
    # Prevent rapid repeated shutdown attempts
    if last_shutdown_attempt and (datetime.now() - last_shutdown_attempt) < timedelta(minutes=5):
        logger.error("Shutdown aborted: Too soon after last attempt")
        return
    
    last_shutdown_attempt = datetime.now()
    logger.critical("Initiating emergency shutdown!")
    
    try:
        result = subprocess.run(
            config["power_off_command"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        logger.critical(f"Shutdown successful. Output: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        logger.critical(f"Shutdown failed ({e.returncode}): {e.stderr.strip()}")
    except Exception as e:
        logger.critical(f"Fatal shutdown error: {str(e)}")

def main_loop() -> None:
    """Main monitoring loop with watchdog timer"""
    logger.info("Temperature monitor started")
    logger.info(f"Monitoring devices: {', '.join(config['devices'])}")
    logger.info(f"Threshold: {config['max_temp']}°C | Check interval: {config['check_interval']}s")
    
    while True:
        start_time = time.monotonic()
        
        try:
            if check_temperatures():
                power_off_system()
        except Exception as e:
            logger.exception(f"Critical monitoring error: {e}")
        
        # Precise sleep accounting for processing time
        elapsed = time.monotonic() - start_time
        sleep_time = max(0, config["check_interval"] - elapsed)
        time.sleep(sleep_time)

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Temperature Monitoring System")
    parser.add_argument("--config", default="/etc/temp_monitor.conf.json", help="Configuration file path")
    parser.add_argument("--test", action="store_true", help="Test mode (no shutdown)")
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    if args.test:
        config["power_off_command"] = ["echo", "TEST MODE: Would execute:"]
        logger.info("Running in TEST MODE")

    # Initialize systems
    setup_logging(config["log_file"])
    over_temp_counts = {device: 0 for device in config["devices"]}
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, shutdown_handler)
    
    # Start main loop
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.critical(f"Fatal startup error: {str(e)}")
        sys.exit(1)
