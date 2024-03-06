import itertools
from datetime import datetime
import os.path
import subprocess
import sys
import time
from collections import defaultdict

import give_prompts
import utils

import matplotlib.pyplot as plt
import numpy as np


def create_bar_chart(data, key, y_label, filename, add_pre_prompts=False):
    color_list = ['green', 'red', 'blue', 'yellow', 'purple', 'orange', 'cyan']

    # if add_pre_prompts is True, the first color will be grey
    if add_pre_prompts:
        color_list = ['grey'] + color_list

    colors = itertools.cycle(color_list)
    # Extracting and organizing values by their list positions
    grouped_values = {}
    for model, details in data.items():
        for i, value in enumerate(details[key]):
            if i not in grouped_values:
                grouped_values[i] = []
            grouped_values[i].append(value)

    # Ensure all lists are of the same length by padding with zeros
    max_length = max(len(v) for v in grouped_values.values())
    for v in grouped_values.values():
        v.extend([0] * (max_length - len(v)))  # Padding shorter lists

    # Data preparation for plotting
    n_groups = len(data)  # Number of groups/models
    n_bars = len(grouped_values)  # Number of bars per group
    values = list(grouped_values.values())  # List of lists of bar heights

    # Plot dimensions and settings
    fig_width = 10  # Adjust as needed
    fig_height = 6  # Adjust as needed
    bar_width = 0.8 / n_bars  # Width of each bar within a group

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    indices = np.arange(n_groups)  # Group positions

    # Plotting bars
    for i, val in enumerate(values):
        # Positioning each bar within its group
        bar_positions = indices + i * bar_width

        if not add_pre_prompts:
            label = f'Prompt {i + 1}'
        else:
            if i == 0:
                label = "Pre-Prompt"
            else:
                label = f'Prompt {i}'
        color = next(colors)
        ax.bar(bar_positions, val, bar_width, label=label, color=color, alpha=0.4, edgecolor='black')

    # Setting x-axis labels and chart title
    ax.set_xlabel('Models')
    ax.set_ylabel(y_label)
    ax.set_title(y_label + ' by Group and Model')
    ax.set_xticks(indices + bar_width * (n_bars - 1) / 2)  # Adjust ticks to group center
    ax.set_xticklabels(list(data.keys()))

    # Adding legend and adjusting layout
    ax.legend()
    plt.tight_layout()  # Adjust layout to fit everything

    # Saving the plot
    plt.savefig(filename)
    plt.close(fig)


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

    return [model for model_group in grouped_models.values() for model in model_group]


def get_max_of_column_grouped_by_prompt(column: str, csv_file: str, time_started: list, time_ended: list) -> list:
    cpu_in_groups = [[]]
    # Open line by line CSV file
    with open(csv_file) as f:
        # Skip the first line
        headers = [str.strip() for str in f.readline().split(',')]
        for line in f:
            # Timestamp,CPU Usage (%)
            values = [s.strip() for s in line.split(',')]
            line_dict = dict(zip(headers, values))

            if utils.check_if_time_is_before(line_dict['Timestamp'], time_started[0]):
                cpu_in_groups[0].append(float(line_dict[column]))
            else:
                i = 0
                while i < len(time_started):
                    if not utils.check_if_time_is_before(line_dict['Timestamp'],
                                                         time_started[i]) and utils.check_if_time_is_before(
                        line_dict['Timestamp'], time_ended[i]):
                        if len(cpu_in_groups) < i + 2:
                            cpu_in_groups.append([])
                        cpu_in_groups[i + 1].append(float(line_dict[column]))
                        break
                    i += 1

    return [max(cpu_group) for cpu_group in cpu_in_groups]


def run(prompt_file: str) -> None:
    models = utils.get_list_of_models()
    # Remove 70b models from the list
    models = [model for model in models if model.split(':')[-1] != '70b']
    models = sort_models(models)
    print('Currently available models -- ' + ' '.join(models))

    data_dict = {}
    input_response_dict = defaultdict(list)

    all_models_folder = utils.make_folder("output", prompt_file.split(".")[0], "all_models",
                                          datetime.now().strftime(utils.datetime_format_with_microseconds))

    for model in models:
        print_header(f"Running {model}")
        give_prompts.run(prompt_file, model)
        print_header(f"Finished running {model}")

        output_folder = utils.get_last_output_folder(prompt_file, model)
        input_response_file = os.path.join(output_folder, "input_response_file.csv")

        words_per_second = []
        responses = []
        time_taken = []
        words_list = []
        time_started = []
        time_ended = []

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
            time_started.append(input_time)
            time_ended.append(response_time)

        cpu_usage_file = os.path.join(output_folder, "cpu_usage.csv")
        cpu_usage = []

        data_dict[model] = {
            "input_text": input_text,
            "words_per_second": words_per_second,
            "responses": responses,
            "time_taken": time_taken,
            "amount_of_words": words_list,
            "time_started": time_started,
            "time_ended": time_ended
        }
        print_header(f"Finished processing {model}")
        time.sleep(5)

        cpu_usage_file = os.path.join(output_folder, "cpu_usage.csv")
        data_dict[model]["max_cpu_usage"] = get_max_of_column_grouped_by_prompt('CPU Usage (%)', cpu_usage_file,
                                                                                time_started, time_ended)

        memory_usage_file = os.path.join(output_folder, "memory_usage.csv")
        data_dict[model]["max_memory_usage"] = get_max_of_column_grouped_by_prompt('Memory Usage (MB)',
                                                                                   memory_usage_file, time_started,
                                                                                   time_ended)

    input_response_table = open(os.path.join(all_models_folder, "input_response_table.md"), "w")

    markdown_headers = ["Prompt", *models]
    input_response_table.write(utils.generate_markdown_line(markdown_headers, is_header=True))

    for prompt, responses in input_response_dict.items():
        input_response_table.write(utils.generate_markdown_line([prompt, *responses]))

    input_response_table.close()

    create_bar_chart(data_dict, "words_per_second", "Words per Second",
                     os.path.join(all_models_folder, "words_per_second.png"))
    create_bar_chart(data_dict, "time_taken", "Time Taken", os.path.join(all_models_folder, "time_taken.png"))
    create_bar_chart(data_dict, "amount_of_words", "Amount of Words",
                     os.path.join(all_models_folder, "amount_of_words.png"))
    create_bar_chart(data_dict, "max_cpu_usage", "Max CPU Usage", os.path.join(all_models_folder, "max_cpu_usage.png"),
                     add_pre_prompts=True)
    create_bar_chart(data_dict, "max_memory_usage", "Max Memory Usage",
                     os.path.join(all_models_folder, "max_memory_usage.png"), add_pre_prompts=True)


if __name__ == "__main__":
    prompt_file = sys.argv[1]
    run(prompt_file)
