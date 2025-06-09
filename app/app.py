#!/usr/bin/env python3
"""
FTP Scheduler App - Versione Completa con Sistema Categorie CDR Unificato
Aggiornato per utilizzare cdr_categories_enhanced.py invece dei file separati
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

# Import moduli migliorati
from flask import Flask, send_from_directory, jsonify
from logger_config import get_logger, log_success, log_error, log_warning, log_info
from config_validator import ConfigValidator
from performance_monitor import get_performance_monitor
from config import save_config_to_env, load_config_from_env_local
from ftp_processor import FTPProcessor
from scheduler import SchedulerManager

#ROUTE Default
from routes.default_routes import create_routes

#ROUTE Categorie
from cdr_categories_enhanced import integrate_enhanced_cdr_system
from routes.cdr_categories_routes import add_cdr_categories_routes

#ROUTE contratti
from routes.contratti_routes import contratti_routes, api_contract_routes

#ROUTE ODOO
from routes.odoo_routes import add_odoo_routes

def create_app():
    """Factory function per creare l'app Flask"""
    app = Flask(__name__, 
                template_folder=os.getenv("TEMPLATE_FOLDER", "templates"),
                static_folder=os.getenv("STATIC_FOLDER", "static"), 
                static_url_path=os.getenv("STATIC_URL_PATH", "/static"))
    
    # Configurazione Flask sicura
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(32)),
        SESSION_COOKIE_SECURE=True if os.getenv('HTTPS', 'false').lower() == 'true' else False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
    )
    
    # Route performance monitoring
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
    print("AVVIO FTP SCHEDULER APP - VERSIONE UNIFICATA CDR 2.0")
    print("="*60)
    print(f"Dashboard: http://{app_host}:{app_port}")
    print(f"Configurazione: http://{app_host}:{app_port}/config")
    print(f"Gestione Categorie CDR: http://{app_host}:{app_port}/cdr_categories")
    print(f"Dashboard CDR: http://{app_host}:{app_port}/cdr_dashboard")
    print(f"Log: http://{app_host}:{app_port}/logs")
    print(f"Stato: http://{app_host}:{app_port}/status")
    print("="*60)
    
    # Informazioni configurazione aggiornate
    secure_config = SecureConfig()
    config = secure_config.get_config()
    
    print(f"Directory output: {config['output_directory']}")
    print(f"Server FTP: {config['ftp_host'] if config['ftp_host'] else '(non configurato)'}")
    print(f"Schedulazione: {config['schedule_type']}")
    print(f"Sistema Categorie CDR: Unificato v2.0")
    print(f"File categorie: {config['config_directory']}/{config['categories_config_file']}")
    print("="*60 + "\n")

def graceful_shutdown(scheduler_manager):
    """Shutdown graceful dell'applicazione"""
    try:
        scheduler_manager.shutdown()
        log_success("Applicazione fermata correttamente")
    except Exception as e:
        log_error(f"Errore durante shutdown: {e}")

def main():
    """Funzione principale con sistema categorie unificato"""
    try:
        log_info("Inizializzazione FTP Scheduler con Sistema Categorie CDR Unificato 2.0")
        
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
        
        # ✅ INIZIALIZZA COMPONENTI CON SISTEMA UNIFICATO
        processor = FTPProcessor(secure_config.get_config())
        
        # ✅ INTEGRA IL SISTEMA CATEGORIE UNIFICATO (sostituisce i vecchi sistemi)
        log_info("Integrazione Sistema CDR Unificato con configurazione da .env...")
        processor = integrate_enhanced_cdr_system(app, processor, secure_config)

        # GESTIONE CONTRATTI
        log_info("Registrazione route gestione contratti...")
        gestione_contratti = contratti_routes(app, secure_config)
        log_success(f"Route categorie registrate: {gestione_contratti['routes_count']} endpoint")

        # log_info("Registrazione route gestione contratti...")
        # contratti = add_cdr_contracts_datatable_routes(app, secure_config)
        # log_success(f"Route categorie registrate: {contratti['routes_count']} endpoint")
    
        # GESTIONE ODOO
        log_info("Registrazione route gestione ODOO...")
        gestione_odoo = add_odoo_routes(app, secure_config)
        log_success(f"Route ODOO registrate: {gestione_odoo['routes_count']} endpoint")

        # ✅ AGGIUNGI ROUTE PER GESTIONE CATEGORIE (aggiornate)
        log_info("Registrazione route gestione categorie unificato...")
        categories_info = add_cdr_categories_routes(app, processor.cdr_analytics, secure_config)
        log_success(f"Route categorie registrate: {categories_info['routes_count']} endpoint")
        
        # Inizializza scheduler
        scheduler_manager = SchedulerManager()
        scheduler_manager.set_config(secure_config.get_config())
        
        # Crea tutte le route standard
        app = create_routes(app, secure_config, processor, scheduler_manager)
        
        # ✅ MANTIENI INTEGRAZIONE CONTRATTI (se necessario)
        try:
            contracts_info = api_contract_routes(app, secure_config, processor)
            log_success(f"Sistema contratti integrato: {contracts_info['routes_count']} endpoint")
        except ImportError:
            log_warning("Sistema contratti non disponibile (modulo non trovato)")

        # try:
        #     from cdr_contract_extractor import integrate_contract_extraction
        #     contracts_info = integrate_contract_extraction(app, secure_config, processor)
        #     log_success(f"Sistema contratti integrato: {contracts_info['routes_count']} endpoint")
        # except ImportError:
        #     log_warning("Sistema contratti non disponibile (modulo non trovato)")    

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
        
        # ✅ VERIFICA SISTEMA CATEGORIE UNIFICATO ALL'AVVIO
        verify_unified_categories_system(processor)
        
        # ✅ REGISTRA BREADCRUMB GLOBALS (se disponibile)
        try:
            from routes.menu_routes import register_breadcrumb_globals
            register_breadcrumb_globals(app)
            log_success("Funzioni breadcrumb registrate")
        except ImportError:
            log_warning("Sistema breadcrumb non disponibile")
        
        # Stampa info di avvio
        print_startup_info(app_host, app_port)
        
        # Registra cleanup per shutdown graceful
        import atexit
        atexit.register(lambda: graceful_shutdown(scheduler_manager))
        
        # Avvia applicazione
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

def verify_unified_categories_system(processor):
    """Verifica che il sistema categorie unificato sia configurato correttamente"""
    try:
        if hasattr(processor, 'cdr_analytics') and hasattr(processor.cdr_analytics, 'categories_manager'):
            categories_manager = processor.cdr_analytics.categories_manager
            
            # Verifica categorie caricate
            categories = categories_manager.get_all_categories()
            active_categories = categories_manager.get_active_categories()
            
            log_success(f"Sistema Categorie CDR Unificato verificato:")
            log_info(f"  - Categorie totali: {len(categories)}")
            log_info(f"  - Categorie attive: {len(active_categories)}")
            log_info(f"  - Markup globale: {categories_manager.global_markup_percent}%")
            
            # Mostra categorie attive con pricing
            for name, category in active_categories.items():
                pricing_info = category.get_pricing_info(categories_manager.global_markup_percent)
                markup_source = "personalizzato" if category.custom_markup_percent is not None else "globale"
                log_info(f"  - {category.display_name}: €{category.price_per_minute}/min base → €{pricing_info['price_with_markup']}/min finale (markup {markup_source}: {pricing_info['markup_percent']}%)")
            
            # Verifica conflitti
            conflicts = categories_manager.validate_patterns_conflicts()
            if conflicts:
                log_warning(f"  - Conflitti pattern rilevati: {len(conflicts)}")
                for conflict in conflicts[:3]:  # Mostra solo i primi 3
                    log_warning(f"    {conflict['category1']} vs {conflict['category2']}: {', '.join(conflict['common_patterns'])}")
            else:
                log_success("  - Nessun conflitto pattern rilevato")
            
            # Verifica statistiche markup
            stats = categories_manager.get_statistics()
            markup_stats = stats.get('markup_statistics', {})
            log_info(f"  - Categorie con markup globale: {markup_stats.get('categories_using_global_markup', 0)}")
            log_info(f"  - Categorie con markup personalizzato: {markup_stats.get('categories_using_custom_markup', 0)}")
                
        else:
            log_error("Sistema categorie CDR unificato non inizializzato correttamente")
            
    except Exception as e:
        log_error(f"Errore verifica sistema categorie unificato: {e}")


if __name__ == '__main__':
    main()