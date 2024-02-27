import datetime
import os

import pandas as pd

datetime_format_with_microseconds = '%Y-%m-%d %H:%M:%S.%f'
datetime_format_no_microseconds = '%Y-%m-%d %H:%M:%S'


def get_last_output_folder(prompt_file: str, model: str) -> str:
    prompt_file = prompt_file.split(".")[0]
    model_path = os.path.join('output', prompt_file, model)
    return os.path.join(model_path, sorted(os.listdir(model_path))[-1])


def get_time_difference(start: str, end: str) -> float:
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    return (end - start).total_seconds()


def check_if_time_is_before(time: str, reference_time: str) -> bool:
    time = pd.to_datetime(time)
    reference_time = pd.to_datetime(reference_time)
    return time < reference_time


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
    # 3  --  2024-02-26 14:08:01  --  2024-02-26 14:08:03  --  2024-02-26 14:08:13.835848  --  True
    start = '2024-02-26 14:08:01'
    end = '2024-02-26 14:08:03'
    # not utils.check_if_time_is_before(timestamp, time_started[i]) and utils.check_if_time_is_before(time_ended[i], timestamp)
    print(not check_if_time_is_before('2024-02-26 14:08:13.835848', start))
    print(check_if_time_is_before('2024-02-26 14:08:13.835848', end))
