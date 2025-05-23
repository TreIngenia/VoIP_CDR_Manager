import os
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

# Funzione helper per convertire stringhe in booleani
def str_to_bool(value, default=False):
    """Converte una stringa in booleano"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return default

# Funzione helper per convertire stringhe in interi
def str_to_int(value, default=0):
    """Converte una stringa in intero"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurazione Flask da variabili d'ambiente
app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key-in-production')

# Funzione helper per convertire stringhe in float
def str_to_float(value, default=0.0):
    """Converte una stringa in float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default
    
# Configurazione globale da variabili d'ambiente con valori di default
CONFIG = {
    'ODOO_URL': os.getenv('ODOO_URL', ''),
    'ODOO_DB': os.getenv('ODOO_DB', ''),
    'ODOO_USERNAME': os.getenv('ODOO_USERNAME', ''),
    'ODOO_API_KEY': os.getenv('ODOO_API_KEY', ''),
    'ftp_host': os.getenv('FTP_HOST', ''),
    'ftp_user': os.getenv('FTP_USER', ''),
    'ftp_password': os.getenv('FTP_PASSWORD', ''),
    'ftp_directory': os.getenv('FTP_DIRECTORY', '/'),
    'download_all_files': str_to_bool(os.getenv('DOWNLOAD_ALL_FILES', 'false')),
    'specific_filename': os.getenv('SPECIFIC_FILENAME', ''),
    'output_directory': os.getenv('OUTPUT_DIRECTORY', 'output'),
    'file_naming_pattern': os.getenv('FILE_NAMING_PATTERN', 'monthly'),
    'custom_pattern': os.getenv('CUSTOM_PATTERN', ''),
    'schedule_type': os.getenv('SCHEDULE_TYPE', 'monthly'),
    'schedule_day': str_to_int(os.getenv('SCHEDULE_DAY', '1'), 1),
    'schedule_hour': str_to_int(os.getenv('SCHEDULE_HOUR', '9'), 9),
    'schedule_minute': str_to_int(os.getenv('SCHEDULE_MINUTE', '0'), 0),
    'interval_days': str_to_int(os.getenv('INTERVAL_DAYS', '30'), 30),
    'cron_expression': os.getenv('CRON_EXPRESSION', '0 9 1 * *'),
    'filter_pattern': os.getenv('FILTER_PATTERN', ''),
    'voip_price_fixed': str_to_float(os.getenv('VOIP_PRICE_FIXED', '0.02'), 0.02),
    'voip_price_mobile': str_to_float(os.getenv('VOIP_PRICE_MOBILE', '0.15'), 0.15),
    'voip_currency': os.getenv('VOIP_CURRENCY', 'EUR'),
    'voip_price_unit': os.getenv('VOIP_PRICE_UNIT', 'per_minute'),  # 'per_minute', 'per_second'
}

def ensure_config_types():
    """Assicura che i tipi di dati nella configurazione siano corretti"""
    try:
        # Tipi numerici interi
        CONFIG['schedule_day'] = int(CONFIG['schedule_day'])
        CONFIG['schedule_hour'] = int(CONFIG['schedule_hour'])
        CONFIG['schedule_minute'] = int(CONFIG['schedule_minute'])
        CONFIG['interval_days'] = int(CONFIG['interval_days'])
        
        # Tipi booleani
        CONFIG['download_all_files'] = bool(CONFIG['download_all_files'])
        
        # Tipi float per prezzi VoIP
        CONFIG['voip_price_fixed'] = float(CONFIG['voip_price_fixed'])
        CONFIG['voip_price_mobile'] = float(CONFIG['voip_price_mobile'])
        
        logger.info("✅ Tipi di configurazione verificati (inclusi prezzi VoIP)")
    except (ValueError, TypeError) as e:
        logger.warning(f"Errore nella conversione dei tipi di configurazione: {e}")
        # Ripristina valori di default
        CONFIG['schedule_day'] = 1
        CONFIG['schedule_hour'] = 9
        CONFIG['schedule_minute'] = 0
        CONFIG['interval_days'] = 30
        CONFIG['download_all_files'] = False
        CONFIG['voip_price_fixed'] = 0.02
        CONFIG['voip_price_mobile'] = 0.15

def save_config_to_env():
    """Salva la configurazione corrente nel file .env principale"""
    try:
        env_content = f"""# Configurazione aggiornata automaticamente - {datetime.now().isoformat()}

ODOO_URL={CONFIG['ODOO_URL']}
ODOO_DB={CONFIG['ODOO_DB']}
ODOO_USERNAME={CONFIG['ODOO_USERNAME']}
ODOO_API_KEY={CONFIG['ODOO_API_KEY']}

SECRET_KEY={app.secret_key}

# Configurazione FTP
FTP_HOST={CONFIG['ftp_host']}
FTP_USER={CONFIG['ftp_user']}
FTP_PASSWORD={CONFIG['ftp_password']}
FTP_DIRECTORY={CONFIG['ftp_directory']}

# Configurazione Download
DOWNLOAD_ALL_FILES={str(CONFIG['download_all_files']).lower()}
SPECIFIC_FILENAME={CONFIG['specific_filename']}
OUTPUT_DIRECTORY={CONFIG['output_directory']}
FILE_NAMING_PATTERN={CONFIG['file_naming_pattern']}
CUSTOM_PATTERN={CONFIG['custom_pattern']}
FILTER_PATTERN={CONFIG.get('filter_pattern', '')}

# Configurazione Schedulazione
SCHEDULE_TYPE={CONFIG['schedule_type']}
SCHEDULE_DAY={CONFIG['schedule_day']}
SCHEDULE_HOUR={CONFIG['schedule_hour']}
SCHEDULE_MINUTE={CONFIG['schedule_minute']}
INTERVAL_DAYS={CONFIG['interval_days']}
CRON_EXPRESSION={CONFIG['cron_expression']}

# Configurazione Prezzi VoIP
VOIP_PRICE_FIXED={CONFIG['voip_price_fixed']}
VOIP_PRICE_MOBILE={CONFIG['voip_price_mobile']}
VOIP_CURRENCY={CONFIG['voip_currency']}
VOIP_PRICE_UNIT={CONFIG['voip_price_unit']}
"""
        
        # Salva nel file .env principale
        with open('.env', 'w') as f:
            f.write(env_content)
        
        # Mantieni anche la copia locale per backup
        with open('.env.local', 'w') as f:
            f.write(env_content)
        
        logger.info("✅ Configurazione salvata in .env e .env.local (inclusi prezzi VoIP)")
        
    except Exception as e:
        logger.error(f"Errore nel salvataggio configurazione: {e}")

def load_config_from_env_local():
    """Carica configurazione da .env.local se esiste e è più recente di .env"""
    try:
        from pathlib import Path
        import os
        
        env_file = Path('.env')
        env_local_file = Path('.env.local')
        
        # Se .env.local esiste ed è più recente di .env
        if (env_local_file.exists() and 
            env_file.exists() and 
            env_local_file.stat().st_mtime > env_file.stat().st_mtime):
            
            logger.info("📁 Caricamento configurazione da .env.local (più recente)")
            
            # Ricarica le variabili d'ambiente da .env.local
            from dotenv import load_dotenv
            load_dotenv('.env.local', override=True)
            
            # Aggiorna CONFIG con i nuovi valori
            CONFIG.update({
                'ftp_host': os.getenv('FTP_HOST', ''),
                'ftp_user': os.getenv('FTP_USER', ''),
                'ftp_password': os.getenv('FTP_PASSWORD', ''),
                'ftp_directory': os.getenv('FTP_DIRECTORY', '/'),
                'download_all_files': str_to_bool(os.getenv('DOWNLOAD_ALL_FILES', 'false')),
                'specific_filename': os.getenv('SPECIFIC_FILENAME', ''),
                'output_directory': os.getenv('OUTPUT_DIRECTORY', 'output'),
                'file_naming_pattern': os.getenv('FILE_NAMING_PATTERN', 'monthly'),
                'custom_pattern': os.getenv('CUSTOM_PATTERN', ''),
                'schedule_type': os.getenv('SCHEDULE_TYPE', 'monthly'),
                'schedule_day': str_to_int(os.getenv('SCHEDULE_DAY', '1'), 1),
                'schedule_hour': str_to_int(os.getenv('SCHEDULE_HOUR', '9'), 9),
                'schedule_minute': str_to_int(os.getenv('SCHEDULE_MINUTE', '0'), 0),
                'interval_days': str_to_int(os.getenv('INTERVAL_DAYS', '30'), 30),
                'cron_expression': os.getenv('CRON_EXPRESSION', '0 9 1 * *'),
                'filter_pattern': os.getenv('FILTER_PATTERN', ''),
            })
            
            logger.info("✅ Configurazione aggiornata da .env.local")
            
    except Exception as e:
        logger.error(f"Errore nel caricamento da .env.local: {e}")


# Scheduler globale
scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

       
class FTPProcessor:
    """Classe per gestire operazioni FTP e conversioni file"""
    def match_pattern(self, filename, pattern):
        """
        Verifica se un filename corrisponde al pattern specificato
        Supporta wildcard (*,?) e variabili temporali (%Y,%m,%d,%H,%M,%S)
        
        Args:
            filename: nome del file da verificare
            pattern: pattern di ricerca (supporta *, ?, %Y, %m, %d, %H, %M, %S)
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
        
        Args:
            pattern: pattern con variabili temporali (es: RIV_*_MESE_%m_*.CDR)
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
        
    def filter_files_by_pattern(self, files, pattern):
        """
        Filtra una lista di file basandosi sul pattern
        
        Args:
            files: lista di nomi file
            pattern: pattern di filtro
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

    def generate_filename_with_filter(self, pattern_type='monthly', custom_pattern='', filter_pattern=''):
        """
        Genera nome file o pattern di filtro basato sulla configurazione
        
        Args:
            pattern_type: tipo di pattern base
            custom_pattern: pattern personalizzato
            filter_pattern: pattern di filtro con wildcard
        """
        # Se è specificato un filtro pattern, usalo direttamente
        if filter_pattern:
            logger.info(f"Usando filtro pattern: {filter_pattern}")
            return filter_pattern
        
        # Altrimenti genera il nome come prima
        return self.generate_filename(pattern_type, custom_pattern)
    
    def __init__(self, config):
        self.config = config
        self.ensure_output_directory()
    
    def ensure_output_directory(self):
        """Crea la directory di output se non esiste"""
        output_dir = Path(self.config['output_directory'])
        output_dir.mkdir(exist_ok=True)
    
    # def generate_filename(self, pattern_type='monthly', custom_pattern=''):
    #     """
    #     Genera il nome del file basato sul pattern specificato
        
    #     Args:
    #         pattern_type: 'monthly', 'weekly', 'daily', 'custom'
    #         custom_pattern: pattern personalizzato se pattern_type è 'custom'
    #     """
    #     now = datetime.now()
        
    #     patterns = {
    #         'monthly': f"report_{now.strftime('%Y_%m')}.csv",
    #         'weekly': f"report_{now.strftime('%Y_W%U')}.csv",
    #         'daily': f"report_{now.strftime('%Y_%m_%d')}.csv",
    #         'quarterly': f"report_{now.strftime('%Y')}_Q{(now.month-1)//3+1}.csv",
    #         'yearly': f"report_{now.strftime('%Y')}.csv"
    #     }
        
    #     if pattern_type == 'custom' and custom_pattern:
    #         try:
    #             return now.strftime(custom_pattern)
    #         except ValueError as e:
    #             logger.error(f"Errore nel pattern personalizzato: {e}")
    #             return patterns['monthly']
        
    #     return patterns.get(pattern_type, patterns['monthly'])
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

    
    def connect_ftp(self):
        """Stabilisce connessione FTP"""
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.config['ftp_host'])
            ftp.login(self.config['ftp_user'], self.config['ftp_password'])
            
            if self.config['ftp_directory'] != '/':
                ftp.cwd(self.config['ftp_directory'])
            
            logger.info(f"Connesso al server FTP: {self.config['ftp_host']}")
            return ftp
        except Exception as e:
            logger.error(f"Errore connessione FTP: {e}")
            raise
    
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
    
    def download_file_from_ftp(self, filename, local_path):
        """Scarica un singolo file dal server FTP"""
        try:
            ftp = self.connect_ftp()
            
            with open(local_path, 'wb') as local_file:
                ftp.retrbinary(f'RETR {filename}', local_file.write)
            
            ftp.quit()
            logger.info(f"File scaricato: {filename} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"Errore nel download di {filename}: {e}")
            return False
    
    # def download_files(self):
    #     """Scarica i file dal server FTP basandosi sulla configurazione"""
    #     downloaded_files = []
        
    #     try:
    #         if self.config['download_all_files']:
    #             # Scarica tutti i file
    #             files = self.list_ftp_files()
    #             for filename in files:
    #                 local_path = Path(self.config['output_directory']) / filename
    #                 if self.download_file_from_ftp(filename, local_path):
    #                     downloaded_files.append(str(local_path))
    #         else:
    #             # Scarica file specifico basato sul pattern
    #             if self.config['specific_filename']:
    #                 filename = self.config['specific_filename']
    #             else:
    #                 filename = self.generate_filename(
    #                     self.config['file_naming_pattern'],
    #                     self.config.get('custom_pattern', '')
    #                 )
                
    #             local_path = Path(self.config['output_directory']) / filename
    #             if self.download_file_from_ftp(filename, local_path):
    #                 downloaded_files.append(str(local_path))
            
    #         return downloaded_files
    #     except Exception as e:
    #         logger.error(f"Errore nel processo di download: {e}")
    #         return []
    def download_files(self):
        """Scarica i file dal server FTP basandosi sulla configurazione"""
        downloaded_files = []
        
        try:
            # Debug: stampa configurazione
            logger.info(f"Configurazione download: download_all_files={self.config['download_all_files']}")
            
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
                
                if self.download_file_from_ftp(filename, local_path):
                    downloaded_files.append(str(local_path))
                    logger.info(f"✅ Download completato: {filename}")
                else:
                    logger.error(f"❌ Download fallito: {filename}")
            
            logger.info(f"Download completato. File scaricati: {len(downloaded_files)}")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Errore nel processo di download: {e}")
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

# Route Flask
@app.route('/')
def index():
    """Pagina principale"""
    # Assicurati che i valori numerici siano effettivamente numeri
    config_safe = CONFIG.copy()
    for key in ['schedule_day', 'schedule_hour', 'schedule_minute', 'interval_days']:
        try:
            config_safe[key] = int(config_safe[key])
        except (ValueError, TypeError):
            # Valori di default se la conversione fallisce
            defaults = {
                'schedule_day': 1,
                'schedule_hour': 9,
                'schedule_minute': 0,
                'interval_days': 30
            }
            config_safe[key] = defaults[key]
    
    return render_template('index.html', config=config_safe)

@app.route('/config', methods=['GET', 'POST'])
def config_page():
    """Pagina di configurazione"""
    if request.method == 'POST':
        # Debug: stampa tutti i dati del form
        logger.info("Dati form ricevuti:")
        for key, value in request.form.items():
            logger.info(f"  {key}: {value}")
        
        # Aggiorna configurazione
        for key in CONFIG.keys():
            if key in request.form:
                if key == 'download_all_files':
                    # Gestione speciale per checkbox
                    CONFIG[key] = request.form.get(key) == 'on'
                    logger.info(f"Checkbox {key} impostato a: {CONFIG[key]}")
                elif key in ['schedule_day', 'schedule_hour', 'schedule_minute', 'interval_days']:
                    try:
                        CONFIG[key] = int(request.form.get(key, CONFIG[key]))
                    except (ValueError, TypeError):
                        CONFIG[key] = CONFIG[key]  # Mantieni valore precedente
                elif key in ['voip_price_fixed', 'voip_price_mobile']:
                    try:
                        CONFIG[key] = float(request.form.get(key, CONFIG[key]))
                        logger.info(f"Prezzo VoIP {key} impostato a: {CONFIG[key]}")
                    except (ValueError, TypeError):
                        CONFIG[key] = CONFIG[key]  # Mantieni valore precedente
                else:
                    CONFIG[key] = request.form.get(key, CONFIG[key])
            else:
                # Per i checkbox non selezionati
                if key == 'download_all_files':
                    CONFIG[key] = False
                    logger.info(f"Checkbox {key} non presente nel form, impostato a: False")
        
        # Log configurazione finale
        logger.info(f"Configurazione aggiornata - prezzi VoIP: fisso={CONFIG['voip_price_fixed']}, mobile={CONFIG['voip_price_mobile']}")
        
        # Salva la configurazione aggiornata
        save_config_to_env()
        
        # Aggiorna il processore con la nuova configurazione
        global processor
        processor = FTPProcessor(CONFIG)
        
        # Riavvia lo scheduler se necessario
        restart_scheduler()
        
        return redirect(url_for('config_page'))
    
    # Assicurati che i valori numerici siano corretti
    config_safe = CONFIG.copy()
    for key in ['schedule_day', 'schedule_hour', 'schedule_minute', 'interval_days']:
        try:
            config_safe[key] = int(config_safe[key])
        except (ValueError, TypeError):
            defaults = {
                'schedule_day': 1,
                'schedule_hour': 9,
                'schedule_minute': 0,
                'interval_days': 30
            }
            config_safe[key] = defaults[key]
    
    # Assicurati che i prezzi VoIP siano float
    for key in ['voip_price_fixed', 'voip_price_mobile']:
        try:
            config_safe[key] = float(config_safe[key])
        except (ValueError, TypeError):
            defaults = {
                'voip_price_fixed': 0.02,
                'voip_price_mobile': 0.15
            }
            config_safe[key] = defaults[key]
    
    return render_template('config.html', config=config_safe)

@app.route('/manual_run')
def manual_run():
    """Esecuzione manuale del processo"""
    try:
        result = processor.process_files()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/test_ftp')
def test_ftp():
    """Test connessione FTP"""
    try:
        files = processor.list_ftp_files()
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logs')
def logs():
    """Visualizzazione log"""
    try:
        with open('app.log', 'r') as f:
            log_content = f.read()
        return f"<pre>{log_content}</pre>"
    except:
        return "Log non disponibile"

@app.route('/status')
def status():
    """Stato dell'applicazione e prossime esecuzioni"""
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
        with open(log_file, 'r') as f:
            last_execution = json.load(f)
    
    # Non esporre password nel JSON di stato
    safe_config = CONFIG.copy()
    if 'ftp_password' in safe_config:
        safe_config['ftp_password'] = '***HIDDEN***'
    
    return jsonify({
        'scheduled_jobs': jobs,
        'last_execution': last_execution,
        'config': safe_config
    })

@app.route('/env_status')
def env_status():
    """Mostra lo stato delle variabili d'ambiente (senza password)"""
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

@app.route('/test_pattern', methods=['POST'])
def test_pattern():
    """Test pattern di filtro file"""
    try:
        data = request.get_json()
        pattern = data.get('pattern', '')
        
        if not pattern:
            return jsonify({'success': False, 'message': 'Pattern non specificato'})
        
        # Testa il pattern
        result = processor.test_pattern_matching(pattern)
        
        if 'error' in result:
            return jsonify({'success': False, 'message': result['error']})
        
        return jsonify({
            'success': True,
            'pattern': result['pattern'],
            'total_files': result['total_files'],
            'matching_files': result['matching_files'],
            'match_count': result['match_count']
        })
        
    except Exception as e:
        logger.error(f"Errore nel test pattern: {e}")
        return jsonify({'success': False, 'message': str(e)})

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
    
# AGGIUNGI ANCHE QUESTA ROUTE PER OTTENERE TUTTI I FILE SUL SERVER
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
        
def restart_scheduler():
    """Riavvia lo scheduler con la nuova configurazione"""
    # Assicura che i tipi siano corretti prima di usare la configurazione
    ensure_config_types()
    
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
            logger.info(f"✅ Schedulazione mensile: giorno {CONFIG['schedule_day']} alle {CONFIG['schedule_hour']}:{CONFIG['schedule_minute']:02d}")
            
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
            logger.info(f"✅ Schedulazione settimanale: giorno {CONFIG['schedule_day']} alle {CONFIG['schedule_hour']}:{CONFIG['schedule_minute']:02d}")
            
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
            logger.info(f"✅ Schedulazione giornaliera alle {CONFIG['schedule_hour']}:{CONFIG['schedule_minute']:02d}")
            
        elif CONFIG['schedule_type'] == 'interval':
            # Usa il vecchio sistema (giorni)
            scheduler.add_job(
                func=scheduled_job,
                trigger=IntervalTrigger(days=CONFIG['interval_days']),
                id='interval_job',
                replace_existing=True
            )
            logger.info(f"✅ Schedulazione a intervallo: ogni {CONFIG['interval_days']} giorni")
            
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
                logger.info(f"✅ Schedulazione precisa: ogni {interval_value} minuti")
                
            elif interval_type == 'hours':
                scheduler.add_job(
                    func=scheduled_job,
                    trigger=IntervalTrigger(hours=interval_value),
                    id='interval_precise_job',
                    replace_existing=True
                )
                logger.info(f"✅ Schedulazione precisa: ogni {interval_value} ore")
                
            elif interval_type == 'seconds':
                scheduler.add_job(
                    func=scheduled_job,
                    trigger=IntervalTrigger(seconds=interval_value),
                    id='interval_precise_job',
                    replace_existing=True
                )
                logger.info(f"✅ Schedulazione precisa: ogni {interval_value} secondi")
                
            else:  # days
                scheduler.add_job(
                    func=scheduled_job,
                    trigger=IntervalTrigger(days=interval_value),
                    id='interval_precise_job',
                    replace_existing=True
                )
                logger.info(f"✅ Schedulazione precisa: ogni {interval_value} giorni")
                
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
                logger.info(f"✅ Schedulazione cron: {CONFIG['cron_expression']}")
            else:
                logger.error(f"❌ Espressione cron non valida: {CONFIG['cron_expression']}")
                
        # Mostra prossima esecuzione
        jobs = scheduler.get_jobs()
        if jobs:
            next_run = jobs[0].next_run_time
            if next_run:
                logger.info(f"🕐 Prossima esecuzione: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
    except Exception as e:
        logger.error(f"❌ Errore nella configurazione scheduler: {e}")

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

# SHORTCUT PER LE CONFIGURAZIONI PIÙ COMUNI

def set_schedule_every_minute():
    """Configura esecuzione ogni minuto"""
    CONFIG['schedule_type'] = 'interval_precise'
    CONFIG['schedule_interval_type'] = 'minutes'
    CONFIG['schedule_interval_value'] = 1
    restart_scheduler()
    logger.info("⏰ Schedulazione impostata: ogni minuto")

def set_schedule_every_hour():
    """Configura esecuzione ogni ora"""
    CONFIG['schedule_type'] = 'interval_precise'
    CONFIG['schedule_interval_type'] = 'hours'
    CONFIG['schedule_interval_value'] = 1
    restart_scheduler()
    logger.info("⏰ Schedulazione impostata: ogni ora")

def set_schedule_every_30_minutes():
    """Configura esecuzione ogni 30 minuti"""
    CONFIG['schedule_type'] = 'interval_precise'
    CONFIG['schedule_interval_type'] = 'minutes'
    CONFIG['schedule_interval_value'] = 30
    restart_scheduler()
    logger.info("⏰ Schedulazione impostata: ogni 30 minuti")

def set_schedule_every_10_seconds():
    """Configura esecuzione ogni 10 secondi (per test)"""
    CONFIG['schedule_type'] = 'interval_precise'
    CONFIG['schedule_interval_type'] = 'seconds'
    CONFIG['schedule_interval_value'] = 10
    restart_scheduler()
    logger.info("⏰ Schedulazione impostata: ogni 10 secondi (TEST)")
        
def print_startup_info():
    """Stampa informazioni di avvio"""
    print("\n" + "="*50)
    print("🚀 FTP SCHEDULER APP AVVIATA")
    print("="*50)
    print(f"📊 Dashboard: http://localhost:{os.getenv('APP_PORT', '5000')}")
    print(f"⚙️  Configurazione: http://localhost:{os.getenv('APP_PORT', '5000')}/config")
    print(f"📋 Log: http://localhost:{os.getenv('APP_PORT', '5000')}/logs")
    print(f"📊 Stato: http://localhost:{os.getenv('APP_PORT', '5000')}/status")
    print(f"🔧 Variabili ENV: http://localhost:{os.getenv('APP_PORT', '5000')}/env_status")
    print("="*50)
    print(f"🗂️  Directory output: {CONFIG['output_directory']}")
    print(f"📡 Server FTP: {CONFIG['ftp_host'] if CONFIG['ftp_host'] else '(non configurato)'}")
    print(f"📅 Schedulazione: {CONFIG['schedule_type']}")
    print("="*50 + "\n")

# Inizializza i tipi di configurazione e avvia lo scheduler
ensure_config_types()
# Chiama questa funzione dopo aver caricato la configurazione iniziale
load_config_from_env_local()
restart_scheduler()

if __name__ == '__main__':
    print_startup_info()
    
    # Configurazione app da variabili d'ambiente
    app_host = os.getenv('APP_HOST', '0.0.0.0')
    app_port = int(os.getenv('APP_PORT', '5000'))
    app_debug = str_to_bool(os.getenv('FLASK_DEBUG', 'true'))
    
    app.run(debug=app_debug, host=app_host, port=app_port)