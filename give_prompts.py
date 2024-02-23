import os.path
import subprocess
import time

import pexpect
import sys
import create_visualisations

def preprocess_csv_content(csv_file_path):
    """Process the CSV file to replace custom delimiters with standard newlines."""

    full_path = os.path.join('prompt_files', csv_file_path)
    with open(full_path, 'r', encoding='utf-8') as csvfile:
        return csvfile.read().replace('|||', '\x1F')

def main(csv_file_path, command):
    csv_content = preprocess_csv_content(csv_file_path)
    csv_lines = csv_content.split('\x1F')

    try:
        # Launch the command with pexpect, increase timeout as needed
        child = pexpect.spawn(command, encoding='utf-8', timeout=10)
        child.logfile = sys.stdout  # Pipe output to stdout for debugging purposes

        # Wait for the initial prompt indicating readiness
        child.expect('>>>', timeout=120)  # Adjust timeout as necessary

        for line in csv_lines:
            trimmed_line = line.strip()
            if trimmed_line:  # Ensure the line is not just whitespace
                # Send the line to the command
                child.sendline(trimmed_line)
                child.sendline('\r')  # Send a newline character to simulate pressing 'Enter
                # Wait for the command to process the input and display the next prompt
                child.expect('>>>', timeout=120)  # Adjust timeout as necessary
                time.sleep(5)

    except pexpect.EOF:
        print("The command exited unexpectedly.")
    except pexpect.TIMEOUT:
        print("The command timed out waiting for an expected prompt.")



def close_ollama():
    try:
        path_prefix = "/Applications/Ollama.app"
        # Escape special characters for use in the grep command

        # List all processes and grep for those starting with the specified path
        # Using awk to print the first column (PID) only if the rest of the line matches the path
        cmd = f"ps -eo pid,command | grep -E '{path_prefix}' | awk '{{print $1}}'"

        print(cmd)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Extract PIDs
        pids = stdout.decode().strip().split('\n')

        for pid in pids:
            if pid.isdigit():
                print(f"Terminating process with PID: {pid}")
                subprocess.run(["kill", "-9", pid])
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    close_ollama()
    if len(sys.argv) < 3:
        print("Usage: script.py <filename.csv> <command>")
        sys.exit(1)

    csv_file = sys.argv[1]
    model = sys.argv[2]

    command = f'python profiler.py "ollama run {model}" --prompt_file {csv_file.split(".")[0]}'
    main(csv_file, command)

    create_visualisations.main(model, csv_file.split(".")[0])
    close_ollama()


