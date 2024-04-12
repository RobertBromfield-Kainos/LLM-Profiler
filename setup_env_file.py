import os

import psutil


def update_env_file(key: str, value: str):
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_file, 'r') as file:
        lines = file.readlines()

    found = False

    with open(env_file, 'w') as file:
        for line in lines:
            if key == line.split('=')[0]:
                line = f'{key}={value}\n'
                found = True
            file.write(line)
        if not found:
            file.write(f'{key}={value}\n')

    print(f'Updated {key} to {value}')


if __name__ == "__main__":
    # If .env does not exist copy sample.env to .env
    if not os.path.exists('.env'):
        os.system('cp sample.env .env')

    cmd_names_env_key_dict = {
        'Ollama': 'OLLAMA_PATH',
        'Ollama Helper (GPU)': 'OLLAMA_HELPER_GPU_PATH',  # Added comma here
        'Ollama Helper': 'OLLAMA_HELPER_PATH',
        'ollama': 'OLLAMA_SERVE_PATH',
        'Ollama Helper (Renderer)': 'OLLAMA_HELPER_RENDERER_PATH'  # Added comma here
    }

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'])

            if proc.info['name'] in cmd_names_env_key_dict.keys():
                update_env_file(cmd_names_env_key_dict[proc.info['name']], cmdline)
        except:
            continue
