#!/usr/bin/env python3
"""
FTP Scheduler App - Versione Completa con Sistema Categorie CDR Integrato
Modifiche per utilizzare il nuovo sistema categorie invece dei precedenti approcci
"""

import os
import sys
import socket
from datetime import timedelta
from pathlib import Path

# Carica variabili dal file .env (opzionale)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Carica variabili dal file .env
    print("📁 File .env caricato")
except ImportError:
    print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")

# Import moduli personalizzati
from config import SecureConfig
# Import moduli migliorati (aggiunti da migrazione)
from logger_config import get_logger, log_success, log_error, log_warning, log_info
from config_validator import ConfigValidator
from performance_monitor import get_performance_monitor
# from exception_handler import ExceptionHandler, log_success, log_error, log_warning, log_info
from config import save_config_to_env, load_config_from_env_local
from ftp_processor import FTPProcessor
from scheduler import SchedulerManager
from routes import create_routes

# ✅ NUOVO: Import del sistema categorie integrato invece dei vecchi sistemi
from cdr_integration_enhanced import integrate_enhanced_cdr_system
from categories_routes import add_categories_routes

# Import Flask
from flask import Flask

def create_app():
    """Factory function per creare l'app Flask"""
    app = Flask(__name__)
    
    # Configurazione Flask sicura
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(32)),
        SESSION_COOKIE_SECURE=True if os.getenv('HTTPS', 'false').lower() == 'true' else False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
    )
    
    
    # Route performance monitoring (aggiunto da migrazione)
    @app.route('/api/metrics/performance')
    def get_performance_metrics():
        monitor = get_performance_monitor()
        return jsonify(monitor.get_application_metrics())
    
    @app.route('/api/health/detailed')
    def get_detailed_health():
        monitor = get_performance_monitor()
        return jsonify(monitor.get_health_status())
    
    return app

def find_free_port(start_port=5000):
    """Trova una porta libera a partire dalla porta specificata"""
    for port in range(start_port, start_port + 10):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    
    return start_port

def print_startup_info(app_host, app_port):
    """Stampa informazioni di avvio con info sistema categorie"""
    print("\n" + "="*60)
    print("AVVIO FTP SCHEDULER APP - VERSIONE CON CATEGORIE CDR 2.0")
    print("="*60)
    print(f"Dashboard: http://{app_host}:{app_port}")
    print(f"Configurazione: http://{app_host}:{app_port}/config")
    print(f"Gestione Categorie CDR: http://{app_host}:{app_port}/categories")  # ✅ NUOVO
    print(f"Dashboard CDR: http://{app_host}:{app_port}/cdr_dashboard")  # ✅ NUOVO
    print(f"Log: http://{app_host}:{app_port}/logs")
    print(f"Stato: http://{app_host}:{app_port}/status")
    print("="*60)
    
    # ✅ Informazioni configurazione aggiornate
    secure_config = SecureConfig()
    config = secure_config.get_config()
    
    print(f"Directory output: {config['output_directory']}")
    print(f"Server FTP: {config['ftp_host'] if config['ftp_host'] else '(non configurato)'}")
    print(f"Schedulazione: {config['schedule_type']}")
    print(f"Sistema Categorie CDR: Abilitato v2.0")  # ✅ NUOVO
    print(f"File categorie: output/cdr_analytics/cdr_categories.json")  # ✅ NUOVO
    print("="*60 + "\n")

def graceful_shutdown(scheduler_manager):
    """Shutdown graceful dell'applicazione"""
    try:
        scheduler_manager.shutdown()
        log_success("Applicazione fermata correttamente")
    except Exception as e:
        log_error(f"Errore durante shutdown: {e}")

def main():
    """Funzione principale con integrazione sistema categorie"""
    try:
        log_info("Inizializzazione FTP Scheduler con Sistema Categorie CDR 2.0")
        
        # Inizializza configurazione sicura
        secure_config = SecureConfig()
        
        # Mostra info configurazione
        config_info = secure_config.get_config()
        log_info(f"Directory config: {config_info['config_directory']}")
        log_info(f"Directory output: {config_info['output_directory']}")
        log_info(f"File categorie: {config_info['categories_config_file']}")

        # Carica configurazione da .env.local se più recente
        load_config_from_env_local(secure_config)
        
        # Crea app Flask
        app = create_app()
        
        # ✅ INIZIALIZZA COMPONENTI CON NUOVO SISTEMA CATEGORIE
        processor = FTPProcessor(secure_config.get_config())
        
        # ✅ INTEGRA IL NUOVO SISTEMA CATEGORIE CDR (sostituisce i vecchi sistemi)
        # log_info("Integrazione Sistema Categorie CDR 2.0...")
        # processor = integrate_enhanced_cdr_system(app, processor)
        log_info("Integrazione Sistema CDR con configurazione da .env...")
        processor = integrate_enhanced_cdr_system(app, processor, secure_config)

        # ✅ AGGIUNGI ROUTE PER GESTIONE CATEGORIE
        log_info("Registrazione route gestione categorie...")
        categories_info = add_categories_routes(app, processor.cdr_analytics, secure_config)
        log_success(f"Route categorie registrate: {categories_info['routes_count']} endpoint")
        
        # Inizializza scheduler
        scheduler_manager = SchedulerManager()
        scheduler_manager.set_config(secure_config.get_config())
        
        # Crea tutte le route standard
        app = create_routes(app, secure_config, processor, scheduler_manager)
              
        # Avvia scheduler
        try:
            scheduler_manager.restart_scheduler()
            log_success("Scheduler inizializzato")
        except Exception as e:
            log_error(f"Errore inizializzazione scheduler: {e}")
        
        # Configurazione server  
        app_host = secure_config.get_config().get('APP_HOST', '127.0.0.1')
        requested_port = secure_config.get_config().get('APP_PORT', 5001)
        app_debug = secure_config.get_config().get('FLASK_DEBUG', False)
        
        # In produzione, disabilita debug mode
        if secure_config.get_config().get('FLASK_ENV') == 'production':
            app_debug = False
        
        # Trova porta libera se quella richiesta è occupata
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((app_host, requested_port))
            app_port = requested_port
        except OSError:
            log_warning(f"Porta {requested_port} occupata, cercando alternativa...")
            app_port = find_free_port(requested_port)
            if app_port != requested_port:
                log_info(f"Usando porta alternativa: {app_port}")
        
        # ✅ VERIFICA SISTEMA CATEGORIE ALL'AVVIO
        verify_categories_system(processor)
        
        # Stampa info di avvio
        print_startup_info(app_host, app_port)
        
        # Registra cleanup per shutdown graceful
        import atexit
        atexit.register(lambda: graceful_shutdown(scheduler_manager))
        
        # Avvia applicazione
        # if sys.platform.startswith('win'):
        #     app.run(debug=app_debug, host=app_host, port=app_port, threaded=True, use_reloader=False)
        # else:
        #     app.run(debug=app_debug, host=app_host, port=app_port, threaded=True)

        app.run(
            debug=app_debug,
            host=app_host,
            port=app_port,
            threaded=True,
            use_reloader=app_debug  # reloader solo se debug è attivo
        )

    except KeyboardInterrupt:
        log_info("Applicazione fermata dall'utente")
        if 'scheduler_manager' in locals():
            graceful_shutdown(scheduler_manager)
    except Exception as e:
        log_error(f"Errore avvio applicazione: {e}")
        if 'scheduler_manager' in locals():
            graceful_shutdown(scheduler_manager)
        sys.exit(1)

def verify_categories_system(processor):
    """Verifica che il sistema categorie sia configurato correttamente"""
    try:
        if hasattr(processor, 'cdr_analytics') and hasattr(processor.cdr_analytics, 'categories_manager'):
            categories_manager = processor.cdr_analytics.categories_manager
            
            # Verifica categorie caricate
            categories = categories_manager.get_all_categories()
            active_categories = categories_manager.get_active_categories()
            
            log_success(f"Sistema Categorie CDR verificato:")
            log_info(f"  - Categorie totali: {len(categories)}")
            log_info(f"  - Categorie attive: {len(active_categories)}")
            
            # Mostra categorie attive
            for name, category in active_categories.items():
                log_info(f"  - {category.display_name}: €{category.price_per_minute}/min ({len(category.patterns)} pattern)")
            
            # Verifica conflitti
            conflicts = categories_manager.validate_patterns_conflicts()
            if conflicts:
                log_warning(f"  - Conflitti pattern rilevati: {len(conflicts)}")
                for conflict in conflicts[:3]:  # Mostra solo i primi 3
                    log_warning(f"    {conflict['category1']} vs {conflict['category2']}: {', '.join(conflict['common_patterns'])}")
            else:
                log_success("  - Nessun conflitto pattern rilevato")
                
        else:
            log_error("Sistema categorie CDR non inizializzato correttamente")
            
    except Exception as e:
        log_error(f"Errore verifica sistema categorie: {e}")


if __name__ == '__main__':
    main()