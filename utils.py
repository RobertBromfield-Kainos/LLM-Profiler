import datetime
import os
import subprocess

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

def get_list_of_models() -> list:
    # Run `ollama list` return contents of NAME column
    cmd = "ollama list"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    lines = stdout.decode().strip().split('\n')[1:]
    models = [line.split()[0] for line in lines]
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



