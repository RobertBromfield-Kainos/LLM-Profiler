import itertools

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from datetime import datetime, timedelta
import constants


def plot_cpu_usage_with_annotations(folder_path):
    # Define paths to the CSV files
    cpu_usage_file_path = os.path.join(folder_path, 'cpu_usage.csv')
    input_response_file_path = os.path.join(folder_path, 'input_response_file.csv')

    # Read the CSV files
    cpu_usage_data = pd.read_csv(cpu_usage_file_path)
    input_response_data = pd.read_csv(input_response_file_path, sep='\\|\\|\\|', engine='python', header=None,
                                      names=['input_timestamp', 'input', 'output_timestamp', 'output'])

    # Convert timestamps to datetime
    cpu_usage_data['Timestamp'] = pd.to_datetime(cpu_usage_data['Timestamp'])
    input_response_data['input_timestamp'] = pd.to_datetime(input_response_data['input_timestamp']) - timedelta(seconds=1)
    input_response_data['output_timestamp'] = pd.to_datetime(input_response_data['output_timestamp']) + timedelta(seconds=2)

    # Find the cutoff time: 2 seconds after the last output
    cutoff_time = input_response_data['output_timestamp'].max() + timedelta(seconds=2)

    # Filter the CPU usage data based on the cutoff time
    cpu_usage_data = cpu_usage_data[cpu_usage_data['Timestamp'] <= cutoff_time]

    # Plotting
    plt.figure(figsize=(15, 8))
    ax = plt.gca()  # Get current axes to set up the formatter and locator for the x-axis dates

    # Plot the entire CPU usage data first
    plt.plot(cpu_usage_data['Timestamp'], cpu_usage_data['CPU Usage (%)'], color='blue', alpha=0.5,
                label='CPU Usage')

    # Highlight sections and add annotations based on input_response data
    prompt_counter = 1
    colors = itertools.cycle(['green', 'red', 'blue', 'yellow', 'purple', 'orange', 'cyan'])
    for _, row in input_response_data.iterrows():
        color = next(colors)
        start, end = row['input_timestamp'], row['output_timestamp']
        ax.axvspan(start, end, color=color, alpha=0.3)
        prompt_counter += 1

    # Formatting the x-axis to make it more readable
    ax.xaxis.set_major_locator(mdates.MinuteLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter(constants.datetime_format))
    plt.gcf().autofmt_xdate()  # Rotation

    plt.title('CPU Usage Over Time with Input-Output Annotations')
    plt.xlabel('Time')
    plt.ylabel('CPU Usage (%)')
    plt.legend()
    plt.tight_layout()  # Adjust layout

    # Create the visualisations folder if it doesn't exist
    visualisations_folder = os.path.join(folder_path, 'visualisations')
    if not os.path.exists(visualisations_folder):
        os.makedirs(visualisations_folder)

    # Save the plot
    plot_file_path = os.path.join(visualisations_folder, 'cpu_usage_with_annotations.png')
    plt.savefig(plot_file_path)
    print(f"Plot saved to {plot_file_path}")

    plt.close()  # Close the plot to free resources


def plot_memory_usage_with_annotations(folder_path):
    # Define paths to the CSV files
    memory_usage_file_path = os.path.join(folder_path, 'memory_usage.csv')
    input_response_file_path = os.path.join(folder_path, 'input_response_file.csv')

    # Read the CSV files
    memory_usage_data = pd.read_csv(memory_usage_file_path)
    input_response_data = pd.read_csv(input_response_file_path, sep='\\|\\|\\|', engine='python', header=None,
                                      names=['input_timestamp', 'input', 'output_timestamp', 'output'])

    # Convert timestamps to datetime
    memory_usage_data['Timestamp'] = pd.to_datetime(memory_usage_data['Timestamp'])
    input_response_data['input_timestamp'] = pd.to_datetime(input_response_data['input_timestamp']) - timedelta(seconds=1)
    input_response_data['output_timestamp'] = pd.to_datetime(input_response_data['output_timestamp']) + timedelta(seconds=2)  # Extend end by 1 second

    # Find the cutoff time: 2 seconds after the last output
    cutoff_time = input_response_data['output_timestamp'].max() + timedelta(seconds=2)

    # Filter the memory usage data based on the cutoff time
    memory_usage_data = memory_usage_data[memory_usage_data['Timestamp'] <= cutoff_time]

    # Set up the subplot environment
    fig, axs = plt.subplots(2, 1, figsize=(15, 12), sharex=True)

    # Plot physical memory usage
    axs[0].plot(memory_usage_data['Timestamp'], memory_usage_data['Memory Usage (MB)'], color='blue', alpha=0.5,
                label='Memory Usage (MB)')

    # Plot virtual memory usage
    axs[1].plot(memory_usage_data['Timestamp'], memory_usage_data['Virtual Memory Usage (MB)'], color='purple', alpha=0.5,
                label='Virtual Memory Usage (MB)')

    # Highlight sections and add annotations based on input_response data for both subplots
    colors = itertools.cycle(['green', 'red', 'blue', 'yellow', 'purple', 'orange', 'cyan'])
    for _, row in input_response_data.iterrows():
        color = next(colors)
        start, end = row['input_timestamp'], row['output_timestamp']
        for ax in axs:
            ax.axvspan(start, end, color=color, alpha=0.3)

    # Formatting the x-axis to make it more readable
    axs[1].xaxis.set_major_locator(mdates.MinuteLocator())
    axs[1].xaxis.set_major_formatter(mdates.DateFormatter(constants.datetime_format))
    fig.autofmt_xdate()  # Rotation

    axs[0].set_title('Physical Memory Usage Over Time with Input-Output Annotations')
    axs[1].set_title('Virtual Memory Usage Over Time with Input-Output Annotations')
    plt.xlabel('Time')
    axs[0].set_ylabel('Memory Usage (MB)')
    axs[1].set_ylabel('Virtual Memory Usage (MB)')
    axs[0].legend()
    axs[1].legend()
    plt.tight_layout()  # Adjust layout

    # Create the visualisations folder if it doesn't exist
    visualisations_folder = os.path.join(folder_path, 'visualisations')
    if not os.path.exists(visualisations_folder):
        os.makedirs(visualisations_folder)

    # Save the plot
    plot_file_path = os.path.join(visualisations_folder, 'memory_usage_with_annotations.png')
    plt.savefig(plot_file_path)
    print(f"Plot saved to {plot_file_path}")

    plt.close(fig)  # Close the plot to free resources


def generate_markdown_table_with_memory_change(folder_path):
    # Define paths to the CSV files
    memory_usage_file_path = os.path.join(folder_path, 'memory_usage.csv')
    cpu_usage_file_path = os.path.join(folder_path, 'cpu_usage.csv')
    input_response_file_path = os.path.join(folder_path, 'input_response_file.csv')

    # Read the CSV files
    memory_usage_data = pd.read_csv(memory_usage_file_path)
    cpu_usage_data = pd.read_csv(cpu_usage_file_path)
    input_response_data = pd.read_csv(input_response_file_path, sep='\\|\\|\\|', engine='python', header=None,
                                      names=['input_timestamp', 'input', 'output_timestamp', 'output'])

    # Convert timestamps to datetime
    memory_usage_data['Timestamp'] = pd.to_datetime(memory_usage_data['Timestamp'])
    cpu_usage_data['Timestamp'] = pd.to_datetime(cpu_usage_data['Timestamp'])
    input_response_data['input_timestamp'] = pd.to_datetime(input_response_data['input_timestamp']) - timedelta(seconds=1)  # Extend start by 1 second
    input_response_data['output_timestamp'] = pd.to_datetime(input_response_data['output_timestamp']) + timedelta(seconds=2)  # Extend end by 1 second

    # Prepare the markdown table
    markdown_table = "| Input | Output | Response Time | Max CPU Usage (%) | Change in Memory Usage (MB) |\n"
    markdown_table += "| --- | --- | --- | --- | --- |\n"

    # Loop through each row in input_response_data to calculate values and add to the table
    for index, row in input_response_data.iterrows():
        input_text = row['input'].strip()
        output_text = row['output'].strip()
        response_time = (row['output_timestamp'] - row['input_timestamp']).total_seconds()

        # Find the maximum CPU usage during the interval of this input-output
        relevant_cpu_usage = cpu_usage_data[
            (cpu_usage_data['Timestamp'] >= row['input_timestamp']) &
            (cpu_usage_data['Timestamp'] <= row['output_timestamp'])
        ]
        max_cpu_usage = relevant_cpu_usage['CPU Usage (%)'].max() if not relevant_cpu_usage.empty else 0

        # Find the last memory usage before the input
        previous_memory_usage = memory_usage_data[
            memory_usage_data['Timestamp'] < row['input_timestamp']
        ]['Memory Usage (MB)'].last_valid_index()
        last_memory_usage_before_input = memory_usage_data.loc[previous_memory_usage, 'Memory Usage (MB)'] \
            if previous_memory_usage is not None else 0

        # Find the maximum memory usage during the interval
        relevant_memory_usage = memory_usage_data[
            (memory_usage_data['Timestamp'] >= row['input_timestamp']) &
            (memory_usage_data['Timestamp'] <= row['output_timestamp'])
        ]
        max_memory_usage = relevant_memory_usage['Memory Usage (MB)'].max() if not relevant_memory_usage.empty else 0

        # Calculate the change in memory usage
        change_in_memory_usage = max_memory_usage - last_memory_usage_before_input

        # Add the row to the markdown table
        markdown_table += f"| {input_text} | {output_text} | {response_time} seconds | {max_cpu_usage:.2f}% | {change_in_memory_usage:.2f} MB |\n"

    # Create the visualisations folder if it doesn't exist
    visualisations_folder = os.path.join(folder_path, 'visualisations')
    if not os.path.exists(visualisations_folder):
        os.makedirs(visualisations_folder)

    # Save the markdown table to a file
    markdown_table_file_path = os.path.join(visualisations_folder, 'input_output_memory_change_table.md')
    with open(markdown_table_file_path, 'w') as file:
        file.write(markdown_table)

def main(model, prompt_file):
    model_path = os.path.join('output',prompt_file, model)
    folder_path = os.path.join(model_path, sorted(os.listdir(model_path))[-1])
    plot_cpu_usage_with_annotations(folder_path)
    plot_memory_usage_with_annotations(folder_path)
    generate_markdown_table_with_memory_change(folder_path)


if __name__ == "__main__":
    model = 'llama2'
    model_path = os.path.join('output', model)
    folder_path = os.path.join(model_path, sorted(os.listdir(model_path))[-1])
    plot_cpu_usage_with_annotations(folder_path)
    plot_memory_usage_with_annotations(folder_path)
    generate_markdown_table_with_memory_change(folder_path)