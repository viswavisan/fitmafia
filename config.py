import os
import configparser
from dotenv import load_dotenv

# 1. Load sensitive variables from .env
load_dotenv()

# 2. Parse non-sensitive settings from properties.ini
config_parser = configparser.ConfigParser()
properties_file = os.path.join(os.path.dirname(__file__), 'properties.ini')

if os.path.exists(properties_file):
    config_parser.read(properties_file)
    for section in config_parser.sections():
        for key, value in config_parser.items(section):
            # Populate environment variables (both original case and uppercase)
            env_key_upper = key.upper()
            if env_key_upper not in os.environ:
                os.environ[env_key_upper] = value
            if key not in os.environ:
                os.environ[key] = value

def get_property(section: str, key: str, default: str = None) -> str:
    """Retrieve a property value from properties.ini or environment variables."""
    if config_parser.has_option(section, key):
        return config_parser.get(section, key)
    return os.getenv(key, os.getenv(key.upper(), default))
