import os.path
import subprocess
import sys
import time
from collections import defaultdict

import give_prompts
import utils

import matplotlib.pyplot as plt
import numpy as np

import matplotlib.pyplot as plt
import numpy as np


def create_bar_chart(data, key, y_label, filename):
    # Extracting and organizing time_taken values by their list positions
    grouped_values = {}
    for model, details in data.items():
        for i, value in enumerate(details[key]):
            if i not in grouped_values:
                grouped_values[i] = []
            grouped_values[i].append(value)

    # Ensure all lists are of the same length
    max_length = max(len(v) for v in grouped_values.values())
    for v in grouped_values.values():
        while len(v) < max_length:
            v.append(0)  # or np.nan, depending on how you want to handle missing data

    # Convert grouped times to a format suitable for plotting
    positions = list(range(len(grouped_values)))
    values = list(grouped_values.values())

    # Plotting

    base_width_per_bar = 1  # the width of the bars
    gap_length = base_width_per_bar * 1.2  # Adjust the gap between groups
    n = len(values)  # Number of bars in each group

    total_bars = sum(len(values) for values in grouped_values.values())

    # Estimate the figure width based on the number of bars and a fixed height
    fig_height = 16  # Fixed height, adjust as needed
    fig_width = total_bars * base_width_per_bar * 2

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Adjusted indices calculation to introduce gaps between groups properly
    ind = np.arange(len(positions)) * (n * base_width_per_bar + gap_length)  # Group start positions

    for i, val in enumerate(values):
        # Plot each bar at its correct position
        ax.bar(ind + i * base_width_per_bar, val, base_width_per_bar, label=f'Prompt {i + 1}')

    ax.set_xlabel('Models')
    ax.set_ylabel(y_label)
    ax.set_title(y_label + ' by Group and Model')

    # Correctly setting x-ticks to be in the middle of each group
    ax.set_xticks(ind + (base_width_per_bar * n / 2) - (base_width_per_bar / 2))

    ax.set_xticklabels([model for model in data.keys()])

    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.subplots_adjust(right=0.75)  # Adjust this value as needed to fit the legend
    plt.rcParams.update({'font.size': 36})

    plt.savefig(filename)
    plt.close(fig)  # Close the plot to free resources


def get_list_of_models() -> list:
    # Run `ollama list` return contents of NAME column
    cmd = "ollama list"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    lines = stdout.decode().strip().split('\n')[1:]
    models = [line.split()[0] for line in lines]
    return models


def print_header(header_text: str) -> None:
    print('-' * len(header_text))
    print(header_text)
    print('-' * len(header_text))

def model_size(model: str) -> int:
    model_size = model.split(':')[-1]
    # if model_size matches the pattern of a number followed by a "b", return the number as an integer
    if model_size[:-1].isdigit() and model_size[-1] == 'b':
        return int(model_size[:-1])
    # otherwise, return 0
    return 0

def sort_models(unsorted_models: list) -> list:
    # Group models by name on left of ":"
    grouped_models = defaultdict(list)
    for model in unsorted_models:
        name = model.split(':')[0]
        grouped_models[name].append(model)

    # Sort by number on right of ":"
    for name, mode_group in grouped_models.items():
        grouped_models[name] = sorted(mode_group, key=lambda x: model_size(x))
        print(grouped_models[name])

    return [model for model_group in grouped_models.values() for model in model_group]


if __name__ == "__main__":
    prompt_file = sys.argv[1]
    models = get_list_of_models()
    # Remove 70b models from the list
    models = [model for model in models if model.split(':')[-1] != '70b']
    models = sort_models(models)
    print('Currently available models -- ' + ' '.join(models))

    data_dict = {}
    input_response_dict = defaultdict(list)

    all_models_folder = utils.make_folder("output", prompt_file.split(".")[0], "all_models")

    for model in models:
        # print_header(f"Running {model}")
        # give_prompts.run(prompt_file, model)
        # print_header(f"Finished running {model}")
        # input_response_file.csv

        # Get words per second from input_response_file.csv
        # 2024-02-23 16:47:10|||Could you write it in PHP|||2024-02-23 16:47:15|||Yes, here is an example of a "Hello World" program in PHP:<br>```<br><?php<br>echo "Hello, World!";<br>?><br>```
        output_folder = utils.get_last_output(prompt_file, model)
        input_response_file = os.path.join(output_folder, "input_response_file.csv")

        words_per_second = []
        responses = []
        time_taken = []
        words_list = []
        for line in open(input_response_file):
            if line.strip() == "":
                continue
            input_time, input_text, response_time, response_text = line.strip().split("|||")
            words = len(response_text.split())
            time_delta = utils.get_time_difference(input_time, response_time)
            time_taken.append(time_delta)
            responses.append(response_text)
            words_per_second.append(words / time_delta)
            words_list.append(words)
            input_response_dict[input_text].append(response_text)

        cpu_usage_file = os.path.join(output_folder, "cpu_usage.csv")
        cpu_usage = []

        data_dict[model] = {
            "input_text": input_text,
            "words_per_second": words_per_second,
            "responses": responses,
            "time_taken": time_taken,
            "amount_of_words": words_list
        }
        print_header(f"Finished processing {model}")
        time.sleep(5)

    input_response_table = open(os.path.join(all_models_folder, "input_response_table.md"), "w")

    markdown_headers = ["Prompt", *models]
    input_response_table.write(utils.generate_markdown_line(markdown_headers, is_header=True))

    for prompt, responses in input_response_dict.items():
        input_response_table.write(utils.generate_markdown_line([prompt, *responses]))

    input_response_table.close()

    create_bar_chart(data_dict, "words_per_second", "Words per Second", os.path.join(all_models_folder, "words_per_second.png"))
    create_bar_chart(data_dict, "time_taken", "Time Taken", os.path.join(all_models_folder, "time_taken.png"))
    create_bar_chart(data_dict, "amount_of_words", "Amount of Words", os.path.join(all_models_folder, "amount_of_words.png"))
