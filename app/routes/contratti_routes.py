"""
Categories Routes - Route Flask per gestione categorie CDR con markup personalizzabili
Aggiornato per utilizzare il sistema unificato cdr_categories_enhanced.py
"""

import json
import logging
from datetime import datetime
import os
from pathlib import Path
from flask import request, jsonify, render_template, Response, request
import csv
import io

from contratti import CDRContractsService

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

def api_contract_routes(app, secure_config):
    from cdr_contract_extractor import extract_cdr_contracts_from_cdr
    @app.route('/api/cdr/extract_contracts', methods=['POST'])
    def extract_cdr_contracts():
        extract_cdr_contracts_from_cdr()    
    # def extract_cdr_contracts():
    
    #     """
    #     API per estrarre tutti i codici contratto dai file CDR presenti sull'FTP
        
    #     Returns:
    #         JSON con lista codici contratto unici e statistiche
    #     """
    #     try:
    #         logger.info("🔍 Avvio estrazione codici contratto da CDR")
            
    #         # # Parametri opzionali dalla richiesta
    #         data = request.get_json() or {}
    #         force_redownload = data.get('force_redownload', False)
    #         # pattern_filter = data.get('pattern_filter', 'RIV_*_*.CDR')  # Pattern per file CDR
            
    #         # # Step 1: Configura processore per scaricare tutti i file CDR
    #         # original_config = processor.config.copy()
    #         # temp_config = processor.config.copy()
            
    #         # Modifica temporanea configurazione per scaricare tutti i CDR
    #         # temp_config['download_all_files'] = False
    #         # temp_config['specific_filename'] = pattern_filter
    #         # temp_config['filter_pattern'] = pattern_filter
            
    #         # processor.config = temp_config
            
    #         # logger.info(f"📥 Configurazione download: pattern='{pattern_filter}'")
            
    #         # Step 2: Scarica tutti i file CDR
    #         from ftp_downloader import FTPDownloader
    #         from cdr_file_manager import get_files_by_extension
    #         # downloader = FTPDownloader(secure_config)
            
    #         # downloaded_files = downloader.process_all_files()
    #         downloaded_files = get_files_by_extension('./data', 'cdr', recursive=False)

    #         if not downloaded_files:
    #             logger.warning("⚠️ Nessun file CDR trovato sull'FTP")
    #             return jsonify({
    #                 'success': False,
    #                 'message': 'Nessun file CDR trovato sul server FTP',
    #                 # 'pattern_used': pattern_filter,
    #                 'contracts_found': 0,
    #                 'files_processed': 0
    #             })
            
    #         logger.info(f"📁 Scaricati {len(downloaded_files)} file CDR")
            
    #         # Step 3: Estrai codici contratto da tutti i file
    #         contracts_data = extract_contracts_from_files(downloaded_files, force_redownload)
            
    #         # Step 4: Salva/aggiorna configurazione contratti
    #         save_result = save_contracts_config(contracts_data, secure_config)
            
    #         # Ripristina configurazione originale
    #         # processor.config = original_config
            
    #         # Step 5: Prepara risposta
    #         response_data = {
    #             'success': True,
    #             'message': f'Estrazione completata: {save_result["new_contracts_added"]} nuovi contratti aggiunti',
    #             # 'pattern_used': pattern_filter,
    #             'files_processed': len(downloaded_files),
    #             'contracts_found_in_files': len(contracts_data['contracts']),
    #             'file_existed_before': save_result['file_existed'],
    #             'contracts_before_extraction': save_result['contracts_before'],
    #             'new_contracts_added': save_result['new_contracts_added'],
    #             'total_contracts_after': save_result['total_contracts_after'],
    #             'config_file_path': save_result['file_path'],
    #             'statistics': contracts_data['statistics'],
    #             'phone_numbers_summary': {
    #                 'total_unique_calling_numbers': sum(c.get('total_unique_numbers', 0) for c in contracts_data['contracts'].values()),
    #                 'contracts_with_numbers': sum(1 for c in contracts_data['contracts'].values() if c.get('total_unique_numbers', 0) > 0)
    #             },
    #             'contracts_preview': list(contracts_data['contracts'].keys())[:10],  # Prime 10 nuovi
    #             'processing_timestamp': datetime.now().isoformat()
    #         }
            
    #         logger.info(f"✅ Estrazione completata: +{save_result['new_contracts_added']} nuovi contratti")
    #         return jsonify(response_data)
            
    #     except Exception as e:
    #         logger.error(f"❌ Errore estrazione codici contratto: {e}")
    #         # Ripristina configurazione in caso di errore
    #         # if 'original_config' in locals():
    #         #     processor.config = original_config
                
    #         return jsonify({
    #             'success': False,
    #             'message': f'Errore durante estrazione: {str(e)}',
    #             'error_type': type(e).__name__,
    #             'timestamp': datetime.now().isoformat()
    #         }), 500

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
            contracts_filename = secure_config.get_config().get('CONTRACTS_CONFIG_FILE')
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
            contracts_filename = secure_config.get_config().get('CONTRACTS_CONFIG_FILE')
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
                contract['contract_name'] = data['contract_name'].strip() if data['contract_name'] is not None else None
            if 'odoo_client_id' in data:
                contract['odoo_client_id'] = data['odoo_client_id'].strip()
            if 'contract_type' in data:
                contract['contract_type'] = data['contract_type'].strip()
            if 'payment_term' in data:
                contract['payment_term'] = data['payment_term'].strip()
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

def add_datatable_routes_to_contratti(app, secure_config):
    """
    Aggiunge le route DataTables al file contratti_routes.py esistente
    
    Args:
        app: Istanza Flask
        secure_config: Configurazione sicura
    """
    
    # Import del servizio (da aggiungere all'inizio del file contratti_routes.py)
    from contratti import create_contracts_service
    
    # Crea istanza del servizio usando l'app Flask corrente
    contracts_service = create_contracts_service(app)
    
    @app.route('/api/contracts/datatable/ajax', methods=['GET'])
    def contracts_datatable_ajax():
        """
        Endpoint per DataTables in modalità AJAX
        Restituisce tutti i dati in formato oggetto JSON
        """
        try:
            logger.info("📋 Richiesta dati contratti per DataTables AJAX")
            
            # Recupera dati dal servizio
            data = contracts_service.get_contracts_for_ajax()
            
            if 'data' not in data:
                logger.error("Formato dati non valido dal servizio")
                return jsonify({
                    'data': [],
                    'error': 'Formato dati non valido'
                }), 500
            
            logger.info(f"✅ Restituiti {len(data['data'])} contratti in formato AJAX")
            # with open('output/contracts_output.json', 'w', encoding='utf-8') as f:
            #     json.dump(data, f, ensure_ascii=False, indent=2)
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"❌ Errore endpoint AJAX: {e}")
            return jsonify({
                'data': [],
                'error': str(e)
            }), 500
    
    @app.route('/api/contracts/datatable/serverside', methods=['GET', 'POST'])
    def contracts_datatable_serverside():
        """
        Endpoint per DataTables in modalità Server-side
        Gestisce paginazione, ordinamento e ricerca lato server
        """
        try:
            logger.info("🖥️ Richiesta dati contratti per DataTables Server-side")
            
            # Estrai parametri DataTables (funziona sia per GET che POST)
            if request.method == 'POST':
                params = request.form
            else:
                params = request.args
            
            # Parametri base DataTables
            draw = int(params.get('draw', 1))
            start = int(params.get('start', 0))
            length = int(params.get('length', 10))
            
            # Parametri ricerca
            search_value = params.get('search[value]', '').strip()
            
            # Parametri ordinamento
            order_column = int(params.get('order[0][column]', 0))
            order_dir = params.get('order[0][dir]', 'asc')
            
            logger.info(f"Parametri: draw={draw}, start={start}, length={length}, search='{search_value}', order={order_column} {order_dir}")
            
            # Recupera dati dal servizio
            data = contracts_service.get_contracts_for_serverside(
                draw=draw,
                start=start,
                length=length,
                search_value=search_value,
                order_column=order_column,
                order_dir=order_dir
            )
            
            # Validazione risposta
            required_keys = ['draw', 'recordsTotal', 'recordsFiltered', 'data']
            if not all(key in data for key in required_keys):
                logger.error("Formato dati server-side non valido dal servizio")
                return jsonify({
                    'draw': draw,
                    'recordsTotal': 0,
                    'recordsFiltered': 0,
                    'data': [],
                    'error': 'Formato dati non valido'
                }), 500
            
            logger.info(f"✅ Server-side: draw={data['draw']}, total={data['recordsTotal']}, filtered={data['recordsFiltered']}, data={len(data['data'])}")
            return jsonify(data)
            
        except ValueError as e:
            logger.error(f"❌ Errore parametri server-side: {e}")
            return jsonify({
                'draw': 1,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': [],
                'error': 'Parametri non validi'
            }), 400
            
        except Exception as e:
            logger.error(f"❌ Errore endpoint server-side: {e}")
            return jsonify({
                'draw': 1,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': [],
                'error': str(e)
            }), 500
    
    @app.route('/api/contracts/datatable/summary', methods=['GET'])
    def contracts_datatable_summary():
        """
        Endpoint per statistiche riassuntive dei contratti
        """
        try:
            logger.info("📊 Richiesta riassunto contratti")
            
            summary = contracts_service.get_contracts_summary()
            
            logger.info("✅ Riassunto contratti generato")
            return jsonify({
                'success': True,
                'summary': summary,
                'timestamp': summary.get('timestamp', '')
            })
            
        except Exception as e:
            logger.error(f"❌ Errore endpoint summary: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/contracts/datatable/test', methods=['GET'])
    def contracts_datatable_test():
        """
        Endpoint di test per verificare il funzionamento del servizio
        """
        try:
            logger.info("🧪 Test endpoint DataTables contratti")
            
            # Test connessione servizio
            summary = contracts_service.get_contracts_summary()
            
            # Test formato AJAX (primi 3 record)
            ajax_data = contracts_service.get_contracts_for_ajax()
            ajax_sample = ajax_data.get('data', [])[:3]
            
            # Test formato server-side (primi 3 record)
            serverside_data = contracts_service.get_contracts_for_serverside(
                draw=1, start=0, length=3
            )
            
            test_results = {
                'service_status': 'OK' if summary and 'error' not in summary else 'ERROR',
                'summary': summary,
                'ajax_format': {
                    'total_records': len(ajax_data.get('data', [])),
                    'sample_data': ajax_sample,
                    'format': 'object_array'
                },
                'serverside_format': {
                    'total_records': serverside_data.get('recordsTotal', 0),
                    'filtered_records': serverside_data.get('recordsFiltered', 0),
                    'sample_data': serverside_data.get('data', [])[:3],
                    'format': 'value_array'
                },
                'endpoints': {
                    'ajax': '/api/contracts/datatable/ajax',
                    'serverside': '/api/contracts/datatable/serverside',
                    'summary': '/api/contracts/datatable/summary',
                    'test': '/api/contracts/datatable/test'
                }
            }
            
            logger.info("✅ Test completato con successo")
            return jsonify({
                'success': True,
                'test_results': test_results,
                'message': 'Test completato con successo'
            })
            
        except Exception as e:
            logger.error(f"❌ Errore test endpoint: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Test fallito'
            }), 500
    
    # Log delle route registrate
    logger.info("🔗 Route DataTables contratti aggiunte a contratti_routes.py:")
    logger.info("   📋 /api/contracts/datatable/ajax (GET)")
    logger.info("   🖥️ /api/contracts/datatable/serverside (GET/POST)")
    logger.info("   📊 /api/contracts/datatable/summary (GET)")
    logger.info("   🧪 /api/contracts/datatable/test (GET)")
    
    return {
        'routes_added': [
            '/api/contracts/datatable/ajax',
            '/api/contracts/datatable/serverside', 
            '/api/contracts/datatable/summary',
            '/api/contracts/datatable/test'
        ],
        'routes_count': 4
    }

def add_elaborazione_contratti_routes(app, secure_config, elaboratore_instance=None):
    """
    Aggiunge route API Flask per l'elaborazione contratti
    
    Args:
        app: Istanza Flask
        elaboratore_instance: Istanza ElaborazioneContratti (opzionale)
    
    Returns:
        Dict con informazioni sulle route aggiunte
    """
    
    # Import della classe (modifica il percorso secondo la tua struttura)
    from contratti import ElaborazioneContratti
    
    # Crea istanza se non fornita
    if elaboratore_instance is None:
        elaboratore_instance = ElaborazioneContratti()
    
    @app.route('/api/contracts/info', methods=['GET'])
    def api_contracts_info():
        """
        GET /api/contracts/info
        Restituisce informazioni sui contratti senza elaborarli
        
        Response:
        {
            "success": true,
            "data": {
                "total": 21,
                "valid": 15,
                "invalid": 6,
                "types": {"A CONSUMO": 15}
            },
            "timestamp": "2024-06-11T..."
        }
        """
        try:
            logger.info("📊 Richiesta info contratti")
            info = elaboratore_instance.ottieni_info_contratti()
            
            return jsonify({
                'success': True,
                'data': info,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Errore API info contratti: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/api/contracts/process', methods=['GET'])
    def api_process_contracts_get():
        """
        GET /api/contracts/run
        Elabora tutti i contratti - SUPER SEMPLICE
        
        Parametri opzionali:
        ?timeout=60
        """
        timeout = int(request.args.get('timeout', 30))
        
        # Chiama elaborazione
        result = elaboratore_instance.elabora_tutti_contratti_get(timeout)
        
        # Restituisci risultato
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
        
    @app.route('/api/contracts/process', methods=['POST'])
    def api_process_contracts():
        """
        POST /api/contracts/process
        Elabora tutti i contratti validi
        
        Request Body (opzionale):
        {
            "processor_name": "nome_funzione_personalizzata",
            "timeout": 30,
            "custom_params": {...}
        }
        
        Response:
        {
            "success": true,
            "message": "Elaborazione completata: 15 successi, 0 errori",
            "results": [...],
            "summary": {
                "total_processed": 15,
                "successful": 15,
                "failed": 0,
                "timeout_used": 30
            }
        }
        """
        try:
            # Leggi parametri dalla richiesta
            data = request.get_json() or {}
            timeout = data.get('timeout', 30)
            processor_name = data.get('processor_name', 'default')
            custom_params = data.get('custom_params', {})
            
            logger.info(f"🔄 Avvio elaborazione contratti (timeout: {timeout}s)")
            
            # Funzione di elaborazione di default
            def default_processor(contract_code: str, contract_type: str, odoo_client_id: str):
                """Elaborazione di default - PERSONALIZZA QUESTA FUNZIONE"""
                logger.info(f"🔄 Elaborando contratto {contract_code}")
                
                # ============================================
                # QUI AGGIUNGI LA TUA LOGICA SPECIFICA:
                # - Generazione report CDR
                # - Chiamate ad altre API
                # - Aggiornamento database
                # - Invio email/notifiche
                # - etc.
                # ============================================
                
                # Esempio base di elaborazione
                elaboration_result = {
                    'contract_code': contract_code,
                    'contract_type': contract_type,
                    'odoo_client_id': odoo_client_id,
                    'status': 'processed',
                    'processor_used': processor_name,
                    'timestamp': datetime.now().isoformat(),
                    'custom_params': custom_params
                }
                
                # Aggiungi logica personalizzata qui
                # elaboration_result['report_generated'] = generate_cdr_report(contract_code)
                # elaboration_result['email_sent'] = send_notification(contract_code)
                
                return elaboration_result
            
            # Esegui elaborazione di tutti i contratti validi
            results = elaboratore_instance.elabora_tutti_contratti(
                processor_func=default_processor,
                timeout=timeout
            )
            
            # Calcola statistiche risultati
            successi = len([r for r in results if r.get('status') != 'failed'])
            errori = len(results) - successi
            
            logger.info(f"✅ Elaborazione completata: {successi} successi, {errori} errori")
            
            return jsonify({
                'success': True,
                'message': f'Elaborazione completata: {successi} successi, {errori} errori',
                'results': results,
                'summary': {
                    'total_processed': len(results),
                    'successful': successi,
                    'failed': errori,
                    'timeout_used': timeout,
                    'processor_used': processor_name,
                    'execution_time': datetime.now().isoformat()
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Errore API elaborazione contratti: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/api/contracts/process/status', methods=['GET'])
    def api_contracts_status():
        """
        GET /api/contracts/process/status
        Verifica lo stato del sistema elaborazione contratti
        """
        try:
            # Testa connessione API contratti
            info = elaboratore_instance.ottieni_info_contratti()
            
            if 'error' in info:
                status = 'error'
                message = f"Errore connessione API: {info['error']}"
            else:
                status = 'ready'
                message = f"Sistema pronto - {info.get('valid', 0)} contratti validi disponibili"
            
            return jsonify({
                'success': True,
                'status': status,
                'message': message,
                'api_url': elaboratore_instance.api_url,
                'contracts_info': info,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Errore verifica status: {e}")
            return jsonify({
                'success': False,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    # Log delle route registrate
    logger.info("🔗 Route API ElaborazioneContratti registrate:")
    logger.info("   GET  /api/contracts/info - Info contratti")
    logger.info("   POST /api/contracts/process - Elabora contratti")
    logger.info("   GET  /api/contracts/process/status - Status sistema")
    
    return {
        'routes_added': [
            '/api/contracts/info',
            '/api/contracts/process',
            '/api/contracts/process/status'
        ],
        'routes_count': 3,
        'elaboratore_instance': elaboratore_instance
    }