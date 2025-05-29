#!/usr/bin/env python3
"""
Logger Configuration - Sistema di logging standardizzato
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

class ProjectLogger:
    """Logger standardizzato per tutto il progetto"""
    
    _loggers = {}
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Inizializza il sistema di logging"""
        if cls._initialized:
            return
            
        # Crea directory logs
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Configura logging root
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Rimuovi handler esistenti
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Ottieni logger standardizzato"""
        cls.initialize()
        
        if name not in cls._loggers:
            cls._loggers[name] = cls._create_logger(name)
        return cls._loggers[name]
    
    @classmethod
    def _create_logger(cls, name: str) -> logging.Logger:
        """Crea nuovo logger"""
        logger = logging.getLogger(name)
        
        if logger.handlers:
            return logger
            
        logger.setLevel(logging.INFO)
        
        # Formatter comune
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        
        # File handler con rotazione
        log_file = Path('logs') / 'app.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        
        return logger

def get_logger(name: str = None) -> logging.Logger:
    """Ottieni logger per modulo corrente"""
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    return ProjectLogger.get_logger(name)

def log_success(message: str, logger_name: str = None):
    """Log messaggio successo"""
    logger = get_logger(logger_name)
    logger.info(f"✅ {message}")

def log_error(message: str, logger_name: str = None):
    """Log messaggio errore"""
    logger = get_logger(logger_name)
    logger.error(f"❌ {message}")

def log_warning(message: str, logger_name: str = None):
    """Log messaggio warning"""
    logger = get_logger(logger_name)
    logger.warning(f"⚠️ {message}")

def log_info(message: str, logger_name: str = None):
    """Log messaggio info"""
    logger = get_logger(logger_name)
    logger.info(f"ℹ️ {message}")
