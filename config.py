import yaml
import sys
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv\

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_CONFIG = {
    "temp_threshold_f": 70.0,
    "check_interval": 60,
    "alert_cooldown": 3600,
    "records_kept": 60
}

@dataclass(frozen=True)
class Settings:
    smtp_email: str
    smtp_password: str
    receiver_email: str
    temp_threshold_f: float
    check_interval: int
    alert_cooldown: int
    records_kept: int
    image_path: Path

def load_settings() -> Settings:
    load_environment(BASE_DIR / ".env")
    cfg = {**DEFAULT_CONFIG, **load_config(BASE_DIR / "config.yaml")}
    return Settings(
        smtp_email=os.environ["SMTP_EMAIL"],
        smtp_password=os.environ["SMTP_PASSWORD"],
        receiver_email=os.environ["RECEIVER_EMAIL"],
        temp_threshold_f=float(cfg["temp_threshold_f"]),
        check_interval=int(cfg["check_interval"]),
        alert_cooldown=int(cfg["alert_cooldown"]),
        records_kept=int(cfg["records_kept"]),
        image_path=BASE_DIR / "images" / "hi.png",
    )

def load_config(filepath="config.yaml"):
    try:
        with open(filepath, "r") as file:
            # Returns None if the file is completely empty
            data = yaml.safe_load(file)
            if data is None:
                print(f"Warning: {filepath} is empty. Using default settings.")
                return DEFAULT_CONFIG
            return data

    except FileNotFoundError:
        print(f"Error: {filepath} not found. Using default settings.")
        return DEFAULT_CONFIG

    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML syntax in {filepath}.")
        # Optional: print the exact line and column of the syntax error
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            print(f"Syntax error at line {mark.line + 1}, column {mark.column + 1}")
        sys.exit(1)  # Stop execution if the config is broken

def load_environment(env_path=".env", required_vars=None):
    if required_vars is None:
        required_vars = ["SMTP_EMAIL", "SMTP_PASSWORD", "RECEIVER_EMAIL"]

    env_file = Path(env_path)

    # 1. Check if the .env file actually exists (since load_dotenv won't raise an error)
    if not env_file.is_file():
        print(f"Warning: {env_path} file not found. Checking system environment variables...")
    else:
        try:
            # override=True ensures .env values update any stale system variables
            loaded = load_dotenv(dotenv_path=env_file, override=True)
            if not loaded:
                print(f"Warning: {env_path} is empty or contains no valid variables.")
        except PermissionError:
            print(f"Error: Permission denied when trying to read {env_path}.")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error loading {env_path}: {e}")
            sys.exit(1)

    # 2. Verify that all required variables exist and are not empty strings
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Ensure they are set in your .env file or system environment.")
        sys.exit(1)