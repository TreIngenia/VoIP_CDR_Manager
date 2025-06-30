"""
Odoo Exceptions v18.2+
Sistema di eccezioni centralizzato per Odoo
"""

class OdooException(Exception):
    """Eccezione base per errori Odoo"""
    def __init__(self, message: str, error_code: str = 'ODOO_ERROR'):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

class OdooConnectionError(OdooException):
    """Errore di connessione ad Odoo"""
    def __init__(self, message: str):
        super().__init__(message, 'CONNECTION_ERROR')

class OdooAuthError(OdooException):
    """Errore di autenticazione Odoo"""
    def __init__(self, message: str):
        super().__init__(message, 'AUTH_ERROR')

class OdooDataError(OdooException):
    """Errore nei dati Odoo"""
    def __init__(self, message: str):
        super().__init__(message, 'DATA_ERROR')

class OdooExecutionError(OdooException):
    """Errore nell'esecuzione di metodi Odoo"""
    def __init__(self, message: str):
        super().__init__(message, 'EXECUTION_ERROR')

class OdooValidationError(OdooException):
    """Errore di validazione dati"""
    def __init__(self, message: str):
        super().__init__(message, 'VALIDATION_ERROR')