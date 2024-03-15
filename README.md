# LLM Profiler

This repository contains a suite of Python scripts designed to profile the performance of LLM Models, automate the process of sending prompts to commands, and generate visualizations to analyze CPU and memory usage. It is intended for developers and researchers who need to monitor and optimize the performance of their applications.

## Installation

1. Clone this repository to your local machine.
2. Ensure you have Python 3.6+ installed.
3. Ensure you have [ollama](https://github.com/ollama/ollama) installed
4. Install the required dependencies by running `pip install -r requirements.txt` in your terminal.

5. Before profiling a model please insure it has been installed and is working with ollama

​	You can do this by using the command
```bash
ollama run <model_name>
```

## Usage

### Profiling a Command at a Time Using the Ollama API

Sends POST requests from prompts in a file to `ollama serve` and monitors its performance.

**Arguments**:

- `--model` (required): The name of the installed model.
- `--prompt_file` (required): Path to the prompt file containing the prompts to send.
- `--code_only` (optional): Set this flag if the prompts will only be code that needs to be completed.

**Usage**

```bash
python profiler_api.py <model> <prompt_file> --code_only
```

### Sending Prompts from a file to a Command

Sends prompts from a CSV file to a command and integrates with visualization generation.

**Arguments**

  -  `prompt_file`  (required): The name of th prompt file.
  -  `model_name` (required): The name of the installed model.

**Usage**:

```bash
python give_prompts.py <prompt_file> <model_name>
```

### Run a Prompt File for All Models

Runs all the prompts with all the models.

**Arguments**

  -  `prompt_file`  (required): The name of th prompt file.
  -  `--api` (optional): Indicates the use of an API for running the prompts.
  -  `--code_only` (optional) :Should be used if the prompts are solely code snippets that need to be completed.

**Usage**:

```bash
python run_all_models.py <prompt_file> --api --code_only
```

### Test Prompts from a Dataset with Python  

Processes prompts from a file for testing against specified models when those prompts are the first part of a python program

**Arguments**:

- `prompt_file` (required): The path to the prompt file, where prompts are delimited with `|||`.
- `--models` (optional): Specify models to run, separated by commas. 
  - If this option is not used it will run all the models 

**Pre-requisite**

As it says below prompt files should be in the format `<name>_prompts.csv` the names of the following files rely on this 

- `<name>_tests.csv` - This will have python code on one line which contains a function called `check()` which has assertions the generated code will be tested against. 
  - Delimted with `|||`
- `<name>_entrypoints.csv` - This will contain the names of the functions that are in the prompts. These will be given to `check()` to test.
  - Delimeted with `,`

### Creating New Prompt Files

Prompt files are CSV files containing commands or inputs you wish to send to the profiled application. To create a new prompt file:

1. Format your prompts in a CSV file, with each prompt in a new line.
2. Each prompt should be delimetered with `|||` 
3. Use the filename format `prompt_files/<name>_prompts.csv` for organization.

## Output

When the `give_prompts.py` file is run it will create the following files in the following structure 

```
├── output
│   ├── <name of prompt file>
│   │   ├── all_models
│   │   │   ├── <timestamp of when run_all_models.py was run>
│   │   │   │   ├── amount_of_words.png
│   │   │   │   ├── input_response_table.md
│   │   │   │   ├── max_cpu_usage.png
│   │   │   │   ├── max_memory_usage.png
│   │   │   │   ├── time_taken.png
│   │   │   │   ├── words_per_second.png
│   │   ├── <model>
│   │   │   ├── <timestamp of when give_prompts.py was run>
│   │   │   │   ├── cpu_usage.csv
│   │   │   │   ├── memory_usage.csv
│   │   │   │   ├── input_response_file.csv
│   │   │   │   ├── visualisations
│   │   │   │   │   ├── cpu_usage.png
│   │   │   │   │   ├── memory_usage.png
│   │   │   │   │   ├── input_output_memory_change_table.md
```



### Explination of Output Files 

| **File Name**                                      | Explanation                                                  |
| -------------------------------------------------- | ------------------------------------------------------------ |
| cpu_usuage.csv                                     | This is a CSV of the CPU Usage while the program is running<br />Titles are `Timestamp` and `CPU Usage (%)` |
| memory_usage.csv                                   | This CSV shows the `Timestamp`, `Memory Usage (MB)` and `Virtual Memory Usage (MB)` while the program is running |
| input_response_file.csv                            | This file is delimetered with `\|\|\|` and each row is:<br />- The timestamp of when the command was inputted <br />- What prompt was inputted <br />- The timestamp of when the output stopped<br />- The output from the LLM |
| visualisations/cpu_usage.png                       | A line graph of the CPU Usage taken from `cpu_usuage.csv` <br />Here the different prompts are visualised by different colour bands.<br />With the band begininging when the prompt was inputted and ending when the output finished. <br />This data is taken from the `input_response_file.csv` |
| visualisations/memory_usage.png                    | A line graph of the Memory Usage taken from `memory_usage.csv` <br />This contains two graphs which are for `Memory Usage (MB)` and `Virtual Memory Usage (MB)`<br /><br />Like the `visualisations/cpu_usage.png` this also has coloured bands denoting when the prompts were run |
| visualisations/input_output_memory_change_table.md | This is a markdown table showing the any other relavent data |



### Example graphs in `visualisations`

#### `cpu_usage.png`

![example_cpu_usage](./.readme_images/cpu_usage.png)

#### `memory_usage.png`

### ![example_memory_usage](./.readme_images/memory_usage.png)

### Example graphs in `all_models`

#### `words_per_second.png`

![words_per_second](./.readme_images/words_per_second.png)



#### `amount_of_words.png`

![amount_of_words](./.readme_images/amount_of_words.png)

#### `max_cpu_usage.png`

![max_cpu_usage](./.readme_images/max_cpu_usage.png)

#### `max_memory_usage.png`

![max_cpu_usage](./.readme_images/max_memory_usage.png)