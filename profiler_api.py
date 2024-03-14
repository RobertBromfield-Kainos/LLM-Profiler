import argparse
import csv
import os
import requests
from datetime import datetime
import psutil
import threading
import time

import create_visualisations
import utils

stop_monitoring = threading.Event()


def get_usage_stats(command):
    """
    Finds the specified command process and returns its CPU, memory,
    and virtual memory usage.
    """
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and command in ' '.join(cmdline):
                cpu_percent = proc.cpu_percent()
                memory_info = proc.memory_info()
                virtual_memory = psutil.virtual_memory()
                return {
                    'cpu_percent': cpu_percent,
                    'memory_used': memory_info.rss,
                    'virtual_memory_used': virtual_memory.used,
                    'virtual_memory_total': virtual_memory.total
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None


def monitor_process(output_folder):
    """
    Monitor 'ollama serve' process and log CPU and memory usage.
    """
    cpu_file = os.path.join(output_folder, 'cpu_usage.csv')
    memory_file = os.path.join(output_folder, 'memory_usage.csv')
    global no_of_tries_monitor_process
    try:
        with open(cpu_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Timestamp', 'CPU Usage (%)'])
        with open(memory_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Timestamp', 'Memory Usage (MB)', 'Virtual Memory Usage (MB)'])

        while not stop_monitoring.is_set():
            stats = get_usage_stats('/Applications/Ollama.app/Contents/Resources/ollama serve')
            if stats:
                current_time = datetime.now().strftime(utils.datetime_format_with_microseconds)
                with open(cpu_file, 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([current_time, stats['cpu_percent']])
                with open(memory_file, 'a', newline='') as file:
                    writer = csv.writer(file)
                    memory_used_mb = stats['memory_used'] / (1024 * 1024)
                    virtual_memory_used_mb = stats['virtual_memory_used'] / (1024 * 1024)
                    writer.writerow([current_time, memory_used_mb, virtual_memory_used_mb])
            else:
                print("ollama serve process not found.")
    except:
        if no_of_tries_monitor_process < 10:
            time.sleep(1)
            no_of_tries_monitor_process += 1
            monitor_process(output_folder)


def send_post_request(model: str, prompt: str, output_folder: str, time_submitted, code_only_flag: bool):
    url = "http://localhost:11434/api/generate"

    prompt = prompt.replace('\\n', '\n')
    if not code_only_flag:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
    else:
        payload = {
          "model": model,
          "raw": True,
          "keep_alive": 1800,
          "options": {
            "temperature": 0,
            "num_predict": 1024,
            "stop": [
              "<fim_prefix>",
              "<fim_suffix>",
              "<fim_middle>",
              "<|endoftext|>",
              "\n\n",
              "```"
            ],
            "num_ctx": 4096
          },
          "prompt": f"<fim_prefix>{prompt}<fim_suffix><fim_middle>",
          "stream": False
        }

    response = requests.post(url, json=payload)
    time_received = datetime.now()

    if response.status_code == 200:
        utils.print_header("Request successful.")
        response_data = response.json()

        print(utils.bold('Prompt:'), prompt)
        save_api_response(response_data, output_folder, prompt, time_submitted, time_received)
        save_other_response_data(response_data, output_folder)
    else:
        print("Failed to send request: ", response.text)


def save_other_response_data(data, output_folder: str):
    # Define the path for the CSV file
    response_data_path = os.path.join(output_folder, 'api_response_data.csv')

    # Define the headers and the data row
    headers = ['total_duration', 'load_duration', 'prompt_eval_count', 'prompt_eval_duration', 'eval_count',
               'eval_duration']
    row = [data['total_duration'], data['load_duration'], data['prompt_eval_count'], data['prompt_eval_duration'],
           data['eval_count'], data['eval_duration']]

    # Check if file exists to decide whether to write headers
    file_exists = os.path.isfile(response_data_path)

    # Open the file in append mode and write the data
    with open(response_data_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(headers)  # Write headers if file does not exist
        writer.writerow(row)


def read_prompts_from_file(prompt_file_path):
    prompts = []
    with open(prompt_file_path, 'r', encoding='utf-8') as file:
        return file.read().strip().split('|||')


def save_api_response(response_data, output_folder, prompt, time_submitted, time_received):
    log_file_path = os.path.join(output_folder, 'input_response_file.csv')
    with open(log_file_path, 'a', newline='') as file:
        # Directly format and write the string with "|||" as the delimiter
        response = response_data.get('response', '')
        response = response.replace('\n', '<br>')
        response = response.replace('\r', '<br>')

        prompt = prompt.replace('\n', '<br>')
        prompt = prompt.replace('\r', '<br>')

        print(utils.bold('Response:'), response)
        line = f"{time_submitted.strftime(utils.datetime_format_with_microseconds)}|||{prompt}|||{time_received.strftime(utils.datetime_format_with_microseconds)}|||{response}\n"
        file.write(line)


def run(model: str, prompt_file_name: str, code_only_flag: bool):
    global stop_monitoring
    stop_monitoring = threading.Event()
    prompt_file_path = os.path.join('prompt_files', prompt_file_name)
    prompts = read_prompts_from_file(prompt_file_path)
    output_folder = utils.make_folder('output_api', prompt_file_name.split('.')[0], model,
                                      datetime.now().strftime(utils.datetime_format_no_microseconds))

    monitor_thread = threading.Thread(target=monitor_process, args=(output_folder,))
    monitor_thread.start()

    for prompt in prompts:
        time_submitted = datetime.now()
        send_post_request(model, prompt, output_folder, time_submitted, code_only_flag)
        time.sleep(5)

    stop_monitoring.set()
    monitor_thread.join()
    try:
        create_visualisations.run(model, prompt_file_name, True)
    except Exception as e:
        utils.print_exception(f'Create Visualisations failed for model: {model}', e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send POST requests from prompts in a file and monitor 'ollama serve'.")
    parser.add_argument('--model', type=str, required=True, help='Model name for the API request')
    parser.add_argument('--prompt_file', type=str, required=True, help='Path to the prompt file')
    parser.add_argument('--code_only', action='store_true',
                        help='If the prompts will only be code that needs to be completed')

    args = parser.parse_args()
    run(args.model, args.prompt_file, args.code_only)
