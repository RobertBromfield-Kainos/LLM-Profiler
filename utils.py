import re
import os
import subprocess
import traceback
from collections import defaultdict

import pandas as pd

datetime_format_with_microseconds = '%Y-%m-%d %H:%M:%S.%f'
datetime_format_no_microseconds = '%Y-%m-%d %H:%M:%S'


def load_env_file(file_path):
    # Check if the function has been called before
    if getattr(load_env_file, 'has_run', False):
        return
    with open(file_path) as file:
        for line in file:
            if line.startswith('#') or not line.strip():
                # Ignore comments and empty lines
                continue
            # Assuming each line is in the form KEY=VALUE
            key, value = line.strip().split('=', 1)
            os.environ[key] = value  # Set as an environment variable
    # Set the function attribute to True to indicate it has run
    load_env_file.has_run = True


load_env_file('.env')
ollama_serve = os.getenv('OLLAMA_SERVE_PATH')
ollama = os.getenv('OLLAMA_PATH')
ollama_helper_gpu = os.getenv('OLLAMA_HELPER_GPU_PATH')
ollama_helper = os.getenv('OLLAMA_HELPER_PATH')
ollama_helper_renderer = os.getenv('OLLAMA_HELPER_RENDERER_PATH')


def get_models_that_have_been_run(prompt_file: str, api_flag: bool) -> list[str]:
    prompt_file = prompt_file.split(".")[0]
    output = "output_api" if api_flag else "output"
    prompt_output_folder = os.path.join(output, prompt_file)
    return [name for name in os.listdir(prompt_output_folder) if
            os.path.isdir(os.path.join(prompt_output_folder, name)) and name != 'all_models']


def get_last_output_folder(prompt_file: str, model: str, api_flag: bool) -> str:
    try:
        prompt_file = prompt_file.split(".")[0]
        output = "output_api" if api_flag else "output"
        model_path = os.path.join(output, prompt_file, model)
        print('model_path:', model_path)
        return os.path.join(model_path, sorted(os.listdir(model_path))[-1])
    except FileNotFoundError:
        return None


def get_time_difference(start: str, end: str) -> float:
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    return (end - start).total_seconds()


def check_if_time_is_before(time: str, reference_time: str) -> bool:
    time = pd.to_datetime(time)
    reference_time = pd.to_datetime(reference_time)
    return time < reference_time


def generate_markdown_line(*items: str | list[str], is_header: bool = False) -> str:
    """
    Generate a Markdown table line from a list of items
    :param items: List of items to include in the line
    :param is_header: Whether the line is a header line
    :return: A Markdown table line
    """
    line = "|"

    if len(items) == 1 and isinstance(items[0], list):
        items = items[0]

    for item in items:
        if isinstance(item, str):
            # Replace newlines with <br> for Markdown
            item = item.replace("\n", "<br>")
            item = item.replace("\r", "<br>")
        line += f" {item} |"
    line += "\n"
    if is_header:
        line += "|" + " --- |" * len(items) + "\n"
    return line


def model_size(model: str) -> tuple:
    # Split model string into components
    parts = model.split(':')[-1].split('-')
    size_part = parts[0]
    suffix = '-'.join(parts[1:]) if len(parts) > 1 else ''

    # Extract the numeric part before "b" for sorting
    if size_part[:-1].isdigit() and size_part[-1] == 'b':
        return (int(size_part[:-1]), suffix)
    # Handle non-standard sizes, placing them last
    return (float('inf'), suffix)


def group_models(unsorted_models: list) -> dict:
    pattern = r'([^:]+):(\d+(\.\d+)?)b(.*)'

    grouped_models = defaultdict(list)
    for model in unsorted_models:
        # Use regular expression to match the parts of the model string
        match = re.match(pattern, model)
        if match:
            prefix = match.group(1)
            suffix = match.group(4)

            grouping_key = (prefix, suffix)
            grouped_models[grouping_key].append(model)
        else:
            # Handle models without the specific ":<number>b" pattern by grouping them based on the entire model string
            grouped_models[model].append(model)

    # Sort models within each group
    for key in grouped_models:
        grouped_models[key] = sorted(grouped_models[key],
                                     key=lambda x: float(re.search(pattern, x).group(2)) if re.search(pattern,
                                                                                                      x) else 0)
    return grouped_models


def sort_models(unsorted_models: list) -> list:
    # Group models by name on left of ":"
    grouped_models = group_models(unsorted_models)
    # Flatten sorted groups into a single list
    sorted_models = [model for model_group in grouped_models.values() for model in model_group]

    return sorted_models


def get_list_of_models() -> list:
    # Run `ollama list` return contents of NAME column
    cmd = "ollama list"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    lines = stdout.decode().strip().split('\n')[1:]
    models = [line.split()[0] for line in lines]
    # Remove 70b models from the list
    models = [model for model in models if model.split(':')[-1] != '70b' and '_' not in model]
    models = sort_models(models)
    return models


def make_folder(*args) -> str:
    """Create a folder with the given name if it doesn't exist. Return the folder path."""
    folder = os.path.join(*args)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


def bold(text: str) -> str:
    return "\033[1m" + text + "\033[0m"


def red(text: str) -> str:
    return "\033[91m" + text + "\033[0m"


def green(text: str) -> str:
    return "\033[92m" + text + "\033[0m"


def print_header(header_text: str) -> None:
    print('-' * len(header_text))
    print(header_text)
    print('-' * len(header_text))


def print_exception(message: str, e: Exception):
    output = '-' * len(red(message))
    output += red(message)
    output += '-' * len(red(message))
    output += ''.join(traceback.format_exception(None, e, e.__traceback__))
    print(output)


def nanoseconds_to_human_readable(ns):
    # Constants for conversions
    nanoseconds_per_microsecond = 1000
    nanoseconds_per_millisecond = nanoseconds_per_microsecond * 1000
    nanoseconds_per_second = nanoseconds_per_millisecond * 1000
    nanoseconds_per_minute = nanoseconds_per_second * 60
    nanoseconds_per_hour = nanoseconds_per_minute * 60
    nanoseconds_per_day = nanoseconds_per_hour * 24

    # Calculations for each unit of time
    days = ns // nanoseconds_per_day
    ns %= nanoseconds_per_day
    hours = ns // nanoseconds_per_hour
    ns %= nanoseconds_per_hour
    minutes = ns // nanoseconds_per_minute
    ns %= nanoseconds_per_minute
    seconds = ns // nanoseconds_per_second
    ns %= nanoseconds_per_second
    # milliseconds = ns // nanoseconds_per_millisecond
    # ns %= nanoseconds_per_millisecond
    microseconds = ns // nanoseconds_per_microsecond
    ns %= nanoseconds_per_microsecond

    # Building the readable string conditionally
    parts = []
    if days > 0: parts.append(f"{days} days")
    if hours > 0: parts.append(f"{hours} hours")
    if minutes > 0: parts.append(f"{minutes} minutes")
    if seconds > 0: parts.append(f"{seconds} seconds")
    if microseconds > 0: parts.append(f"{microseconds} microseconds")

    # Joining the non-zero parts or returning '0 nanoseconds' if all are zero
    readable_time = ", ".join(parts) if parts else "0 nanoseconds"

    return readable_time


def close_ollama():
    try:
        path_prefix = "/Applications/Ollama.app"
        # Escape special characters for use in the grep command

        # List all processes and grep for those starting with the specified path
        # Using awk to print the first column (PID) only if the rest of the line matches the path
        cmd = f"ps -eo pid,command | grep -E '{path_prefix}' | awk '{{print $1}}'"

        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Extract PIDs
        pids = stdout.decode().strip().split('\n')

        for pid in pids:
            if pid.isdigit():
                print(f"Terminating process with PID: {pid}")
                subprocess.run(["kill", "-9", pid])
    except Exception as e:
        print(f"An error occurred: {e}")
