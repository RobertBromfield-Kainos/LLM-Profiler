import argparse
import concurrent.futures
import multiprocessing
import os.path
import re
import traceback
from enum import Enum, auto

import autopep8

import run_all_models
import utils


class SuccessAttribute(Enum):
    COMPLETELY_CORRECT = auto()
    SUCCESS_RESPONSE_ONLY = auto()
    SUCCESS_WITH_TAB = auto()
    EMPTY_RESPONSE = False


class EvaluationResult:
    def __init__(self, evaluation_result=None, success_bool_attr=None):
        self.completely_correct_bool = False
        self.success_response_only_bool = False
        self.success_with_tab_bool = False
        self.empty_response_bool = False
        self.result_type = None
        self.result = None

        if evaluation_result is not None and success_bool_attr is not None:
            self.update_result(evaluation_result, success_bool_attr)

    def update_result(self, evaluation_result: tuple, success_bool_attr: SuccessAttribute):
        success_bool, self.result_type, self.result = evaluation_result
        # Map the enum to the corresponding boolean attribute
        attr_map = {
            SuccessAttribute.COMPLETELY_CORRECT: 'completely_correct_bool',
            SuccessAttribute.SUCCESS_RESPONSE_ONLY: 'success_response_only_bool',
            SuccessAttribute.SUCCESS_WITH_TAB: 'success_with_tab_bool',
            SuccessAttribute.EMPTY_RESPONSE: 'empty_response_bool',
        }

        if success_bool_attr in attr_map:
            setattr(self, attr_map[success_bool_attr], success_bool)
        else:
            raise ValueError(f"{success_bool_attr} is not a valid SuccessAttribute enum value.")


# Define execute_code at the top level
def worker(code, globals_dict, locals_dict, queue):
    try:
        exec(code, globals_dict, locals_dict)
        # If no exception is raised, assume success
        queue.put(('success', locals_dict.get('result', None)))
    except SyntaxError as e:
        queue.put(('syntax error', traceback.format_exc()))
    except AssertionError as e:
        queue.put(('assertion error', traceback.format_exc()))
    except Exception as e:
        queue.put(('error', traceback.format_exc()))


def run_code_with_timeout(full_code, test_case, globals_dict, locals_dict, entry_point, timeout):
    # Define the full code with the test case appended
    full_code_plus_test_case = full_code + '\n' + test_case
    full_code_plus_test_case += f"\nresult = check({entry_point})\n"

    print(full_code_plus_test_case)

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=worker, args=(full_code_plus_test_case, globals_dict, locals_dict, queue))

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()
        return 'timeout', None

    result_type, result_value = queue.get()
    return result_type, result_value


def evaluate_prompt_response(prompt, response, test_case, globals_dict, locals_dict, entry_point):
    try:
        # Generate full code from prompt and validated response
        full_code = get_code_from_prompt_response(prompt, response)
        full_code_plus_test_case = full_code + '\n' + test_case
        full_code_plus_test_case += f"\nresult = check({entry_point})\n"

        # Execute the code and capture the result
        result_type, result = run_code_with_timeout(full_code, test_case, globals_dict, locals_dict, entry_point, 5)
        success_bool = result_type == 'success'

        # Return result for further processing if needed
        return success_bool, result_type, result
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False, 'error', None


def comprehensive_evaluate(prompt, response, test_case, entry_point, globals_dict={},
                           locals_dict={}) -> EvaluationResult:
    output = EvaluationResult()
    sanitised_response = extract_relevant_content(response)

    if sanitised_response.strip() == '':
        output.empty_response_bool = True
        utils.print_header(utils.red('Empty Response'))
        return output

    # Initial evaluation
    eval_output = evaluate_prompt_response(prompt, sanitised_response, test_case, globals_dict, locals_dict,
                                           entry_point)
    output.update_result(eval_output, SuccessAttribute.COMPLETELY_CORRECT)
    success_text = utils.green('Success') if output.completely_correct_bool else utils.red('Failed')
    header_output = ''

    # Adjust response based on the evaluation outcome
    if not output.completely_correct_bool:
        first_line_of_prompt = prompt.strip().split('\n')[0].strip()
        first_line_of_response = response.strip().split('\n')[0].strip()

        # Check if first lines match, implying potential need to evaluate response alone
        if first_line_of_prompt == first_line_of_response:
            eval_output = evaluate_prompt_response('', sanitised_response, test_case,
                                                   globals_dict,
                                                   locals_dict, entry_point)

            output.update_result(eval_output, SuccessAttribute.SUCCESS_RESPONSE_ONLY)
            success_text = utils.green('Success') if output.success_response_only_bool else utils.red('Failed')

            header_output = 'Tried with Response Only: '
        elif not sanitised_response.startswith("    "):
            # Adjust for missing indentation and reevaluate
            response_with_tabs = '    ' + sanitised_response.replace('\n', '\n    ')
            eval_output = evaluate_prompt_response(prompt, response_with_tabs, test_case,
                                                   globals_dict, locals_dict,
                                                   entry_point)
            output.update_result(eval_output, SuccessAttribute.SUCCESS_WITH_TAB)

            success_text = utils.green('Success') if output.success_with_tab_bool else utils.red('Failed')
            header_output = 'Tried Tab With Tab Added: '

    utils.print_header(header_output + success_text + '\n' + str(output.result))
    return output


def evaluate_code(prompts, responses, test_cases, entry_points):
    workers = min(len(prompts), multiprocessing.cpu_count())
    tasks = zip(prompts, responses, test_cases, entry_points)

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        # Directly use the comprehensive_evaluate function without lambda
        evaluation_results = list(executor.map(comprehensive_evaluate, *zip(*tasks)))

    completely_correct_responses = 0
    success_with_tab_added = 0
    correct_with_just_response = 0

    assertion_errors = 0
    syntax_errors = 0
    other_errors = 0
    empty_responses = 0
    # Process the results as needed
    for evaluation_result in evaluation_results:
        completely_correct_responses += 1 if evaluation_result.completely_correct_bool else 0
        success_with_tab_added += 1 if evaluation_result.success_with_tab_bool else 0
        correct_with_just_response += 1 if evaluation_result.success_response_only_bool else 0

        assertion_errors += 1 if evaluation_result.result_type == 'assertion error' else 0
        syntax_errors += 1 if evaluation_result.result_type == 'syntax error' else 0
        other_errors += 1 if evaluation_result.result_type == 'error' else 0
        empty_responses += 1 if evaluation_result.empty_response_bool else 0

    return completely_correct_responses, success_with_tab_added, correct_with_just_response, assertion_errors, syntax_errors, other_errors, empty_responses


def get_code_from_prompt_response(prompt: str, response: str):
    prompt = prompt.replace('\\n', '\n')
    response = response.replace('\\n', '\n')
    return prompt + response


def extract_relevant_content(text):
    # Compile patterns to match content after <suffix> and within <fim_prefix> or <fim_middle>

    text = text.replace('<br>', '\n')
    text = text.replace('\\end{code}', '')

    patterns = {
        'after_suffix': re.compile(r'(?<=<suffix>)(.*?)(?=<|$)', re.DOTALL),
        'fim_prefix': re.compile(r'(?<=<fim_prefix>)(.*?)(?=<fim_middle>)', re.DOTALL),
        'fim_middle': re.compile(r'(.*?)(?=</fim_middle>|$)', re.DOTALL),
    }

    # Search for each pattern and store results
    extracted_content = []
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text)
        for match in matches:
            if match:  # Check if match is not an empty string
                extracted_content.append(match)  # Append without stripping

    # Return the first piece of extracted content if any, otherwise return an empty string
    return extracted_content[0] if extracted_content else ''


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process command line arguments.')
    parser.add_argument('prompt_file', type=str, help='The path to the prompt file.')
    parser.add_argument('--models', type=str, help='If you only want to run some models')
    args = parser.parse_args()

    prompts_csv_file_name = args.prompt_file

    last_all_models_output_folder = utils.get_last_output_folder(prompts_csv_file_name, 'all_models', True)
    all_run_models = utils.get_models_that_have_been_run(prompts_csv_file_name, True)
    all_run_models = utils.sort_models(all_run_models)

    markdown_table_file = open(os.path.join(last_all_models_output_folder, 'overall_results.md'), 'w')
    markdown_table_headers = utils.generate_markdown_line('Model', 'Correct Responses With No Modification',
                                                          'Correct When Tab Added', 'Correct With Just Response',
                                                          'Overall Successes', 'Assertion Errors', 'Syntax Errors',
                                                          'Other Errors', 'Empty Responses',
                                                          'Average CPU Spike', 'Max CPU', 'Average Memory',
                                                          'Max Memory', 'Average Virtual Memory', 'Max Virtual Memory',
                                                          'Average Duration of Prompt', 'Max Duration of Prompt',
                                                          is_header=True)
    markdown_table_file.write(markdown_table_headers)

    optional_models = args.models
    if optional_models is not None:
        all_run_models = [m for m in all_run_models if m in optional_models.split(',')]

    for model in all_run_models:
        utils.print_header(utils.red(model))

        prompts_csv_file = open('prompt_files/' + prompts_csv_file_name, 'r')
        prompts = prompts_csv_file.readlines()[0].split('|||')

        output_folder = utils.get_last_output_folder(prompts_csv_file_name, model, True)
        input_response_file = open(os.path.join(output_folder, 'input_response_file.csv'), 'r')

        # Make an array of 'total_duration' in api_response_data.csv in the output folder which has "," as a delimiter
        # And headers on the first line
        with open(os.path.join(output_folder, 'api_response_data.csv'), 'r') as file:
            total_duration_list = [int(line.split(',')[0]) for line in file.readlines()[1:] if ',' in line]

        with open(os.path.join(output_folder, 'input_response_file.csv'), 'r') as file:
            lines = file.readlines()
            time_started_list = [line.split('|||')[0] for line in lines if '|||' in line]
            time_ended_list = [line.split('|||')[2] for line in lines if '|||' in line]
            responses = [line.split('|||')[3] for line in lines if '|||' in line]
            responses = [response.replace('\\n', '\n') for response in responses]

        cpu_usage_file = os.path.join(output_folder, "cpu_usage.csv")
        cpu_list = run_all_models.get_max_of_column_grouped_by_prompt('CPU Usage (%)', cpu_usage_file,
                                                                      time_started_list, time_ended_list)

        memory_usage_file = os.path.join(output_folder, "memory_usage.csv")
        memory_list = run_all_models.get_max_of_column_grouped_by_prompt('Memory Usage (MB)', memory_usage_file,
                                                                         time_started_list, time_ended_list)
        virtual_memory_list = run_all_models.get_max_of_column_grouped_by_prompt('Virtual Memory Usage (MB)',
                                                                                 memory_usage_file, time_started_list,
                                                                                 time_ended_list)

        max_cpu = max(cpu_list)
        max_memory = max(memory_list)
        max_virtual_memory = max(virtual_memory_list)

        max_total_duration = max(total_duration_list)
        max_total_duration = utils.nanoseconds_to_human_readable(max_total_duration)

        average_cpu = round(sum(cpu_list) / len(cpu_list), 2)
        average_memory = round(sum(memory_list) / len(memory_list), 2)
        average_virtual_memory = round(sum(virtual_memory_list) / len(virtual_memory_list), 2)

        average_total_duration = sum(total_duration_list) / len(total_duration_list)
        average_total_duration = utils.nanoseconds_to_human_readable(average_total_duration)

        print('Test file:', 'tests/' + prompts_csv_file_name.replace('_prompts', '_tests'))
        test_csv_file = open('tests/' + prompts_csv_file_name.replace('_prompts', '_tests'), 'r').readlines()
        tests = test_csv_file[0].split('|||')
        tests = [test.replace('\\n', '\n') for test in tests]

        entry_points = open(
            os.path.join('tests', prompts_csv_file_name.replace('_prompts', '_entrypoints'))).readlines()
        entry_points = entry_points[0].split(',')

        (completely_correct_responses, success_with_tab_added, correct_with_just_response,
         assertion_errors, syntax_errors, other_errors, empty_responses) = evaluate_code(prompts, responses, tests,
                                                                                         entry_points)

        all_successes = completely_correct_responses + success_with_tab_added + correct_with_just_response

        utils.print_header("Results for " + utils.bold(model))

        print('Completly Correct Responses', completely_correct_responses, '/', len(responses))
        print('Correct Responses With Tab Added', success_with_tab_added, '/', len(responses))
        print('Correct With Just Response', correct_with_just_response, '/', len(responses))
        print('All Successes:', all_successes, '/', len(responses))

        results = [
            model, completely_correct_responses, success_with_tab_added, correct_with_just_response,
            all_successes, assertion_errors, syntax_errors, other_errors, empty_responses,
            average_cpu, max_cpu, average_memory, max_memory, average_virtual_memory,
            max_virtual_memory, average_total_duration, max_total_duration
        ]
        results = [str(a) for a in results]

        markdown_table_line = utils.generate_markdown_line(results)
        markdown_table_file.write(markdown_table_line)
        markdown_table_file.flush()
