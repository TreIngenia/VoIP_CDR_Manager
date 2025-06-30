"""
Odoo Client Core v18.2+ - VERSIONE MIGLIORATA
Client principale consolidato per Odoo SaaS~18.2+ con gestione robusta delle connessioni
"""
import xmlrpc.client
from datetime import datetime
from typing import Dict, Any, Optional, List
import time
import threading
from contextlib import contextmanager

from .odoo_config import OdooConfig
from .odoo_exceptions import (
    OdooConnectionError, OdooAuthError, 
    OdooExecutionError, OdooDataError
)

try:
    from logger_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

class OdooClient:
    """Client Odoo consolidato per versione 18.2+ con gestione robusta delle connessioni"""
    
    def __init__(self, config: OdooConfig):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Connessione
        self.uid = None
        self.models = None
        self.common = None
        self.version_info = None
        
        # Cache per performance
        self._field_cache = {}
        self._model_cache = {}
        
        # Gestione connessioni multiple e thread safety
        self._connection_lock = threading.RLock()
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms tra richieste
        self._max_retries = 3
        self._retry_delay = 0.5  # 500ms
    
    @contextmanager
    def _rate_limit(self):
        """Context manager per limitare la frequenza delle richieste"""
        with self._connection_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self._min_request_interval:
                sleep_time = self._min_request_interval - time_since_last
                time.sleep(sleep_time)
            
            self._last_request_time = time.time()
            yield
    
    def _create_fresh_connection(self):
        """Crea una nuova connessione XML-RPC"""
        try:
            # Inizializza connessione common
            self.common = xmlrpc.client.ServerProxy(
                f"{self.config.url}/xmlrpc/2/common",
                allow_none=True,
                use_datetime=True
            )
            
            # Inizializza models
            self.models = xmlrpc.client.ServerProxy(
                f"{self.config.url}/xmlrpc/2/object",
                allow_none=True,
                use_datetime=True
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore creazione connessione: {e}")
            return False
    
    def connect(self) -> bool:
        """Connessione ottimizzata per Odoo 18.2+ con retry logic"""
        with self._connection_lock:
            try:
                # Crea connessione fresh
                if not self._create_fresh_connection():
                    raise OdooConnectionError("Impossibile creare connessione XML-RPC")
                
                # Verifica versione server
                self.version_info = self.common.version()
                server_version = self.version_info.get('server_version', '')
                self.logger.info(f"Connessione a Odoo {server_version}")
                
                # Verifica compatibilità
                if not self._check_version_compatibility(server_version):
                    self.logger.warning(f"Versione {server_version} potrebbe richiedere adattamenti")
                
                # Autenticazione
                self.uid = self.common.authenticate(
                    self.config.database,
                    self.config.username,
                    self.config.api_key,
                    {}
                )
                
                if not self.uid:
                    raise OdooAuthError("Autenticazione Odoo fallita - controlla username e API key")
                
                self.logger.info(f"Connesso ad Odoo 18.2+ con UID: {self.uid}")
                return True
                
            except Exception as e:
                error_msg = f"Errore connessione Odoo: {e}"
                self.logger.error(error_msg)
                raise OdooConnectionError(error_msg)
    
    def _check_version_compatibility(self, version: str) -> bool:
        """Verifica compatibilità specifica per 18.2+"""
        if version.startswith('18.'):
            try:
                major, minor = version.split('.')[:2]
                minor_num = float(minor)
                if minor_num >= 2:
                    self.logger.info("Versione 18.2+ rilevata - compatibilità completa")
                    return True
                else:
                    self.logger.warning(f"Versione 18.{minor} - alcune funzionalità potrebbero differire")
                    return True
            except:
                return True
        elif version.startswith(('17.', '16.')):
            self.logger.warning(f"Versione {version} - compatibilità parziale")
            return True
        else:
            self.logger.warning(f"Versione {version} non testata")
            return False
    
    def _is_connection_error(self, exception_str: str) -> bool:
        """Identifica errori di connessione che richiedono riconnessione"""
        connection_errors = [
            'CannotSendRequest',
            'Request-sent',
            'BadStatusLine',
            'ConnectionResetError',
            'Connection refused',
            'Connection aborted',
            'RemoteDisconnected',
            'timeout',
            'Connection broken'
        ]
        
        return any(error in str(exception_str) for error in connection_errors)
    
    def _reset_connection(self):
        """Reset completo della connessione"""
        self.uid = None
        self.models = None
        self.common = None
        self.logger.info("Connessione resettata")
    
    def execute(self, model: str, method: str, *args, **kwargs):
        """Wrapper ottimizzato per execute_kw con gestione errori robusta e retry logic"""
        for attempt in range(self._max_retries):
            try:
                with self._rate_limit():
                    # Verifica connessione
                    if not self.uid or not self.models:
                        if not self.connect():
                            raise OdooConnectionError("Impossibile connettersi ad Odoo")
                    
                    # Context ottimizzato per 18.2+
                    if 'context' not in kwargs:
                        kwargs['context'] = self._get_default_context()
                    
                    # Gestione timeout per operazioni lunghe
                    if method in ['create', 'write', 'unlink'] and 'timeout' not in kwargs:
                        kwargs['timeout'] = 300
                    
                    # Esegui richiesta
                    if kwargs:
                        result = self.models.execute_kw(
                            self.config.database, 
                            self.uid, 
                            self.config.api_key,
                            model, 
                            method, 
                            list(args), 
                            kwargs
                        )
                    else:
                        result = self.models.execute_kw(
                            self.config.database, 
                            self.uid, 
                            self.config.api_key,
                            model, 
                            method, 
                            list(args)
                        )
                    
                    return result
                    
            except Exception as e:
                error_str = str(e)
                
                # Se è un errore di connessione e non è l'ultimo tentativo
                if self._is_connection_error(error_str) and attempt < self._max_retries - 1:
                    self.logger.warning(f"Errore connessione (tentativo {attempt + 1}/{self._max_retries}): {error_str}")
                    
                    # Reset connessione
                    with self._connection_lock:
                        self._reset_connection()
                    
                    # Attendi prima del retry
                    time.sleep(self._retry_delay * (attempt + 1))
                    continue
                
                # Se non è un errore di connessione o è l'ultimo tentativo
                error_msg = f"Errore esecuzione {model}.{method}: {e}"
                self.logger.error(error_msg)
                raise OdooExecutionError(error_msg)
        
        # Se arriviamo qui, tutti i tentativi sono falliti
        raise OdooExecutionError(f"Tutti i {self._max_retries} tentativi falliti per {model}.{method}")
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Context ottimizzato per Odoo 18.2+"""
        return {
            'lang': 'it_IT',
            'tz': 'Europe/Rome',
            'active_test': True,
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'tracking_disable': True,
            'mail_notify_force_send': False,
        }
    
    def get_model_fields(self, model: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Ottiene definizioni campi per un modello con caching"""
        if model in self._field_cache and not force_refresh:
            return self._field_cache[model]
        
        try:
            fields_info = self.execute(model, 'fields_get', [])
            self._field_cache[model] = fields_info
            
            self.logger.debug(f"Campi per {model}: {len(fields_info)} disponibili")
            return fields_info
            
        except Exception as e:
            self.logger.error(f"Errore recupero campi per {model}: {e}")
            return {}
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connessione completo per 18.2+"""
        try:
            if not self.connect():
                return {'success': False, 'error': 'Connessione fallita'}
            
            # Test dati base
            user_data = self.execute('res.users', 'read', [self.uid], fields=['name', 'login'])
            company_info = self.get_company_info()
            
            # Conteggi
            partners_count = self.execute('res.partner', 'search_count', [('customer_rank', '>', 0)])
            products_count = self.execute('product.product', 'search_count', [('sale_ok', '=', True)])
            
            # Test compatibilità campi
            partner_fields = self.get_model_fields('res.partner')
            move_fields = self.get_model_fields('account.move')
            
            return {
                'success': True,
                'connection_info': {
                    'server_version': self.version_info.get('server_version'),
                    'protocol_version': self.version_info.get('protocol_version'),
                    'user_name': user_data[0]['name'],
                    'user_login': user_data[0]['login'],
                    'company_name': company_info['name'],
                    'database': self.config.database,
                    'uid': self.uid
                },
                'stats': {
                    'customers_count': partners_count,
                    'products_count': products_count
                },
                'compatibility': {
                    'mobile_field_available': 'mobile' in partner_fields,
                    'invoice_payment_term_id_available': 'invoice_payment_term_id' in move_fields,
                    'analytic_distribution_available': 'analytic_distribution' in self.get_model_fields('account.move.line'),
                    'partner_fields_count': len(partner_fields),
                    'move_fields_count': len(move_fields)
                },
                'performance': {
                    'min_request_interval': self._min_request_interval,
                    'max_retries': self._max_retries,
                    'retry_delay': self._retry_delay
                },
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def get_company_info(self) -> Dict[str, Any]:
        """Informazioni azienda per 18.2+"""
        try:
            user_data = self.execute('res.users', 'read', [self.uid], fields=['company_id'])
            company_id = user_data[0]['company_id'][0]
            
            company_data = self.execute(
                'res.company',
                'read',
                [company_id],
                fields=[
                    'name', 'email', 'phone', 'website', 'vat',
                    'street', 'street2', 'city', 'zip', 'state_id', 'country_id',
                    'currency_id', 'logo'
                ]
            )[0]
            
            return {
                'id': company_id,
                'name': company_data.get('name'),
                'email': company_data.get('email'),
                'phone': company_data.get('phone'),
                'website': company_data.get('website'),
                'vat': company_data.get('vat'),
                'address': {
                    'street': company_data.get('street', ''),
                    'street2': company_data.get('street2', ''),
                    'city': company_data.get('city', ''),
                    'zip': company_data.get('zip', ''),
                    'state': company_data.get('state_id')[1] if company_data.get('state_id') else '',
                    'country': company_data.get('country_id')[1] if company_data.get('country_id') else '',
                },
                'currency': company_data.get('currency_id')[1] if company_data.get('currency_id') else 'EUR',
                'has_logo': bool(company_data.get('logo'))
            }
            
        except Exception as e:
            self.logger.error(f"Errore recupero info azienda: {e}")
            raise OdooDataError(f"Errore recupero info azienda: {e}")

def create_odoo_client(secure_config) -> OdooClient:
    """Factory function per creare client Odoo da secure_config"""
    config = OdooConfig.from_secure_config(secure_config)
    return OdooClient(config)