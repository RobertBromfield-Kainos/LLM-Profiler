import re
import os
import subprocess
from collections import defaultdict

import pandas as pd

datetime_format_with_microseconds = '%Y-%m-%d %H:%M:%S.%f'
datetime_format_no_microseconds = '%Y-%m-%d %H:%M:%S'


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


def generate_markdown_line(*items: str, is_header: bool = False) -> str:
    """
    Generate a Markdown table line from a list of items
    :param items: List of items to include in the line
    :param is_header: Whether the line is a header line
    :return: A Markdown table line
    """
    line = "|"
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
    grouped_models = defaultdict(list)
    for model in unsorted_models:
        # Use regular expression to match the parts of the model string
        match = re.match(r'([^:]+):(\d+)b(.*)', model)
        if match:
            prefix = match.group(1)
            suffix = match.group(3)
            grouping_key = (prefix, suffix)
            grouped_models[grouping_key].append(model)
        else:
            # Handle models without the specific ":<number>b" pattern by grouping them based on the entire model string
            grouped_models[model].append(model)

    # Sort models within each group
    for key in grouped_models:
        grouped_models[key] = sorted(grouped_models[key],
                                     key=lambda x: int(re.search(r':(\d+)b', x).group(1)) if re.search(r':(\d+)b',
                                                                                                       x) else 0)

    return grouped_models


def sort_models(unsorted_models: list) -> list:
    # Group models by name on left of ":"
    grouped_models = group_models(unsorted_models)

    # Sort within groups by model size, then by any suffix
    for name, model_group in grouped_models.items():
        grouped_models[name] = sorted(model_group, key=lambda x: (model_size(x), x))

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


if __name__ == "__main__":
    a = 0
    b = True

def make_folder(*args) -> str:
    """Create a folder with the given name if it doesn't exist. Return the folder path."""
    folder = os.path.join(*args)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder



