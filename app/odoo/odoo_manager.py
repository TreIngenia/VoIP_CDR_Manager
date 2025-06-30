"""
Odoo Manager v18.2+
Manager principale che coordina tutti i componenti
"""
from typing import Dict, Any, Optional

from .odoo_config import OdooConfig
from .odoo_client import OdooClient
from .odoo_partners import OdooPartnerManager
from .odoo_products import OdooProductManager
from .odoo_invoices import OdooInvoiceManager
from .odoo_subscriptions import OdooSubscriptionManager
from .odoo_exceptions import OdooConnectionError

try:
    from logger_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

class OdooManager:
    """Manager principale per tutte le operazioni Odoo"""
    
    def __init__(self, secure_config):
        self.logger = get_logger(__name__)
        
        # Inizializza configurazione e client
        self.config = OdooConfig.from_secure_config(secure_config)
        self.client = OdooClient(self.config)
        
        # Inizializza manager specializzati
        self.partners = OdooPartnerManager(self.client)
        self.products = OdooProductManager(self.client)
        self.invoices = OdooInvoiceManager(self.client)
        self.subscriptions = OdooSubscriptionManager(self.client)
        
        # Flag connessione
        self._connected = False
    
    def connect(self) -> bool:
        """Connette a Odoo e verifica funzionalità"""
        try:
            if self.client.connect():
                self._connected = True
                self.logger.info("🚀 OdooManager connesso e pronto")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Errore connessione OdooManager: {e}")
            raise OdooConnectionError(f"Impossibile connettere OdooManager: {e}")
    
    def ensure_connected(self):
        """Assicura che la connessione sia attiva"""
        if not self._connected:
            self.connect()
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connessione completo"""
        try:
            self.ensure_connected()
            return self.client.test_connection()
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'manager': 'OdooManager'
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Informazioni sistema complete"""
        try:
            self.ensure_connected()
            
            test_result = self.test_connection()
            company_info = self.client.get_company_info()
            partners_summary = self.partners.get_partners_summary()
            
            return {
                'success': True,
                'connection': test_result,
                'company': company_info,
                'partners_summary': partners_summary,
                'odoo_url': self.config.url,
                'database': self.config.database,
                'manager_version': '18.2+',
                'components': {
                    'partners': True,
                    'products': True,
                    'invoices': True,
                    'subscriptions': True
                }
            }
            
        except Exception as e:
            self.logger.error(f"Errore get_system_info: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def get_odoo_manager(secure_config) -> OdooManager:
    """Factory function per creare OdooManager"""
    return OdooManager(secure_config)

# Compatibilità con codice esistente
def get_odoo_client(secure_config) -> OdooClient:
    """Factory function per compatibilità - restituisce solo il client"""
    config = OdooConfig.from_secure_config(secure_config)
    return OdooClient(config)

def create_odoo_client(secure_config) -> OdooClient:
    """Factory function alternativa per compatibilità"""
    return get_odoo_client(secure_config)