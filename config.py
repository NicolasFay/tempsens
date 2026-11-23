import yaml
import sys
import os
import logging
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv\

logger = logging.getLogger(__name__)

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
                logger.warning(f"{filepath} is empty. Using default settings.")
                return DEFAULT_CONFIG
            return data

    except FileNotFoundError:
        logger.error(f"{filepath} not found. Using default settings.")
        return DEFAULT_CONFIG

    except yaml.YAMLError as e:
        logger.exception(f"YAMLError: Invalid YAML syntax in {filepath}.")
        # Optional: print the exact line and column of the syntax error
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            logger.error(f"Syntax error at line {mark.line + 1}, column {mark.column + 1}")
        sys.exit(1)  # Stop execution if the config is broken

def load_environment(env_path=".env", required_vars=None):
    if required_vars is None:
        required_vars = ["SMTP_EMAIL", "SMTP_PASSWORD", "RECEIVER_EMAIL"]

    env_file = Path(env_path)

    # 1. Check if the .env file actually exists (since load_dotenv won't raise an error)
    if not env_file.is_file():
        logger.warning(f"{env_path} file not found. Checking system environment variables...")
    else:
        try:
            # override=True ensures .env values update any stale system variables
            loaded = load_dotenv(dotenv_path=env_file, override=True)
            if not loaded:
                logger.warning(f"{env_path} is empty or contains no valid variables.")
        except PermissionError:
            logger.exception(f"PermissionError: Permission denied when trying to read {env_path}.")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"Unexpected error loading {env_path}: {e}")
            sys.exit(1)

    # 2. Verify that all required variables exist and are not empty strings
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.info("Ensure they are set in your .env file or system environment.")
        sys.exit(1)