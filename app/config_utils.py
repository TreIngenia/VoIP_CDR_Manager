import os
from dotenv import load_dotenv

def save_config_to_env(config: dict, filename='.env.local'):
    with open(filename, 'w', encoding='utf-8') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")

def load_config_from_env_local(filename='.env.local') -> dict:
    load_dotenv(dotenv_path=filename)
    return dict(os.environ)
