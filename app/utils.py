"""
Utilità e funzioni helper per FTP Scheduler App
"""

import os
import sys
import socket
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
import requests

logger = logging.getLogger(__name__)

def validate_port(port, default_port=5000):
    """Valida e normalizza il numero di porta"""
    try:
        port = int(port)
        if 1 <= port <= 65535:
            return port
        else:
            logger.warning(f"Porta {port} non valida, uso porta default {default_port}")
            return default_port
    except (ValueError, TypeError):
        logger.warning(f"Porta non numerica, uso porta default {default_port}")
        return default_port

def is_port_free(host, port):
    """Verifica se una porta è libera"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False

def find_free_port(start_port=5000, max_attempts=10):
    """Trova una porta libera a partire dalla porta specificata"""
    for port in range(start_port, start_port + max_attempts):
        if is_port_free('127.0.0.1', port):
            return port
    
    # Se non trova nessuna porta libera, usa la porta originale
    logger.warning(f"Nessuna porta libera trovata tra {start_port}-{start_port + max_attempts}")
    return start_port

def ensure_directory_exists(directory_path):
    """Assicura che una directory esista, creandola se necessario"""
    try:
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Impossibile creare directory {directory_path}: {e}")
        return False

def get_file_size_human_readable(file_path):
    """Restituisce la dimensione di un file in formato human-readable"""
    try:
        size = Path(file_path).stat().st_size
        
        # Converte bytes in formato human-readable
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    except Exception as e:
        logger.error(f"Errore nel calcolo dimensione file {file_path}: {e}")
        return "Sconosciuta"

def clean_filename(filename):
    """Pulisce un nome file da caratteri non sicuri"""
    import re
    
    # Rimuovi caratteri non sicuri
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Rimuovi path traversal
    filename = filename.replace('..', '_')
    
    # Limita lunghezza
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename

def format_datetime(dt=None, format_string='%Y-%m-%d %H:%M:%S'):
    """Formatta una data/ora"""
    if dt is None:
        dt = datetime.now()
    
    try:
        return dt.strftime(format_string)
    except Exception as e:
        logger.error(f"Errore formattazione data: {e}")
        return str(dt)

def parse_file_extension(filename):
    """Estrae e normalizza l'estensione di un file"""
    try:
        ext = Path(filename).suffix.lower()
        return ext if ext else None
    except Exception:
        return None

def is_text_file(filename):
    """Verifica se un file è probabilmente un file di testo"""
    text_extensions = {'.txt', '.csv', '.json', '.xml', '.log', '.md', '.yaml', '.yml',
                      '.ini', '.cfg', '.conf', '.py', '.js', '.html', '.htm', '.css'}
    
    ext = parse_file_extension(filename)
    return ext in text_extensions if ext else False

def is_binary_file(filename):
    """Verifica se un file è probabilmente binario"""
    binary_extensions = {'.exe', '.dll', '.bin', '.pdf', '.zip', '.rar', '.7z',
                         '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
                         '.mp3', '.wav', '.mp4', '.avi', '.mov', '.wmv'}
    
    ext = parse_file_extension(filename)
    return ext in binary_extensions if ext else False

def safe_json_dumps(data, indent=2):
    """JSON dump sicuro che gestisce oggetti non serializzabili"""
    import json
    
    def json_serializer(obj):
        """Serializzatore personalizzato per oggetti non standard"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    try:
        return json.dumps(data, indent=indent, ensure_ascii=False, default=json_serializer)
    except Exception as e:
        logger.error(f"Errore serializzazione JSON: {e}")
        return json.dumps({'error': 'Serialization failed', 'data': str(data)}, indent=indent)

def get_system_info():
    """Raccoglie informazioni sul sistema"""
    import platform
    
    try:
        info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': platform.node(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'python_implementation': platform.python_implementation(),
        }
        
        # Aggiungi info memoria se disponibile
        try:
            import psutil
            memory = psutil.virtual_memory()
            info['memory_total'] = f"{memory.total / (1024**3):.1f} GB"
            info['memory_available'] = f"{memory.available / (1024**3):.1f} GB"
            info['memory_percent'] = f"{memory.percent}%"
        except ImportError:
            info['memory_info'] = 'psutil non disponibile'
        
        return info
    except Exception as e:
        logger.error(f"Errore raccolta info sistema: {e}")
        return {'error': str(e)}

def validate_email(email):
    """Validazione semplice email"""
    import re
    
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_url(url):
    """Validazione semplice URL"""
    import re
    
    if not url:
        return False
    
    pattern = r'^https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})?(?::\d+)?(?:/.*)?$'
    return bool(re.match(pattern, url))

def truncate_string(text, max_length=100, suffix='...'):
    """Tronca una stringa mantenendo un suffisso"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def get_file_hash(file_path, algorithm='md5'):
    """Calcola hash di un file"""
    import hashlib
    
    try:
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"Errore calcolo hash per {file_path}: {e}")
        return None

def backup_file(file_path, backup_suffix=None):
    """Crea un backup di un file"""
    try:
        source = Path(file_path)
        if not source.exists():
            return None
        
        if backup_suffix is None:
            backup_suffix = f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = source.parent / (source.name + backup_suffix)
        
        import shutil
        shutil.copy2(source, backup_path)
        
        logger.info(f"Backup creato: {backup_path}")
        return str(backup_path)
    except Exception as e:
        logger.error(f"Errore creazione backup per {file_path}: {e}")
        return None

def rotate_logs(log_file, max_files=5, max_size_mb=10):
    """Ruota i file di log quando diventano troppo grandi"""
    try:
        log_path = Path(log_file)
        if not log_path.exists():
            return
        
        # Controlla dimensione
        size_mb = log_path.stat().st_size / (1024 * 1024)
        if size_mb < max_size_mb:
            return
        
        # Ruota i file esistenti
        for i in range(max_files - 1, 0, -1):
            old_file = log_path.parent / f"{log_path.stem}.{i}{log_path.suffix}"
            new_file = log_path.parent / f"{log_path.stem}.{i+1}{log_path.suffix}"
            
            if old_file.exists():
                if new_file.exists():
                    new_file.unlink()
                old_file.rename(new_file)
        
        # Sposta il file corrente
        rotated_file = log_path.parent / f"{log_path.stem}.1{log_path.suffix}"
        if rotated_file.exists():
            rotated_file.unlink()
        log_path.rename(rotated_file)
        
        logger.info(f"Log ruotato: {log_file}")
        
    except Exception as e:
        logger.error(f"Errore rotazione log {log_file}: {e}")

def get_disk_usage(path):
    """Ottieni informazioni sull'uso del disco"""
    try:
        import shutil
        usage = shutil.disk_usage(path)
        
        return {
            'total': usage.total,
            'used': usage.total - usage.free,
            'free': usage.free,
            'total_gb': round(usage.total / (1024**3), 2),
            'used_gb': round((usage.total - usage.free) / (1024**3), 2),
            'free_gb': round(usage.free / (1024**3), 2),
            'percent_used': round(((usage.total - usage.free) / usage.total) * 100, 1)
        }
    except Exception as e:
        logger.error(f"Errore calcolo uso disco per {path}: {e}")
        return None

def format_bytes(bytes_count):
    """Formatta i byte in formato human-readable"""
    try:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} EB"
    except Exception:
        return str(bytes_count)

def is_valid_cron_expression(cron_expr):
    """Valida un'espressione cron (semplice)"""
    if not cron_expr:
        return False
    
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return False
    
    # Validazione molto semplice - ogni parte può essere numero, *, o range
    import re
    pattern = r'^(\*|\d+(-\d+)?|\d+(,\d+)*)$'
    
    for part in parts:
        if not re.match(pattern, part):
            return False
    
    return True

def sanitize_env_value(value):
    """Sanitizza un valore per file .env"""
    if not isinstance(value, str):
        value = str(value)
    
    # Escape caratteri speciali se necessario
    if ' ' in value or '"' in value or "'" in value:
        value = value.replace('"', '\\"')
        value = f'"{value}"'
    
    return value

class ProgressTracker:
    """Classe per tracciare il progresso di operazioni lunghe"""
    
    def __init__(self, total_items=0, description="Processing"):
        self.total_items = total_items
        self.current_item = 0
        self.description = description
        self.start_time = datetime.now()
        self.last_update = self.start_time
    
    def update(self, increment=1, description=None):
        """Aggiorna il progresso"""
        self.current_item += increment
        if description:
            self.description = description
        
        now = datetime.now()
        # Aggiorna solo ogni secondo per non spammare i log
        if (now - self.last_update).total_seconds() >= 1:
            self.log_progress()
            self.last_update = now
    
    def log_progress(self):
        """Log del progresso corrente"""
        if self.total_items > 0:
            percent = (self.current_item / self.total_items) * 100
            elapsed = datetime.now() - self.start_time
            
            if self.current_item > 0:
                avg_time = elapsed.total_seconds() / self.current_item
                remaining_items = self.total_items - self.current_item
                eta_seconds = avg_time * remaining_items
                eta = timedelta(seconds=int(eta_seconds))
                
                logger.info(f"{self.description}: {self.current_item}/{self.total_items} ({percent:.1f}%) - ETA: {eta}")
            else:
                logger.info(f"{self.description}: {self.current_item}/{self.total_items} ({percent:.1f}%)")
        else:
            logger.info(f"{self.description}: {self.current_item} items processed")
    
    def finish(self):
        """Completa il tracking"""
        elapsed = datetime.now() - self.start_time
        logger.info(f"{self.description} completato: {self.current_item} items in {elapsed}")

def retry_on_failure(max_attempts=3, delay_seconds=1, exceptions=(Exception,)):
    """Decorator per retry automatico in caso di fallimento"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Tentativo {attempt + 1} fallito per {func.__name__}: {e}")
                        import time
                        time.sleep(delay_seconds)
                    else:
                        logger.error(f"Tutti i {max_attempts} tentativi falliti per {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator

def extract_data_from_api(api_link):
    """Versione completa con gestione errori"""
    base_url = os.getenv("BASE_HOST")
    base_port = os.getenv("APP_PORT")
    # base_url = f"{base_url}:{base_port}"
    url = f"{base_url}{api_link}"
    # Headers (opzionali)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Dati opzionali
    data = {
        "source": "api_call",
        "timestamp": "2024-06-11T10:00:00Z"
    }
    
    try:
        print("🔄 Chiamando API extract_contracts...")
        
        response = requests.post(
            url, 
            json=data, 
            headers=headers,
            timeout=30  # Timeout di 30 secondi
        )
        
        # Controlla status code
        response.raise_for_status()
        
        # Parse JSON response
        result = response.json()
        
        print("✅ API chiamata con successo!")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Message: {result.get('message', 'N/A')}")
        
        if 'data' in result:
            print(f"Dati ricevuti: {len(result['data'])} elementi")
        
        return result
        
    except requests.exceptions.Timeout:
        print("⏱️ Timeout - L'API ha impiegato troppo tempo")
        return None
        
    except requests.exceptions.ConnectionError:
        print("🔌 Errore di connessione - Verifica che il server sia attivo")
        return None
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Errore HTTP {e.response.status_code}: {e.response.text}")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Errore generico: {e}")
        return None
        
    except json.JSONDecodeError:
        print("❌ Risposta non è JSON valido")
        return None