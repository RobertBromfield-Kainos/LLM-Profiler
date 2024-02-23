import argparse
import csv
import os
import pty
import select
import sys
import threading
import time
import psutil
from datetime import datetime
import tty
import termios
import re

import constants

# Initialize a lock for file operations
lock = threading.Lock()


def get_usage_stats(command):
    """
    Finds the specified command process and returns its CPU, memory,
    and virtual memory usage.

    :param command: Command line string to search for in running processes.
    :return: A dictionary with CPU usage percentage, memory usage in bytes,
             and virtual memory used and total in bytes. Returns None if process is not found.
    """
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
        try:
            # Ensure cmdline is not None and contains elements
            cmdline = proc.info.get('cmdline', [])
            if cmdline and command in ' '.join(cmdline):
                cpu_percent = proc.cpu_percent(interval=0)
                memory_info = proc.memory_info()
                virtual_memory = psutil.virtual_memory()
                return {
                    'cpu_percent': cpu_percent,
                    'memory_used': memory_info.rss,  # Resident Set Size
                    'virtual_memory_used': virtual_memory.used,
                    'virtual_memory_total': virtual_memory.total
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None

no_of_tries_monitor_process = 0

# Function to monitor the process and log CPU and memory usage
def monitor_process(pid, cpu_file, memory_file):
    global no_of_tries_monitor_process
    try:
        p = psutil.Process(pid)
        while p.is_running():
            ollama_serve_stats = get_usage_stats('/Applications/Ollama.app/Contents/Resources/ollama serve')

            cpu_percent = p.cpu_percent(interval=0) + ollama_serve_stats['cpu_percent']
            memory_info = (p.memory_info().rss + ollama_serve_stats['memory_used']) / (
                        1024 * 1024)  # Convert bytes to MB
            virtual_memory = (p.memory_info().vms + ollama_serve_stats['virtual_memory_used']) / (
                        1024 * 1024)  # Convert bytes to MB

            current_time = datetime.now().strftime(constants.datetime_format)
            with open(cpu_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([current_time, cpu_percent])

            with open(memory_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([current_time, memory_info, virtual_memory])
    except Exception:
        if no_of_tries_monitor_process < 10:
            time.sleep(1)
            no_of_tries_monitor_process += 1
            monitor_process(pid, cpu_file, memory_file)



# Global buffer for input
input_buffer = ''


# Function to handle input from the user and send it to the subprocess
def handle_input(master_fd, output_folder):
    global input_buffer
    input_response_file = open(output_folder + 'input_response_file.csv', 'a')
    try:
        # Set stdin to non-blocking mode
        original_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

        while True:
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            if readable:
                input_char = sys.stdin.read(1)
                os.write(master_fd, input_char.encode())  # Send input to subprocess

                # Append to input buffer
                if input_char.isprintable():
                    input_buffer += input_char

                if input_char == '\r':
                    with lock:
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        input_response_file.write("\n" + str(now) + '|||' + input_buffer + '|||')
                        input_response_file.flush()
                        input_buffer = ''  # Clear the buffer after logging



    except Exception as e:
        print(f"Error handling input: {e}", flush=True)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_settings)


def extract_text_between_patterns(text, start_pattern=r'[\u2800-\u28FF]+', end_pattern=r'>>>'):
    # Compile patterns for efficiency if called multiple times
    start_regex = re.compile(start_pattern)
    end_regex = re.compile(end_pattern)

    # Find all start positions
    start_positions = [(match.start(), match.end()) for match in start_regex.finditer(text)]
    end_positions = [match.start() for match in end_regex.finditer(text)]

    extracted_texts = []
    last_end = 0
    for start, end_start in start_positions:
        if start < last_end:
            # Skip if this start is before the last end used
            continue
        # Find the first end position that is after the start position
        end = next((end for end in end_positions if end > start), None)
        if end:
            segment = text[end_start:end]
            # Remove any leading Braille characters from the segment
            segment_cleaned = re.sub(start_pattern, '', segment).strip()
            extracted_texts.append(segment_cleaned)
            last_end = end
        else:
            # If there's no end pattern after this start, break the loop
            break

    # Replace all new lines with URL encoded new lines
    extracted_texts = [text.replace('\r\n', '<br>') for text in extracted_texts]

    return extracted_texts


def clean_output_text(output):
    """
    Clean the output text by removing ANSI escape sequences and
    deleting lines starting with '>>> '.
    """
    # Compile regex patterns for matching ANSI escape codes and lines starting with ">>> "
    ansi_escape_pattern = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')

    # Remove ANSI escape codes
    output = ansi_escape_pattern.sub('', output)

    # Split output into lines, filter out unwanted lines, and rejoin back into a single string
    lines = output.split('\n')
    cleaned_output = '\n'.join(lines)

    return cleaned_output


def handle_output(master_fd, output_folder):
    full_output = ""
    i = 0

    b = False
    last_response_len = 0

    try:
        while True:
            readable, _, _ = select.select([master_fd], [], [], 0.1)
            if readable:
                output = os.read(master_fd, 1024).decode()
                if output != "" and "\n..." not in output:
                    print(output, end='')  # Print original output to console
                    sys.stdout.flush()

                    full_output += output

                    responses = extract_text_between_patterns(clean_output_text(full_output))

                    if len(responses) > 0:
                        if (responses[-1] != ""
                                and len(responses) != last_response_len):
                            response_file = open(output_folder + 'input_response_file.csv', 'a')
                            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            response_file.write(now + "|||" + responses[-1] + '\n')
                            response_file.flush()
                            last_response_len = len(responses)
                    i += 1

    except Exception as e:
        print(f"Error handling output: {e}", flush=True)


# Function to spawn the subprocess in a new pseudo-terminal
def spawn_process(command):
    master_fd, slave_fd = pty.openpty()
    pid = os.fork()
    if pid == 0:  # Child process
        os.setsid()
        os.dup2(slave_fd, sys.stdin.fileno())
        os.dup2(slave_fd, sys.stdout.fileno())
        os.dup2(slave_fd, sys.stderr.fileno())
        os.close(master_fd)
        os.execvp("sh", ["sh", "-c", command])
    else:  # Parent process
        os.close(slave_fd)
        return master_fd, pid


def make_folder(*args):
    """Create a folder with the given name if it doesn't exist. Return the folder path."""
    folder = os.path.join(*args)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


# Main function to set up the profiler
def main(args):
    command = args.command

    # Get last word of command
    model_name = command.split()[-1]

    if not args.prompt_file:
        output_folder = make_folder('output', model_name, datetime.now().strftime(constants.datetime_format) + '/')
    else:
        output_folder = make_folder('output', args.prompt_file, model_name,
                                    datetime.now().strftime(constants.datetime_format) + '/')

    master_fd, pid = spawn_process(command)

    # Prepare CSV files for logging
    cpu_file = output_folder + 'cpu_usage.csv'
    memory_file = output_folder + 'memory_usage.csv'
    with open(cpu_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'CPU Usage (%)'])
    with open(memory_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Memory Usage (MB)', 'Virtual Memory Usage (MB)'])

    # Monitor process in a separate thread
    monitor_thread = threading.Thread(target=monitor_process, args=(pid, cpu_file, memory_file))
    monitor_thread.start()

    # Handle input and output in separate threads
    input_thread = threading.Thread(target=handle_input, args=(master_fd, output_folder))
    output_thread = threading.Thread(target=handle_output, args=(master_fd, output_folder))

    input_thread.start()
    output_thread.start()

    input_thread.join()
    output_thread.join()

    # Wait for the monitor thread to finish
    monitor_thread.join()

    # Cleanup
    os.close(master_fd)


def run_ollama(model):
    command = 'ollama run ' + model
    main(command)




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Profile a command's CPU and memory usage and log input leading to output.")
    parser.add_argument('command', type=str, help='The command to profile')

    # Add optional argument for prompt file
    parser.add_argument('--prompt_file', type=str, help='The prompt file to use')

    args = parser.parse_args()

    main(args)
