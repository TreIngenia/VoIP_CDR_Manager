import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging sicuro
# Usa il nuovo sistema di logging standardizzato
from logger_config import get_logger, log_success, log_error, log_warning, log_info

# Inizializza logging
# logger = get_logger(__name__)

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
            'ftp_port': os.getenv('FTP_PORT', ''),
            'ftp_user': os.getenv('FTP_USER', ''),
            'ftp_password': os.getenv('FTP_PASSWORD', ''),
            'ftp_directory': os.getenv('FTP_DIRECTORY', '/'),
            'download_all_files': self._str_to_bool(os.getenv('DOWNLOAD_ALL_FILES', 'false')),
            'specific_filename': os.getenv('SPECIFIC_FILENAME', ''),
            'output_directory': os.getenv('OUTPUT_DIRECTORY', './output'),
            'analytics_output_folder': os.getenv('ANALYTICS_OUTPUT_FOLDER', './output/cdr_analytics'),
            'config_directory': os.getenv('CONFIG_DIRECTORY', 'config'),
            'categories_config_file': os.getenv('CATEGORIES_CONFIG_FILE', 'cdr_categories.json'),
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
            'voip_markup_percent': self._str_to_float(os.getenv('VOIP_MARKUP_PERCENT', '0.0'), 0.0),
            'voip_price_fixed_final': self._str_to_float(os.getenv('VOIP_PRICE_FIXED_FINAL', '0.02'), 0.02),
            'voip_price_mobile_final': self._str_to_float(os.getenv('VOIP_PRICE_MOBILE_FINAL', '0.15'), 0.15),
            'voip_currency': os.getenv('VOIP_CURRENCY', 'EUR'),
            'voip_price_unit': os.getenv('VOIP_PRICE_UNIT', 'per_minute'),
            'schedule_interval_type': os.getenv('SCHEDULE_INTERVAL_TYPE', 'minutes'),
            'schedule_interval_value': self._str_to_int(os.getenv('SCHEDULE_INTERVAL_VALUE', '30'), 30),
            'CONTRACTS_CONFIG_DIRECTORY': os.getenv('CONTRACTS_CONFIG_DIRECTORY', 'config'),
            'CONTRACTS_CONFIG_FILE': os.getenv('CONTRACTS_CONFIG_FILE', 'cdr_contracts.json'),
            'TEMPLATE_FOLDER': os.getenv('TEMPLATE_FOLDER', 'templates'),
            'STATIC_FOLDER': os.getenv('STATIC_FOLDER', 'assets'),
            'STATIC_URL_PATH': os.getenv('STATIC_URL_PATH', '/assets'),
            'FLASK_ENV': os.getenv('FLASK_ENV', 'development'),
            'FLASK_DEBUG': self._str_to_bool(os.getenv('FLASK_DEBUG', 'true')),
            'APP_PORT': self._str_to_int(os.getenv('APP_PORT', '5001'), 5001),
            'APP_HOST': os.getenv('APP_HOST', '127.0.0.1'),
            'BASE_HOST': os.getenv('BASE_HOST', 'http://127.0.0.1'),
        }

    def get_config_file_path(self, filename: str = None) -> Path:
        """
        Restituisce il percorso completo per un file di configurazione
        
        Args:
            filename: Nome del file (se None, usa categories_config_file)
        
        Returns:
            Path completo del file di configurazione
        """
        if filename is None:
            filename = self.config['categories_config_file']
        
        config_dir = Path(self.config['config_directory'])
        return config_dir / filename
    
    def ensure_config_directory(self):
        """Assicura che la directory di configurazione esista"""
        config_dir = Path(self.config['config_directory'])
        config_dir.mkdir(parents=True, exist_ok=True)
        log_info(f"Directory config: {config_dir.resolve()}")
        return config_dir
        
    def _validate_config(self):
        """Valida configurazione"""
        # # Valida directory output
        # output_dir = Path(self.config['output_directory'])
        # if not output_dir.is_absolute():
        #     self.config['output_directory'] = str(Path.cwd() / output_dir)
        
        # Directory di configurazione
        config_dir = self.ensure_config_directory()
        
        # # Directory output
        # output_dir = Path(self.config['output_directory'])
        # if not output_dir.is_absolute():
        #     # Percorso relativo
        #     output_dir = Path.cwd() / output_dir
        
        # try:
        #     output_dir.mkdir(parents=True, exist_ok=True)
        #     self.config['output_directory'] = str(output_dir.resolve())
        #     log_info(f"Directory output: {output_dir.resolve()}")
        # except Exception as e:
        #     log_error(f"Impossibile creare directory output: {e}")
        #     # Fallback
        #     self.config['output_directory'] = str(Path.cwd() / "output")
        output_dir = Path(self.config['output_directory'])

        # Se il path è relativo, usalo così com'è (senza convertirlo in assoluto)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Mantenere il path come è stato fornito (senza .resolve())
            self.config['output_directory'] = str(output_dir)

            log_info(f"Directory output: {output_dir}")
        except Exception as e:
            log_error(f"Impossibile creare directory output: {e}")
            # Fallback a ./output
            fallback = Path("./output")
            fallback.mkdir(parents=True, exist_ok=True)
            self.config['output_directory'] = str(fallback)
        
        # Validazione nome file categorie
        categories_file = self.config['categories_config_file']
        if not categories_file or not categories_file.endswith('.json'):
            log_warning(f"Nome file categorie non valido: {categories_file}")
            self.config['categories_config_file'] = 'cdr_categories.json'

        # Valida pattern file
        if self.config['specific_filename']:
            if not self._validate_filename_pattern(self.config['specific_filename']):
                log_warning(f"Pattern filename potenzialmente non sicuro: {self.config['specific_filename']}")
                self.config['specific_filename'] = ''
        
        # Valida prezzi VoIP
        if self.config['voip_price_fixed'] < 0:
            self.config['voip_price_fixed'] = 0.02
        if self.config['voip_price_mobile'] < 0:
            self.config['voip_price_mobile'] = 0.15
        if self.config['voip_markup_percent'] < 0:
            self.config['voip_markup_percent'] = 0.0
        if self.config['voip_price_fixed_final'] < 0:
            self.config['voip_price_fixed_final'] = 0.02
        if self.config['voip_price_mobile_final'] < 0:
            self.config['voip_price_mobile_final'] = 0.15
            
        # Calcola automaticamente prezzi finali se il markup è cambiato
        self._calculate_final_prices()
        
        # Assicura che i valori numerici siano corretti
        for key in ['schedule_day', 'schedule_hour', 'schedule_minute', 'interval_days']:
            if not isinstance(self.config[key], int):
                self.config[key] = self._str_to_int(self.config[key], 1 if key == 'schedule_day' else 0)
    
    def _validate_filename_pattern(self, pattern):
        """Valida pattern filename per sicurezza"""
        if not pattern:
            return True
        
        # Blocca path traversal
        if '..' in pattern or ('/' in pattern and not pattern.startswith('/')) or '\\' in pattern:
            return False
        
        # Valida caratteri permessi (lettere, numeri, underscore, punto, asterisco, percentuale)
        import re
        allowed_chars = re.compile(r'^[a-zA-Z0-9_.%/*-]+$')
        return bool(allowed_chars.match(pattern))
    
    

    def validate_all_config(self):
        """Valida tutta la configurazione"""
        all_errors = []
        all_errors.extend(self._validate_ftp_config())
        all_errors.extend(self._validate_voip_config())
        
        if all_errors:
            log_warning(f"Errori di validazione configurazione: {all_errors}")
            return False, all_errors
        
        return True, []
    
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
                        log_warning(f"Pattern non sicuro ignorato: {value}")
                        continue
                
                # Conversioni di tipo
                if key in ['schedule_day', 'schedule_hour', 'schedule_minute', 'interval_days', 'schedule_interval_value']:
                    value = self._str_to_int(value, self.config[key])
                elif key in ['voip_price_fixed', 'voip_price_mobile', 'voip_markup_percent', 'voip_price_fixed_final', 'voip_price_mobile_final']:
                    value = self._str_to_float(value, self.config[key])
                elif key == 'download_all_files':
                    value = self._str_to_bool(value, self.config[key])
                
                self.config[key] = value
        
        self._validate_config()
    
    def _calculate_final_prices(self):
        """Calcola automaticamente i prezzi finali basati su prezzo base + ricarico"""
        try:
            markup_percent = self.config.get('voip_markup_percent', 0.0)
            base_fixed = self.config.get('voip_price_fixed', 0.02)
            base_mobile = self.config.get('voip_price_mobile', 0.15)
            
            # Calcola prezzi finali con ricarico
            markup_multiplier = 1 + (markup_percent / 100)
            
            calculated_fixed = base_fixed * markup_multiplier
            calculated_mobile = base_mobile * markup_multiplier
            
            # Aggiorna solo se i prezzi finali non sono stati impostati manualmente
            self.config['voip_price_fixed_final'] = round(calculated_fixed, 4)
            self.config['voip_price_mobile_final'] = round(calculated_mobile, 4)
            
            log_info(f"Prezzi VoIP calcolati - Fisso: {base_fixed} + {markup_percent}% = {calculated_fixed:.4f}, Mobile: {base_mobile} + {markup_percent}% = {calculated_mobile:.4f}")
            
        except Exception as e:
            log_error(f"Errore calcolo prezzi finali VoIP: {e}")
    
    def update_voip_prices(self, base_fixed=None, base_mobile=None, markup_percent=None):
        """Aggiorna prezzi VoIP e ricalcola automaticamente i prezzi finali"""
        if base_fixed is not None:
            self.config['voip_price_fixed'] = self._str_to_float(base_fixed, self.config['voip_price_fixed'])
        if base_mobile is not None:
            self.config['voip_price_mobile'] = self._str_to_float(base_mobile, self.config['voip_price_mobile'])
        if markup_percent is not None:
            self.config['voip_markup_percent'] = self._str_to_float(markup_percent, self.config['voip_markup_percent'])
        
        # Ricalcola prezzi finali
        self._calculate_final_prices()
        
        return {
            'base_fixed': self.config['voip_price_fixed'],
            'base_mobile': self.config['voip_price_mobile'],
            'markup_percent': self.config['voip_markup_percent'],
            'final_fixed': self.config['voip_price_fixed_final'],
            'final_mobile': self.config['voip_price_mobile_final']
        }
    
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

def save_config_to_env(secure_config, app_secret_key):
    """Salva configurazione con backup e validazione"""
    try:
        config = secure_config.get_config()
        
        # Percorso file .env
        env_file = Path('.env')
        
        # Cartella backup
        backup_dir = Path('env_backup')
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Crea backup prima della modifica
        if env_file.exists():
            backup_file = backup_dir / f'.env.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            env_file.rename(backup_file)
            log_info(f"Backup configurazione creato: {backup_file}")
        
        # Contenuto del nuovo file .env
        env_content = f"""# Configurazione aggiornata automaticamente - {datetime.now().isoformat()}
# Parametri di configurazione per accesso ad ODOO
ODOO_URL={config['ODOO_URL']}
ODOO_DB={config['ODOO_DB']}
ODOO_USERNAME={config['ODOO_USERNAME']}
ODOO_API_KEY={config['ODOO_API_KEY']}

# Sicurezza Flask
SECRET_KEY={app_secret_key}

# Configurazione Server FTP
FTP_HOST={config['ftp_host']}
FTP_PORT={config['ftp_port']}
FTP_USER={config['ftp_user']}
FTP_PASSWORD={config['ftp_password']}
FTP_DIRECTORY={config['ftp_directory']}

# Configurazione Download
DOWNLOAD_ALL_FILES={str(config['download_all_files']).lower()}
SPECIFIC_FILENAME={config['specific_filename']}
OUTPUT_DIRECTORY={config['output_directory']}
ANALYTICS_OUTPUT_FOLDER={config['ANALYTICS_OUTPUT_FOLDER']}
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

# Configurazione Schedulazione Precisa
SCHEDULE_INTERVAL_TYPE={config.get('schedule_interval_type', 'minutes')}
SCHEDULE_INTERVAL_VALUE={config.get('schedule_interval_value', 30)}

# Configurazione Prezzi VoIP
VOIP_PRICE_FIXED={config['voip_price_fixed']}
VOIP_PRICE_MOBILE={config['voip_price_mobile']}
VOIP_MARKUP_PERCENT={config['voip_markup_percent']}
VOIP_PRICE_FIXED_FINAL={config['voip_price_fixed_final']}
VOIP_PRICE_MOBILE_FINAL={config['voip_price_mobile_final']}
VOIP_CURRENCY={config['voip_currency']}
VOIP_PRICE_UNIT={config['voip_price_unit']}

# Configurazione elenco cotratti
CONTRACTS_CONFIG_DIRECTORY={config.get('CONTRACTS_CONFIG_DIRECTORY', 'config')}
CONTRACTS_CONFIG_FILE={config.get('CONTRACTS_CONFIG_FILE', 'cdr_contracts.json')}

#Templates
TEMPLATE_FOLDER={config.get('TEMPLATE_FOLDER', 'templates')}
STATIC_FOLDER={config.get('STATIC_FOLDER', 'assets')}
STATIC_URL_PATH={config.get('STATIC_URL_PATH', '/assets')}

# Configurazione Applicazione
FLASK_ENV={config.get('FLASK_ENV', 'development')}
FLASK_DEBUG={str(config.get('FLASK_DEBUG', True)).lower()}
APP_PORT={config.get('APP_PORT', 5001)}
APP_HOST={config.get('APP_HOST', '127.0.0.1')}
BASE_HOST={config.get('BASE_HOST', 'http://127.0.0.1')}

"""
        # Scrittura dei file .env e .env.local
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)

        if not sys.platform.startswith('win'):
            os.chmod('.env', 0o600)

        with open('.env.local', 'w', encoding='utf-8') as f:
            f.write(env_content)

        log_success("Configurazione salvata correttamente")

        # Cleanup backup vecchi
        cleanup_old_backups(backup_dir)

    except Exception as e:
        log_error(f"Errore nel salvataggio configurazione: {e}")

def cleanup_old_backups(backup_dir: Path, max_backups=5):
    """Mantiene solo gli ultimi `max_backups` file nella cartella di backup"""
    try:
        backups = sorted(backup_dir.glob('.env.backup.*'), key=os.path.getmtime, reverse=True)
        for old_backup in backups[max_backups:]:
            old_backup.unlink()
            log_info(f"Backup eliminato: {old_backup}")
    except Exception as e:
        log_error(f"Errore durante la pulizia dei backup: {e}")



def load_config_from_env_local(secure_config):
    """Carica configurazione da .env.local se esiste e è più recente di .env"""
    try:
        env_file = Path('.env')
        env_local_file = Path('.env.local')
        
        # Se .env.local esiste ed è più recente di .env
        if (env_local_file.exists() and 
            env_file.exists() and 
            env_local_file.stat().st_mtime > env_file.stat().st_mtime):
            
            log_info("Caricamento configurazione da .env.local (più recente)")
            
            # Ricarica le variabili d'ambiente da .env.local
            try:
                from dotenv import load_dotenv
                load_dotenv('.env.local', override=True)
                
                # Aggiorna CONFIG con i nuovi valori
                updates = {
                    'ftp_host': os.getenv('FTP_HOST', ''),
                    'ftp_port': os.getenv('FTP_PORT', ''),
                    'ftp_user': os.getenv('FTP_USER', ''),
                    'ftp_password': os.getenv('FTP_PASSWORD', ''),
                    'ftp_directory': os.getenv('FTP_DIRECTORY', '/'),
                    'download_all_files': secure_config._str_to_bool(os.getenv('DOWNLOAD_ALL_FILES', 'false')),
                    'specific_filename': os.getenv('SPECIFIC_FILENAME', ''),
                    'file_naming_pattern': os.getenv('FILE_NAMING_PATTERN', 'monthly'),
                    'custom_pattern': os.getenv('CUSTOM_PATTERN', ''),
                    'schedule_type': os.getenv('SCHEDULE_TYPE', 'monthly'),
                    'schedule_day': secure_config._str_to_int(os.getenv('SCHEDULE_DAY', '1'), 1),
                    'schedule_hour': secure_config._str_to_int(os.getenv('SCHEDULE_HOUR', '9'), 9),
                    'schedule_minute': secure_config._str_to_int(os.getenv('SCHEDULE_MINUTE', '0'), 0),
                    'interval_days': secure_config._str_to_int(os.getenv('INTERVAL_DAYS', '30'), 30),
                    'cron_expression': os.getenv('CRON_EXPRESSION', '0 9 1 * *'),
                    'filter_pattern': os.getenv('FILTER_PATTERN', ''),
                }
                
                secure_config.update_config(updates)
                log_info("Configurazione aggiornata da .env.local")
                
            except ImportError:
                log_warning("python-dotenv non disponibile per .env.local")
                
    except Exception as e:
        log_error(f"Errore nel caricamento da .env.local: {e}")