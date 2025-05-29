#!/usr/bin/env python3
"""
Exception Handler - Gestione centralizzata delle eccezioni
"""

import traceback
from typing import Optional, Dict, Any
from functools import wraps
from datetime import datetime
from logger_config import get_logger

class ProjectException(Exception):
    """Eccezione base del progetto"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 'UNKNOWN_ERROR'
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

class FTPException(ProjectException):
    """Eccezioni FTP specifiche"""
    pass

class CDRException(ProjectException):
    """Eccezioni CDR specifiche"""
    pass

class ConfigException(ProjectException):
    """Eccezioni configurazione"""
    pass

class OdooException(ProjectException):
    """Eccezioni Odoo"""
    pass

class ExceptionHandler:
    """Gestore centralizzato delle eccezioni"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def handle_exception(self, exc: Exception, context: str = None) -> Dict[str, Any]:
        """Gestisce eccezione e restituisce response standardizzata"""
        
        # Log dettagliato dell'errore
        self.logger.error(f"Eccezione in {context or 'unknown'}: {exc}")
        self.logger.debug(f"Traceback: {traceback.format_exc()}")
        
        # Determina tipo di errore e response
        if isinstance(exc, ProjectException):
            return {
                'success': False,
                'error_code': exc.error_code,
                'message': exc.message,
                'details': exc.details,
                'timestamp': exc.timestamp
            }
        elif isinstance(exc, (ConnectionError, TimeoutError)):
            return {
                'success': False,
                'error_code': 'CONNECTION_ERROR',
                'message': 'Errore di connessione',
                'details': {'original_error': str(exc)},
                'timestamp': datetime.now().isoformat()
            }
        elif isinstance(exc, (ValueError, TypeError)):
            return {
                'success': False,
                'error_code': 'VALIDATION_ERROR', 
                'message': 'Errore validazione dati',
                'details': {'original_error': str(exc)},
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Errore generico - non esporre dettagli interni
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': 'Errore interno del sistema',
                'details': {},
                'timestamp': datetime.now().isoformat()
            }

def handle_exceptions(context: str = None):
    """Decorator per gestione automatica eccezioni"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = ExceptionHandler()
                return handler.handle_exception(e, context or func.__name__)
        return wrapper
    return decorator

# Response helper per Flask
class APIResponse:
    """Standardizza response API"""
    
    @staticmethod
    def success(data: Any = None, message: str = None) -> Dict[str, Any]:
        """Response di successo"""
        response = {'success': True}
        if message:
            response['message'] = message
        if data is not None:
            response['data'] = data
        response['timestamp'] = datetime.now().isoformat()
        return response
    
    @staticmethod
    def error(message: str, error_code: str = None, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Response di errore"""
        return {
            'success': False,
            'message': message,
            'error_code': error_code or 'UNKNOWN_ERROR',
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
