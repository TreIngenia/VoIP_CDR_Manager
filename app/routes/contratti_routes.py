"""
Categories Routes - Route Flask per gestione categorie CDR con markup personalizzabili
Aggiornato per utilizzare il sistema unificato cdr_categories_enhanced.py
"""

import json
import logging
from datetime import datetime
import os
from pathlib import Path
from flask import request, jsonify, render_template, Response
import csv
import io

# from contratti import CDRContractsService

logger = logging.getLogger(__name__)

def contratti_routes(app, secure_config):
    @app.route('/gestione_contratti')
    def gestione_contratti():
        from routes.menu_routes import render_with_menu_context
        return render_with_menu_context('gestione_contratti.html', {'config':secure_config})    


    # Restituisce le informazioni sulle route aggiunte
    return {
        'routes_added': [
            '/gestione_contratti'
        ],
        'routes_count': 1
    }

def api_contract_routes(app, secure_config, processor):
    from cdr_contract_extractor import extract_contracts_from_files, save_contracts_config
    
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
            "contract_type": "A CONSUMO",
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
            if 'contract_type' in data:
                contract['contract_type'] = data['contract_type'].strip()
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
        
    @app.route('/api/cdr/contract_type')    
    def contract_type():
        json_path = os.path.join(app.root_path, 'config/cdr_contract_type.json')
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
#-------------------------------------------

    logger.info("🔗 Route estrazione codici contratto CDR registrate")
    
    return {
        'routes_added': [
            '/api/cdr/extract_contracts',
            '/api/cdr/contracts_config', 
            '/api/cdr/update_contract',
            '/api/cdr/contract_type',
        ],
        'routes_count': 4
    }
