import yaml
import sys
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

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
    telegram_token: str = field(repr=False)
    telegram_chat_id: int

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
        telegram_token=os.environ["TELEGRAM_TOKEN"],
        telegram_chat_id=int(os.environ["TELEGRAM_CHAT_ID"]),
    )

def load_config(filepath="config.yaml"):
    try:
        with open(filepath, "r") as file:
            # Returns None if the file is completely empty
            data = yaml.safe_load(file)
            if data is None:
                logger.warning("%s is empty. Using default settings.", filepath)
                return DEFAULT_CONFIG
            return data

    except FileNotFoundError:
        logger.error("%s not found. Using default settings.", filepath)
        return DEFAULT_CONFIG

    except yaml.YAMLError as e:
        logger.exception("YAMLError: Invalid YAML syntax in %s.", filepath)
        # Optional: print the exact line and column of the syntax error
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            logger.error("Syntax error at line %d, column %d", (mark.line + 1), (mark.column + 1))
        sys.exit(1)  # Stop execution if the config is broken

def load_environment(env_path=".env", required_vars=None):
    if required_vars is None:
        required_vars = ["SMTP_EMAIL", "SMTP_PASSWORD", "RECEIVER_EMAIL", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"]

    env_file = Path(env_path)

    # 1. Check if the .env file actually exists (since load_dotenv won't raise an error)
    if not env_file.is_file():
        logger.warning("%s file not found. Checking system environment variables...", env_path)
    else:
        try:
            # override=True ensures .env values update any stale system variables
            loaded = load_dotenv(dotenv_path=env_file, override=True)
            if not loaded:
                logger.warning("%s is empty or contains no valid variables.", env_path)
        except PermissionError:
            logger.exception("PermissionError: Permission denied when trying to read %s.", env_path)
            sys.exit(1)
        except Exception as e:
            logger.exception("Unexpected error loading %s: %s", env_path, e)
            sys.exit(1)

    # 2. Verify that all required variables exist and are not empty strings
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error("Missing required environment variables: %s", ", ".join(missing_vars))
        logger.info("Ensure they are set in your .env file or system environment.")
        sys.exit(1)