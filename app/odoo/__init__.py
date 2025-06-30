"""
Odoo Integration Package v18.2+
Sistema modulare per l'integrazione con Odoo SaaS 18.2+
VERSIONE PULITA - SENZA COMPATIBILITÀ LEGACY
"""

# Import delle classi principali per export package
from .odoo_config import OdooConfig, ConfigurationError
from .odoo_client import OdooClient
from .odoo_manager import OdooManager, get_odoo_manager, get_odoo_client, create_odoo_client
from .odoo_exceptions import (
    OdooException, OdooConnectionError, OdooAuthError, 
    OdooDataError, OdooExecutionError, OdooValidationError
)

# Import dei manager specializzati
from .odoo_partners import OdooPartnerManager
from .odoo_products import OdooProductManager
from .odoo_invoices import OdooInvoiceManager, InvoiceItem, InvoiceData
from .odoo_subscriptions import OdooSubscriptionManager

# Import delle utilità
from .odoo_utils import (
    format_date, calculate_due_date, build_select2_response,
    build_api_response, validate_pagination_params, 
    calculate_pagination_info, PerformanceTimer
)

# Versione del package
__version__ = "2.0.0"
__odoo_version__ = "18.2+"

# Informazioni package
__package_info__ = {
    "name": "odoo_integration",
    "version": __version__,
    "odoo_compatibility": __odoo_version__,
    "structure": "clean_modular_package",
    "legacy_support": False,
    "components": {
        "config": "Gestione configurazione centralizzata",
        "client": "Client core per connessione Odoo",
        "managers": {
            "partners": "Gestione clienti e fornitori",
            "products": "Gestione prodotti e termini pagamento",
            "invoices": "Sistema fatturazione completo",
            "subscriptions": "Gestione abbonamenti e ordini ricorrenti"
        },
        "utils": "Utilità e helper functions",
        "exceptions": "Sistema eccezioni standardizzato"
    },
    "features": [
        "Architettura modulare",
        "Performance monitoring",
        "Caching intelligente",
        "Gestione errori avanzata",
        "Logging strutturato",
        "Validazione dati",
        "API standardizzate",
        "Zero legacy dependencies"
    ]
}

def get_package_info():
    """Restituisce informazioni sul package"""
    return __package_info__

def create_full_manager(secure_config):
    """Crea manager completo con tutti i componenti"""
    return get_odoo_manager(secure_config)

def get_system_info():
    """Restituisce informazioni sistema (alias per compatibilità)"""
    return __package_info__

# Export di tutte le classi e funzioni principali
__all__ = [
    # Configurazione
    'OdooConfig', 'ConfigurationError',
    
    # Client e Manager
    'OdooClient', 'OdooManager', 
    'create_odoo_client', 'get_odoo_client', 'get_odoo_manager',
    
    # Manager specializzati
    'OdooPartnerManager', 'OdooProductManager', 
    'OdooInvoiceManager', 'OdooSubscriptionManager',
    
    # Strutture dati
    'InvoiceItem', 'InvoiceData',
    
    # Eccezioni
    'OdooException', 'OdooConnectionError', 'OdooAuthError',
    'OdooDataError', 'OdooExecutionError', 'OdooValidationError',
    
    # Utilità
    'format_date', 'calculate_due_date', 'build_select2_response',
    'build_api_response', 'validate_pagination_params',
    'calculate_pagination_info', 'PerformanceTimer',
    
    # Funzioni helper
    'get_package_info', 'create_full_manager', 'get_system_info'
]