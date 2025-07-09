#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def parse_temperature_line(line):
    """
    Parse a single line of temperature data.
    
    Args:
    line (str): A line from the input file.

    Returns:
    tuple: (datetime, room, temp_c, temp_f) or None if parsing fails.
    """
    try:
        # Split the line into datetime and temperature parts
        date_time_str, room_temp = line.strip().split(' - ')
        room, temp = room_temp.split(': ')
        
        # Parse both Celsius and Fahrenheit
        celsius, fahrenheit = temp.split(' / ')
        temp_c = float(celsius.split('°C')[0])
        temp_f = float(fahrenheit.split('°F')[0])
        
        # Validate that C/F conversion is approximately correct
        if not (abs((temp_c * 9/5 + 32) - temp_f) < 0.1):
            return None  # Invalid temperature conversion
        
        date_time = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        return date_time, room, temp_c, temp_f
    except Exception as e:
        return None

def read_temperature_data(filename):
    """
    Read and validate temperature data from file.
    
    Args:
    filename (str): Path to the input file.

    Returns:
    tuple: (DataFrame, list of invalid lines, total line count)
    """
    data = []
    invalid_lines = []
    total_lines = 0

    with open(filename, 'r') as file:
        for line in file:
            total_lines += 1
            parsed_data = parse_temperature_line(line)
            if parsed_data:
                data.append(parsed_data)
            else:
                invalid_lines.append(line.strip())

    df = pd.DataFrame(data, columns=['datetime', 'room', 'temperature_c', 'temperature_f'])
    return df, invalid_lines, total_lines

def clean_temperature_data(df, min_temp_c, max_temp_c, z_threshold=3):
    """
    Remove temperature outliers using absolute limits and z-score method.
    
    Args:
    df (DataFrame): Input data.
    min_temp_c (float): Minimum valid temperature in Celsius.
    max_temp_c (float): Maximum valid temperature in Celsius.
    z_threshold (float): Z-score threshold for outlier detection.

    Returns:
    tuple: (Cleaned DataFrame, statistics dictionary)
    """
    stats = {'original_count': len(df), 'removed_absolute': 0, 'removed_zscore': 0}
    
    # Remove temperatures outside absolute limits (using Celsius)
    df = df[(df['temperature_c'] >= min_temp_c) & (df['temperature_c'] <= max_temp_c)]
    stats['removed_absolute'] = stats['original_count'] - len(df)
    
    # Apply z-score cleaning for each room
    for room in df['room'].unique():
        room_data = df[df['room'] == room]
        z_scores = np.abs((room_data['temperature_c'] - room_data['temperature_c'].mean()) / room_data['temperature_c'].std())
        df = df.drop(room_data[z_scores > z_threshold].index)
    
    stats['removed_zscore'] = stats['original_count'] - stats['removed_absolute'] - len(df)
    stats['final_count'] = len(df)
    
    return df, stats

def generate_summary(df):
    """
    Generate summary statistics for each room.
    
    Args:
    df (DataFrame): Cleaned temperature data.

    Returns:
    str: Formatted summary string.
    """
    summary = ""
    for room in sorted(df['room'].unique()):
        room_data = df[df['room'] == room]
        summary += f"{room}:\n"
        summary += f"  Count: {len(room_data)}\n"
        # Celsius statistics
        summary += f"  Celsius:\n"
        summary += f"    Average: {room_data['temperature_c'].mean():.2f}°C\n"
        summary += f"    Std Dev: {room_data['temperature_c'].std():.2f}°C\n"
        summary += f"    Minimum: {room_data['temperature_c'].min():.2f}°C\n"
        summary += f"    Maximum: {room_data['temperature_c'].max():.2f}°C\n"
        summary += f"    Median: {room_data['temperature_c'].median():.2f}°C\n"
        # Fahrenheit statistics
        summary += f"  Fahrenheit:\n"
        summary += f"    Average: {room_data['temperature_f'].mean():.2f}°F\n"
        summary += f"    Std Dev: {room_data['temperature_f'].std():.2f}°F\n"
        summary += f"    Minimum: {room_data['temperature_f'].min():.2f}°F\n"
        summary += f"    Maximum: {room_data['temperature_f'].max():.2f}°F\n"
        summary += f"    Median: {room_data['temperature_f'].median():.2f}°F\n"
        summary += "\n"
    return summary

def process_temperature_data(filename, days_to_show, min_temp_c, max_temp_c):
    """
    Process and visualize temperature data.
    
    Args:
    filename (str): Path to the input file.
    days_to_show (int): Number of days to include in the visualization.
    min_temp_c (float): Minimum valid temperature in Celsius.
    max_temp_c (float): Maximum valid temperature in Celsius.
    """
    df, invalid_lines, total_lines = read_temperature_data(filename)
    
    # Filter for the last X days
    end_date = df['datetime'].max()
    start_date = end_date - timedelta(days=days_to_show)
    df_filtered = df[df['datetime'] >= start_date]

    # Clean the filtered data
    cleaned_df, cleaning_stats = clean_temperature_data(df_filtered, min_temp_c, max_temp_c)

    # Convert temperature limits to Fahrenheit for display
    min_temp_f = min_temp_c * 9/5 + 32
    max_temp_f = max_temp_c * 9/5 + 32

    # Print statistics
    print("\nData Processing Statistics:")
    print(f"Total lines processed: {total_lines}")
    print(f"Valid lines: {len(df)}")
    print(f"Invalid lines: {len(invalid_lines)}")
    
    print("\nData Cleaning Statistics:")
    print(f"Date range: {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}")
    print(f"Original measurements in date range: {cleaning_stats['original_count']}")
    print(f"Removed (outside {min_temp_c}°C-{max_temp_c}°C): {cleaning_stats['removed_absolute']}")
    print(f"Removed (statistical outliers): {cleaning_stats['removed_zscore']}")
    print(f"Final measurements: {cleaning_stats['final_count']}")

    if invalid_lines:
        print("\nFirst 10 invalid lines:")
        for line in invalid_lines[:10]:
            print(line)
        if len(invalid_lines) > 10:
            print(f"...and {len(invalid_lines) - 10} more.")

    # Print summary
    print("\nTemperature Summary:")
    print(generate_summary(cleaned_df))

    # Create two subplots: one for Celsius, one for Fahrenheit
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), sharex=True)

    # Plot Celsius
    for room, color in [('Room 1.400', 'blue'), ('Room 1.401', 'red')]:
        room_data = cleaned_df[cleaned_df['room'] == room]
        ax1.plot(room_data['datetime'], room_data['temperature_c'], 
                label=room, color=color, linewidth=1)

        # Add min/max annotations (Celsius)
        for func, xytext in [(max, (10, 10)), (min, (10, -10))]:
            temp = func(room_data['temperature_c'])
            time = room_data.loc[room_data['temperature_c'].idxmax() if func == max else room_data['temperature_c'].idxmin(), 'datetime']
            ax1.annotate(f'{room}\n{func.__name__}: {temp:.2f}°C',
                        xy=(time, temp), xytext=xytext,
                        textcoords='offset points', fontsize=8, color=color)

    # Plot Fahrenheit
    for room, color in [('Room 1.400', 'blue'), ('Room 1.401', 'red')]:
        room_data = cleaned_df[cleaned_df['room'] == room]
        ax2.plot(room_data['datetime'], room_data['temperature_f'], 
                label=room, color=color, linewidth=1)

        # Add min/max annotations (Fahrenheit)
        for func, xytext in [(max, (10, 10)), (min, (10, -10))]:
            temp = func(room_data['temperature_f'])
            time = room_data.loc[room_data['temperature_f'].idxmax() if func == max else room_data['temperature_f'].idxmin(), 'datetime']
            ax2.annotate(f'{room}\n{func.__name__}: {temp:.2f}°F',
                        xy=(time, temp), xytext=xytext,
                        textcoords='offset points', fontsize=8, color=color)

    # Add temperature limit lines
    ax1.axhline(y=min_temp_c, color='orange', linestyle='--', alpha=0.5, label='Min Temp Limit')
    ax1.axhline(y=max_temp_c, color='orange', linestyle='--', alpha=0.5, label='Max Temp Limit')
    ax2.axhline(y=min_temp_f, color='orange', linestyle='--', alpha=0.5, label='Min Temp Limit')
    ax2.axhline(y=max_temp_f, color='orange', linestyle='--', alpha=0.5, label='Max Temp Limit')

    # Customize the plots
    ax1.set_title(f'Temperature Variation (Last {days_to_show} Days) - Celsius', fontsize=14)
    ax2.set_title('Temperature Variation - Fahrenheit', fontsize=14)
    ax2.set_xlabel('Date/Time', fontsize=12)
    ax1.set_ylabel('Temperature (°C)', fontsize=12)
    ax2.set_ylabel('Temperature (°F)', fontsize=12)
    
    for ax in [ax1, ax2]:
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend(fontsize=10)

    plt.xticks(rotation=45)

    # Add statistics text
    stats_text = generate_summary(cleaned_df)
    plt.figtext(0.02, 0.02, stats_text, fontsize=8, va='bottom')

    # Save and show the plot
    plt.tight_layout()
    plot_filename = f'temperature_plot_{days_to_show}days.png'
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved as: {plot_filename}")
    plt.show()

def main():
    """
    Main function to parse command-line arguments and run the data processing.
    """
    parser = argparse.ArgumentParser(description='Process and visualize temperature data from a file.')
    parser.add_argument('filename', type=Path, help='Path to the temperature data file')
    parser.add_argument('-d', '--days', type=int, default=7, help='Number of days to show (default: 7)')
    parser.add_argument('--min-temp', type=float, default=20, 
                        help='Minimum valid temperature in Celsius (default: 20)')
    parser.add_argument('--max-temp', type=float, default=50, 
                        help='Maximum valid temperature in Celsius (default: 50)')

    args = parser.parse_args()

    if args.days <= 0:
        print("Error: Number of days must be positive")
        sys.exit(1)

    if args.min_temp >= args.max_temp:
        print("Error: Minimum temperature must be less than maximum temperature")
        sys.exit(1)

    try:
        process_temperature_data(args.filename, args.days, args.min_temp, args.max_temp)
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

