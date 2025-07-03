"""
Script per scaricare file da FTP basato su template di pattern
Esempio template: RIV_12345_MESE_%m_%Y-*.CDR
"""

import ftplib
import re
import os
from datetime import datetime
import fnmatch
from pathlib import Path
import pandas as pd
import json
from collections import OrderedDict
# import logging
from logger_config import get_logger
# from exception_handler import handle_exceptions, APIResponse, ExceptionHandler
# from performance_monitor import get_performance_monitor
# from pathlib import Path
# from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, Response
from utils import extract_data_from_api
logger = get_logger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()  # Carica variabili dal file .env
    print("📁 File .env caricato")
    FTP_HOST=os.getenv('FTP_HOST')
    FTP_PORT=int(os.getenv('FTP_PORT'))
    FTP_USER=os.getenv('FTP_USER')
    FTP_PASSWORD=os.getenv('FTP_PASSWORD')
    FTP_DIRECTORY=os.getenv('FTP_DIRECTORY')
    SPECIFIC_FILENAME=os.getenv('SPECIFIC_FILENAME')
    OUTPUT_DIRECTORY=os.getenv('OUTPUT_DIRECTORY')
    
except ImportError:
    print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")

class FTPDownloader:
    def __init__(self, secureconfig): 
    # def __init__(self, host, username, password, port=21):
        """
        Inizializza la connessione FTP
        
        Args:
            host (str): Indirizzo del server FTP
            username (str): Nome utente
            password (str): Password
            port (int): Porta FTP (default 21)
        """
        config = secureconfig.get_config()
        self.secureconfig = secureconfig
        self.config = secureconfig.get_config()
        self.host = config.get('ftp_host')
        self.username = config.get('ftp_user')
        self.password = config.get('ftp_password')
        self.port = int(config.get('ftp_port'))
        self.ftp = None

        self.cdr_analytics = None
        self._init_cdr_system()

       
    
    # === SEZIONE CDR (nuovo) ===
    def _is_cdr_file(self, json_file_path): pass
    def _process_cdr_files(self, converted_files): pass
    def _init_cdr_system(self): pass
    
    # === METODO PRINCIPALE (sostituisce process_files) ===
    def process_complete_workflow(self):
        """
        Nuovo metodo che sostituisce process_files():
        1. Download con pattern avanzati
        2. Conversione automatica  
        3. Processing CDR automatico
        4. Risultato unificato
        """
        pass

    def _init_cdr_system(self):

        # secure_config = self.config.get_config() # ✅ Crea nuovo oggetto
        from cdr_categories_enhanced import CDRAnalyticsEnhanced
        self.cdr_analytics = CDRAnalyticsEnhanced(
            self.config.get('output_directory'), 
            secure_config=self.secureconfig  # Passa secure_config
        )    
    
    def connetti(self):
        """Stabilisce la connessione al server FTP"""
        try:
            print(f"Connessione a {self.host}:{self.port}...")
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port)
            self.ftp.login(self.username, self.password)
            print("Connessione FTP stabilita con successo!")
            return True
        except Exception as e:
            print(f"Errore nella connessione FTP: {e}")
            return False
    
    def disconnetti(self):
        """Chiude la connessione FTP"""
        if self.ftp:
            try:
                self.ftp.quit()
                print("Connessione FTP chiusa.")
            except:
                self.ftp.close()
    
    def espandi_template(self, template, data=None):
        """
        Espande un template con data e wildcards
        
        Args:
            template (str): Template come RIV_12345_MESE_%m_%Y-*.CDR
            data (datetime): Data da usare (default oggi)
        
        Returns:
            str: Pattern espanso
        """
        if data is None:
            data = datetime.now()
        
        # Espande le variabili di data
        pattern = data.strftime(template)
        return pattern
    
    def lista_file_ftp(self, directory="/"):
        """
        Ottiene la lista di tutti i file nella directory FTP
        
        Args:
            directory (str): Directory da esplorare
            
        Returns:
            list: Lista dei nomi dei file
        """
        try:
            # Cambia directory
            self.ftp.cwd(directory)
            
            # Ottiene la lista dei file
            file_list = []
            self.ftp.retrlines('NLST', file_list.append)
            
            print(f"Trovati {len(file_list)} file nella directory {directory}")
            return file_list
            
        except Exception as e:
            print(f"Errore nel listare i file: {e}")
            return []
    
    def filtra_file_per_pattern(self, file_list, pattern):
        """
        Filtra i file che corrispondono al pattern
        
        Args:
            file_list (list): Lista di nomi file
            pattern (str): Pattern con wildcards (es: RIV_12345_MESE_12_2024-*.CDR)
            
        Returns:
            list: File che corrispondono al pattern
        """
        file_corrispondenti = []
        
        for filename in file_list:
            if fnmatch.fnmatch(filename, pattern):
                file_corrispondenti.append(filename)
        
        print(f"File che corrispondono al pattern '{pattern}': {len(file_corrispondenti)}")
        for f in file_corrispondenti:
            print(f"  - {f}")
            
        return file_corrispondenti
    
    def scarica_file(self, nome_file_remoto, cartella_locale="./downloads"):
        """
        Scarica un singolo file dal server FTP
        
        Args:
            nome_file_remoto (str): Nome del file sul server
            cartella_locale (str): Cartella locale dove salvare
            
        Returns:
            bool: True se il download è riuscito
        """
        try:
            # Crea la cartella locale se non esiste
            os.makedirs(cartella_locale, exist_ok=True)
            
            # Percorso completo del file locale
            percorso_locale = os.path.join(cartella_locale, nome_file_remoto)
            
            # Scarica il file
            with open(percorso_locale, 'wb') as file_locale:
                self.ftp.retrbinary(f'RETR {nome_file_remoto}', file_locale.write)
            
            print(f"✓ Scaricato: {nome_file_remoto} -> {percorso_locale}")
            return True
            
        except Exception as e:
            print(f"✗ Errore nello scaricare {nome_file_remoto}: {e}")
            return False
    
    def scarica_per_template(self, template, directory_ftp="/", cartella_locale="./downloads", data=None, test=None):
        """
        Scarica tutti i file che corrispondono al template
        
        Args:
            template (str): Template come RIV_12345_MESE_%m_%Y-*.CDR
            directory_ftp (str): Directory FTP da esplorare
            cartella_locale (str): Cartella locale per i download
            data (datetime): Data per il template (default oggi)
            
        Returns:
            list: Lista dei file scaricati con successo
        """
        print(f"\n=== DOWNLOAD CON TEMPLATE: {template} ===")
        
        # Espande il template
        pattern = self.espandi_template(template, data)
        print(f"Pattern espanso: {pattern}")
        
        # Ottiene la lista dei file
        file_list = self.lista_file_ftp(directory_ftp)
        if not file_list:
            return []
        
        # Filtra i file per pattern
        file_da_scaricare = self.filtra_file_per_pattern(file_list, pattern)
        
        if not file_da_scaricare:
            print("Nessun file trovato che corrisponda al pattern.")
            return []
        
        # Scarica i file
        file_scaricati = []
        if test:
            print(f"\nInizio download di {len(file_da_scaricare)} file...")
            
            for filename in file_da_scaricare:
                    file_scaricati.append(filename)
            
            print(f"\n=== DOWNLOAD COMPLETATO ===")
            print(f"File scaricati con successo: {len(file_scaricati)}/{len(file_da_scaricare)}")
            
            return file_scaricati
            # return "TEST"
        else:
            print(f"\nInizio download di {len(file_da_scaricare)} file...")
            
            for filename in file_da_scaricare:
                if self.scarica_file(filename, cartella_locale):
                    file_scaricati.append(filename)
            
            print(f"\n=== DOWNLOAD COMPLETATO ===")
            print(f"File scaricati con successo: {len(file_scaricati)}/{len(file_da_scaricare)}")
            
            return file_scaricati

    # def runftp(self, get_template, get_test):
    #     from config import SecureConfig
    #     secure_config = SecureConfig()
    #     config = secure_config.get_config()
    #     # print(config)
    #     downloader = FTPDownloader(config)
    #     # """Test connessione FTP"""
    #     try:
    #         # Connettiti
    #         if not downloader.connetti():
    #             return
            
    #         # Scarica i file per template
    #         file_scaricati = downloader.scarica_per_template(
    #             template=get_template,
    #             directory_ftp=FTP_DIRECTORY,
    #             cartella_locale=OUTPUT_DIRECTORY,
    #             data=None,
    #             test=get_test
    #         )

    #         server = OrderedDict([
    #             ("FTP_HOST", FTP_HOST),
    #             ("FTP_USER", FTP_USER),
    #             ("FTP_PASSWORD", "*************"),
    #             ("FTP_PORT", FTP_PORT),
    #             ("FTP_DIRECTORY", FTP_DIRECTORY)
    #         ])

    #         response_data = OrderedDict([
    #             ("success", True),
    #             ("server", server),
    #             ("files", file_scaricati)
    #         ])

    #         if file_scaricati:
    #             print(f"\n🎉 Download completato! File scaricati:")
    #             for f in file_scaricati:
    #                 print(f"  ✓ {f}")
    #             return jsonify({'ftp_connection': True, 'success': True, 'files': file_scaricati})
    #         else:
    #             logger.error(f"Errore test FTP: Nessun file presente nell'FTP.'")
    #         return jsonify({'ftp_connection': True, 'success': False, 'message': 'Nessun file presente nell\'FTP.'})
        
    #     except Exception as e:
    #         logger.error(f"Errore test FTP: {e}")
    #         return jsonify({'ftp_connection': False, 'success': False, 'message': str(e)})

    #     finally:
    #         # Disconnetti sempre
    #         downloader.disconnetti()

    def runftp(self, get_template, get_test):
        """Versione per le route web (con jsonify)"""
        try:
            # Usa la versione interna
            result = self.runftp_internal(get_template, get_test)
            
            # Restituisci JSON response per le route web
            from flask import jsonify
            return jsonify(result)
            
        except Exception as e:
            from flask import jsonify
            return jsonify({
                'ftp_connection': False, 
                'success': False, 
                'message': str(e)
            })
        
    def runftp_internal(self, get_template, get_test):
        """Versione interna che restituisce dizionario Python puro (senza jsonify)"""
        try:
            # Connettiti
            if not self.connetti():
                return {'success': False, 'files': [], 'message': 'Connessione FTP fallita'}
            
            try:
                # Scarica i file per template
                file_scaricati = self.scarica_per_template(
                    template=get_template,
                    directory_ftp=self.config.get('ftp_directory', '/'),
                    cartella_locale=os.path.join(self.config.get('output_directory'), 'ftp_cdr'),
                    data=None,
                    test=get_test
                )

                server_info = {
                    "FTP_HOST": self.config.get('ftp_host'),
                    "FTP_USER": self.config.get('ftp_user'),
                    "FTP_PASSWORD": "*************",
                    "FTP_PORT": self.config.get('ftp_port'),
                    "FTP_DIRECTORY": self.config.get('ftp_directory')
                }

                if file_scaricati:
                    print(f"\n🎉 Download completato! File scaricati:")
                    for f in file_scaricati:
                        print(f"  ✓ {f}")
                    
                    return {
                        'ftp_connection': True, 
                        'success': True, 
                        'files': file_scaricati,
                        'server': server_info
                    }
                else:
                    print("Nessun file presente nell'FTP.")
                    return {
                        'ftp_connection': True, 
                        'success': False, 
                        'message': 'Nessun file presente nell\'FTP.',
                        'files': [],
                        'server': server_info
                    }
            
            finally:
                self.disconnetti()
                
        except Exception as e:
            print(f"Errore FTP: {e}")
            return {
                'ftp_connection': False, 
                'success': False, 
                'message': str(e),
                'files': []
            }



###########################################################################################################

###########################################################################################################


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
                with open(file_path, 'r', encoding='cp1252') as f:
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
                logger.info(f"Puliti {len(temp_files)} file temporanei")
                
        except Exception as e:
            logger.error(f"Errore pulizia directory: {e}")
    
    def process_files(self):
        """
        Metodo di compatibilità temporaneo
        Sostituirà il vecchio processor.process_files()
        """
        
        # print("🔄 Avvio processo download e conversione...")
        get_template = self.config['specific_filename']
        get_test = self.config.get('test_mode', False)
        
        # print(f"📂 Template e modalità test: {get_template}, {get_test}")
        
        # 1. Download dei file
        downloaded_response = self.runftp_internal(get_template, get_test)
        
        return downloaded_response
            
       
    def check_file(self, get_template, get_test):
        """
        Metodo di compatibilità temporaneo
        Sostituirà il vecchio processor.process_files()
        """
        try:
            print("🔄 Avvio processo download e conversione...")
            # get_template = self.config['specific_filename']
            # get_test = self.config.get('test_mode', False)
            directory_ftp = self.config.get('ftp_directory', '/')
            
            if not self.connetti():
                return
       
            file_list = self.lista_file_ftp(directory_ftp)

            self.disconnetti()
            
            print(f"📂 Template e modalità test: {get_template}, {get_test}")
            
            # 1. Download dei file
            downloaded_response = self.runftp_internal(get_template, get_test)
            print(f"📥 Response type: {type(downloaded_response)}")
            print(f"📥 Response data: {downloaded_response}")
            
            # ✅ ESTRAI I DATI DAL RESPONSE OBJECT
            if hasattr(downloaded_response, 'get_json'):
                # È un Response object di Flask
                downloaded_files = downloaded_response.get_json()
            elif hasattr(downloaded_response, 'json'):
                # Potrebbe essere un altro tipo di response
                downloaded_files = downloaded_response.json
            else:
                # Assume che sia già un dizionario
                downloaded_files = downloaded_response
            
            print(f"📥 Dati estratti: {downloaded_files}")
            print(f"📥 Tipo dati estratti: {type(downloaded_files)}")
            
            

            return {
                'success': True,
                'total_in_ftp': file_list,
                'downloaded_files': downloaded_files          
            }
            
        except Exception as e:
            print(f"❌ Errore in process_files: {e}")
            import traceback
            traceback.print_exc()  # Per debug completo
            return {
                'success': False,
                'message': str(e),
                'downloaded_files': [],
                'converted_files': [],
                'timestamp': datetime.now().isoformat()
            }
    
    def process_all_files(self):
        """
        Metodo di compatibilità temporaneo
        Sostituirà il vecchio processor.process_files()
        """
        try:
            print("🔄 Avvio processo download e conversione...")
            get_template = self.config['specific_filename']
            get_test = self.config.get('test_mode', False)
            
            print(f"📂 Template e modalità test: {get_template}, {get_test}")
            
            # 1. Download dei file
            downloaded_response = self.runftp_internal("*", get_test)
            print(f"📥 Response type: {type(downloaded_response)}")
            print(f"📥 Response data: {downloaded_response}")
            
            # ✅ ESTRAI I DATI DAL RESPONSE OBJECT
            if hasattr(downloaded_response, 'get_json'):
                # È un Response object di Flask
                downloaded_files = downloaded_response.get_json()
            elif hasattr(downloaded_response, 'json'):
                # Potrebbe essere un altro tipo di response
                downloaded_files = downloaded_response.json
            else:
                # Assume che sia già un dizionario
                downloaded_files = downloaded_response
            
            print(f"📥 Dati estratti: {downloaded_files}")
            print(f"📥 Tipo dati estratti: {type(downloaded_files)}")
            
            # ✅ CONTROLLA I DATI ESTRATTI
            if not downloaded_files or not downloaded_files.get('success', False):
                return {
                    'success': False,
                    'message': downloaded_files.get('message', 'Download fallito') if downloaded_files else 'Nessuna risposta dal server',
                    'downloaded_files': [],
                    'converted_files': [],
                    'timestamp': datetime.now().isoformat()
                }
            
            file_list = downloaded_files.get('files', [])
            
            if not file_list:
                return {
                    'success': False,
                    'message': 'Nessun file scaricato',
                    'downloaded_files': [],
                    'converted_files': [],
                    'timestamp': datetime.now().isoformat()
                }
            
            print(f"📄 Lista file da elaborare: {file_list}")
            
            # 2. Conversione JSON (da implementare)
            converted_files = []
            for file_path in file_list:
                print(f"📄 Elaborando file: {file_path}")
                directory = self.config['output_directory']
                full_path = os.path.join(directory, file_path)
                #Converto il file in json
                file_json = self.convert_to_json(full_path)
                converted_files.append(file_path)  # Temporaneo
            
            # 3. Risultato compatibile con app.py
            result = {
                'success': True,
                'message': f'Processo completato: {len(file_list)} file scaricati',
                'downloaded_files': file_list,
                'converted_files': converted_files,
                'total_downloaded': len(file_list),
                'total_converted': len(converted_files),
                'timestamp': datetime.now().isoformat()
            }

            try:
                cdr_results = []
                # for json_file in converted_files:
                cdr_result = self.cdr_analytics.process_cdr_file(file_json)
                
                # ✅ PULISCI RISULTATO CDR
                if isinstance(cdr_result, dict):
                    clean_cdr_result = {
                        'success': cdr_result.get('success', False),
                        'message': cdr_result.get('message', ''),
                        'source_file': str(cdr_result.get('source_file', '')),
                        'total_records': cdr_result.get('total_records', 0),
                        'total_contracts': cdr_result.get('total_contracts', 0),
                        'generated_files': [str(f) for f in cdr_result.get('generated_files', [])],
                        'categories_system_enabled': cdr_result.get('categories_system_enabled', False),
                        'processing_timestamp': cdr_result.get('processing_timestamp', datetime.now().isoformat())
                    }
                    
                    # Aggiungi statistiche categorie se disponibili
                    if 'category_stats' in cdr_result:
                        clean_cdr_result['category_stats'] = cdr_result['category_stats']
                    
                    cdr_results.append(clean_cdr_result)
                
                if cdr_results:
                    result['cdr_analytics'] = {
                        'processed_files': len(cdr_results),
                        'successful_analyses': sum(1 for r in cdr_results if r.get('success')),
                        'total_reports_generated': sum(len(r.get('generated_files', [])) for r in cdr_results),
                        'categories_system_enabled': any(r.get('categories_system_enabled', False) for r in cdr_results),
                        'results': cdr_results
                    }
                    
            except Exception as e:
                logger.error(f"Errore elaborazione CDR: {e}")
                result['cdr_analytics'] = {
                    'error': str(e),
                    'processed_files': 0
                }
            
            logger.info(f"Processo completato: {len(converted_files)} file convertiti")
            extract_data_from_api("/api/cdr/extract_contracts")
            return result
            
        except Exception as e:
            print(f"❌ Errore in process_files: {e}")
            import traceback
            traceback.print_exc()  # Per debug completo
            return {
                'success': False,
                'message': str(e),
                'downloaded_files': [],
                'converted_files': [],
                'timestamp': datetime.now().isoformat()
            }

def main():
    """Esempio di utilizzo dello script"""
    
    # # CONFIGURAZIONE FTP - MODIFICA QUESTI VALORI
    # # FTP_HOST = "ftp.domain.comm"
    # # FTP_USER = "username"
    # # FTP_PASSWORD = "pasword"
    # # FTP_PORT = 21
    
    # # # CONFIGURAZIONE DOWNLOAD
    # # SPECIFIC_FILENAME = "RIV_12345_MESE_%m_%Y-*.CDR"  # Il tuo template
    # # FTP_DIRECTORY = "/"  # Directory sul server FTP
    # # OUTPUT_DIRECTORY = "./output"  # Dove salvare i file
    
    # # Opzionale: specifica una data diversa da oggi
    # # data_specifica = datetime(2024, 12, 1)  # 1 dicembre 2024
    # data_specifica = None  # Usa la data di oggi
    # # Crea il downloader
    # from config import SecureConfig
    # secure_config = SecureConfig()
    # config = secure_config.get_config()
    # print(f"TEST----------------------->{dir(config)}")
    # downloader = FTPDownloader(config)
    
    # try:
    #     # Connettiti
    #     if not downloader.connetti():
    #         return
        
    #     # Scarica i file per template
    #     # file_scaricati = downloader.scarica_per_template(
    #     #     template=SPECIFIC_FILENAME,
    #     #     directory_ftp=FTP_DIRECTORY,
    #     #     cartella_locale=OUTPUT_DIRECTORY,
    #     #     data=data_specifica,
    #     #     test=True
    #     # )
    #     ftp_directory = config.get('ftp_directory', '/')
    #     file_scaricati = downloader.lista_file_ftp(ftp_directory)
    #     lista_file = downloader.lista_file_ftp(
    #         directory=FTP_DIRECTORY
    #     )
    #     # file_da_scaricare = downloader.filtra_file_per_pattern(lista_file, SPECIFIC_FILENAME)
    #     # print(file_da_scaricare)
    #     # # Mostra il risultato
    #     # if lista_file:
    #     #     print(f"\n🎉 Elenco completato! File presenti:")
    #     #     for f in lista_file:
    #     #         print(f"  ✓ {f}")
    #     # else:
    #     #     print("\n❌ Nessun file è stato presente.")

    #     # Mostra il risultato
    #     if file_scaricati:
    #         print(f"\n🎉 Download completato! File scaricati:")
    #         for f in file_scaricati:
    #             print(f"  ✓ {f}")
    #     else:
    #         print("\n❌ Nessun file è stato scaricato.")
            
    # finally:
    #     # Disconnetti sempre
    #     downloader.disconnetti()


if __name__ == "__main__":
    main()