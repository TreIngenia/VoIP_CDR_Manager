#!/usr/bin/env python3
"""
File Converter - Funzioni separate per conversione file
Estratte da FTPProcessor per uso modulare
"""

import json
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def convert_to_json(file_path, output_directory):
    """
    Converte un file in formato JSON
    Supporta CSV, TXT, Excel, e file CDR
    
    Args:
        file_path (str|Path): Path del file da convertire
        output_directory (str|Path): Directory di output
        
    Returns:
        str|None: Path del file JSON creato o None se errore
    """
    try:
        file_path = Path(file_path)
        output_directory = Path(output_directory)
        file_extension = file_path.suffix.lower()
        
        # Determina il nome del file JSON di output
        json_filename = file_path.stem + '.json'
        json_path = output_directory / json_filename
        
        data = None
        
        # Controlla se è un file CDR (Call Detail Record) basandosi sul nome o estensione
        if file_extension == '.cdr' or 'CDR' in file_path.name.upper():
            data = _parse_cdr_file(file_path)
        elif file_extension == '.csv':
            data = _parse_csv_file(file_path)
        elif file_extension in ['.xlsx', '.xls']:
            data = _parse_excel_file(file_path)
        elif file_extension == '.txt':
            data = _parse_txt_file(file_path)
        elif file_extension == '.json':
            data = _parse_json_file(file_path)
        else:
            data = _parse_unknown_file(file_path)
        
        if data is None:
            logger.error(f"Impossibile convertire il file: {file_path}")
            return None
        
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

def _parse_cdr_file(file_path):
    """Parsing specifico per file CDR"""
    try:
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
        return data
        
    except Exception as e:
        logger.error(f"Errore parsing CDR {file_path}: {e}")
        return None

def _parse_csv_file(file_path):
    """Parsing per file CSV"""
    try:
        # Prova prima con punto e virgola (comune in Europa)
        try:
            df = pd.read_csv(file_path, sep=';')
            if len(df.columns) == 1:
                # Se ha una sola colonna, prova con virgola
                df = pd.read_csv(file_path, sep=',')
        except:
            # Fallback con virgola
            df = pd.read_csv(file_path, sep=',')
        
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"Errore parsing CSV {file_path}: {e}")
        return None

def _parse_excel_file(file_path):
    """Parsing per file Excel"""
    try:
        df = pd.read_excel(file_path)
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"Errore parsing Excel {file_path}: {e}")
        return None

def _parse_txt_file(file_path):
    """Parsing per file TXT"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        
        # Se la prima riga contiene molti punti e virgola, trattalo come CDR
        if first_line.count(';') >= 5:
            return _parse_cdr_file(file_path)
        else:
            # Assume formato CSV con tab o altro delimitatore
            try:
                df = pd.read_csv(file_path, delimiter='\t')
                return df.to_dict('records')
            except:
                # Se fallisce come CSV, legge come testo semplice
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                return {'lines': [line.strip() for line in lines]}
                
    except Exception as e:
        logger.error(f"Errore parsing TXT {file_path}: {e}")
        return None

def _parse_json_file(file_path):
    """Parsing per file JSON (copia)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Errore parsing JSON {file_path}: {e}")
        return None

def _parse_unknown_file(file_path):
    """Parsing per file di tipo sconosciuto"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Controlla se il contenuto sembra un file CDR
        if content.count(';') > content.count(',') and content.count(';') > 10:
            # Crea file temporaneo CDR
            temp_cdr = file_path.parent / (file_path.stem + '.cdr')
            with open(temp_cdr, 'w', encoding='utf-8') as f:
                f.write(content)
            
            result = _parse_cdr_file(temp_cdr)
            
            # Rimuovi file temporaneo
            try:
                temp_cdr.unlink()
            except:
                pass
            
            return result
        else:
            return {'content': content, 'source_file': file_path.name}
            
    except Exception as e:
        logger.error(f"Errore parsing file sconosciuto {file_path}: {e}")
        return None

def convert_multiple_files(file_paths, output_directory):
    """
    Converte più file in JSON
    
    Args:
        file_paths (list): Lista di path dei file
        output_directory (str|Path): Directory di output
        
    Returns:
        dict: Risultato con file convertiti e errori
    """
    converted_files = []
    conversion_errors = []
    
    for file_path in file_paths:
        try:
            json_path = convert_to_json(file_path, output_directory)
            if json_path:
                converted_files.append(json_path)
            else:
                conversion_errors.append(f"Conversione fallita per: {file_path}")
        except Exception as e:
            conversion_errors.append(f"Errore conversione {file_path}: {str(e)}")
    
    return {
        'converted_files': converted_files,
        'conversion_errors': conversion_errors,
        'total_converted': len(converted_files),
        'total_errors': len(conversion_errors)
    }

def is_cdr_file(json_file_path):
    """
    Determina se un file JSON è un file CDR
    
    Args:
        json_file_path (str|Path): Path del file JSON
        
    Returns:
        bool: True se è un file CDR
    """
    try:
        filename = Path(json_file_path).name.upper()
        
        # Check nome file
        if any(keyword in filename for keyword in ['CDR', 'RIV', 'CALL', 'DETAIL']):
            return True
        
        # Check contenuto
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check metadati
        metadata = data.get('metadata', {})
        if metadata.get('file_type') == 'CDR':
            return True
        
        # Check struttura record
        records = data.get('records', [])
        if records and len(records) > 0:
            first_record = records[0]
            cdr_fields = [
                'data_ora_chiamata', 'numero_chiamante', 'numero_chiamato', 
                'durata_secondi', 'tipo_chiamata', 'costo_euro', 'codice_contratto'
            ]
            
            matching_fields = sum(1 for field in cdr_fields if field in first_record)
            return matching_fields >= 5
        
        return False
        
    except Exception as e:
        logger.error(f"Errore verifica file CDR {json_file_path}: {e}")
        return False