import json
import logging
from logger_config import get_logger, log_success, log_error, log_warning, log_info
from exception_handler import handle_exceptions, APIResponse, ExceptionHandler
from performance_monitor import get_performance_monitor
from pathlib import Path
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, Response

def schedule_routes(app, secure_config, scheduler_manager):
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
            log_error(f"Errore nella configurazione rapida: {e}")
            return jsonify({'success': False, 'message': str(e)})


    @app.route('/schedule_reset')
    def schedule_reset():
        """Reset della schedulazione ai valori originali del file .env"""
        try:
            # Legge direttamente dal file .env
            env_values = _read_env_file()
            
            if not env_values:
                return jsonify({
                    'success': False, 
                    'message': 'File .env non trovato o non leggibile'
                })
            
            # Estrae solo i parametri di schedulazione dal .env
            schedule_params = {
                'schedule_type': env_values.get('SCHEDULE_TYPE', 'monthly'),
                'schedule_day': int(env_values.get('SCHEDULE_DAY', 1)),
                'schedule_hour': int(env_values.get('SCHEDULE_HOUR', 9)),
                'schedule_minute': int(env_values.get('SCHEDULE_MINUTE', 0)),
                'interval_days': int(env_values.get('INTERVAL_DAYS', 30)),
                'cron_expression': env_values.get('CRON_EXPRESSION', '0 9 1 * *')
            }
            
            # Aggiorna solo i parametri di schedulazione
            secure_config.update_config(schedule_params)
            
            # Riavvia scheduler con nuova configurazione
            scheduler_manager.set_config(secure_config.get_config())
            success = scheduler_manager.restart_scheduler()
            
            if success:
                # Salva configurazione
                from config import save_config_to_env
                save_config_to_env(secure_config, app.secret_key)
                
                log_info("Schedulazione ripristinata ai valori del file .env")
                
                return jsonify({
                    'success': True,
                    'message': 'Schedulazione ripristinata ai valori originali del file .env',
                    'schedule_description': scheduler_manager.get_schedule_description(),
                    'original_values': schedule_params,
                    'next_jobs': scheduler_manager.get_next_scheduled_jobs()
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': 'Errore nel riavvio dello scheduler'
                })
                
        except Exception as e:
            log_error(f"Errore nel reset della schedulazione: {e}")
            return jsonify({
                'success': False, 
                'message': f'Errore durante il reset: {str(e)}'
            })


    def _read_env_file():
        """Legge il file .env e restituisce un dizionario con i valori"""
        from pathlib import Path
        
        env_file = Path('.env')
        if not env_file.exists():
            log_error("File .env non trovato")
            return None
        
        env_values = {}
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Ignora righe vuote e commenti
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")  # Rimuove virgolette
                        env_values[key] = value
            
            log_info(f"Letti {len(env_values)} parametri dal file .env")
            return env_values
            
        except Exception as e:
            log_error(f"Errore lettura file .env: {e}")
            return None