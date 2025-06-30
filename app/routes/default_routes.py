import json
import logging
from logger_config import get_logger, log_success, log_error, log_warning, log_info
from exception_handler import handle_exceptions, APIResponse, ExceptionHandler
from performance_monitor import get_performance_monitor
from pathlib import Path
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, Response
from ftp_downloader import FTPDownloader
logger = get_logger(__name__)

def create_routes(app, secure_config, scheduler_manager):
    from routes.menu_routes import menu_bp, register_menu_globals, render_with_menu_context
    """Crea tutte le route Flask"""
    # Registra blueprint menu
    app.register_blueprint(menu_bp)
    
    # Registra funzioni globali menu
    register_menu_globals(app)

    @app.route('/')
    def index():
        """Pagina principale"""
        dashboard_data = {
            'config': secure_config.get_safe_config(),
            'stats': {
                'scheduler_running': scheduler_manager.is_running(),
                'total_jobs': len(scheduler_manager.get_job_info()),
            }
        }
        # return render_template('index.html', config=secure_config.get_config())
        return render_with_menu_context('index.html', dashboard_data)

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
                from config import save_config_to_env
                save_config_to_env(secure_config, app.secret_key)
                           
                # Aggiorna e riavvia scheduler
                scheduler_manager.set_config(secure_config)
                scheduler_manager.restart_scheduler()
                
                logger.info("Configurazione aggiornata con successo")
                return redirect(url_for('config_page'))
                
            except Exception as e:
                logger.error(f"Errore aggiornamento configurazione: {e}")
                # In caso di errore, non crashare ma mostrare messaggio
                return render_template('config.html', 
                                     config=secure_config.get_config(),
                                     error=f"Errore nell'aggiornamento: {str(e)}")
        
        return render_with_menu_context('config.html', {'config':secure_config.get_config()})

    def clean_for_json_serialization(data):
        """
        Pulisce i dati per renderli serializzabili in JSON
        
        Args:
            data: Dati da pulire (dict, list, o altro)
            
        Returns:
            Dati puliti serializzabili in JSON
        """
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                try:
                    cleaned[key] = clean_for_json_serialization(value)
                except Exception as e:
                    # Se il valore non è serializzabile, convertilo in stringa
                    logger.warning(f"Valore non serializzabile per chiave '{key}': {e}")
                    cleaned[key] = str(value)
            return cleaned
            
        elif isinstance(data, list):
            return [clean_for_json_serialization(item) for item in data]
            
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
            
        elif hasattr(data, 'isoformat'):  # datetime objects
            return data.isoformat()
            
        elif hasattr(data, '__dict__'):  # Custom objects
            return str(data)
            
        else:
            # Fallback per altri tipi
            return str(data)
        

    @app.route('/logs')
    def logs():
        """Visualizza i log dell'applicazione su pagina HTML"""
        try:
            config = secure_config.get_config()
            log_file = Path() / 'logs/app.log'
            last_logs = []

            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        all_lines = f.readlines()
                except UnicodeDecodeError:
                    with open(log_file, 'r', encoding='latin1') as f:
                        all_lines = f.readlines()

                last_logs = [line.strip() for line in all_lines if line.strip()]
            else:
                last_logs = ["⚠️ File di log non trovato."]

            return render_with_menu_context('logs.html', {'logs':last_logs})

        except Exception as e:
            logger.error(f"Errore endpoint logs: {e}")
            return render_template('logs.html', logs=["❌ Errore interno del server."])

    @app.route('/status')
    def status():
        """Stato dell'applicazione senza dati sensibili"""
        try:
            jobs = scheduler_manager.get_job_info()
            
            # Legge l'ultima esecuzione se disponibile
            last_execution = None
            log_file = Path(secure_config.get_config()['output_directory']) / 'last_execution.json'
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        last_execution = json.load(f)
                except Exception as e:
                    logger.error(f"Errore lettura ultima esecuzione: {e}")
            
            last_logs = jsonify({
                'scheduled_jobs': jobs,
                'last_execution': last_execution,
                'config': secure_config.get_safe_config(),
                'scheduler_running': scheduler_manager.is_running()
            })
        
            return last_logs
        except Exception as e:
            logger.error(f"Errore endpoint status: {e}")
            return jsonify({'error': 'Errore interno del server'}), 500
        
    @app.route('/status_page')
    def status_page():
        """Stato dell'applicazione senza dati sensibili"""
        try:
            jobs = scheduler_manager.get_job_info()
            
            # Legge l'ultima esecuzione se disponibile
            last_execution = None
            log_file = Path(secure_config.get_config()['output_directory']) / 'last_execution.json'
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        last_execution = json.load(f)
                except Exception as e:
                    logger.error(f"Errore lettura ultima esecuzione: {e}")
            
            last_logs = {
                'scheduled_jobs': jobs,
                'last_execution': last_execution,
                'config': secure_config.get_safe_config(),
                'scheduler_running': scheduler_manager.is_running()
            }
            last_logs_json = jsonify(last_logs)
             # ✅ Converti in testo JSON formattato
            json_text = json.dumps(last_logs, indent=2, ensure_ascii=False)
            # return  last_logs_json
            return render_template('logs.html', json=json_text)
        except Exception as e:
            logger.error(f"Errore endpoint status: {e}")
            return jsonify({'error': 'Errore interno del server'}), 500
        

    @app.route('/test_pattern', methods=['POST'])
    def test_pattern():
        """Test pattern con validazione input"""
        try:
            from ftp_downloader import FTPDownloader
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'})
            
            pattern = data.get('pattern', '').strip()
            
            converter = FTPDownloader(secure_config)
            result = converter.check_file(pattern,True)

            if result['success'] == True:
                    return jsonify({
                    'success': True,
                    'pattern': pattern,
                    'match_count': len(result['downloaded_files']['files']),
                    'matching_files': result['downloaded_files']['files'],  # Limita risultati
                    'total_files': len(result['total_in_ftp'])
                })
            else:
                return jsonify({'success': False, 'message': result['error']})
            
            
            
        except Exception as e:
            log_error(f"Errore nel test pattern: {e}")
            return jsonify({'success': False, 'message': 'Errore interno del server'})


    @app.route('/pattern_examples')
    def pattern_examples():
        """Restituisce esempi di pattern con variabili temporali"""
        try:
            from file_processor import ConvertFILE
            file = ConvertFILE(secure_config)
            examples = file.generate_pattern_examples()
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
            
            converter = FTPDownloader(secure_config)
            result = converter.check_file("*",True)

            if result['success'] == True:
                    return jsonify({
                'success': True,
                'files': result['total_in_ftp'],
                'count': len(result['total_in_ftp'])
            })

            
        except Exception as e:
            logger.error(f"Errore nel listare file FTP: {e}")
            return jsonify({'success': False, 'message': str(e)})
    

    @app.route('/schedule_info')
    def schedule_info():
        """Informazioni sulla schedulazione corrente"""
        try:
            job_info = scheduler_manager.get_job_info()
            
            return jsonify({
                'success': True,
                'schedule_description': scheduler_manager.get_schedule_description(),
                'active_jobs': job_info,
                'scheduler_running': scheduler_manager.is_running(),
            })
            
        except Exception as e:
            logger.error(f"Errore nel recupero info schedulazione: {e}")
            return jsonify({'success': False, 'message': str(e)})


    @app.route('/api/voip/update_prices', methods=['POST'])
    def update_voip_prices():
        """API per aggiornare prezzi VoIP e calcolare automaticamente i prezzi finali"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'})
            
            base_fixed = data.get('base_fixed')
            base_mobile = data.get('base_mobile')
            markup_percent = data.get('markup_percent')
            
            # Aggiorna prezzi usando il metodo della configurazione sicura
            result = secure_config.update_voip_prices(base_fixed, base_mobile, markup_percent)
            
            # Salva configurazione
            from config import save_config_to_env
            save_config_to_env(secure_config, app.secret_key)
            
            return jsonify({
                'success': True,
                'message': 'Prezzi VoIP aggiornati',
                'prices': result
            })
            
        except Exception as e:
            logger.error(f"Errore aggiornamento prezzi VoIP via API: {e}")
            return jsonify({'success': False, 'message': str(e)})


    @app.route('/api/voip/calculate', methods=['POST'])
    def calculate_voip_prices():
        """API per calcolare prezzi finali senza salvare"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'})
            
            base_fixed = float(data.get('base_fixed', 0))
            base_mobile = float(data.get('base_mobile', 0))
            markup_percent = float(data.get('markup_percent', 0))
            
            # Calcola prezzi finali
            markup_multiplier = 1 + (markup_percent / 100)
            final_fixed = base_fixed * markup_multiplier
            final_mobile = base_mobile * markup_multiplier
            
            return jsonify({
                'success': True,
                'calculation': {
                    'base_fixed': base_fixed,
                    'base_mobile': base_mobile,
                    'markup_percent': markup_percent,
                    'markup_multiplier': markup_multiplier,
                    'final_fixed': round(final_fixed, 4),
                    'final_mobile': round(final_mobile, 4),
                    'example_5min_fixed': round(final_fixed * 5, 2),
                    'example_5min_mobile': round(final_mobile * 5, 2)
                }
            })
            
        except Exception as e:
            logger.error(f"Errore calcolo prezzi VoIP: {e}")
            return jsonify({'success': False, 'message': str(e)})


    @app.route('/health')
    def health_check():
        """Endpoint di health check per monitoraggio"""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'checks': {}
            }
            
            # Check FTP connectivity
            try:
                ftp = processor.connect_ftp()
                ftp.quit()
                health_status['checks']['ftp'] = {
                    'status': 'pass',
                    'details': 'FTP connection successful'
                }
            except Exception as e:
                health_status['checks']['ftp'] = {
                    'status': 'fail',
                    'details': f'FTP connection failed: {str(e)}'
                }
            
            # Check scheduler
            health_status['checks']['scheduler'] = {
                'status': 'pass' if scheduler_manager.is_running() else 'fail',
                'details': f'Scheduler running: {scheduler_manager.is_running()}'
            }
            
            # Check disk space
            try:
                import shutil
                output_dir = secure_config.get_config()['output_directory']
                disk_usage = shutil.disk_usage(output_dir)
                free_percent = (disk_usage.free / disk_usage.total) * 100
                
                if free_percent < 10:
                    status = 'fail'
                    message = f'Low disk space: {free_percent:.1f}% free'
                elif free_percent < 20:
                    status = 'warn'
                    message = f'Disk space warning: {free_percent:.1f}% free'
                else:
                    status = 'pass'
                    message = f'Disk space OK: {free_percent:.1f}% free'
                
                health_status['checks']['disk_space'] = {
                    'status': status,
                    'details': message,
                    'free_gb': round(disk_usage.free / (1024**3), 2),
                    'total_gb': round(disk_usage.total / (1024**3), 2)
                }
            except Exception as e:
                health_status['checks']['disk_space'] = {
                    'status': 'warn',
                    'details': f'Could not check disk space: {str(e)}'
                }
            
            # Overall health status
            failed_checks = [k for k, v in health_status['checks'].items() if v['status'] == 'fail']
            if failed_checks:
                health_status['status'] = 'unhealthy'
                health_status['failed_checks'] = failed_checks
            elif any(v['status'] == 'warn' for v in health_status['checks'].values()):
                health_status['status'] = 'degraded'
            
            # Return appropriate HTTP status
            if health_status['status'] == 'healthy':
                return jsonify(health_status), 200
            elif health_status['status'] == 'degraded':
                return jsonify(health_status), 200  # Still OK but with warnings
            else:
                return jsonify(health_status), 503  # Service Unavailable
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }), 500

    def _scheduled_job():
        from config import SecureConfig
        secure_config = SecureConfig()
        config = secure_config.get_config()
        
        # ✅ Istanzia il downloader
        downloader = FTPDownloader(config)
        
        # ✅ Chiama il metodo sull'istanza
        result = downloader.process_files()
        # return(result)

        # result = processor.process_files()
        
        # Salva il risultato dell'ultima esecuzione
        config = secure_config.get_config()
        log_file = Path(config['output_directory']) / 'last_execution.json'
        with open(log_file, 'w') as f:
            json.dump(result, f, indent=2)
    
    # Imposta la funzione job nello scheduler
    scheduler_manager.set_job_function(_scheduled_job)
    
    # Aggiungi questi route nella funzione setup_cdr_analytics()

    # @app.route('/cdr_dashboard')
    # def cdr_dashboard():
    #     """Dashboard principale CDR Analytics"""
    #     try:
    #         # Ottieni statistiche
    #         reports = processor.cdr_analytics.list_generated_reports()
    #         # Separa report individuali e summary
    #         individual_reports = [r for r in reports if not r['is_summary']]
    #         summary_reports = [r for r in reports if r['is_summary']]
            
    #         # Calcola statistiche
    #         total_size = sum(r['size_bytes'] for r in reports)
            
    #         stats = {
    #             'total_reports': len(reports),
    #             'individual_reports': len(individual_reports),
    #             'summary_reports': len(summary_reports),
    #             'total_size_mb': round(total_size / (1024*1024), 2),
    #             'analytics_directory': str(processor.cdr_analytics.analytics_directory)
    #         }
            
    #         return render_template('cdr_dashboard.html', 
    #                             reports=reports,  # Ultimi 10
    #                             stats=stats,
    #                             individual_reports=individual_reports,
    #                             summary_reports=summary_reports)
                                
    #     except Exception as e:
    #         logger.error(f"Errore dashboard CDR: {e}")
    #         return render_template('error.html', 
    #                             error_message=f"Errore caricamento dashboard CDR: {e}")

    @app.route('/cdr_analytics/process_all')
    def process_all_cdr():
        """Elabora tutti i file CDR nella directory output"""
        try:
            output_dir = Path(processor.config['output_directory'])
            processed_files = []
            errors = []
            
            # Trova tutti i file JSON che potrebbero essere CDR
            for json_file in output_dir.glob("*.json"):
                # Usa il metodo _is_cdr_file del processore se disponibile
                is_cdr = False
                if hasattr(processor, '_is_cdr_file'):
                    is_cdr = processor._is_cdr_file(str(json_file))
                else:
                    # Fallback: controlla il nome del file
                    filename = json_file.name.upper()
                    is_cdr = 'CDR' in filename or 'RIV' in filename
                
                if is_cdr:
                    try:
                        result = processor.cdr_analytics.process_cdr_file(str(json_file))
                        if result['success']:
                            processed_files.append({
                                'file': json_file.name,
                                'reports_generated': len(result.get('generated_files', [])),
                                'voip_enabled': result.get('voip_pricing_enabled', False),
                                'contracts': result.get('total_contracts', 0)
                            })
                        else:
                            errors.append({
                                'file': json_file.name,
                                'error': result.get('message', 'Errore sconosciuto')
                            })
                    except Exception as e:
                        errors.append({
                            'file': json_file.name,
                            'error': str(e)
                        })
            
            return jsonify({
                'success': True,
                'processed_files': len(processed_files),
                'errors': len(errors),
                'files_details': processed_files,
                'errors_details': errors,
                'voip_pricing_enabled': any(f.get('voip_enabled', False) for f in processed_files)
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/cdr_analytics/report_details/<path:filename>')
    def cdr_report_details(filename):
        """Mostra dettagli di un report specifico con supporto per file SUMMARY"""
        try:
            report_path = processor.cdr_analytics.analytics_directory / filename
            
            if not report_path.exists():
                return jsonify({'success': False, 'message': 'Report non trovato'}), 404
            
            # Carica il report
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            # ✅ CORREZIONE: Rileva automaticamente il tipo di file
            is_summary = filename.startswith('SUMMARY_') or 'global_totals' in report_data
            
            if is_summary:
                # ========== GESTIONE FILE SUMMARY (Report Globale) ==========
                metadata = report_data.get('metadata', {})
                global_totals = report_data.get('global_totals', {})
                global_by_type = report_data.get('global_by_call_type', {})
                
                details = {
                    'filename': filename,
                    'is_summary': True,
                    'contract_code': 'SUMMARY_GLOBALE',
                    'total_calls': global_totals.get('total_calls', 0),
                    'total_duration_minutes': global_totals.get('total_duration_minutes', 0),
                    'total_cost': global_totals.get('total_cost_euro', 0),
                    'client_city': f"Tutti i contratti ({global_totals.get('total_contracts', 0)} contratti)",
                    'generation_date': metadata.get('generation_timestamp'),
                    'call_types_breakdown': global_by_type,  # ✅ Usa la struttura corretta per SUMMARY
                    'contracts_summary': report_data.get('contracts_summary', {}),
                    'top_contracts': report_data.get('top_contracts', {}),
                    'metadata': metadata
                }
            else:
                # ========== GESTIONE FILE CONTRATTO SINGOLO (Report Individuale) ==========
                summary = report_data.get('summary', {})
                metadata = report_data.get('metadata', {})
                
                details = {
                    'filename': filename,
                    'is_summary': False,
                    'contract_code': summary.get('codice_contratto'),
                    'total_calls': summary.get('totale_chiamate'),
                    'total_duration_minutes': summary.get('durata_totale_minuti'),
                    'total_cost': summary.get('costo_totale_euro'),
                    'client_city': summary.get('cliente_finale_comune'),
                    'generation_date': metadata.get('generation_timestamp'),
                    'call_types_breakdown': report_data.get('call_types_breakdown', {}),  # ✅ Usa la struttura corretta per contratti singoli
                    'daily_breakdown': report_data.get('daily_breakdown', {})
                }
            
            return jsonify({'success': True, 'details': details})
            
        except Exception as e:
            logger.error(f"Errore dettagli report: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
        
    

    
    
    @app.route('/api/cdr/process_with_categories/<path:filename>')
    def process_single_cdr_with_categories(filename):
        """Elabora un singolo file CDR con il nuovo sistema categorie"""
        try:
            from flask import jsonify
            
            file_path = Path(processor.config['output_directory']) / filename
            
            if not file_path.exists():
                return jsonify({'success': False, 'message': 'File non trovato'}), 404
            
            # ✅ USA IL NUOVO SISTEMA INTEGRATO
            result = processor.cdr_analytics.process_cdr_file(str(file_path))
            
            if result['success']:
                # ✅ ESTRAI INFO CATEGORIE PER RISPOSTA
                category_stats = result.get('category_stats', {})
                categories_summary = {
                    'total_categories_used': len(category_stats),
                    'categories_breakdown': category_stats,
                    'has_costo_cliente_by_category': True,  # ✅ CONFERMA CAMPO RICHIESTO
                    'system_version': '2.0'
                }
                
                result['categories_summary'] = categories_summary
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/cdr/categories_summary')
    def get_categories_system_summary():
        """Restituisce riassunto sistema categorie"""
        try:
            from flask import jsonify
            
            if not hasattr(processor, 'cdr_analytics') or not hasattr(processor.cdr_analytics, 'categories_manager'):
                return jsonify({'success': False, 'message': 'Sistema categorie non disponibile'}), 500
            
            categories_manager = processor.cdr_analytics.categories_manager
            
            # ✅ INFO SISTEMA CATEGORIE
            summary = {
                'success': True,
                'system_version': '2.0',
                'system_enabled': True,
                'categories_stats': categories_manager.get_statistics(),
                'active_categories': len(categories_manager.get_active_categories()),
                'total_categories': len(categories_manager.get_all_categories()),
                'conflicts': categories_manager.validate_patterns_conflicts(),
                'config_file': str(categories_manager.config_file),
                'features': {
                    'costo_cliente_totale_euro_by_category': True,  # ✅ CAMPO RICHIESTO
                    'pattern_matching': True,
                    'custom_pricing': True,
                    'conflict_detection': True,
                    'import_export': True
                }
            }
            
            return jsonify(summary)
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/cdr/test_category_matching', methods=['POST'])
    def test_category_matching():
        """Testa il matching di categorie per tipi di chiamata"""
        try:
            from flask import request, jsonify
            
            data = request.get_json()
            if not data or 'call_types' not in data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            call_types = data['call_types']
            duration_seconds = int(data.get('duration_seconds', 300))
            
            if not hasattr(processor, 'cdr_analytics') or not hasattr(processor.cdr_analytics, 'categories_manager'):
                return jsonify({'success': False, 'message': 'Sistema categorie non disponibile'}), 500
            
            categories_manager = processor.cdr_analytics.categories_manager
            results = []
            
            for call_type in call_types:
                # ✅ USA IL NUOVO SISTEMA DI CALCOLO
                classification = categories_manager.calculate_call_cost(call_type, duration_seconds)
                
                results.append({
                    'call_type': call_type,
                    'category_name': classification['category_name'],
                    'category_display': classification['category_display_name'],
                    'matched': classification['matched'],
                    'price_per_minute': classification['price_per_minute'],
                    'cost_calculated': classification['cost_calculated'],
                    'currency': classification['currency'],
                    'duration_billed': classification['duration_billed'],
                    'unit_label': classification['unit_label']
                })
            
            return jsonify({
                'success': True,
                'test_duration_seconds': duration_seconds,
                'results': results,
                'system_version': '2.0'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/cdr/reports_with_categories')
    def list_reports_with_categories():
        """Lista report CDR con informazioni su supporto categorie"""
        try:
            from flask import jsonify
            
            if not hasattr(processor, 'cdr_analytics'):
                return jsonify({'success': False, 'message': 'Sistema CDR non disponibile'}), 500
            
            reports = processor.cdr_analytics.list_generated_reports()
            
            # ✅ AGGIUNGI INFO CATEGORIE
            enhanced_reports = []
            for report in reports:
                enhanced_report = report.copy()
                enhanced_report['supports_categories'] = report.get('categories_version', '1.0') == '2.0'
                enhanced_report['has_costo_by_category'] = report.get('has_categories', False)
                enhanced_reports.append(enhanced_report)
            
            return jsonify({
                'success': True,
                'reports': enhanced_reports,
                'total_reports': len(enhanced_reports),
                'categories_enabled_reports': len([r for r in enhanced_reports if r['supports_categories']]),
                'system_version': '2.0'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # @app.route('/gestione_contratti')
    # def gestione_utenti():
    #     return render_with_menu_context('gestione_contratti.html', {'config':secure_config.get_config()})    
    
    @app.route('/default_page')
    def default_page():
        return render_with_menu_context('index_base.html', {'config':secure_config.get_config()})    


    # ============ ERROR HANDLERS ============

    @app.errorhandler(404)
    def not_found_error(error):
        """Handler per errori 404"""
        return render_with_menu_context(
            'templates/error.html', 
            {'error_code': 404, 'error_message': 'La pagina richiesta non è stata trovata'}
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handler per errori 500"""
        return render_with_menu_context(
            'templates/error.html',
            {'error_code': 500, 'error_message': 'Si è verificato un errore interno del server'}
        ), 500

    # ============ CONTEXT PROCESSORS ============               
    return app