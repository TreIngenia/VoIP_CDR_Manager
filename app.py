#!/usr/bin/env python3
"""
FTP Scheduler App - Versione Completa e Modulare
Combinazione di app.py e app_new.py con tutte le funzionalità
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
from config import SecureConfig, save_config_to_env, load_config_from_env_local, log_success, log_error, log_warning, log_info
from ftp_processor import FTPProcessor
from scheduler import SchedulerManager
from integration_cdr_analytics import setup_cdr_analytics
from routes import create_routes
from cdr_integration import integrate_enhanced_cdr_system
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
    
    # Se non trova nessuna porta libera, usa la porta originale
    return start_port

def print_startup_info(app_host, app_port):
    """Stampa informazioni di avvio senza emoji per compatibilità"""
    print("\n" + "="*50)
    print("AVVIO FTP SCHEDULER APP - VERSIONE COMPLETA")
    print("="*50)
    print(f"Dashboard: http://{app_host}:{app_port}")
    print(f"Configurazione: http://{app_host}:{app_port}/config")
    print(f"Log: http://{app_host}:{app_port}/logs")
    print(f"Stato: http://{app_host}:{app_port}/status")
    print(f"Variabili ENV: http://{app_host}:{app_port}/env_status")
    print("="*50)
    
    # Informazioni configurazione
    secure_config = SecureConfig()
    config = secure_config.get_config()
    
    print(f"Directory output: {config['output_directory']}")
    print(f"Server FTP: {config['ftp_host'] if config['ftp_host'] else '(non configurato)'}")
    print(f"Schedulazione: {config['schedule_type']}")
    print(f"Prezzi VoIP: Fisso={config['voip_price_fixed']} {config['voip_currency']}/min, Mobile={config['voip_price_mobile']} {config['voip_currency']}/min")
    print("="*50 + "\n")

def graceful_shutdown(scheduler_manager):
    """Shutdown graceful dell'applicazione"""
    try:
        scheduler_manager.shutdown()
    except Exception as e:
        log_error(f"Errore durante shutdown: {e}")

def main():
    """Funzione principale"""
    try:
        # Inizializza configurazione sicura
        secure_config = SecureConfig()
        
        # Carica configurazione da .env.local se più recente
        load_config_from_env_local(secure_config)
        
        # Crea app Flask
        app = create_app()
        
        # Inizializza componenti
        processor = FTPProcessor(secure_config.get_config())
        processor = integrate_enhanced_cdr_system(app, processor)
        add_categories_routes(app, processor.cdr_analytics)
        setup_cdr_analytics(app, processor)
        scheduler_manager = SchedulerManager()
        scheduler_manager.set_config(secure_config.get_config())
        
        # Crea tutte le route
        app = create_routes(app, secure_config, processor, scheduler_manager)
        
        # Avvia scheduler
        try:
            scheduler_manager.restart_scheduler()
            log_success("Scheduler inizializzato correttamente")
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
            log_warning(f"Porta {requested_port} occupata, cercando porta alternativa...")
            app_port = find_free_port(requested_port)
            if app_port != requested_port:
                log_info(f"Usando porta alternativa: {app_port}")
        
        # Stampa info di avvio
        print_startup_info(app_host, app_port)
        
        # Aggiorna info di startup con porta effettiva
        if app_port != requested_port:
            print(f"\n[INFO] Applicazione disponibile su: http://{app_host}:{app_port}")
        
        # Registra cleanup per shutdown graceful
        import atexit
        atexit.register(lambda: graceful_shutdown(scheduler_manager))
        
        # Avvia applicazione
        if sys.platform.startswith('win'):
            # Su Windows, usa threaded=True per evitare problemi con scheduler
            app.run(debug=app_debug, host=app_host, port=app_port, threaded=True, use_reloader=False)
        else:
            # Su Linux/Mac, configurazione standard
            app.run(debug=app_debug, host=app_host, port=app_port, threaded=True)
            
    except KeyboardInterrupt:
        log_info("Applicazione fermata dall'utente")
        if 'scheduler_manager' in locals():
            graceful_shutdown(scheduler_manager)
    except Exception as e:
        log_error(f"Errore avvio applicazione: {e}")
        if 'scheduler_manager' in locals():
            graceful_shutdown(scheduler_manager)
        sys.exit(1)

if __name__ == '__main__':
    main()