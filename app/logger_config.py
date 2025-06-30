# #!/usr/bin/env python3
# """
# Logger Configuration - Sistema di logging standardizzato
# """

# import logging
# import sys
# from pathlib import Path
# from logging.handlers import RotatingFileHandler
# from datetime import datetime

# class ProjectLogger:
#     """Logger standardizzato per tutto il progetto"""
    
#     _loggers = {}
#     _initialized = False
    
#     @classmethod
#     def initialize(cls):
#         """Inizializza il sistema di logging"""
#         if cls._initialized:
#             return
            
#         # Crea directory logs
#         log_dir = Path('logs')
#         log_dir.mkdir(exist_ok=True)
        
#         # Configura logging root
#         root_logger = logging.getLogger()
#         root_logger.setLevel(logging.INFO)
        
#         # Rimuovi handler esistenti
#         for handler in root_logger.handlers[:]:
#             root_logger.removeHandler(handler)
        
#         cls._initialized = True
    
#     @classmethod
#     def get_logger(cls, name: str) -> logging.Logger:
#         """Ottieni logger standardizzato"""
#         cls.initialize()
        
#         if name not in cls._loggers:
#             cls._loggers[name] = cls._create_logger(name)
#         return cls._loggers[name]
    
#     @classmethod
#     def _create_logger(cls, name: str) -> logging.Logger:
#         """Crea nuovo logger"""
#         logger = logging.getLogger(name)
        
#         if logger.handlers:
#             return logger
            
#         logger.setLevel(logging.INFO)
        
#         # Formatter comune
#         # formatter = logging.Formatter(
#         #     '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         #     datefmt='%Y-%m-%d %H:%M:%S'
#         # )
#         formatter = logging.Formatter(
#             '%(asctime)s - %(levelname)s - [%(name)s] %(filename)s:%(lineno)d (%(funcName)s) - %(message)s'
#         )
        
#         # Console handler
#         console_handler = logging.StreamHandler(sys.stdout)
#         console_handler.setFormatter(formatter)
#         console_handler.setLevel(logging.INFO)
#         logger.addHandler(console_handler)
        
#         # File handler con rotazione
#         log_file = Path('logs') / 'app.log'
#         file_handler = RotatingFileHandler(
#             log_file,
#             maxBytes=10*1024*1024,  # 10MB
#             backupCount=5,
#             encoding='utf-8'
#         )
#         file_handler.setFormatter(formatter)
#         file_handler.setLevel(logging.INFO)
#         logger.addHandler(file_handler)
        
#         return logger

# def get_logger(name: str = None) -> logging.Logger:
#     """Ottieni logger per modulo corrente"""
#     if name is None:
#         import inspect
#         frame = inspect.currentframe().f_back
#         name = frame.f_globals.get('__name__', 'unknown')
#     return ProjectLogger.get_logger(name)

# def log_success(message: str, logger_name: str = None):
#     """Log messaggio successo"""
#     logger = get_logger(__name__)
#     logger.info(f"\033[92m[SUCCESS]\033[0m {message}", stacklevel=2)

# def log_error(message: str, logger_name: str = None):
#     """Log messaggio errore"""
#     logger = get_logger(__name__)
#     logger.error(f"\033[91m[ERRORE]\033[0m {message}", stacklevel=2)

# def log_warning(message: str, logger_name: str = None):
#     """Log messaggio warning"""
#     logger = get_logger(__name__)
#     logger.warning(f"\033[93m[WARING]\033[0m {message}", stacklevel=2)

# def log_info(message: str, logger_name: str = None):
#     """Log messaggio info"""
#     logger = get_logger(__name__)
#     logger.info(f"\033[94m[INFO]\033[0m {message}", stacklevel=2)

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
