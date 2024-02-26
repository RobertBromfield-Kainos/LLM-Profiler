import datetime
import os

import pandas as pd

datetime_format_with_microseconds = '%Y-%m-%d %H:%M:%S.%f'
datetime_format_no_microseconds = '%Y-%m-%d %H:%M:%S'

def get_last_output(prompt_file: str, model: str) -> str:
    prompt_file = prompt_file.split(".")[0]
    model_path = os.path.join('output', prompt_file, model)
    return os.path.join(model_path, sorted(os.listdir(model_path))[-1])

def get_time_difference(start: str, end: str) -> float:
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    return (end - start).total_seconds()

def generate_markdown_line(items: list, is_header: bool = False) -> str:
    """
    Generate a markdown table line from a list of items
    :param items: List of items to include in the line
    :param is_header: Whether the line is a header line
    :return: A markdown table line
    """
    line = "|"
    for item in items:
        line += f" {item} |"
    line += "\n"
    if is_header:
        line += "|" + " --- |" * len(items) + "\n"
    return line

def make_folder(*args) -> str:
    """Create a folder with the given name if it doesn't exist. Return the folder path."""
    folder = os.path.join(*args)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder

if __name__ == "__main__":
    start = "2024-02-23 16:47:10.000000"
    end = "2024-02-23 16:47:15.000000"
    print(get_time_difference(start, end)) # 5.0