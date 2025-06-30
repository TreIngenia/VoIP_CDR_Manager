import os
import sys
import json
import ftplib
import logging
import fnmatch
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from utils import extract_data_from_api
logger = logging.getLogger(__name__)

class ConvertFILE:
    """Classe per gestire operazioni FTP e conversioni file con sicurezza migliorata"""
    
    def __init__(self, secureconfig):
        config = secureconfig.get_config()
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
        """Scarica i file dal server FTP basandosi sulla configurazione - VERSIONE DEFINITIVAMENTE CORRETTA"""
        downloaded_files = []
        
        try:
            # Debug: stampa configurazione COMPLETA
            logger.info("=== CONFIGURAZIONE DOWNLOAD ===")
            logger.info(f"download_all_files = {self.config.get('download_all_files')} (tipo: {type(self.config.get('download_all_files'))})")
            logger.info(f"specific_filename = {self.config.get('specific_filename')}")
            logger.info(f"filter_pattern = {self.config.get('filter_pattern')}")
            logger.info(f"file_naming_pattern = {self.config.get('file_naming_pattern')}")
            logger.info(f"custom_pattern = {self.config.get('custom_pattern')}")
            logger.info("=== FINE CONFIGURAZIONE ===")
            
            # Pulizia file temporanei all'inizio
            self.cleanup_output_directory("*.tmp")
            
            # CONVERSIONE BOOLEANA RIGOROSA - FIX DEFINITIVO
            download_all_raw = self.config.get('download_all_files', False)
            
            # Gestione rigorosa di tutti i tipi possibili
            if isinstance(download_all_raw, bool):
                download_all = download_all_raw
            elif isinstance(download_all_raw, str):
                # FIX: "false" deve essere False, solo "true" deve essere True
                download_all = download_all_raw.lower().strip() in ('true', '1', 'yes', 'on')
            elif download_all_raw is None:
                download_all = False
            elif isinstance(download_all_raw, (int, float)):
                # Per numeri: 0 = False, tutto il resto = True
                download_all = bool(download_all_raw) and download_all_raw != 0
            else:
                # Conversione generica per altri tipi
                download_all = False  # Default sicuro
            
            logger.info(f"download_all_raw = {repr(download_all_raw)}")
            logger.info(f"download_all convertito = {download_all} (tipo: {type(download_all)})")
            
            # Ottieni lista completa file dal server
            all_files = self.list_ftp_files()
            logger.info(f"File totali trovati sul server FTP: {len(all_files)}")
            
            if not all_files:
                logger.warning("Nessun file trovato sul server FTP")
                return []
            
            # CONTROLLO ESPLICITO E DEFINITIVO
            if download_all == True:
                logger.info("🔄 MODALITÀ: SCARICA TUTTI I FILE")
                files_to_download = all_files
            else:
                logger.info("🎯 MODALITÀ: SCARICA FILE SPECIFICI/PATTERN")
                files_to_download = []
                
                # STEP 1: Controlla SPECIFIC_FILENAME
                specific_filename = self.config.get('specific_filename')
                if specific_filename and specific_filename.strip():
                    logger.info(f"🔍 STEP 1: Usando SPECIFIC_FILENAME = '{specific_filename}'")
                    
                    # Controlla se è un pattern (contiene wildcard o variabili temporali)
                    if '*' in specific_filename or '?' in specific_filename or '%' in specific_filename:
                        logger.info(f"   ➜ Pattern rilevato, applico filtro")
                        files_to_download = self.filter_files_by_pattern(all_files, specific_filename)
                        logger.info(f"   ➜ File trovati con pattern: {len(files_to_download)}")
                    else:
                        logger.info(f"   ➜ Nome esatto, cerco file specifico")
                        files_to_download = [specific_filename] if specific_filename in all_files else []
                        logger.info(f"   ➜ File trovato: {'Sì' if files_to_download else 'No'}")
                
                # STEP 2: Se non trovato, controlla FILTER_PATTERN
                elif self.config.get('filter_pattern') and self.config.get('filter_pattern').strip():
                    filter_pattern = self.config.get('filter_pattern')
                    logger.info(f"🔍 STEP 2: Usando FILTER_PATTERN = '{filter_pattern}'")
                    files_to_download = self.filter_files_by_pattern(all_files, filter_pattern)
                    logger.info(f"   ➜ File trovati con pattern: {len(files_to_download)}")
                
                # STEP 3: Se non trovato, genera pattern temporale
                else:
                    logger.info("🔍 STEP 3: Generando pattern temporale")
                    filename = self.generate_filename(
                        self.config.get('file_naming_pattern', 'monthly'),
                        self.config.get('custom_pattern', '')
                    )
                    logger.info(f"   ➜ Pattern generato: '{filename}'")
                    
                    # Controlla se il nome generato contiene wildcard
                    if '*' in filename or '?' in filename:
                        files_to_download = self.filter_files_by_pattern(all_files, filename)
                        logger.info(f"   ➜ File trovati con pattern temporale: {len(files_to_download)}")
                    else:
                        files_to_download = [filename] if filename in all_files else []
                        logger.info(f"   ➜ File temporale trovato: {'Sì' if files_to_download else 'No'}")
                
                # CONTROLLO FINALE: Se non trova nulla, NON scaricare tutto!
                if not files_to_download:
                    logger.warning("❌ NESSUN FILE CORRISPONDE AI CRITERI - NON SCARICO NULLA")
                    logger.warning("   Se vuoi scaricare tutti i file, imposta DOWNLOAD_ALL_FILES=true")
                    return []
                else:
                    logger.info(f"✅ TROVATI {len(files_to_download)} FILE DA SCARICARE")
                    for f in files_to_download:
                        logger.info(f"   - {f}")
            
            # Download dei file selezionati
            logger.info(f"📥 INIZIO DOWNLOAD: {len(files_to_download)} file")
            
            for filename in files_to_download:
                # Ignora directory e file nascosti
                if filename.startswith('.') or filename.endswith('/'):
                    logger.info(f"⏭️  Ignorato: {filename} (directory o file nascosto)")
                    continue
                
                local_path = Path(self.config['output_directory']) / filename
                logger.info(f"⬇️  Scaricamento: {filename}")
                
                # Avviso se file esiste già
                if local_path.exists():
                    logger.warning(f"⚠️  File esistente sarà sovrascritto: {filename}")
                
                if self.download_file_from_ftp(filename, local_path):
                    downloaded_files.append(str(local_path))
                    logger.info(f"✅ [OK] Download completato: {filename}")
                else:
                    logger.error(f"❌ [ERROR] Download fallito: {filename}")
            
            # Pulizia finale file temporanei
            self.cleanup_output_directory("*.tmp")
            
            logger.info(f"🎉 Download completato. File scaricati: {len(downloaded_files)}")
            
            # Log finale dei file scaricati
            if downloaded_files:
                logger.info("📁 File scaricati:")
                for f in downloaded_files:
                    logger.info(f"   - {Path(f).name}")
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"💥 Errore nel processo di download: {e}")
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

    def process_files(self):
        """Processo completo: download e conversione con risultato JSON-safe"""
        try:
            logger.info("Inizio processo di elaborazione file")
            
            # Download dei file
            downloaded_files = self.download_files()
            
            if not downloaded_files:
                logger.warning("Nessun file scaricato")
                return {
                    'success': False, 
                    'message': 'Nessun file scaricato - verificare pattern o disponibilità file',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Conversione in JSON
            converted_files = []
            conversion_errors = []
            
            for file_path in downloaded_files:
                try:
                    json_path = self.convert_to_json(file_path)
                    if json_path:
                        converted_files.append(json_path)
                    else:
                        conversion_errors.append(f"Conversione fallita per: {file_path}")
                except Exception as e:
                    conversion_errors.append(f"Errore conversione {file_path}: {str(e)}")
            
            # ✅ RISULTATO PULITO E SERIALIZZABILE
            result = {
                'success': True,
                'message': f'Processo completato: {len(converted_files)} file convertiti',
                'downloaded_files': [str(f) for f in downloaded_files],  # Converti Path in string
                'converted_files': [str(f) for f in converted_files],    # Converti Path in string
                'total_downloaded': len(downloaded_files),
                'total_converted': len(converted_files),
                'conversion_errors': conversion_errors,
                'timestamp': datetime.now().isoformat()
            }
            
            # ✅ ELABORAZIONE CDR SE DISPONIBILE (con pulizia)
            if hasattr(self, 'cdr_analytics') and converted_files:
                try:
                    cdr_results = []
                    
                    for json_file in converted_files:
                        if hasattr(self, '_is_cdr_file') and self._is_cdr_file(json_file):
                            cdr_result = self.cdr_analytics.process_cdr_file(json_file)
                            
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
            logger.error(f"Errore nel processo completo: {e}")
            return {
                'success': False, 
                'message': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }

    def debug_configuration(self):
        """Metodo di debug per controllare la configurazione"""
        logger.info("🔧 === DEBUG CONFIGURAZIONE ===")
        logger.info(f"Configurazione completa: {self.config}")
        
        # Test specifici per ogni valore
        for key, value in self.config.items():
            logger.info(f"  {key} = {repr(value)} (tipo: {type(value).__name__})")
        
        # Test conversione booleana
        download_all_raw = self.config.get('download_all_files', 'MISSING')
        logger.info(f"download_all_files RAW: {repr(download_all_raw)}")
        
        if isinstance(download_all_raw, str):
            test_values = ['true', '1', 'yes', 'on', 'True', 'TRUE']
            is_true = download_all_raw.lower() in ['true', '1', 'yes', 'on'] or download_all_raw in ['True', 'TRUE']
            logger.info(f"  String test: '{download_all_raw}' -> {is_true}")
            logger.info(f"  Lower case: '{download_all_raw.lower()}'")
            logger.info(f"  In test values: {download_all_raw.lower() in ['true', '1', 'yes', 'on']}")
        
        logger.info("🔧 === FINE DEBUG ===")
        
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
                'RIV_*_MESE_*_%Y-*.CDR',    # Anno corrente con variabile
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