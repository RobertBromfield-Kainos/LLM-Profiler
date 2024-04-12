import argparse
import concurrent.futures
import csv
import itertools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os.path
from collections import defaultdict
import give_prompts
import profiler_api
import utils
import numpy as np
import pandas as pd
import os
import matplotlib

# Set the backend to 'Agg' to avoid GUI-related operations. Needs to be done before importing pyplot.
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sort_data_dictionary(data: dict) -> dict:
    unsorted_keys = list(data.keys())
    sorted_keys = utils.sort_models(unsorted_keys)
    return {key: data[key] for key in sorted_keys}


def create_bar_chart(data, key, y_label, filename, add_pre_prompts=False):
    color_list = ['green', 'red', 'blue', 'yellow', 'purple', 'orange', 'cyan']

    # if add_pre_prompts is True, the first color will be grey
    if add_pre_prompts:
        color_list = ['grey'] + color_list

    colors = itertools.cycle(color_list)
    # Extracting and organizing values by their list positions
    grouped_values = {}

    data = sort_data_dictionary(data)

    for model, details in data.items():

        if details[key] is None:
            continue

        for i, value in enumerate(details[key]):
            if i not in grouped_values:
                grouped_values[i] = []
            # # Only append if the current list has less than 5 items
            # if len(grouped_values[i]) < 5:
            grouped_values[i].append(value)

    # Remove empty lists

    if len(grouped_values.values()) == 0:
        return

    # Ensure all lists are of the same length by padding with zeros
    max_length = max(len(v) for v in grouped_values.values())
    for v in grouped_values.values():
        v.extend([0] * (max_length - len(v)))  # Padding shorter lists

    # Data preparation for plotting
    n_groups = len(data)  # Number of groups/models
    n_bars = len(grouped_values)  # Number of bars per group
    values = list(grouped_values.values())  # List of lists of bar heights

    # Plot dimensions and settings
    fig_width = 3 * len(values)  # Adjust as needed
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

        print('', len(bar_positions), len(val))  # Add similar checks for other arrays if applicable

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


def get_max_of_column_grouped_by_prompt(column: str, csv_file: str, time_started: list, time_ended: list) -> list:
    # Convert time strings to datetime objects for comparison
    time_ranges = [(datetime.strptime(start, utils.datetime_format_with_microseconds),
                    datetime.strptime(end, utils.datetime_format_with_microseconds)) for
                   start, end in zip(time_started, time_ended)]

    # Initialize a dictionary to hold the max values for each time range, keys are index of the time range
    max_values = {i: 0 for i in range(len(time_ranges))}

    try:
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = datetime.strptime(row['Timestamp'], utils.datetime_format_with_microseconds)
                # Find the time range the timestamp falls into
                for i, (start, end) in enumerate(time_ranges):
                    if start <= timestamp <= end:
                        value = float(row[column])
                        if value > max_values[i]:
                            max_values[i] = value
                        break  # Move to the next row once the correct time range is found

        # Extract the maximum values in the order of time ranges
        return [max_values[i] for i in range(len(time_ranges))]

    except Exception as e:
        print(f"Error: {e}")
        print('column:', column)
        print('csv_file:', csv_file)
        print('time_started:', time_started)
        print('time_ended:', time_ended)
        return []


def extract_columns_values(output_folder: str, filename: str, columns: list[str]) -> dict:
    """
    Extracts all values from specified columns in a CSV file and returns them as a dictionary
    with each key being the column name and the value being a list of the column's values.
    Only the first 15 rows are returned if the CSV file has more than 15 rows.

    :param output_folder: The folder where the CSV file is located.
    :param filename: The name of the CSV file.
    :param columns: A list of column names to extract values from.
    :return: A dictionary with column names as keys and lists of their values.
    """
    file_path = os.path.join(output_folder, filename)
    df = pd.read_csv(file_path, usecols=columns)

    # Ensure only the first 15 rows are considered if there are more than 15
    if len(df) > 15:
        df = df.head(15)

    columns_data = {col: df[col].tolist() for col in df.columns}

    return columns_data


def process_input_response_file(input_response_file: str, output_folder: str, api_flag: bool):
    # Initialize data structures for results
    words_per_second_list, response_list, time_taken_list, amount_of_words_list, time_started_list, time_ended_list = [], [], [], [], [], []

    i = 0
    with open(input_response_file) as file:
        for line in file:
            if line.strip() == "":
                continue
            try:
                input_time, input_text, response_time, response_text = line.strip().split("|||")
                words = len(response_text.split())
                time_delta = utils.get_time_difference(input_time, response_time)
                words_per_second_list.append(words / time_delta)
                response_list.append(response_text)
                time_taken_list.append(time_delta)
                amount_of_words_list.append(words)
                time_started_list.append(input_time)
                time_ended_list.append(response_time)
                # Add other necessary processing here
            except Exception as e:
                utils.print_exception(f'Too few values on line {i + 1} of input_response_file.csv', e)
            if i > 15:  # Limit to first 16 lines for demo
                break
            i += 1

    output_dictionary = {
        "words_per_second": words_per_second_list,
        "responses": response_list,
        "time_taken": time_taken_list,
        "amount_of_words": amount_of_words_list,
        "time_started": time_started_list,
        "time_ended": time_ended_list,
    }

    cpu_usage_file = os.path.join(output_folder, "cpu_usage.csv")
    output_dictionary["max_cpu_usage"] = get_max_of_column_grouped_by_prompt('CPU Usage (%)', cpu_usage_file,
                                                                             time_started_list, time_ended_list)

    memory_usage_file = os.path.join(output_folder, "memory_usage.csv")
    output_dictionary["max_memory_usage"] = get_max_of_column_grouped_by_prompt('Memory Usage (MB)',
                                                                                memory_usage_file, time_started_list,
                                                                                time_ended_list)

    if api_flag:
        api_response_values = extract_columns_values(output_folder, 'api_response_data.csv',
                                                     ['total_duration', 'eval_count', 'eval_duration',
                                                      'prompt_eval_duration'])
        output_dictionary.update(api_response_values)

        output_dictionary['tokens_per_second'] = [count / duration if duration != 0 else 0 for count, duration in
                                                  zip(api_response_values['eval_count'],
                                                      api_response_values['eval_duration'])]

    # Replace this return statement with your actual data structure
    return output_dictionary


def process_model(model: str, prompt_file: str, do_not_run: bool, api_flag: bool, code_only: bool):
    # Pre-model processing, like printing headers
    utils.print_header(f"Running {model}")

    # Post-model processing setup (unchanged)
    try:
        output_folder = utils.get_last_output_folder(prompt_file, model, api_flag)
        input_response_file = os.path.join(output_folder, "input_response_file.csv")
    except Exception as e:
        print(f"Error: {e}")
        print('output_folder:', output_folder)
        print('prompt_file:', prompt_file, 'model:', model, 'api_flag:', api_flag)

    # Parallel processing of input_response_file
    with ThreadPoolExecutor(max_workers=5) as executor:
        future = executor.submit(process_input_response_file, input_response_file, output_folder, api_flag)
        return future.result()


def run(prompt_file: str, api_flag: bool, code_only: bool, optional_models: str, do_not_run: bool,
        temperature: str) -> None:
    models = utils.get_list_of_models()

    if optional_models is not None:
        models = [m for m in models if m in optional_models.split(',')]

    print('Currently available models -- ' + ' '.join(models))

    data_dict = {}
    input_response_dict = defaultdict(list)

    output = "output_api" if api_flag else "output"

    all_models_folder = utils.make_folder(output, prompt_file.split(".")[0], "all_models",
                                          datetime.now().strftime(utils.datetime_format_with_microseconds))

    for model in models:
        utils.print_header(f"Running {model}")
        if not do_not_run:
            if not api_flag:
                give_prompts.run(prompt_file, model)
            else:
                profiler_api.run(model, prompt_file, code_only, temperature)
            utils.print_header(f"Finished running {model}")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Create a future for each call to process_model
        future_to_model = {executor.submit(process_model, model, prompt_file, do_not_run, api_flag, code_only): model
                           for model in
                           models}

        # As each future completes, its result is added to data_dict
        for future in concurrent.futures.as_completed(future_to_model):
            model = future_to_model[future]
            try:
                result = future.result()
                data_dict[model] = result  # Store the result using model as the key
            except Exception as exc:
                print(f'{model} generated an exception: {exc}')

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
                     add_pre_prompts=(not api_flag))
    create_bar_chart(data_dict, "max_memory_usage", "Max Memory Usage",
                     os.path.join(all_models_folder, "max_memory_usage.png"), add_pre_prompts=(not api_flag))

    if api_flag:
        create_bar_chart(data_dict, "total_duration", "API Total Duration",
                         os.path.join(all_models_folder, "api_total_duration.png"))
        create_bar_chart(data_dict, "eval_count", "Amount of Tokens",
                         os.path.join(all_models_folder, "api_amount_of_token_duration.png"))
        create_bar_chart(data_dict, "tokens_per_second", "API Tokens Per Second",
                         os.path.join(all_models_folder, "api_tokens_per_second.png"))
        create_bar_chart(data_dict, "prompt_eval_duration", "API Time to Evaluate the Prompt",
                         os.path.join(all_models_folder, "api_prompt_eval_duration.png"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run all the prompts with all the models'.")

    parser = argparse.ArgumentParser(description='Process command line arguments.')
    parser.add_argument('prompt_file', type=str, help='The path to the prompt file.')
    parser.add_argument('--api', action='store_true', help='Flag to use API.')
    parser.add_argument('--code_only', action='store_true',
                        help='If the prompts will only be code that needs to be completed')

    parser.add_argument('--models', type=str, help='If you only want to run some models')

    parser.add_argument('--do_not_run', action='store_true',
                        help='This will collate the current data from all the models into a graph without running the prompts')
    parser.add_argument('--temp', type=str, default=0,
                        help='The temperature which is in the API Call. Note: Only to be used with `--code_only` flag')

    args = parser.parse_args()

    run(args.prompt_file, args.api, args.code_only, args.models, args.do_not_run, args.temp)
