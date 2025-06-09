"""
FTP Scheduler App - Package Initialization
Versione modulare completa e funzionante
"""

__version__ = "2.0.0"
__author__ = "FTP Scheduler Team"
__description__ = "Applicazione per download automatico e schedulato da server FTP con conversione JSON"

# Import principali per facilitare l'uso
from .config import SecureConfig, save_config_to_env, load_config_from_env_local
from .ftp_processor import FTPProcessor
from .scheduler import SchedulerManager
from .utils import (
    find_free_port, 
    ensure_directory_exists, 
    clean_filename, 
    format_datetime,
    ProgressTracker,
    retry_on_failure
)

__all__ = [
    'SecureConfig',
    'FTPProcessor', 
    'SchedulerManager',
    'save_config_to_env',
    'load_config_from_env_local',
    'find_free_port',
    'ensure_directory_exists',
    'clean_filename',
    'format_datetime',
    'ProgressTracker',
    'retry_on_failure',
]

def get_version():
    """Restituisce la versione del package"""
    return __version__

def get_info():
    """Restituisce informazioni sul package"""
    return {
        'name': 'FTP Scheduler App',
        'version': __version__,
        'author': __author__,
        'description': __description__
    }