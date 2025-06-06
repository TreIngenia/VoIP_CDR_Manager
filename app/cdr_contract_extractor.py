#!/usr/bin/env python3
"""
CDR Contract Extractor - Estrazione codici contratto da file CDR
Funzione per scaricare tutti i CDR dall'FTP ed estrarre codici contratto unici
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Any
from flask import jsonify, request

logger = logging.getLogger(__name__)

def add_cdr_contract_routes(app, secure_config, processor):
    """
    Aggiunge route per estrazione codici contratto CDR
    
    Args:
        app: Istanza Flask
        secure_config: Configurazione sicura
        processor: Processore FTP
    """
    
    @app.route('/api/cdr/extract_contracts', methods=['POST'])
    def extract_cdr_contracts():
        """
        API per estrarre tutti i codici contratto dai file CDR presenti sull'FTP
        
        Returns:
            JSON con lista codici contratto unici e statistiche
        """
        try:
            logger.info("🔍 Avvio estrazione codici contratto da CDR")
            
            # Parametri opzionali dalla richiesta
            data = request.get_json() or {}
            force_redownload = data.get('force_redownload', False)
            pattern_filter = data.get('pattern_filter', 'RIV_*_*.CDR')  # Pattern per file CDR
            
            # Step 1: Configura processore per scaricare tutti i file CDR
            original_config = processor.config.copy()
            temp_config = processor.config.copy()
            
            # Modifica temporanea configurazione per scaricare tutti i CDR
            temp_config['download_all_files'] = False
            temp_config['specific_filename'] = pattern_filter
            temp_config['filter_pattern'] = pattern_filter
            
            processor.config = temp_config
            
            logger.info(f"📥 Configurazione download: pattern='{pattern_filter}'")
            
            # Step 2: Scarica tutti i file CDR
            downloaded_files = processor.download_files()
            
            if not downloaded_files:
                logger.warning("⚠️ Nessun file CDR trovato sull'FTP")
                return jsonify({
                    'success': False,
                    'message': 'Nessun file CDR trovato sul server FTP',
                    'pattern_used': pattern_filter,
                    'contracts_found': 0,
                    'files_processed': 0
                })
            
            logger.info(f"📁 Scaricati {len(downloaded_files)} file CDR")
            
            # Step 3: Estrai codici contratto da tutti i file
            contracts_data = extract_contracts_from_files(downloaded_files, force_redownload)
            
            # Step 4: Salva/aggiorna configurazione contratti
            save_result = save_contracts_config(contracts_data, secure_config)
            
            # Ripristina configurazione originale
            processor.config = original_config
            
            # Step 5: Prepara risposta
            response_data = {
                'success': True,
                'message': f'Estrazione completata: {save_result["new_contracts_added"]} nuovi contratti aggiunti',
                'pattern_used': pattern_filter,
                'files_processed': len(downloaded_files),
                'contracts_found_in_files': len(contracts_data['contracts']),
                'file_existed_before': save_result['file_existed'],
                'contracts_before_extraction': save_result['contracts_before'],
                'new_contracts_added': save_result['new_contracts_added'],
                'total_contracts_after': save_result['total_contracts_after'],
                'config_file_path': save_result['file_path'],
                'statistics': contracts_data['statistics'],
                'phone_numbers_summary': {
                    'total_unique_calling_numbers': sum(c.get('total_unique_numbers', 0) for c in contracts_data['contracts'].values()),
                    'contracts_with_numbers': sum(1 for c in contracts_data['contracts'].values() if c.get('total_unique_numbers', 0) > 0)
                },
                'contracts_preview': list(contracts_data['contracts'].keys())[:10],  # Prime 10 nuovi
                'processing_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Estrazione completata: +{save_result['new_contracts_added']} nuovi contratti")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"❌ Errore estrazione codici contratto: {e}")
            # Ripristina configurazione in caso di errore
            if 'original_config' in locals():
                processor.config = original_config
                
            return jsonify({
                'success': False,
                'message': f'Errore durante estrazione: {str(e)}',
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/api/cdr/contracts_config', methods=['GET'])
    def get_contracts_config():
        """
        API per ottenere la configurazione contratti salvata
        
        Returns:
            JSON con configurazione contratti corrente
        """
        try:
            config_dir = Path(secure_config.get_config().get('CONTRACTS_CONFIG_DIRECTORY', 
                                                           secure_config.get_config().get('config_directory', 'config')))
            contracts_filename = secure_config.get_config().get('CONTRACTS_CONFIG_FILE', 'cdr_contracts.json')
            contracts_file = config_dir / contracts_filename
            
            if not contracts_file.exists():
                return jsonify({
                    'success': False,
                    'message': 'File configurazione contratti non trovato',
                    'suggestion': 'Esegui prima estrazione codici contratto'
                })
            
            with open(contracts_file, 'r', encoding='utf-8') as f:
                contracts_data = json.load(f)
            
            return jsonify({
                'success': True,
                'config_file': str(contracts_file),
                'contracts_count': len(contracts_data.get('contracts', {})),
                'last_updated': contracts_data.get('metadata', {}).get('last_updated'),
                'data': contracts_data
            })
            
        except Exception as e:
            logger.error(f"Errore lettura configurazione contratti: {e}")
            return jsonify({
                'success': False,
                'message': f'Errore lettura configurazione: {str(e)}'
            }), 500

    @app.route('/api/cdr/update_contract', methods=['POST'])
    def update_contract_info():
        """
        API per aggiornare informazioni di un contratto specifico
        
        Body JSON:
        {
            "contract_code": "12345",
            "contract_name": "Nome Cliente",
            "odoo_client_id": 8378,
            "notes": "Note aggiuntive"
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'Dati non validi'
                }), 400
            
            contract_code = data.get('contract_code')
            if not contract_code:
                return jsonify({
                    'success': False,
                    'message': 'Codice contratto obbligatorio'
                }), 400
            
            # Carica configurazione esistente
            config_dir = Path(secure_config.get_config().get('CONTRACTS_CONFIG_DIRECTORY',
                                                           secure_config.get_config().get('config_directory', 'config')))
            contracts_filename = secure_config.get_config().get('CONTRACTS_CONFIG_FILE', 'cdr_contracts.json')
            contracts_file = config_dir / contracts_filename
            
            if not contracts_file.exists():
                return jsonify({
                    'success': False,
                    'message': 'File configurazione contratti non trovato'
                }), 404
            
            with open(contracts_file, 'r', encoding='utf-8') as f:
                contracts_data = json.load(f)
            
            # Verifica esistenza contratto
            if str(contract_code) not in contracts_data.get('contracts', {}):
                return jsonify({
                    'success': False,
                    'message': f'Codice contratto {contract_code} non trovato'
                }), 404
            
            # Aggiorna informazioni contratto
            contract = contracts_data['contracts'][str(contract_code)]
            
            if 'contract_name' in data:
                contract['contract_name'] = data['contract_name'].strip()
            if 'odoo_client_id' in data:
                contract['odoo_client_id'] = data['odoo_client_id'].strip()
            if 'notes' in data:
                contract['notes'] = data['notes'].strip()
            
            contract['last_updated'] = datetime.now().isoformat()
            
            # Aggiorna metadata
            contracts_data['metadata']['last_updated'] = datetime.now().isoformat()
            contracts_data['metadata']['manual_updates'] = contracts_data['metadata'].get('manual_updates', 0) + 1
            
            # Salva configurazione aggiornata
            with open(contracts_file, 'w', encoding='utf-8') as f:
                json.dump(contracts_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Contratto {contract_code} aggiornato")
            
            return jsonify({
                'success': True,
                'message': f'Contratto {contract_code} aggiornato con successo',
                'updated_contract': contract
            })
            
        except Exception as e:
            logger.error(f"Errore aggiornamento contratto: {e}")
            return jsonify({
                'success': False,
                'message': f'Errore aggiornamento: {str(e)}'
            }), 500

    logger.info("🔗 Route estrazione codici contratto CDR registrate")
    
    return {
        'routes_added': [
            '/api/cdr/extract_contracts',
            '/api/cdr/contracts_config', 
            '/api/cdr/update_contract'
        ],
        'routes_count': 3
    }


def extract_contracts_from_files(downloaded_files: List[str], force_redownload: bool = False) -> Dict[str, Any]:
    """
    Estrae codici contratto da una lista di file CDR
    
    Args:
        downloaded_files: Lista percorsi file scaricati
        force_redownload: Se forzare riprocessamento file già elaborati
        
    Returns:
        Dict con contratti unici e statistiche
    """
    logger.info(f"🔍 Estrazione codici contratto da {len(downloaded_files)} file")
    
    contracts = {}  # {contract_code: {data}}
    statistics = {
        'total_files_processed': 0,
        'total_records_processed': 0,
        'unique_contracts_found': 0,
        'files_with_errors': 0,
        'processing_errors': []
    }
    
    for file_path in downloaded_files:
        try:
            file_path = Path(file_path)
            
            # Verifica se è un file CDR
            if not is_cdr_file(file_path):
                logger.debug(f"File ignorato (non CDR): {file_path.name}")
                continue
            
            logger.info(f"📄 Elaborazione file: {file_path.name}")
            
            # Estrai contratti dal file
            file_contracts = extract_codes_from_single_file(file_path)
            
            if file_contracts:
                statistics['total_records_processed'] += file_contracts['records_count']
                
                # Unifica contratti
                for contract_code, contract_info in file_contracts['contracts'].items():
                    if contract_code not in contracts:
                        # ✅ NUOVO CONTRATTO CON NUMERI CHIAMANTE
                        contracts[contract_code] = {
                            'contract_code': contract_code,
                            'contract_name': '',  # Da compilare manualmente
                            'odoo_client_id': None,  # Da compilare manualmente
                            'first_seen_file': file_path.name,
                            'first_seen_date': datetime.now().isoformat(),
                            'last_seen_file': file_path.name,
                            'last_seen_date': datetime.now().isoformat(),
                            'total_calls_found': contract_info['calls_count'],
                            'files_found_in': [file_path.name],
                            'notes': '',
                            # ✅ SOLO NUMERI CHIAMANTE
                            'phone_numbers': contract_info['phone_numbers'],
                            'total_unique_numbers': contract_info['total_unique_numbers']
                        }
                    else:
                        # ✅ CONTRATTO ESISTENTE - AGGIORNA STATISTICHE E NUMERI CHIAMANTE
                        existing_contract = contracts[contract_code]
                        existing_contract['last_seen_file'] = file_path.name
                        existing_contract['last_seen_date'] = datetime.now().isoformat()
                        existing_contract['total_calls_found'] += contract_info['calls_count']
                        
                        if file_path.name not in existing_contract['files_found_in']:
                            existing_contract['files_found_in'].append(file_path.name)
                        
                        # ✅ UNIFICA NUMERI CHIAMANTE (EVITA DUPLICATI)
                        all_phone_numbers = set(existing_contract.get('phone_numbers', []))
                        all_phone_numbers.update(contract_info['phone_numbers'])
                        
                        # Aggiorna con lista ordinata
                        existing_contract['phone_numbers'] = sorted(list(all_phone_numbers))
                        existing_contract['total_unique_numbers'] = len(all_phone_numbers)
                
                statistics['total_files_processed'] += 1
                logger.info(f"✅ File elaborato: {len(file_contracts['contracts'])} contratti unici trovati")
                
            else:
                logger.warning(f"⚠️ Nessun contratto trovato in: {file_path.name}")
                
        except Exception as e:
            logger.error(f"❌ Errore elaborazione file {file_path}: {e}")
            statistics['files_with_errors'] += 1
            statistics['processing_errors'].append({
                'file': str(file_path),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    statistics['unique_contracts_found'] = len(contracts)
    
    logger.info(f"📊 Estrazione completata: {statistics['unique_contracts_found']} contratti unici da {statistics['total_files_processed']} file")
    
    return {
        'contracts': contracts,
        'statistics': statistics,
        'extraction_timestamp': datetime.now().isoformat()
    }


def extract_codes_from_single_file(file_path: Path) -> Dict[str, Any]:
    """
    Estrae codici contratto e numeri chiamante da un singolo file CDR
    
    Args:
        file_path: Percorso al file CDR
        
    Returns:
        Dict con contratti e numeri chiamante trovati nel file
    """
    try:
        contracts = defaultdict(lambda: {
            'calls_count': 0, 
            'phone_numbers': set()  # Solo numeri chiamante
        })
        total_records = 0
        
        # Headers standard per file CDR (dal codice esistente)
        cdr_headers = [
            'data_ora_chiamata', 'numero_chiamante', 'numero_chiamato',
            'durata_secondi', 'tipo_chiamata', 'operatore', 'costo_euro',
            'codice_contratto', 'codice_servizio', 'cliente_finale_comune', 'prefisso_chiamato'
        ]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                fields = line.split(';')
                
                # Assicura che ci siano abbastanza campi
                while len(fields) < len(cdr_headers):
                    fields.append('')
                
                # Estrai campi principali
                if len(fields) > 7:
                    numero_chiamante = fields[1].strip()  # Index 1 - SOLO QUESTO
                    contract_code_raw = fields[7].strip() # Index 7
                    
                    if contract_code_raw and contract_code_raw.isdigit():
                        contract_code = str(contract_code_raw)
                        
                        # ✅ AGGIORNA CONTATORI
                        contracts[contract_code]['calls_count'] += 1
                        
                        # ✅ AGGIUNGI SOLO NUMERO CHIAMANTE
                        if numero_chiamante and numero_chiamante.isdigit():
                            contracts[contract_code]['phone_numbers'].add(numero_chiamante)
                        
                        total_records += 1
        
        # ✅ CONVERTE SET IN LISTE ORDINATE PER JSON SERIALIZATION
        processed_contracts = {}
        for contract_code, data in contracts.items():
            processed_contracts[contract_code] = {
                'calls_count': data['calls_count'],
                'phone_numbers': sorted(list(data['phone_numbers'])),
                'total_unique_numbers': len(data['phone_numbers'])
            }
        
        if processed_contracts:
            logger.debug(f"File {file_path.name}: {len(processed_contracts)} contratti, {total_records} record")
            # ✅ LOG NUMERI TELEFONO PER DEBUG (SOLO CHIAMANTI)
            for contract_code, data in list(processed_contracts.items())[:3]:  # Prime 3 per debug
                logger.debug(f"  Contratto {contract_code}: {data['total_unique_numbers']} numeri chiamante unici")
            
        return {
            'contracts': processed_contracts,
            'records_count': total_records,
            'file_name': file_path.name
        }
        
    except Exception as e:
        logger.error(f"Errore lettura file {file_path}: {e}")
        return None


def is_cdr_file(file_path: Path) -> bool:
    """
    Verifica se un file è un file CDR basandosi su nome ed estensione
    
    Args:
        file_path: Percorso al file
        
    Returns:
        True se è un file CDR
    """
    filename = file_path.name.upper()
    
    # Criteri identificazione file CDR
    cdr_indicators = ['CDR', 'RIV', 'CALL', 'DETAIL']
    cdr_extensions = ['.CDR', '.TXT', '.CSV']
    
    # Controlla nome file
    has_cdr_indicator = any(indicator in filename for indicator in cdr_indicators)
    
    # Controlla estensione
    has_cdr_extension = any(filename.endswith(ext) for ext in cdr_extensions)
    
    return has_cdr_indicator or has_cdr_extension


def save_contracts_config(contracts_data: Dict[str, Any], secure_config) -> Dict[str, Any]:
    """
    Salva/aggiorna la configurazione contratti in un file JSON
    Se il file esiste, aggiunge solo i codici NON presenti mantenendo quelli esistenti
    
    Args:
        contracts_data: Dati contratti estratti
        secure_config: Configurazione sicura per percorsi
        
    Returns:
        Dict con risultati operazione e statistiche
    """
    try:
        config = secure_config.get_config()
        
        # ✅ LEGGI PERCORSI DA .ENV
        config_dir = Path(config.get('CONTRACTS_CONFIG_DIRECTORY', config.get('config_directory', 'config')))
        contracts_filename = config.get('CONTRACTS_CONFIG_FILE', 'cdr_contracts.json')
        
        config_dir.mkdir(parents=True, exist_ok=True)
        contracts_file = config_dir / contracts_filename
        
        logger.info(f"📁 Directory config: {config_dir}")
        logger.info(f"📄 File contratti: {contracts_filename}")
        
        existing_contracts = {}
        existing_metadata = {}
        file_existed = False
        
        # ✅ VERIFICA SE FILE ESISTE E CARICALO
        if contracts_file.exists():
            file_existed = True
            logger.info(f"📋 File esistente trovato: {contracts_file}")
            
            try:
                with open(contracts_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_contracts = existing_data.get('contracts', {})
                    existing_metadata = existing_data.get('metadata', {})
                    
                logger.info(f"📊 Contratti esistenti: {len(existing_contracts)}")
                
                # Crea backup del file esistente
                backup_file = config_dir / f'{contracts_filename}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                import shutil
                shutil.copy2(contracts_file, backup_file)
                logger.info(f"💾 Backup creato: {backup_file}")
                
            except Exception as e:
                logger.error(f"❌ Errore lettura file esistente: {e}")
                # In caso di errore, continua come se il file non esistesse
                existing_contracts = {}
                existing_metadata = {}
        else:
            logger.info(f"🆕 Creazione nuovo file: {contracts_file}")
        
        # ✅ UNIFICA CONTRATTI: AGGIUNGI SOLO QUELLI NON PRESENTI
        new_contracts_added = 0
        updated_contracts = existing_contracts.copy()  # Mantieni tutti i contratti esistenti
        
        for contract_code, contract_info in contracts_data['contracts'].items():
            if contract_code not in updated_contracts:
                # ✅ NUOVO CONTRATTO - AGGIUNGILO
                updated_contracts[contract_code] = contract_info
                new_contracts_added += 1
                logger.info(f"➕ Nuovo contratto aggiunto: {contract_code}")
            else:
                # ✅ CONTRATTO ESISTENTE - AGGIORNA SOLO STATISTICHE TECNICHE (NON I DATI MANUALI)
                existing_contract = updated_contracts[contract_code]
                
                # Aggiorna solo campi tecnici, mantieni quelli manuali
                existing_contract['last_seen_file'] = contract_info['last_seen_file']
                existing_contract['last_seen_date'] = contract_info['last_seen_date']
                existing_contract['total_calls_found'] = existing_contract.get('total_calls_found', 0) + contract_info['total_calls_found']
                
                # Aggiungi nuovo file alla lista se non presente
                files_list = existing_contract.get('files_found_in', [])
                if contract_info['last_seen_file'] not in files_list:
                    files_list.append(contract_info['last_seen_file'])
                    existing_contract['files_found_in'] = files_list
                
                logger.debug(f"🔄 Contratto esistente aggiornato (statistiche): {contract_code}")
        
        # ✅ PREPARA METADATA AGGIORNATA
        now = datetime.now().isoformat()
        
        if file_existed:
            # Aggiorna metadata esistente
            metadata = existing_metadata.copy()
            metadata['last_updated'] = now
            metadata['total_contracts'] = len(updated_contracts)
            metadata['last_extraction_added_contracts'] = new_contracts_added
            metadata['extraction_runs'] = metadata.get('extraction_runs', 0) + 1
        else:
            # Nuova metadata
            metadata = {
                'version': '1.0',
                'created_date': now,
                'last_updated': now,
                'total_contracts': len(updated_contracts),
                'extraction_source': 'FTP_CDR_Files',
                'manual_updates': 0,
                'extraction_runs': 1,
                'last_extraction_added_contracts': new_contracts_added,
                'description': 'Configurazione codici contratto estratti da file CDR'
            }
        
        # ✅ PREPARA DATI FINALI
        final_data = {
            'metadata': metadata,
            'contracts': updated_contracts,
            'last_extraction': {
                'timestamp': contracts_data['extraction_timestamp'],
                'files_processed': contracts_data['statistics']['total_files_processed'],
                'records_processed': contracts_data['statistics']['total_records_processed'],
                'new_contracts_added': new_contracts_added,
                'existing_contracts_preserved': len(existing_contracts),
                'total_contracts_after': len(updated_contracts)
            }
        }
        
        # ✅ SALVA FILE AGGIORNATO
        with open(contracts_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        result = {
            'file_path': str(contracts_file),
            'file_existed': file_existed,
            'contracts_before': len(existing_contracts),
            'new_contracts_added': new_contracts_added,
            'total_contracts_after': len(updated_contracts),
            'preserved_existing_data': file_existed
        }
        
        if file_existed:
            logger.info(f"✅ File aggiornato: +{new_contracts_added} nuovi contratti (totale: {len(updated_contracts)})")
        else:
            logger.info(f"✅ Nuovo file creato: {len(updated_contracts)} contratti")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Errore salvataggio configurazione contratti: {e}")
        raise


# Esempio di utilizzo nelle route principali
def integrate_contract_extraction(app, secure_config, processor):
    """
    Integra l'estrazione codici contratto nell'app principale
    
    Args:
        app: Istanza Flask
        secure_config: Configurazione sicura  
        processor: Processore FTP
    """
    # Aggiungi route per estrazione contratti
    routes_info = add_cdr_contract_routes(app, secure_config, processor)
    
    logger.info(f"🔗 Sistema estrazione codici contratto integrato: {routes_info['routes_count']} route")
    
    return routes_info