"""
Odoo Configuration Manager v18.2+
Gestione centralizzata della configurazione Odoo
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    from logger_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

@dataclass
class OdooConfig:
    """Classe di configurazione Odoo centralizzata"""
    url: str
    database: str
    username: str
    api_key: str
    
    def __post_init__(self):
        """Validazione configurazione dopo inizializzazione"""
        self.validate()
    
    @classmethod
    def from_secure_config(cls, secure_config) -> 'OdooConfig':
        """Crea configurazione da secure_config"""
        try:
            config = secure_config.get_config()
            
            return cls(
                url=config.get('ODOO_URL', ''),
                database=config.get('ODOO_DB', ''),
                username=config.get('ODOO_USERNAME', ''),
                api_key=config.get('ODOO_API_KEY', '')
            )
            
        except Exception as e:
            logger.error(f"Errore creazione configurazione da secure_config: {e}")
            raise ConfigurationError(f"Impossibile caricare configurazione: {e}")
    
    def validate(self) -> bool:
        """Valida la configurazione"""
        required_fields = {
            'url': self.url,
            'database': self.database,
            'username': self.username,
            'api_key': self.api_key
        }
        
        missing = [field for field, value in required_fields.items() if not value]
        
        if missing:
            raise ConfigurationError(f"Configurazione Odoo incompleta: {missing}")
        
        if not self.url.startswith(('http://', 'https://')):
            raise ConfigurationError("URL Odoo deve iniziare con http:// o https://")
        
        logger.info("Configurazione Odoo validata con successo")
        return True
    
    def to_dict(self) -> Dict[str, str]:
        """Converte in dizionario per compatibilità"""
        return {
            'ODOO_URL': self.url,
            'ODOO_DB': self.database,
            'ODOO_USERNAME': self.username,
            'ODOO_API_KEY': self.api_key
        }

class ConfigurationError(Exception):
    """Eccezione per errori di configurazione"""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message