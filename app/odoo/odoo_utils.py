"""
Odoo Utils v18.2+ - VERSIONE MIGLIORATA
Utilità e helper functions per l'integrazione Odoo con gestione robusta degli errori
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
# from flask import jsonify
import json
import time
import functools
import threading

try:
    from logger_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

def retry_on_connection_error(max_retries=3, delay=0.5, backoff=2):
    """Decorator per retry automatico su errori di connessione"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Lista degli errori che giustificano un retry
                    retryable_errors = [
                        'request-sent', 'cannotsendrequest', 'badstatusline',
                        'connectionreseterror', 'connection refused',
                        'connection aborted', 'remotedisconnected', 'timeout'
                    ]
                    
                    is_retryable = any(error in error_str for error in retryable_errors)
                    
                    if is_retryable and retries < max_retries - 1:
                        logger.warning(f"Errore connessione (retry {retries + 1}/{max_retries}): {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                        retries += 1
                        continue
                    else:
                        # Re-raise l'eccezione originale
                        raise
            
            return None  # Non dovrebbe mai arrivare qui
        return wrapper
    return decorator

def format_date(date_string: Optional[str]) -> Optional[Dict]:
    """Formatta date per JSON in modo consistente"""
    if date_string:
        try:
            if isinstance(date_string, str):
                date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                date_obj = date_string
                
            return {
                "iso": date_obj.isoformat(),
                "formatted": date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                "date_only": date_obj.strftime('%Y-%m-%d'),
                "italian": date_obj.strftime('%d/%m/%Y')
            }
        except Exception as e:
            logger.warning(f"Errore formattazione data {date_string}: {e}")
            return {"raw": str(date_string), "error": str(e)}
    return None

def calculate_due_date(invoice_date: str, days: int) -> str:
    """Calcola data di scadenza aggiungendo giorni"""
    try:
        if isinstance(invoice_date, str):
            date_obj = datetime.strptime(invoice_date, '%Y-%m-%d')
        else:
            date_obj = invoice_date
            
        due_date = date_obj + timedelta(days=days)
        return due_date.strftime('%Y-%m-%d')
    except Exception as e:
        logger.error(f"Errore calcolo data scadenza: {e}")
        return invoice_date

def build_select2_response(data: List[Dict], id_field: str = 'id', text_field: str = 'name') -> Dict:
    """Costruisce risposta per Select2"""
    try:
        results = []
        for item in data:
            if isinstance(item, dict):
                item_id = item.get(id_field)
                item_text = item.get(text_field, item.get('display_name', 'N/A'))
                
                if item_id is not None:
                    results.append({
                        'id': item_id,
                        'text': str(item_text)
                    })
        
        return {
            'success': True,
            'results': results,
            'total': len(results)
        }
    except Exception as e:
        logger.error(f"Errore build_select2_response: {e}")
        return {
            'success': False,
            'results': [],
            'total': 0,
            'error': str(e)
        }

def safe_get_field(data: Dict, field: str, default: Any = None) -> Any:
    """Ottiene un campo da un dict in modo sicuro, gestendo i formati Odoo"""
    try:
        value = data.get(field, default)
        
        # Gestisce i campi Many2one di Odoo [id, name]
        if isinstance(value, list) and len(value) == 2:
            return {
                'id': value[0],
                'name': value[1]
            }
        
        return value
    except Exception:
        return default

def process_odoo_relation_field(field_value: Any) -> Dict[str, Any]:
    """Processa i campi relazionali di Odoo (Many2one, etc.)"""
    try:
        if isinstance(field_value, list) and len(field_value) >= 2:
            return {
                'id': field_value[0],
                'name': field_value[1],
                'display_name': field_value[1]
            }
        elif isinstance(field_value, (int, float)):
            return {
                'id': field_value,
                'name': 'N/A',
                'display_name': 'N/A'
            }
        else:
            return {
                'id': None,
                'name': '',
                'display_name': ''
            }
    except Exception:
        return {
            'id': None,
            'name': '',
            'display_name': ''
        }

def build_api_response(success: bool, data: Any = None, message: str = "", 
                      error_code: str = "", status_code: int = 200) -> tuple:
    """Costruisce risposta API standardizzata con gestione migliorata degli errori"""
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    
    if success:
        if data is not None:
            # Se data è un dizionario, lo merge con response
            if isinstance(data, dict):
                response.update(data)
            else:
                response['data'] = data
        if message:
            response['message'] = message
    else:
        # Gestione degli errori migliorata
        error_info = {
            'message': message or 'Errore sconosciuto',
            'code': error_code or 'UNKNOWN_ERROR'
        }
        
        # Aggiungi suggerimenti per errori comuni
        if 'request-sent' in message.lower() or 'cannotsendrequest' in message.lower():
            error_info['suggestion'] = 'Errore di connessione. Riprova tra qualche secondo.'
            error_info['retry_recommended'] = True
        elif 'connection' in message.lower():
            error_info['suggestion'] = 'Problemi di connessione con il server Odoo.'
            error_info['retry_recommended'] = True
        elif 'auth' in error_code.lower():
            error_info['suggestion'] = 'Verifica le credenziali di accesso.'
            error_info['retry_recommended'] = False
        
        response['error'] = error_info
        
        if status_code == 200:
            status_code = 400
    # return jsonify(response), status_code
    # return json.dumps(response), status_code
    return response, status_code

def validate_pagination_params(page: int, per_page: int, max_per_page: int = 100) -> Dict:
    """Valida e normalizza parametri di paginazione"""
    try:
        page = max(1, int(page))
        per_page = max(1, min(int(per_page), max_per_page))
        offset = (page - 1) * per_page
        
        return {
            'page': page,
            'per_page': per_page,
            'offset': offset,
            'valid': True
        }
    except (ValueError, TypeError):
        return {
            'page': 1,
            'per_page': 20,
            'offset': 0,
            'valid': False,
            'error': 'Parametri di paginazione non validi'
        }

def calculate_pagination_info(page: int, per_page: int, total_count: int) -> Dict:
    """Calcola informazioni di paginazione"""
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        'current_page': page,
        'per_page': per_page,
        'total_count': total_count,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_prev': has_prev,
        'start_item': ((page - 1) * per_page) + 1 if total_count > 0 else 0,
        'end_item': min(page * per_page, total_count)
    }

def clean_partner_data(partner: Dict) -> Dict:
    """Pulisce e normalizza i dati di un partner"""
    try:
        return {
            'id': partner.get('id'),
            'name': partner.get('name', '').strip(),
            'display_name': partner.get('display_name', '').strip(),
            'email': partner.get('email', '').strip().lower() if partner.get('email') else '',
            'phone': partner.get('phone', '').strip(),
            'mobile': partner.get('mobile', '').strip(),
            'vat': partner.get('vat', '').strip(),
            'is_company': bool(partner.get('is_company', False)),
            'customer_rank': int(partner.get('customer_rank', 0)),
            'supplier_rank': int(partner.get('supplier_rank', 0)),
            'active': bool(partner.get('active', True))
        }
    except Exception as e:
        logger.error(f"Errore pulizia dati partner: {e}")
        return partner

def format_currency(amount: float, currency: str = 'EUR') -> str:
    """Formatta importi con valuta"""
    try:
        if currency.upper() == 'EUR':
            return f"€ {amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            return f"{amount:,.2f} {currency}"
    except Exception:
        return f"{amount} {currency}"

def build_address_string(partner: Dict) -> str:
    """Costruisce stringa indirizzo completo"""
    try:
        address_parts = []
        
        # Via
        street = partner.get('street', '').strip()
        if street:
            address_parts.append(street)
        
        # Via 2
        street2 = partner.get('street2', '').strip()
        if street2:
            address_parts.append(street2)
        
        # Città, CAP
        city = partner.get('city', '').strip()
        zip_code = partner.get('zip', '').strip()
        
        if city and zip_code:
            address_parts.append(f"{zip_code} {city}")
        elif city:
            address_parts.append(city)
        elif zip_code:
            address_parts.append(zip_code)
        
        # Provincia/Stato
        state_name = ''
        if partner.get('state_id'):
            state_info = process_odoo_relation_field(partner['state_id'])
            state_name = state_info.get('name', '')
        
        if state_name:
            address_parts.append(state_name)
        
        # Paese
        country_name = ''
        if partner.get('country_id'):
            country_info = process_odoo_relation_field(partner['country_id'])
            country_name = country_info.get('name', '')
        
        if country_name:
            address_parts.append(country_name)
        
        return ', '.join(address_parts)
        
    except Exception as e:
        logger.error(f"Errore costruzione indirizzo: {e}")
        return ''

def extract_error_message(exception: Exception) -> str:
    """Estrae messaggio di errore pulito da eccezioni"""
    try:
        error_msg = str(exception)
        
        # Rimuove prefissi comuni di Odoo
        prefixes_to_remove = [
            'XMLRPC fault: ',
            'Fault ',
            'Error: ',
            'Exception: '
        ]
        
        for prefix in prefixes_to_remove:
            if error_msg.startswith(prefix):
                error_msg = error_msg[len(prefix):]
        
        # Limita lunghezza
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        
        return error_msg.strip()
        
    except Exception:
        return "Errore sconosciuto"

def log_performance(func_name: str, start_time: datetime, record_count: int = 0):
    """Log performance di operazioni"""
    try:
        duration = datetime.now() - start_time
        duration_ms = duration.total_seconds() * 1000
        
        if record_count > 0:
            per_record = duration_ms / record_count
            logger.info(f"⚡ {func_name}: {duration_ms:.2f}ms ({record_count} record, {per_record:.2f}ms/record)")
        else:
            logger.info(f"⚡ {func_name}: {duration_ms:.2f}ms")
            
    except Exception:
        pass

class PerformanceTimer:
    """Context manager per misurare performance con gestione errori migliorata"""
    
    def __init__(self, operation_name: str, record_count: int = 0):
        self.operation_name = operation_name
        self.record_count = record_count
        self.start_time = None
        self.error_occurred = False
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            if exc_type is not None:
                self.error_occurred = True
                # Log dell'errore con timing
                duration = datetime.now() - self.start_time
                duration_ms = duration.total_seconds() * 1000
                logger.error(f"❌ {self.operation_name}: ERRORE dopo {duration_ms:.2f}ms - {exc_val}")
            else:
                log_performance(self.operation_name, self.start_time, self.record_count)

class RateLimiter:
    """Semplice rate limiter per controllare la frequenza delle richieste"""
    
    def __init__(self, min_interval: float = 0.1):
        self.min_interval = min_interval
        self.last_call = 0
        self._lock = threading.RLock() if 'threading' in globals() else None
    
    def wait_if_needed(self):
        """Attende se necessario per rispettare il rate limit"""
        if self._lock:
            with self._lock:
                self._wait_internal()
        else:
            self._wait_internal()
    
    def _wait_internal(self):
        """Implementazione interna del wait"""
        current_time = time.time()
        time_since_last = current_time - self.last_call
        
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_call = time.time()

# Rate limiter globale per operazioni Odoo
odoo_rate_limiter = RateLimiter(0.1)  # 100ms tra richieste

def with_rate_limit(func):
    """Decorator per applicare rate limiting"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        odoo_rate_limiter.wait_if_needed()
        return func(*args, **kwargs)
    return wrapper