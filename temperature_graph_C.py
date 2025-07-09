#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def parse_temperature_line(line):
    """Parse a single line of temperature data."""
    try:
        date_time_str, room_temp = line.strip().split(' - ')
        room, temp = room_temp.split(': ')
        temp_c = float(temp.split('°C')[0])
        date_time = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        return date_time, room, temp_c
    except Exception as e:
        return None


def read_temperature_data(filename):
    """Read and validate temperature data from file."""
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

    df = pd.DataFrame(data, columns=['datetime', 'room', 'temperature'])
    return df, invalid_lines, total_lines


def clean_temperature_data(df, min_temp, max_temp, z_threshold=3):
    """Remove temperature outliers using absolute limits and z-score method."""
    stats = {'original_count': len(df), 'removed_absolute': 0, 'removed_zscore': 0}
    
    # Remove temperatures outside absolute limits
    df = df[(df['temperature'] >= min_temp) & (df['temperature'] <= max_temp)]
    stats['removed_absolute'] = stats['original_count'] - len(df)
    
    # Apply z-score cleaning for each room
    for room in df['room'].unique():
        room_data = df[df['room'] == room]
        z_scores = np.abs((room_data['temperature'] - room_data['temperature'].mean()) / room_data['temperature'].std())
        df = df.drop(room_data[z_scores > z_threshold].index)
    
    stats['removed_zscore'] = stats['original_count'] - stats['removed_absolute'] - len(df)
    stats['final_count'] = len(df)
    
    return df, stats


def generate_summary(df):
    """Generate summary statistics for each room."""
    summary = ""
    for room in sorted(df['room'].unique()):
        room_data = df[df['room'] == room]
        summary += f"{room}:\n"
        summary += f"  Count: {len(room_data)}\n"
        summary += f"  Average: {room_data['temperature'].mean():.2f}°C\n"
        summary += f"  Std Dev: {room_data['temperature'].std():.2f}°C\n"
        summary += f"  Minimum: {room_data['temperature'].min():.2f}°C\n"
        summary += f"  Maximum: {room_data['temperature'].max():.2f}°C\n"
        summary += f"  Median: {room_data['temperature'].median():.2f}°C\n\n"
    return summary


def process_temperature_data(filename, days_to_show, min_temp, max_temp):
    """Process and visualize temperature data."""
    df, invalid_lines, total_lines = read_temperature_data(filename)
    
    # Filter for the last X days
    end_date = df['datetime'].max()
    start_date = end_date - timedelta(days=days_to_show)
    df_filtered = df[df['datetime'] >= start_date]

    # Clean the filtered data
    cleaned_df, cleaning_stats = clean_temperature_data(df_filtered, min_temp, max_temp)

    # Print statistics
    print("\nData Processing Statistics:")
    print(f"Total lines processed: {total_lines}")
    print(f"Valid lines: {len(df)}")
    print(f"Invalid lines: {len(invalid_lines)}")
    
    print("\nData Cleaning Statistics:")
    print(f"Date range: {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}")
    print(f"Original measurements in date range: {cleaning_stats['original_count']}")
    print(f"Removed (outside {min_temp}°C-{max_temp}°C): {cleaning_stats['removed_absolute']}")
    print(f"Removed (statistical outliers): {cleaning_stats['removed_zscore']}")
    print(f"Final measurements: {cleaning_stats['final_count']}")

    if invalid_lines:
        print("\nFirst 10 invalid lines:")
        for line in invalid_lines[:10]:
            print(line)
        if len(invalid_lines) > 10:
            print(f"...and {len(invalid_lines) - 10} more.")

    # Generate and print summary
    print("\nTemperature Summary:")
    print(generate_summary(cleaned_df))

    # Create the plot
    plt.figure(figsize=(15, 8))
    
    for room, color in [('Room 1.400', 'blue'), ('Room 1.401', 'red')]:
        room_data = cleaned_df[cleaned_df['room'] == room]
        plt.plot(room_data['datetime'], room_data['temperature'], label=room, color=color, linewidth=1)

        # Add min/max annotations
        for func, xytext in [(max, (10, 10)), (min, (10, -10))]:
            temp = func(room_data['temperature'])
            time = room_data.loc[room_data['temperature'].idxmax() if func == max else room_data['temperature'].idxmin(), 'datetime']
            plt.annotate(f'{room}\n{func.__name__}: {temp:.2f}°C',
                         xy=(time, temp), xytext=xytext,
                         textcoords='offset points', fontsize=8, color=color)

    # Add temperature limit lines
    plt.axhline(y=min_temp, color='orange', linestyle='--', alpha=0.5, label='Min Temp Limit')
    plt.axhline(y=max_temp, color='orange', linestyle='--', alpha=0.5, label='Max Temp Limit')

    # Customize the plot
    plt.title(f'Temperature Variation (Last {days_to_show} Days)\nCleaned Data: {min_temp}°C-{max_temp}°C', fontsize=14)
    plt.xlabel('Date/Time', fontsize=12)
    plt.ylabel('Temperature (°C)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10)
    plt.xticks(rotation=45)

    # Add statistics text
    stats_text = "\n".join([
        f"Statistics (Last {days_to_show} Days):",
        *(f"{room} - Avg: {data['temperature'].mean():.2f}°C, Std: {data['temperature'].std():.2f}°C, "
          f"Min: {data['temperature'].min():.2f}°C, Max: {data['temperature'].max():.2f}°C"
          for room, data in cleaned_df.groupby('room'))
    ])
    plt.figtext(0.02, 0.02, stats_text, fontsize=8, va='bottom')

    # Save and show the plot
    plt.tight_layout()
    plot_filename = f'temperature_plot_{days_to_show}days.png'
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved as: {plot_filename}")
    plt.show()


def main():
    parser = argparse.ArgumentParser(description='Process and visualize temperature data from a file.')
    parser.add_argument('filename', type=Path, help='Path to the temperature data file')
    parser.add_argument('-d', '--days', type=int, default=7, help='Number of days to show (default: 7)')
    parser.add_argument('--min-temp', type=float, default=20, help='Minimum valid temperature in Celsius (default: 20)')
    parser.add_argument('--max-temp', type=float, default=50, help='Maximum valid temperature in Celsius (default: 50)')

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

