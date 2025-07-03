import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# === FORMATTER SENZA COLORI PER IL FILE LOG ===
file_formatter = logging.Formatter(
    fmt="%(asctime)s - %(levelname)s - [%(name)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# === FORMATTER CON COLORI ANSI PER CONSOLE ===
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[92m',      # Green
        'WARNING': '\033[93m',   # Yellow
        'ERROR': '\033[91m',     # Red
        'CRITICAL': '\033[95m'   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

console_formatter = ColorFormatter(
    fmt="%(asctime)s - %(levelname)s - [%(name)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%H:%M:%S"
)

# === GET LOGGER ===
def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        logs_path = Path("logs")
        logs_path.mkdir(exist_ok=True)

        # Console handler con colori
        ch = logging.StreamHandler()
        ch.setFormatter(console_formatter)
        logger.addHandler(ch)

        # File handler senza colori
        fh = RotatingFileHandler(
            logs_path / "app.log",
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding="utf-8"
        )
        fh.setFormatter(file_formatter)
        logger.addHandler(fh)

    return logger

# === SHORTCUT FUNCTIONS ===
def log_info(message):
    logger = get_logger("app")
    logger.debug("[INFO] " + message, stacklevel=2)

def log_error(message):
    logger = get_logger("app")
    logger.error("[ERROR] " + message, stacklevel=2)

def log_warning(message):
    logger = get_logger("app")
    logger.warning("[WARNING] " + message, stacklevel=2)

def log_success(message):
    logger = get_logger("app")
    logger.info("[OK] " + message, stacklevel=2)
