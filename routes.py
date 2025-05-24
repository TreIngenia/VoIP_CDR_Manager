import json
import logging
from pathlib import Path
from flask import render_template, request, jsonify, redirect, url_for

logger = logging.getLogger(__name__)

def create_routes(app, secure_config, processor, scheduler_manager):
    """Crea tutte le route Flask"""
    
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
                from config import save_config_to_env
                save_config_to_env(secure_config, app.secret_key)
                
                # Aggiorna processore
                processor.config = secure_config.get_config()
                
                # Aggiorna e riavvia scheduler
                scheduler_manager.set_config(secure_config.get_config())
                scheduler_manager.restart_scheduler()
                
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
            
            return jsonify({
                'scheduled_jobs': jobs,
                'last_execution': last_execution,
                'config': secure_config.get_safe_config(),
                'scheduler_running': scheduler_manager.is_running()
            })
        except Exception as e:
            logger.error(f"Errore endpoint status: {e}")
            return jsonify({'error': 'Errore interno del server'}), 500

    @app.route('/env_status')
    def env_status():
        """Mostra lo stato delle variabili d'ambiente (senza password)"""
        try:
            import os
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
            from datetime import datetime
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
            from scheduler import (set_schedule_every_minute, set_schedule_every_hour, 
                                 set_schedule_every_30_minutes, set_schedule_every_10_seconds)
            
            if schedule_type == 'every_minute':
                set_schedule_every_minute(scheduler_manager)
                message = "Schedulazione impostata: ogni minuto"
                
            elif schedule_type == 'every_hour':
                set_schedule_every_hour(scheduler_manager)
                message = "Schedulazione impostata: ogni ora"
                
            elif schedule_type == 'every_30_minutes':
                set_schedule_every_30_minutes(scheduler_manager)
                message = "Schedulazione impostata: ogni 30 minuti"
                
            elif schedule_type == 'every_10_seconds':
                set_schedule_every_10_seconds(scheduler_manager)
                message = "Schedulazione impostata: ogni 10 secondi (TEST)"
                
            else:
                return jsonify({'success': False, 'message': 'Tipo di schedulazione non riconosciuto'})
            
            # Salva configurazione
            from config import save_config_to_env
            save_config_to_env(secure_config, app.secret_key)
            
            return jsonify({
                'success': True,
                'message': message,
                'schedule_description': scheduler_manager.get_schedule_description(),
                'next_jobs': scheduler_manager.get_next_scheduled_jobs()
            })
            
        except Exception as e:
            logger.error(f"Errore nella configurazione rapida: {e}")
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

    def _scheduled_job():
        """Job schedulato che esegue il processo completo"""
        logger.info("Esecuzione job schedulato")
        result = processor.process_files()
        
        # Salva il risultato dell'ultima esecuzione
        config = secure_config.get_config()
        log_file = Path(config['output_directory']) / 'last_execution.json'
        with open(log_file, 'w') as f:
            json.dump(result, f, indent=2)
    
    # Imposta la funzione job nello scheduler
    scheduler_manager.set_job_function(_scheduled_job)
    
    return app