import os.path
import subprocess
import sys
import time

import give_prompts
import utils


def get_list_of_models():
    # Run `ollama list` return contents of NAME column
    cmd = "ollama list"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    lines = stdout.decode().strip().split('\n')[1:]
    models = [line.split()[0] for line in lines]
    return models


def print_header(header_text: str):
    print('-' * len(header_text))
    print(header_text)
    print('-' * len(header_text))

if __name__ == "__main__":
    prompt_file = sys.argv[1]
    models = get_list_of_models()
    # Remove 70b models from the list
    models = [model for model in models if model.split(':')[-1] != '70b']
    print('Currently available models -- ' + ' '.join(models))


    data_dict = {}

    for model in models:
        print_header(f"Running {model}")
        give_prompts.run(prompt_file, model)
        print_header(f"Finished running {model}")
        # input_response_file.csv

        # Get words per second from input_response_file.csv
        # 2024-02-23 16:47:10|||Could you write it in PHP|||2024-02-23 16:47:15|||Yes, here is an example of a "Hello World" program in PHP:<br>```<br><?php<br>echo "Hello, World!";<br>?><br>```

        output_folder = utils.get_last_output(prompt_file, model)
        input_response_file = os.path.join(output_folder, "input_response_file.csv")
        words_per_second = []
        responses = []
        time_taken = []
        for line in open(input_response_file):
            if line.strip() == "":
                continue
            input_time, input_text, response_time, response_text = line.strip().split("|||")
            words = len(response_text.split())
            time_delta = utils.get_time_difference(input_time, response_time)
            time_taken.append(time_delta)
            responses.append(response_text)
            words_per_second.append(words / time_delta)

        cpu_usage_file = os.path.join(output_folder, "cpu_usage.csv")
        cpu_usage = []


        data_dict[model] = {
            "words_per_second": words_per_second,
            "responses": responses,
            "time_taken": time_taken
        }
        print_header(f"Finished processing {model}")
        time.sleep(5)
    print(data_dict)






