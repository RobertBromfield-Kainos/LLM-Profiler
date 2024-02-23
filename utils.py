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

if __name__ == "__main__":
    start = "2024-02-23 16:47:10.000000"
    end = "2024-02-23 16:47:15.000000"
    print(get_time_difference(start, end)) # 5.0