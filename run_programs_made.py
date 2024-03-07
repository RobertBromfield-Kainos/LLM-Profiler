import argparse
import os.path
import re
import subprocess
import shlex
import run_all_models
import utils


class ProgrammingLanguage:
    def __init__(self, name: str, run_command: str, file_extension: str):
        self.name = name
        self.run_command = run_command
        self.file_extension = file_extension

    def get_command(self, file: str, input: str = '') -> str:
        file = os.path.join('scripts_made', file)
        return self.run_command.format(name=file, parmeters=input, file_extension='.' + self.file_extension)

    def save(self, file: str, code: str) -> None:
        with open(os.path.join('scripts_made', file) + "." + self.file_extension, "w") as f:
            f.write(code)
        f.close()


dict = {
    "java": ProgrammingLanguage("java", "java {name}{file_extension} {input}", "java"),
    "python": ProgrammingLanguage("python", "python {name}{file_extension}", "py"),
    "javascript": ProgrammingLanguage("javascript", "node {name}{file_extension}", "js"),
    "php": ProgrammingLanguage("php", "php {name}{file_extension}", "php"),
    "c": ProgrammingLanguage("c", "gcc -o {name} {name}{file_extension} && ./{name}", "c"),
    "c++": ProgrammingLanguage("c++", "g++ {name}{file_extension} -o {name} && ./{name}", "cpp")
}


def execute_command(command):
    # Check if the command uses shell features
    if '&&' in command or '||' in command or ';' in command:
        # Use shell=True for complex shell commands
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
    else:
        # For simpler commands, split and execute without shell
        args = shlex.split(command)
        result = subprocess.run(args, capture_output=True, text=True)

    return result


def extract_code(text: str) -> str:
    # Regular expression to match text between triple backticks
    # and optionally match a language name immediately after the first set of backticks
    pattern = r"```(?:[^\n]*\n)?(.*?)```"

    # Using re.DOTALL to match across multiple lines
    match = re.search(pattern, text.replace('<br>', '\n'), re.DOTALL)

    if match:
        # Extracting the text between the first pair of triple backticks
        return match.group(1).strip()
    else:
        return ''

if __name__ == "__main__":
    test_folder = 'tests'
    # prompt_file = "hello_world_prompts.csv"


    parser = argparse.ArgumentParser(
        description="Profile a command's CPU and memory usage and log input leading to output.")
    parser.add_argument('prompt_file', type=str, help='The prompt file to use')

    # Add optional argument for prompt file
    parser.add_argument('--run_all_models', action='store_true', help='Run the file run_all_models.py with the given prompt file.')

    parser.add_argument('--api_flag', action='store_true', help='Run the file run_all_models.py with the given prompt file.')

    args = parser.parse_args()
    prompt_file = args.prompt_file

    if args.run_all_models:
        run_all_models.run(prompt_file)


    models = utils.get_list_of_models()
    for model in models:
        expected_output_language_file = os.path.join(test_folder, prompt_file.replace('_prompts.csv', '_languages.csv'))
        expected_output_language_file = open(expected_output_language_file, "r")
        languages = expected_output_language_file.read().split(',')

        code_dict = {}
        passed_dict = {}

        # print(languages)

        expected_output_file = os.path.join(test_folder, prompt_file.replace('_prompts.csv', '_expected_output_input.csv'))
        expected_output_file = open(expected_output_file, "r")
        expected_output_file_contents = expected_output_file.readlines()

        output_folder = utils.get_last_output_folder(prompt_file.split('.')[0], model, args.api_flag)
        if output_folder is None:
            print(f"No output folder found for {model}")
            continue

        input_response_file = open(os.path.join(output_folder, 'input_response_file.csv'), "r")

        i = 0
        for line in input_response_file:
            if line.strip() == "":
                continue

            input_timestamp, input, response_timestamp, response = line.split("|||")

            programming_language = languages[i]

            if programming_language not in dict.keys():
                if programming_language != 'None':
                    print(f"Programming language {programming_language} not supported")
                i += 1
                continue

            code = extract_code(response)
            code_dict[input] = code

            dict[programming_language].save("test", code)

            command = dict[programming_language].get_command("test")

            # print('-->', command)

            expected_output = ''

            # Get Expected Output
            # Check if file only contains one line

            command_parameter = ''

            if len(expected_output_file_contents) == 1:
                line = expected_output_file_contents[0]
                split_line = line.split("|||")
                if split_line[0] == 'all':
                    expected_output = split_line[1].strip()
                if len(split_line) > 2:
                    command_parameter = split_line[2].strip()

            # Run command and capture output
            result = execute_command(command)

            # The stdout attribute contains the command's standard output
            # print('Output:  ', result.stdout.strip())
            # print('Expected:', expected_output)

            real_output = result.stdout.strip()
            passed = result.stdout.strip() == expected_output
            passed_dict[input] = passed

            i += 1

        markdown_table = utils.generate_markdown_line("Input", "Code", "Expected Output", "Output", "Passed", "Error",
                                                      is_header=True)

        score = 0

        for input, code in code_dict.items():
            passed = passed_dict[input]
            score += (1 if passed else 0)
            markdown_table += utils.generate_markdown_line(input, code, expected_output, real_output, passed,
                                                           result.stderr)

        markdown_table += "\n\n"
        markdown_table += utils.generate_markdown_line("Score", is_header=True)
        markdown_table += utils.generate_markdown_line(f'{score}/{len(code_dict)}')

        all_models_folder = os.path.join(test_folder, prompt_file.split('.')[0], "all_models")
        utils.make_folder(all_models_folder)

        print(all_models_folder)

        code_output_table = open(os.path.join(all_models_folder, model + "_code_output_table.md"), "w")
        code_output_table.write(markdown_table)
        code_output_table.close()

    input_response_file.close()
    expected_output_file.close()
    expected_output_language_file.close()
