import os
import sys
import json
import ftplib
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import csv
import re
import fnmatch
from io import StringIO

from flask import Flask, render_template, request, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# Carica variabili dal file .env (opzionale)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Carica variabili dal file .env
    print("📁 File .env caricato")
except ImportError:
    print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")

# Fix per encoding Windows - Configurazione logging sicura
class UnicodeStreamHandler(logging.StreamHandler):
    """StreamHandler che gestisce correttamente Unicode su Windows"""
    
    def __init__(self, stream=None):
        super().__init__(stream)
        
    def emit(self, record):
        try:
            msg = self.format(record)
            # Sostituisci emoji con testo su Windows
            if sys.platform.startswith('win'):
                emoji_replacements = {
                    '✅': '[OK]',
                    '❌': '[ERROR]',
                    '⚠️': '[WARNING]',
                    '🕐': '[TIME]',
                    '📁': '[FILE]',
                    '📊': '[CHART]',
                    '⚙️': '[CONFIG]',
                    '📋': '[LOG]',
                    '🔧': '[TOOL]',
                    '🗂️': '[FOLDER]',
                    '📡': '[SERVER]',
                    '📅': '[CALENDAR]',
                    '🚀': '[ROCKET]',
                    '💾': '[DISK]',
                    '🔍': '[SEARCH]',
                    '🎯': '[TARGET]',
                    '📦': '[PACKAGE]',
                    '🔄': '[REFRESH]',
                    '⏰': '[CLOCK]'
                }
                
                for emoji, replacement in emoji_replacements.items():
                    msg = msg.replace(emoji, replacement)
            
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# Configurazione logging migliorata per Windows
def setup_logging():
    """Setup logging con supporto Unicode"""
    
    # Configura formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler per file (sempre UTF-8)
    file_handler = logging.FileHandler('app.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Handler per console (gestione Unicode)
    console_handler = UnicodeStreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configura logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()  # Rimuovi handler esistenti
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

# Inizializza logging
setup_logging()
logger = logging.getLogger(__name__)

# Test logging
logger.info("Sistema di logging inizializzato correttamente")

# Funzioni helper per logging cross-platform
def log_success(message):
    """Log messaggio di successo"""
    logger.info(f"[OK] {message}")

def log_error(message):
    """Log messaggio di errore"""
    logger.error(f"[ERROR] {message}")

def log_warning(message):
    """Log messaggio di warning"""
    logger.warning(f"[WARNING] {message}")

def log_info(message):
    """Log messaggio informativo"""
    logger.info(f"[INFO] {message}")

# Classe per gestione configurazione sicura
class SecureConfig:
    """Gestione sicura della configurazione"""
    
    def __init__(self):
        self._sensitive_keys = {'ftp_password', 'api_key', 'secret_key', 'odoo_api_key'}
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self):
        """Carica configurazione da variabili d'ambiente"""
        return {
            'ODOO_URL': os.getenv('ODOO_URL', ''),
            'ODOO_DB': os.getenv('ODOO_DB', ''),
            'ODOO_USERNAME': os.getenv('ODOO_USERNAME', ''),
            'ODOO_API_KEY': os.getenv('ODOO_API_KEY', ''),
            'ftp_host': os.getenv('FTP_HOST', ''),
            'ftp_user': os.getenv('FTP_USER', ''),
            'ftp_password': os.getenv('FTP_PASSWORD', ''),
            'ftp_directory': os.getenv('FTP_DIRECTORY', '/'),
            'download_all_files': self._str_to_bool(os.getenv('DOWNLOAD_ALL_FILES', 'false')),
            'specific_filename': os.getenv('SPECIFIC_FILENAME', ''),
            'output_directory': os.getenv('OUTPUT_DIRECTORY', 'output'),
            'file_naming_pattern': os.getenv('FILE_NAMING_PATTERN', 'monthly'),
            'custom_pattern': os.getenv('CUSTOM_PATTERN', ''),
            'schedule_type': os.getenv('SCHEDULE_TYPE', 'monthly'),
            'schedule_day': self._str_to_int(os.getenv('SCHEDULE_DAY', '1'), 1),
            'schedule_hour': self._str_to_int(os.getenv('SCHEDULE_HOUR', '9'), 9),
            'schedule_minute': self._str_to_int(os.getenv('SCHEDULE_MINUTE', '0'), 0),
            'interval_days': self._str_to_int(os.getenv('INTERVAL_DAYS', '30'), 30),
            'cron_expression': os.getenv('CRON_EXPRESSION', '0 9 1 * *'),
            'filter_pattern': os.getenv('FILTER_PATTERN', ''),
            'voip_price_fixed': self._str_to_float(os.getenv('VOIP_PRICE_FIXED', '0.02'), 0.02),
            'voip_price_mobile': self._str_to_float(os.getenv('VOIP_PRICE_MOBILE', '0.15'), 0.15),
            'voip_currency': os.getenv('VOIP_CURRENCY', 'EUR'),
            'voip_price_unit': os.getenv('VOIP_PRICE_UNIT', 'per_minute'),
        }
    
    def _validate_config(self):
        """Valida configurazione"""
        # Valida directory output
        output_dir = Path(self.config['output_directory'])
        if not output_dir.is_absolute():
            # Assicura che sia relativa alla directory corrente
            self.config['output_directory'] = str(Path.cwd() / output_dir)
        
        # Valida pattern file
        if self.config['specific_filename']:
            if not self._validate_filename_pattern(self.config['specific_filename']):
                logger.warning(f"Pattern filename potenzialmente non sicuro: {self.config['specific_filename']}")
                self.config['specific_filename'] = ''
        
        # Valida prezzi VoIP
        if self.config['voip_price_fixed'] < 0:
            self.config['voip_price_fixed'] = 0.02
        if self.config['voip_price_mobile'] < 0:
            self.config['voip_price_mobile'] = 0.15
        
        # Assicura che i valori numerici siano corretti
        for key in ['schedule_day', 'schedule_hour', 'schedule_minute', 'interval_days']:
            if not isinstance(self.config[key], int):
                self.config[key] = self._str_to_int(self.config[key], 1 if key == 'schedule_day' else 0)
    
    def _validate_filename_pattern(self, pattern):
        """Valida pattern filename per sicurezza"""
        if not pattern:
            return True
        
        # Blocca path traversal
        if '..' in pattern or '/' in pattern or '\\' in pattern:
            return False
        
        # Valida caratteri permessi (lettere, numeri, underscore, punto, asterisco, percentuale)
        allowed_chars = re.compile(r'^[a-zA-Z0-9_.\-*%]+$')
        return bool(allowed_chars.match(pattern))
    
    def get_safe_config(self):
        """Restituisce configurazione senza dati sensibili"""
        safe_config = {}
        for key, value in self.config.items():
            if any(sensitive in key.lower() for sensitive in self._sensitive_keys):
                safe_config[key] = '***HIDDEN***' if value else ''
            else:
                safe_config[key] = value
        return safe_config
    
    def get_config(self):
        """Restituisce configurazione completa (uso interno)"""
        return self.config.copy()
    
    def update_config(self, updates):
        """Aggiorna configurazione con validazione"""
        for key, value in updates.items():
            if key in self.config:
                # Validazione specifica per filename pattern
                if key in ['specific_filename', 'filter_pattern']:
                    if value and not self._validate_filename_pattern(value):
                        logger.warning(f"Pattern non sicuro ignorato: {value}")
                        continue
                
                # Conversioni di tipo
                if key in ['schedule_day', 'schedule_hour', 'schedule_minute', 'interval_days']:
                    value = self._str_to_int(value, self.config[key])
                elif key in ['voip_price_fixed', 'voip_price_mobile']:
                    value = self._str_to_float(value, self.config[key])
                elif key == 'download_all_files':
                    value = self._str_to_bool(value, self.config[key])
                
                self.config[key] = value
        
        self._validate_config()
    
    @staticmethod
    def _str_to_bool(value, default=False):
        """Converte stringa in booleano"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return default
    
    @staticmethod
    def _str_to_int(value, default=0):
        """Converte stringa in intero"""
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def _str_to_float(value, default=0.0):
        """Converte stringa in float"""
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default

# Istanza globale sicura
secure_config = SecureConfig()
CONFIG = secure_config.get_config()

# Configurazione Flask sicura
app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(32)),
    SESSION_COOKIE_SECURE=True if os.getenv('HTTPS', 'false').lower() == 'true' else False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)

# Scheduler globale
scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

class FTPProcessor:
    """Classe per gestire operazioni FTP e conversioni file con sicurezza migliorata"""
    
    def __init__(self, config):
        self.config = config
        self.ensure_output_directory()
    
    def ensure_output_directory(self):
        """Crea la directory di output se non esiste"""
        output_dir = Path(self.config['output_directory'])
        output_dir.mkdir(exist_ok=True)
    
    def _validate_filename(self, filename):
        """Valida nome file per sicurezza"""
        if not filename:
            return False
        
        # Blocca path traversal e caratteri pericolosi
        dangerous_patterns = ['..', '/', '\\', '|', ';', '&', '$', '`']
        for pattern in dangerous_patterns:
            if pattern in filename:
                return False
        
        # Controlla lunghezza
        if len(filename) > 255:
            return False
        
        return True
    
    def connect_ftp(self):
        """Connessione FTP con gestione errori migliorata"""
        ftp = None
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.config['ftp_host'], timeout=30)  # Timeout aggiunto
            ftp.login(self.config['ftp_user'], self.config['ftp_password'])
            
            # Validazione directory
            if self.config['ftp_directory'] and self.config['ftp_directory'] != '/':
                # Sanitizza il path per evitare path traversal
                clean_dir = self.config['ftp_directory'].strip('/')
                if '..' not in clean_dir:
                    ftp.cwd('/' + clean_dir)
                else:
                    logger.warning("Directory FTP contiene path traversal, uso directory root")
            
            logger.info(f"Connesso al server FTP: {self.config['ftp_host']}")
            return ftp
            
        except ftplib.error_perm as e:
            logger.error(f"Errore permessi FTP: {e}")
            if ftp:
                try:
                    ftp.quit()
                except:
                    pass
            raise
        except ftplib.error_temp as e:
            logger.error(f"Errore temporaneo FTP: {e}")
            if ftp:
                try:
                    ftp.quit()
                except:
                    pass
            raise
        except Exception as e:
            logger.error(f"Errore connessione FTP: {e}")
            if ftp:
                try:
                    ftp.quit()
                except:
                    pass
            raise
    
    def download_file_from_ftp(self, filename, local_path):
        """Download con gestione errori robusta e sovrascrittura file"""
        ftp = None
        temp_path = None
        
        try:
            # Validazione filename
            if not self._validate_filename(filename):
                logger.error(f"Nome file non sicuro: {filename}")
                return False
            
            # Converti local_path in Path object
            local_path = Path(local_path)
            
            # Path temporaneo per download atomico
            temp_path = local_path.parent / (local_path.name + '.tmp')
            
            # Rimuovi file temporaneo se esiste già
            if temp_path.exists():
                try:
                    temp_path.unlink()
                    logger.debug(f"File temporaneo esistente rimosso: {temp_path}")
                except Exception as e:
                    logger.warning(f"Impossibile rimuovere file temporaneo {temp_path}: {e}")
            
            ftp = self.connect_ftp()
            
            with open(temp_path, 'wb') as temp_file:
                ftp.retrbinary(f'RETR {filename}', temp_file.write)
            
            # Gestione sovrascrittura file esistente (specifico per Windows)
            if local_path.exists():
                try:
                    # Su Windows, prima rimuovi il file esistente
                    if sys.platform.startswith('win'):
                        local_path.unlink()
                        logger.debug(f"File esistente rimosso per sovrascrittura: {local_path}")
                    else:
                        # Su Linux/Mac, rename sovrascrive automaticamente
                        pass
                except Exception as e:
                    logger.warning(f"Impossibile rimuovere file esistente {local_path}: {e}")
            
            # Sposta il file temporaneo al nome finale
            try:
                temp_path.rename(local_path)
                logger.info(f"File scaricato: {filename} -> {local_path}")
                return True
            except Exception as e:
                # Se rename fallisce, prova con copy + delete
                logger.warning(f"Rename fallito, provo con copy: {e}")
                try:
                    import shutil
                    shutil.copy2(temp_path, local_path)
                    temp_path.unlink()  # Rimuovi il temporaneo dopo la copia
                    logger.info(f"File scaricato (con copy): {filename} -> {local_path}")
                    return True
                except Exception as e2:
                    logger.error(f"Anche copy fallito: {e2}")
                    return False
            
        except ftplib.error_perm as e:
            logger.error(f"File non trovato o permessi insufficienti per {filename}: {e}")
            return False
        except ftplib.error_temp as e:
            logger.error(f"Errore temporaneo FTP per {filename}: {e}")
            return False
        except IOError as e:
            logger.error(f"Errore I/O per {filename}: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore generico per {filename}: {e}")
            return False
        finally:
            # Cleanup
            if ftp:
                try:
                    ftp.quit()
                except:
                    pass
            
            # Rimuovi file temporaneo se esiste ancora
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    logger.debug(f"File temporaneo pulito: {temp_path}")
                except Exception as e:
                    logger.warning(f"Impossibile rimuovere file temporaneo {temp_path}: {e}")

    def cleanup_output_directory(self, pattern="*.tmp"):
        """Pulisce file temporanei nella directory di output"""
        try:
            output_dir = Path(self.config['output_directory'])
            temp_files = list(output_dir.glob(pattern))
            
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                    logger.debug(f"File temporaneo rimosso: {temp_file}")
                except Exception as e:
                    logger.warning(f"Impossibile rimuovere {temp_file}: {e}")
            
            if temp_files:
                log_info(f"Puliti {len(temp_files)} file temporanei")
                
        except Exception as e:
            logger.error(f"Errore pulizia directory: {e}")




    def list_ftp_files(self):
        """Lista i file presenti sul server FTP"""
        try:
            ftp = self.connect_ftp()
            files = ftp.nlst()
            ftp.quit()
            return files
        except Exception as e:
            logger.error(f"Errore nel listare i file FTP: {e}")
            return []
    
    def match_pattern(self, filename, pattern):
        """
        Verifica se un filename corrisponde al pattern specificato
        Supporta wildcard (*,?) e variabili temporali (%Y,%m,%d,%H,%M,%S)
        """
        if not pattern:
            return True
        
        try:
            # Prima espandi le variabili temporali
            expanded_pattern = self.expand_temporal_pattern(pattern)
            
            # Pattern con wildcard (es: RIV_12345_MESE_*_2025-*.CDR)
            if '*' in expanded_pattern or '?' in expanded_pattern:
                result = fnmatch.fnmatch(filename.upper(), expanded_pattern.upper())
                if result:
                    logger.debug(f"Match wildcard: '{filename}' corrisponde a '{expanded_pattern}'")
                return result
            
            # Pattern regex (es: RIV_12345_MESE_\d{2}_.*\.CDR)
            elif '\\' in expanded_pattern or '[' in expanded_pattern or '^' in expanded_pattern:
                result = bool(re.match(expanded_pattern, filename, re.IGNORECASE))
                if result:
                    logger.debug(f"Match regex: '{filename}' corrisponde a '{expanded_pattern}'")
                return result
            
            # Match esatto
            else:
                result = filename.upper() == expanded_pattern.upper()
                if result:
                    logger.debug(f"Match esatto: '{filename}' corrisponde a '{expanded_pattern}'")
                return result
                
        except Exception as e:
            logger.error(f"Errore nel pattern matching '{pattern}' per file '{filename}': {e}")
            return False
    
    def expand_temporal_pattern(self, pattern):
        """
        Espande le variabili temporali in un pattern
        Supporta sia wildcard (*) che variabili temporali (%Y, %m, etc.)
        """
        try:
            now = datetime.now()
            
            # Sostituisci le variabili temporali
            expanded_pattern = pattern
            
            # Variabili base
            expanded_pattern = expanded_pattern.replace('%Y', str(now.year))
            expanded_pattern = expanded_pattern.replace('%y', str(now.year)[-2:])
            expanded_pattern = expanded_pattern.replace('%m', f"{now.month:02d}")
            expanded_pattern = expanded_pattern.replace('%d', f"{now.day:02d}")
            
            # Variabili orario
            expanded_pattern = expanded_pattern.replace('%H', f"{now.hour:02d}")
            expanded_pattern = expanded_pattern.replace('%M', f"{now.minute:02d}")
            expanded_pattern = expanded_pattern.replace('%S', f"{now.second:02d}")
            
            # Variabili settimana
            expanded_pattern = expanded_pattern.replace('%U', f"{now.strftime('%U')}")
            expanded_pattern = expanded_pattern.replace('%W', f"{now.strftime('%W')}")
            
            # Variabili mese testuale
            expanded_pattern = expanded_pattern.replace('%b', now.strftime('%b'))  # Jan, Feb, etc.
            expanded_pattern = expanded_pattern.replace('%B', now.strftime('%B'))  # January, February, etc.
            
            # Variabili giorno settimana
            expanded_pattern = expanded_pattern.replace('%a', now.strftime('%a'))  # Mon, Tue, etc.
            expanded_pattern = expanded_pattern.replace('%A', now.strftime('%A'))  # Monday, Tuesday, etc.
            
            logger.info(f"Pattern espanso: '{pattern}' -> '{expanded_pattern}'")
            return expanded_pattern
            
        except Exception as e:
            logger.error(f"Errore nell'espansione del pattern '{pattern}': {e}")
            return pattern
    
    def filter_files_by_pattern(self, files, pattern):
        """
        Filtra una lista di file basandosi sul pattern
        """
        if not pattern:
            return files
        
        filtered_files = []
        for filename in files:
            if self.match_pattern(filename, pattern):
                filtered_files.append(filename)
                logger.info(f"File '{filename}' corrisponde al pattern '{pattern}'")
            else:
                logger.debug(f"File '{filename}' NON corrisponde al pattern '{pattern}'")
        
        logger.info(f"Pattern '{pattern}': trovati {len(filtered_files)} file su {len(files)} totali")
        return filtered_files
    
    def generate_filename(self, pattern_type='monthly', custom_pattern=''):
        """
        Genera il nome del file basato sul pattern specificato
        Ora supporta anche pattern con wildcard per il filtering
        """
        now = datetime.now()
        
        patterns = {
            'monthly': f"report_{now.strftime('%Y_%m')}.csv",
            'weekly': f"report_{now.strftime('%Y_W%U')}.csv",
            'daily': f"report_{now.strftime('%Y_%m_%d')}.csv",
            'quarterly': f"report_{now.strftime('%Y')}_Q{(now.month-1)//3+1}.csv",
            'yearly': f"report_{now.strftime('%Y')}.csv",
            # Nuovi pattern per file CDR
            'cdr_monthly': f"RIV_*_MESE_{now.strftime('%m')}_*.CDR",
            'cdr_any_month': "RIV_*_MESE_*_*.CDR",
            'cdr_current_year': f"RIV_*_MESE_*_{now.strftime('%Y')}-*.CDR",
            'cdr_specific_client': "RIV_12345_MESE_*_*.CDR"
        }
        
        if pattern_type == 'custom' and custom_pattern:
            try:
                # Supporta pattern estesi con ora, minuti, secondi E wildcard
                if '*' in custom_pattern or '?' in custom_pattern:
                    # Pattern con wildcard - non sostituire le date
                    generated_name = custom_pattern
                    logger.info(f"Pattern wildcard personalizzato: '{custom_pattern}'")
                else:
                    # Pattern normale con sostituzione date
                    generated_name = now.strftime(custom_pattern)
                    logger.info(f"Pattern personalizzato '{custom_pattern}' -> '{generated_name}'")
                
                return generated_name
            except ValueError as e:
                logger.error(f"Errore nel pattern personalizzato '{custom_pattern}': {e}")
                logger.info("Pattern validi includono: %Y=anno, %m=mese, %d=giorno, %H=ora, %M=minuto, %S=secondo, *=wildcard")
                return patterns['monthly']
        
        result = patterns.get(pattern_type, patterns['monthly'])
        logger.info(f"Pattern '{pattern_type}' -> '{result}'")
        return result
    
    def download_files(self):
        """Scarica i file dal server FTP basandosi sulla configurazione"""
        downloaded_files = []
        
        try:
            # Debug: stampa configurazione
            logger.info(f"Configurazione download: download_all_files={self.config['download_all_files']}")
            
            # Pulizia file temporanei all'inizio
            self.cleanup_output_directory("*.tmp")
            
            # Converti esplicitamente in booleano se è stringa
            download_all = self.config['download_all_files']
            if isinstance(download_all, str):
                download_all = download_all.lower() in ('true', '1', 'yes', 'on')
            elif download_all is None:
                download_all = False
            
            # Ottieni lista completa file dal server
            all_files = self.list_ftp_files()
            logger.info(f"File totali trovati sul server FTP: {len(all_files)}")
            
            if not all_files:
                logger.warning("Nessun file trovato sul server FTP")
                return []
            
            if download_all:
                # Modalità: scarica tutti i file
                logger.info("Modalità: scarica tutti i file")
                files_to_download = all_files
            else:
                # Modalità: file specifico o con pattern
                logger.info("Modalità: file specifico/pattern")
                
                if self.config.get('specific_filename'):
                    # Nome file specifico
                    specific_name = self.config['specific_filename']
                    logger.info(f"Cercando file specifico: {specific_name}")
                    
                    # Controlla se è un pattern (contiene wildcard)
                    if '*' in specific_name or '?' in specific_name:
                        logger.info(f"Rilevato pattern wildcard: {specific_name}")
                        files_to_download = self.filter_files_by_pattern(all_files, specific_name)
                    else:
                        # Nome esatto
                        files_to_download = [specific_name] if specific_name in all_files else []
                        if not files_to_download:
                            logger.warning(f"File specifico '{specific_name}' non trovato sul server")
                
                elif self.config.get('filter_pattern'):
                    # Pattern di filtro dedicato
                    filter_pattern = self.config['filter_pattern']
                    logger.info(f"Usando pattern di filtro: {filter_pattern}")
                    files_to_download = self.filter_files_by_pattern(all_files, filter_pattern)
                
                else:
                    # Genera nome basato su pattern temporale
                    filename = self.generate_filename(
                        self.config['file_naming_pattern'],
                        self.config.get('custom_pattern', '')
                    )
                    logger.info(f"Nome file generato dal pattern: {filename}")
                    
                    # Controlla se il nome generato contiene wildcard
                    if '*' in filename or '?' in filename:
                        files_to_download = self.filter_files_by_pattern(all_files, filename)
                    else:
                        files_to_download = [filename] if filename in all_files else []
                        if not files_to_download:
                            logger.warning(f"File generato '{filename}' non trovato sul server")
            
            # Download dei file selezionati
            logger.info(f"File da scaricare: {len(files_to_download)}")
            
            for filename in files_to_download:
                # Ignora directory e file nascosti
                if filename.startswith('.') or filename.endswith('/'):
                    logger.info(f"Ignorato: {filename} (directory o file nascosto)")
                    continue
                
                local_path = Path(self.config['output_directory']) / filename
                logger.info(f"Scaricamento: {filename}")
                
                # Avviso se file esiste già
                if local_path.exists():
                    log_warning(f"File esistente sarà sovrascritto: {filename}")
                
                if self.download_file_from_ftp(filename, local_path):
                    downloaded_files.append(str(local_path))
                    log_success(f"Download completato: {filename}")
                else:
                    log_error(f"Download fallito: {filename}")
            
            # Pulizia finale file temporanei
            self.cleanup_output_directory("*.tmp")
            
            logger.info(f"Download completato. File scaricati: {len(downloaded_files)}")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Errore nel processo di download: {e}")
            # Pulizia anche in caso di errore
            try:
                self.cleanup_output_directory("*.tmp")
            except:
                pass
            return []
    
    def convert_to_json(self, file_path):
        """
        Converte un file in formato JSON
        Supporta CSV, TXT, Excel, e file CDR
        """
        try:
            file_path = Path(file_path)
            file_extension = file_path.suffix.lower()
            
            # Determina il nome del file JSON di output
            json_filename = file_path.stem + '.json'
            json_path = Path(self.config['output_directory']) / json_filename
            
            data = None
            
            # Controlla se è un file CDR (Call Detail Record) basandosi sul nome o estensione
            if file_extension == '.cdr' or 'CDR' in file_path.name.upper():
                # File CDR - parsing personalizzato
                cdr_headers = [
                    'data_ora_chiamata',
                    'numero_chiamante', 
                    'numero_chiamato',
                    'durata_secondi',
                    'tipo_chiamata',
                    'operatore',
                    'costo_euro',
                    'codice_contratto',
                    'codice_servizio',
                    'cliente_finale_comune',
                    'prefisso_chiamato'
                ]
                
                data = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line:  # Ignora righe vuote
                            fields = line.split(';')
                            
                            # Assicurati che ci siano abbastanza campi
                            while len(fields) < len(cdr_headers):
                                fields.append('')
                            
                            # Crea record con conversioni di tipo appropriate
                            record = {}
                            for i, header in enumerate(cdr_headers):
                                if i < len(fields):
                                    value = fields[i].strip()
                                    
                                    # Conversioni di tipo specifiche
                                    if header == 'durata_secondi':
                                        try:
                                            record[header] = int(value) if value else 0
                                        except ValueError:
                                            record[header] = 0
                                    elif header == 'costo_euro':
                                        try:
                                            record[header] = float(value.replace(',', '.')) if value else 0.0
                                        except ValueError:
                                            record[header] = 0.0
                                    elif header in ['codice_contratto', 'codice_servizio']:
                                        try:
                                            record[header] = int(value) if value else 0
                                        except ValueError:
                                            record[header] = 0
                                    else:
                                        record[header] = value
                                else:
                                    record[header] = ''
                            
                            # Aggiungi metadati utili
                            record['record_number'] = line_num
                            record['raw_line'] = line
                            
                            data.append(record)
                
                logger.info(f"File CDR processato: {len(data)} record trovati")
            
            elif file_extension == '.csv':
                # Legge CSV - controlla se è separato da punto e virgola
                try:
                    # Prova prima con punto e virgola (comune in Europa)
                    df = pd.read_csv(file_path, sep=';')
                    if len(df.columns) == 1:
                        # Se ha una sola colonna, prova con virgola
                        df = pd.read_csv(file_path, sep=',')
                except:
                    # Fallback con virgola
                    df = pd.read_csv(file_path, sep=',')
                
                data = df.to_dict('records')
            
            elif file_extension in ['.xlsx', '.xls']:
                # Legge Excel
                df = pd.read_excel(file_path)
                data = df.to_dict('records')
            
            elif file_extension == '.txt':
                # Legge file di testo - controlla se contiene dati CDR
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                
                # Se la prima riga contiene molti punti e virgola, trattalo come CDR
                if first_line.count(';') >= 5:
                    # Riprocessa come file CDR
                    return self.convert_to_json_as_cdr(file_path)
                else:
                    # Assume formato CSV con tab o altro delimitatore
                    try:
                        df = pd.read_csv(file_path, delimiter='\t')
                        data = df.to_dict('records')
                    except:
                        # Se fallisce come CSV, legge come testo semplice
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        data = {'lines': [line.strip() for line in lines]}
            
            elif file_extension == '.json':
                # File già JSON, lo copia
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            else:
                # File non supportato, prova a leggerlo come testo
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Controlla se il contenuto sembra un file CDR
                if content.count(';') > content.count(',') and content.count(';') > 10:
                    # Riprocessa come CDR salvando temporaneamente
                    temp_cdr = file_path.parent / (file_path.stem + '.cdr')
                    with open(temp_cdr, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    result = self.convert_to_json_as_cdr(temp_cdr)
                    
                    # Rimuovi file temporaneo
                    try:
                        temp_cdr.unlink()
                    except:
                        pass
                    
                    return result
                else:
                    data = {'content': content, 'source_file': file_path.name}
            
            # Aggiungi metadati al JSON
            if isinstance(data, list) and len(data) > 0:
                metadata = {
                    'source_file': file_path.name,
                    'conversion_timestamp': datetime.now().isoformat(),
                    'total_records': len(data),
                    'file_type': 'CDR' if (file_extension == '.cdr' or 'CDR' in file_path.name.upper()) else 'standard'
                }
                
                # Crea struttura finale con metadati
                final_data = {
                    'metadata': metadata,
                    'records': data
                }
            else:
                final_data = data
            
            # Salva il file JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"File convertito in JSON: {json_path}")
            return str(json_path)
            
        except Exception as e:
            logger.error(f"Errore nella conversione di {file_path}: {e}")
            return None

    def convert_to_json_as_cdr(self, file_path):
        """
        Funzione helper per convertire specificamente file CDR
        """
        try:
            # Usa la stessa logica della funzione principale ma forza il tipo CDR
            original_name = file_path.name
            file_path = Path(file_path)
            
            # Simula estensione .cdr per forzare il parsing CDR
            temp_path = file_path.parent / (file_path.stem + '.cdr')
            if not temp_path.exists():
                temp_path = file_path
            
            return self.convert_to_json(temp_path)
            
        except Exception as e:
            logger.error(f"Errore nella conversione CDR di {file_path}: {e}")
            return None

    def process_files(self):
        """Processo completo: download e conversione"""
        try:
            logger.info("Inizio processo di elaborazione file")
            
            # Download dei file
            downloaded_files = self.download_files()
            
            if not downloaded_files:
                logger.warning("Nessun file scaricato")
                return {'success': False, 'message': 'Nessun file scaricato'}
            
            # Conversione in JSON
            converted_files = []
            for file_path in downloaded_files:
                json_path = self.convert_to_json(file_path)
                if json_path:
                    converted_files.append(json_path)
            
            result = {
                'success': True,
                'downloaded_files': downloaded_files,
                'converted_files': converted_files,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Processo completato: {len(converted_files)} file convertiti")
            return result
            
        except Exception as e:
            logger.error(f"Errore nel processo completo: {e}")
            return {'success': False, 'message': str(e)}

def test_pattern_matching(self, pattern):
    """
    Testa un pattern contro i file presenti sul server FTP
    Utile per debug e anteprima risultati
    """
    try:
        all_files = self.list_ftp_files()
        matching_files = self.filter_files_by_pattern(all_files, pattern)
        
        result = {
            'pattern': pattern,
            'total_files': len(all_files),
            'matching_files': matching_files,
            'match_count': len(matching_files),
            'all_files': all_files  # Per debug
        }
        
        logger.info(f"Test pattern '{pattern}': {len(matching_files)} file corrispondenti")
        return result
        
    except Exception as e:
        logger.error(f"Errore nel test pattern: {e}")
        return {
            'pattern': pattern,
            'error': str(e),
            'total_files': 0,
            'matching_files': [],
            'match_count': 0
        }

def generate_pattern_examples(self):
    """
    Genera esempi di pattern con le variabili attuali per l'interfaccia
    """
    now = datetime.now()
    
    examples = {
        'basic_wildcards': [
            'RIV_*_MESE_*_*.CDR',
            'RIV_12345_MESE_*_*.CDR',
            'RIV_*_MESE_03_*.CDR'
        ],
        'temporal_current': [
            f'RIV_*_MESE_{now.month:02d}_*.CDR',  # Mese corrente
            f'RIV_*_MESE_*_{now.year}-*.CDR',    # Anno corrente
            f'RIV_*_MESE_{now.month:02d}_{now.year}-{now.month:02d}-*.CDR'  # Mese e anno correnti
        ],
        'temporal_variables': [
            'RIV_*_MESE_%m_*.CDR',      # Mese corrente con variabile
            'RIV_*_MESE_*_%Y-%.CDR',    # Anno corrente con variabile
            'RIV_*_MESE_%m_%Y-%m-*.CDR' # Mese e anno correnti
        ],
        'advanced_combinations': [
            'RIV_*_MESE_%m_%Y-%m-%d-*.CDR',     # Giorno specifico
            'RIV_*_MESE_%m_%Y-%m-*-%H.*.CDR',   # Ora specifica
            'RIV_12345_MESE_%m_%Y-*-*-*.CDR'    # Cliente e mese specifici
        ]
    }
    
    # Espandi gli esempi per mostrare i risultati
    expanded_examples = {}
    for category, patterns in examples.items():
        expanded_examples[category] = []
        for pattern in patterns:
            expanded = self.expand_temporal_pattern(pattern)
            expanded_examples[category].append({
                'pattern': pattern,
                'expanded': expanded,
                'description': self.get_pattern_description(pattern)
            })
    
    return expanded_examples

def get_pattern_description(self, pattern):
    """
    Genera descrizione user-friendly per un pattern
    """
    descriptions = {
        'RIV_*_MESE_*_*.CDR': 'Tutti i file CDR di qualsiasi cliente e mese',
        'RIV_12345_MESE_*_*.CDR': 'Tutti i file del cliente 12345',
        'RIV_*_MESE_03_*.CDR': 'File di marzo di qualsiasi cliente',
        'RIV_*_MESE_%m_*.CDR': 'File del mese corrente di qualsiasi cliente',
        'RIV_*_MESE_*_%Y-*.CDR': 'File dell\'anno corrente di qualsiasi cliente',
        'RIV_*_MESE_%m_%Y-%m-*.CDR': 'File del mese corrente dell\'anno corrente'
    }
    
    return descriptions.get(pattern, 'Pattern personalizzato')

# Istanza globale del processore
processor = FTPProcessor(CONFIG)

def scheduled_job():
    """Job schedulato che esegue il processo completo"""
    logger.info("Esecuzione job schedulato")
    result = processor.process_files()
    
    # Salva il risultato dell'ultima esecuzione
    log_file = Path(CONFIG['output_directory']) / 'last_execution.json'
    with open(log_file, 'w') as f:
        json.dump(result, f, indent=2)

def restart_scheduler():
    """Riavvia lo scheduler con la nuova configurazione"""
    # Rimuove tutti i job esistenti
    scheduler.remove_all_jobs()
    
    try:
        if CONFIG['schedule_type'] == 'monthly':
            scheduler.add_job(
                func=scheduled_job,
                trigger=CronTrigger(
                    day=CONFIG['schedule_day'],
                    hour=CONFIG['schedule_hour'],
                    minute=CONFIG['schedule_minute']
                ),
                id='monthly_job',
                replace_existing=True
            )
            log_success(f"Schedulazione mensile: giorno {CONFIG['schedule_day']} alle {CONFIG['schedule_hour']}:{CONFIG['schedule_minute']:02d}")
            
        elif CONFIG['schedule_type'] == 'weekly':
            scheduler.add_job(
                func=scheduled_job,
                trigger=CronTrigger(
                    day_of_week=CONFIG['schedule_day'],
                    hour=CONFIG['schedule_hour'],
                    minute=CONFIG['schedule_minute']
                ),
                id='weekly_job',
                replace_existing=True
            )
            log_success(f"Schedulazione settimanale: giorno {CONFIG['schedule_day']} alle {CONFIG['schedule_hour']}:{CONFIG['schedule_minute']:02d}")
            
        elif CONFIG['schedule_type'] == 'daily':
            scheduler.add_job(
                func=scheduled_job,
                trigger=CronTrigger(
                    hour=CONFIG['schedule_hour'],
                    minute=CONFIG['schedule_minute']
                ),
                id='daily_job',
                replace_existing=True
            )
            log_success(f"Schedulazione giornaliera alle {CONFIG['schedule_hour']}:{CONFIG['schedule_minute']:02d}")
            
        elif CONFIG['schedule_type'] == 'interval':
            # Usa il vecchio sistema (giorni)
            scheduler.add_job(
                func=scheduled_job,
                trigger=IntervalTrigger(days=CONFIG['interval_days']),
                id='interval_job',
                replace_existing=True
            )
            log_success(f"Schedulazione a intervallo: ogni {CONFIG['interval_days']} giorni")
            
        elif CONFIG['schedule_type'] == 'interval_precise':
            # Nuovo sistema con minuti/ore/giorni
            interval_type = CONFIG.get('schedule_interval_type', 'minutes')
            interval_value = CONFIG.get('schedule_interval_value', 30)
            
            if interval_type == 'minutes':
                scheduler.add_job(
                    func=scheduled_job,
                    trigger=IntervalTrigger(minutes=interval_value),
                    id='interval_precise_job',
                    replace_existing=True
                )
                log_success(f"Schedulazione precisa: ogni {interval_value} minuti")
                
            elif interval_type == 'hours':
                scheduler.add_job(
                    func=scheduled_job,
                    trigger=IntervalTrigger(hours=interval_value),
                    id='interval_precise_job',
                    replace_existing=True
                )
                log_success(f"Schedulazione precisa: ogni {interval_value} ore")
                
            elif interval_type == 'seconds':
                scheduler.add_job(
                    func=scheduled_job,
                    trigger=IntervalTrigger(seconds=interval_value),
                    id='interval_precise_job',
                    replace_existing=True
                )
                log_success(f"Schedulazione precisa: ogni {interval_value} secondi")
                
            else:  # days
                scheduler.add_job(
                    func=scheduled_job,
                    trigger=IntervalTrigger(days=interval_value),
                    id='interval_precise_job',
                    replace_existing=True
                )
                log_success(f"Schedulazione precisa: ogni {interval_value} giorni")
                
        elif CONFIG['schedule_type'] == 'cron':
            # Parsing manuale dell'espressione cron
            parts = CONFIG['cron_expression'].split()
            if len(parts) == 5:
                scheduler.add_job(
                    func=scheduled_job,
                    trigger=CronTrigger(
                        minute=parts[0],
                        hour=parts[1],
                        day=parts[2],
                        month=parts[3],
                        day_of_week=parts[4]
                    ),
                    id='cron_job',
                    replace_existing=True
                )
                log_success(f"Schedulazione cron: {CONFIG['cron_expression']}")
            else:
                log_error(f"Espressione cron non valida: {CONFIG['cron_expression']}")
                
        # Mostra prossima esecuzione
        jobs = scheduler.get_jobs()
        if jobs:
            next_run = jobs[0].next_run_time
            if next_run:
                log_info(f"Prossima esecuzione: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
    except Exception as e:
        log_error(f"Errore nella configurazione scheduler: {e}")

def save_config_to_env():
    """Salva configurazione con backup e validazione"""
    try:
        config = secure_config.get_config()
        
        # Crea backup prima della modifica
        env_file = Path('.env')
        if env_file.exists():
            backup_file = Path(f'.env.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            env_file.rename(backup_file)
            log_info(f"Backup configurazione creato: {backup_file}")
        
        env_content = f"""# Configurazione aggiornata automaticamente - {datetime.now().isoformat()}

ODOO_URL={config['ODOO_URL']}
ODOO_DB={config['ODOO_DB']}
ODOO_USERNAME={config['ODOO_USERNAME']}
ODOO_API_KEY={config['ODOO_API_KEY']}

SECRET_KEY={app.secret_key}

# Configurazione FTP
FTP_HOST={config['ftp_host']}
FTP_USER={config['ftp_user']}
FTP_PASSWORD={config['ftp_password']}
FTP_DIRECTORY={config['ftp_directory']}

# Configurazione Download
DOWNLOAD_ALL_FILES={str(config['download_all_files']).lower()}
SPECIFIC_FILENAME={config['specific_filename']}
OUTPUT_DIRECTORY={config['output_directory']}
FILE_NAMING_PATTERN={config['file_naming_pattern']}
CUSTOM_PATTERN={config['custom_pattern']}
FILTER_PATTERN={config.get('filter_pattern', '')}

# Configurazione Schedulazione
SCHEDULE_TYPE={config['schedule_type']}
SCHEDULE_DAY={config['schedule_day']}
SCHEDULE_HOUR={config['schedule_hour']}
SCHEDULE_MINUTE={config['schedule_minute']}
INTERVAL_DAYS={config['interval_days']}
CRON_EXPRESSION={config['cron_expression']}

# Configurazione Prezzi VoIP
VOIP_PRICE_FIXED={config['voip_price_fixed']}
VOIP_PRICE_MOBILE={config['voip_price_mobile']}
VOIP_CURRENCY={config['voip_currency']}
VOIP_PRICE_UNIT={config['voip_price_unit']}
"""
        
        # Salva con permessi sicuri
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        # Su Windows non possiamo usare chmod
        if not sys.platform.startswith('win'):
            os.chmod('.env', 0o600)
        
        # Mantieni anche la copia locale per backup
        with open('.env.local', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        log_success("Configurazione salvata correttamente")
        
        # Mantieni backup solo degli ultimi 5 file
        cleanup_old_backups()
        
    except Exception as e:
        log_error(f"Errore nel salvataggio configurazione: {e}")

def cleanup_old_backups():
    """Rimuove backup vecchi per limitare spazio disco"""
    try:
        backup_files = list(Path('.').glob('.env.backup.*'))
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Mantieni solo i 5 backup più recenti
        for old_backup in backup_files[5:]:
            old_backup.unlink()
            logger.info(f"Backup vecchio rimosso: {old_backup}")
    except Exception as e:
        logger.error(f"Errore pulizia backup: {e}")

def get_schedule_description():
    """Restituisce una descrizione user-friendly della schedulazione corrente"""
    try:
        schedule_type = CONFIG['schedule_type']
        
        if schedule_type == 'monthly':
            return f"Mensile: giorno {CONFIG['schedule_day']} alle {CONFIG['schedule_hour']}:{CONFIG['schedule_minute']:02d}"
            
        elif schedule_type == 'weekly':
            days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
            day_name = days[CONFIG['schedule_day']] if CONFIG['schedule_day'] < 7 else 'Sconosciuto'
            return f"Settimanale: ogni {day_name} alle {CONFIG['schedule_hour']}:{CONFIG['schedule_minute']:02d}"
            
        elif schedule_type == 'daily':
            return f"Giornaliero: ogni giorno alle {CONFIG['schedule_hour']}:{CONFIG['schedule_minute']:02d}"
            
        elif schedule_type == 'interval':
            return f"Intervallo: ogni {CONFIG['interval_days']} giorni"
            
        elif schedule_type == 'interval_precise':
            interval_type = CONFIG.get('schedule_interval_type', 'minutes')
            interval_value = CONFIG.get('schedule_interval_value', 30)
            
            type_labels = {
                'seconds': 'secondi',
                'minutes': 'minuti', 
                'hours': 'ore',
                'days': 'giorni'
            }
            
            return f"Intervallo preciso: ogni {interval_value} {type_labels.get(interval_type, 'unità')}"
            
        elif schedule_type == 'cron':
            return f"Cron: {CONFIG['cron_expression']}"
            
        return "Non configurato"
        
    except Exception as e:
        logger.error(f"Errore nella descrizione schedulazione: {e}")
        return "Errore configurazione"

def get_next_scheduled_jobs(limit=3):
    """Restituisce le prossime esecuzioni programmate"""
    try:
        jobs = scheduler.get_jobs()
        next_runs = []
        
        for job in jobs:
            if job.next_run_time:
                next_runs.append({
                    'job_id': job.id,
                    'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'next_run_iso': job.next_run_time.isoformat()
                })
        
        # Ordina per data più vicina
        next_runs.sort(key=lambda x: x['next_run_iso'])
        
        return next_runs[:limit]
        
    except Exception as e:
        logger.error(f"Errore nel recupero prossime esecuzioni: {e}")
        return []

# SHORTCUT PER LE CONFIGURAZIONI PIÙ COMUNI
def set_schedule_every_minute():
    """Configura esecuzione ogni minuto"""
    CONFIG['schedule_type'] = 'interval_precise'
    CONFIG['schedule_interval_type'] = 'minutes'
    CONFIG['schedule_interval_value'] = 1
    restart_scheduler()
    log_info("Schedulazione impostata: ogni minuto")

def set_schedule_every_hour():
    """Configura esecuzione ogni ora"""
    CONFIG['schedule_type'] = 'interval_precise'
    CONFIG['schedule_interval_type'] = 'hours'
    CONFIG['schedule_interval_value'] = 1
    restart_scheduler()
    log_info("Schedulazione impostata: ogni ora")

def set_schedule_every_30_minutes():
    """Configura esecuzione ogni 30 minuti"""
    CONFIG['schedule_type'] = 'interval_precise'
    CONFIG['schedule_interval_type'] = 'minutes'
    CONFIG['schedule_interval_value'] = 30
    restart_scheduler()
    log_info("Schedulazione impostata: ogni 30 minuti")

def set_schedule_every_10_seconds():
    """Configura esecuzione ogni 10 secondi (per test)"""
    CONFIG['schedule_type'] = 'interval_precise'
    CONFIG['schedule_interval_type'] = 'seconds'
    CONFIG['schedule_interval_value'] = 10
    restart_scheduler()
    log_info("Schedulazione impostata: ogni 10 secondi (TEST)")

# Route Flask Sicure
@app.route('/')
def index():
    """Pagina principale"""
    return render_template('index.html', config=secure_config.get_config())

@app.route('/config', methods=['GET', 'POST'])
def config_page():
    """Pagina configurazione con validazione migliorata"""
    if request.method == 'POST':
        try:
            # Raccogli aggiornamenti dal form
            updates = {}
            
            for key in secure_config.get_config().keys():
                if key in request.form:
                    value = request.form.get(key, '').strip()
                    
                    # Gestione speciale per checkbox
                    if key == 'download_all_files':
                        updates[key] = request.form.get(key) == 'on'
                    else:
                        updates[key] = value
                else:
                    # Per checkbox non selezionati
                    if key == 'download_all_files':
                        updates[key] = False
            
            # Debug: stampa tutti i dati del form
            logger.info("Dati form ricevuti:")
            for key, value in updates.items():
                if 'password' not in key.lower() and 'key' not in key.lower():
                    logger.info(f"  {key}: {value}")
            
            # Aggiorna configurazione con validazione
            secure_config.update_config(updates)
            
            # Salva configurazione
            save_config_to_env()
            
            # Aggiorna istanza globale
            global CONFIG
            CONFIG = secure_config.get_config()
            
            # Aggiorna processore
            global processor
            processor = FTPProcessor(CONFIG)
            
            # Riavvia scheduler
            restart_scheduler()
            
            logger.info("Configurazione aggiornata con successo")
            return redirect(url_for('config_page'))
            
        except Exception as e:
            logger.error(f"Errore aggiornamento configurazione: {e}")
            # In caso di errore, non crashare ma mostrare messaggio
            return render_template('config.html', 
                                 config=secure_config.get_config(),
                                 error=f"Errore nell'aggiornamento: {str(e)}")
    
    return render_template('config.html', config=secure_config.get_config())

@app.route('/manual_run')
def manual_run():
    """Esecuzione manuale del processo"""
    try:
        result = processor.process_files()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Errore esecuzione manuale: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/test_ftp')
def test_ftp():
    """Test connessione FTP"""
    try:
        files = processor.list_ftp_files()
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        logger.error(f"Errore test FTP: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logs')
def logs():
    """Visualizzazione log"""
    try:
        with open('app.log', 'r', encoding='utf-8') as f:
            log_content = f.read()
        return f"<pre>{log_content}</pre>"
    except Exception as e:
        logger.error(f"Errore lettura log: {e}")
        return "Log non disponibile"

@app.route('/status')
def status():
    """Stato dell'applicazione senza dati sensibili"""
    try:
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        # Legge l'ultima esecuzione se disponibile
        last_execution = None
        log_file = Path(CONFIG['output_directory']) / 'last_execution.json'
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    last_execution = json.load(f)
            except Exception as e:
                logger.error(f"Errore lettura ultima esecuzione: {e}")
        
        return jsonify({
            'scheduled_jobs': jobs,
            'last_execution': last_execution,
            'config': secure_config.get_safe_config()  # ← CONFIG SICURA
        })
    except Exception as e:
        logger.error(f"Errore endpoint status: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

@app.route('/env_status')
def env_status():
    """Mostra lo stato delle variabili d'ambiente (senza password)"""
    try:
        env_vars = {}
        env_keys = [
            'FTP_HOST', 'FTP_USER', 'FTP_DIRECTORY', 'DOWNLOAD_ALL_FILES',
            'OUTPUT_DIRECTORY', 'FILE_NAMING_PATTERN', 'SCHEDULE_TYPE',
            'SCHEDULE_DAY', 'SCHEDULE_HOUR', 'SCHEDULE_MINUTE'
        ]
        
        for key in env_keys:
            value = os.getenv(key)
            env_vars[key] = value if value else '(non impostato)'
        
        # Mostra se la password è impostata senza rivelare il valore
        env_vars['FTP_PASSWORD'] = 'IMPOSTATA' if os.getenv('FTP_PASSWORD') else '(non impostata)'
        
        return jsonify(env_vars)
    except Exception as e:
        logger.error(f"Errore env_status: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

@app.route('/test_pattern', methods=['POST'])
def test_pattern():
    """Test pattern con validazione input"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Dati non validi'})
        
        pattern = data.get('pattern', '').strip()
        
        if not pattern:
            return jsonify({'success': False, 'message': 'Pattern non specificato'})
        
        # Validazione pattern
        if not secure_config._validate_filename_pattern(pattern):
            return jsonify({'success': False, 'message': 'Pattern contiene caratteri non sicuri'})
        
        if len(pattern) > 200:
            return jsonify({'success': False, 'message': 'Pattern troppo lungo'})
        
        # Testa il pattern
        result = processor.test_pattern_matching(pattern)
        
        if 'error' in result:
            return jsonify({'success': False, 'message': result['error']})
        
        return jsonify({
            'success': True,
            'pattern': result['pattern'],
            'total_files': result['total_files'],
            'matching_files': result['matching_files'][:50],  # Limita risultati
            'match_count': result['match_count']
        })
        
    except Exception as e:
        logger.error(f"Errore nel test pattern: {e}")
        return jsonify({'success': False, 'message': 'Errore interno del server'})

@app.route('/pattern_examples')
def pattern_examples():
    """Restituisce esempi di pattern con variabili temporali"""
    try:
        examples = processor.generate_pattern_examples()
        return jsonify({
            'success': True,
            'examples': examples,
            'current_datetime': {
                'year': datetime.now().year,
                'month': datetime.now().month,
                'day': datetime.now().day,
                'hour': datetime.now().hour,
                'minute': datetime.now().minute
            }
        })
    except Exception as e:
        logger.error(f"Errore nel generare esempi pattern: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/list_ftp_files')
def list_ftp_files():
    """Lista tutti i file presenti sul server FTP"""
    try:
        files = processor.list_ftp_files()
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        logger.error(f"Errore nel listare file FTP: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/quick_schedule/<schedule_type>')
def quick_schedule(schedule_type):
    """Configurazioni rapide di schedulazione"""
    try:
        if schedule_type == 'every_minute':
            set_schedule_every_minute()
            message = "Schedulazione impostata: ogni minuto"
            
        elif schedule_type == 'every_hour':
            set_schedule_every_hour()
            message = "Schedulazione impostata: ogni ora"
            
        elif schedule_type == 'every_30_minutes':
            set_schedule_every_30_minutes()
            message = "Schedulazione impostata: ogni 30 minuti"
            
        elif schedule_type == 'every_10_seconds':
            set_schedule_every_10_seconds()
            message = "Schedulazione impostata: ogni 10 secondi (TEST)"
            
        else:
            return jsonify({'success': False, 'message': 'Tipo di schedulazione non riconosciuto'})
        
        # Salva configurazione
        save_config_to_env()
        
        return jsonify({
            'success': True,
            'message': message,
            'schedule_description': get_schedule_description(),
            'next_jobs': get_next_scheduled_jobs()
        })
        
    except Exception as e:
        logger.error(f"Errore nella configurazione rapida: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/schedule_info')
def schedule_info():
    """Informazioni sulla schedulazione corrente"""
    try:
        jobs = scheduler.get_jobs()
        job_info = []
        
        for job in jobs:
            job_info.append({
                'id': job.id,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'func_name': job.func.__name__ if hasattr(job, 'func') else 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'schedule_description': get_schedule_description(),
            'active_jobs': job_info,
            'scheduler_running': scheduler.running,
        })
        
    except Exception as e:
        logger.error(f"Errore nel recupero info schedulazione: {e}")
        return jsonify({'success': False, 'message': str(e)})

def print_startup_info():
    """Stampa informazioni di avvio senza emoji"""
    print("\n" + "="*50)
    print("AVVIO FTP SCHEDULER APP")
    print("="*50)
    print(f"Dashboard: http://localhost:{os.getenv('APP_PORT', '5000')}")
    print(f"Configurazione: http://localhost:{os.getenv('APP_PORT', '5000')}/config")
    print(f"Log: http://localhost:{os.getenv('APP_PORT', '5000')}/logs")
    print(f"Stato: http://localhost:{os.getenv('APP_PORT', '5000')}/status")
    print(f"Variabili ENV: http://localhost:{os.getenv('APP_PORT', '5000')}/env_status")
    print("="*50)
    print(f"Directory output: {CONFIG['output_directory']}")
    print(f"Server FTP: {CONFIG['ftp_host'] if CONFIG['ftp_host'] else '(non configurato)'}")
    print(f"Schedulazione: {CONFIG['schedule_type']}")
    print("="*50 + "\n")

def find_free_port(start_port=5000):
    """Trova una porta libera a partire dalla porta specificata"""
    import socket
    
    for port in range(start_port, start_port + 10):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    
    # Se non trova nessuna porta libera, usa la porta originale
    return start_port

def graceful_shutdown():
    """Shutdown graceful dell'applicazione"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            log_info("Scheduler fermato correttamente")
    except Exception as e:
        log_error(f"Errore durante shutdown scheduler: {e}")

# Registra cleanup per shutdown graceful
atexit.register(graceful_shutdown)

# Inizializza e avvia lo scheduler
try:
    restart_scheduler()
    log_success("Scheduler inizializzato correttamente")
except Exception as e:
    log_error(f"Errore inizializzazione scheduler: {e}")

if __name__ == '__main__':
    try:
        print_startup_info()
        
        # Configurazione app sicura
        app_host = os.getenv('APP_HOST', '127.0.0.1')  # Solo localhost di default
        requested_port = int(os.getenv('APP_PORT', '5001'))
        app_debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'  # Debug FALSE di default
        
        # In produzione, disabilita debug mode
        if os.getenv('FLASK_ENV') == 'production':
            app_debug = False
        
        # Trova porta libera se quella richiesta è occupata
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((app_host, requested_port))
            app_port = requested_port
        except OSError:
            log_warning(f"Porta {requested_port} occupata, cercando porta alternativa...")
            app_port = find_free_port(requested_port)
            if app_port != requested_port:
                log_info(f"Usando porta alternativa: {app_port}")
        
        # Aggiorna info di startup con porta effettiva
        if app_port != requested_port:
            print(f"\n[INFO] Applicazione disponibile su: http://{app_host}:{app_port}")
        
        # Configura Flask per gestire shutdown graceful su Windows
        if sys.platform.startswith('win'):
            # Su Windows, usa threaded=True per evitare problemi con scheduler
            app.run(debug=app_debug, host=app_host, port=app_port, threaded=True, use_reloader=False)
        else:
            # Su Linux/Mac, configurazione standard
            app.run(debug=app_debug, host=app_host, port=app_port, threaded=True)
            
    except KeyboardInterrupt:
        log_info("Applicazione fermata dall'utente")
        graceful_shutdown()
    except Exception as e:
        log_error(f"Errore avvio applicazione: {e}")
        graceful_shutdown()
        sys.exit(1)
                