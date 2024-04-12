import os

import psutil


def update_env_file(key: str, value: str):
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_file, 'r') as file:
        lines = file.readlines()

    with open(env_file, 'w') as file:
        for line in lines:
            if key == line.split('=')[0]:
                line = f'{key}={value}\n'
            file.write(line)

    print(f'Updated {key} to {value}')


if __name__ == "__main__":
    # If .env does not exist copy sample.env to .env
    if not os.path.exists('.env'):
        os.system('cp sample.env .env')

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'])
            cmdline_split = cmdline.split('/')
            if cmdline_split[-1] == 'ollama serve':
                update_env_file('OLLAMA_SERVE_PATH', cmdline)
        except:
            continue
