#!/usr/bin/env python3
"""
Script di configurazione rapida per CDR Analytics + VoIP
Automatizza il setup e permette di testare la configurazione
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def check_current_installation():
    """Verifica l'installazione corrente"""
    print("🔍 Verifica installazione corrente...")
    
    required_files = [
        'app.py',
        'config.py', 
        'ftp_processor.py',
        'cdr_analytics.py',
        'integration_cdr_analytics.py',
        'templates/index.html',
        'templates/config.html'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ File mancanti:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ Tutti i file richiesti sono presenti")
    return True

def backup_existing_files():
    """Crea backup dei file esistenti"""
    print("💾 Creazione backup file esistenti...")
    
    backup_dir = Path(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_dir.mkdir(exist_ok=True)
    
    files_to_backup = [
        'cdr_analytics.py',
        'integration_cdr_analytics.py',
        'templates/cdr_dashboard.html'
    ]
    
    backed_up = []
    for file_path in files_to_backup:
        source = Path(file_path)
        if source.exists():
            destination = backup_dir / source.name
            import shutil
            shutil.copy2(source, destination)
            backed_up.append(str(destination))
            print(f"   ✅ {file_path} -> {destination}")
    
    print(f"📁 Backup creato in: {backup_dir}")
    return str(backup_dir), backed_up

def check_voip_config():
    """Verifica la configurazione VoIP corrente"""
    print("💰 Verifica configurazione VoIP...")
    
    try:
        from config import SecureConfig
        config = SecureConfig()
        voip_config = config.get_config()
        
        required_voip_fields = [
            'voip_price_fixed_final',
            'voip_price_mobile_final', 
            'voip_currency',
            'voip_price_unit'
        ]
        
        missing_voip = []
        for field in required_voip_fields:
            if field not in voip_config or voip_config[field] is None:
                missing_voip.append(field)
        
        if missing_voip:
            print("⚠️ Configurazione VoIP incompleta:")
            for field in missing_voip:
                print(f"   - {field}")
            
            # Proponi configurazione di default
            return setup_default_voip_config(config)
        else:
            print("✅ Configurazione VoIP presente:")
            print(f"   Fisso: {voip_config.get('voip_price_fixed_final')} {voip_config.get('voip_currency')}")
            print(f"   Mobile: {voip_config.get('voip_price_mobile_final')} {voip_config.get('voip_currency')}")
            print(f"   Unità: {voip_config.get('voip_price_unit')}")
            return True
        
    except Exception as e:
        print(f"❌ Errore verifica configurazione VoIP: {e}")
        return False

def setup_default_voip_config(config):
    """Imposta configurazione VoIP di default"""
    print("\n🛠️ Configurazione VoIP di default")
    
    response = input("Vuoi impostare una configurazione VoIP di default? (s/N): ").lower()
    if response not in ['s', 'si', 'y', 'yes']:
        print("⚠️ Configurazione VoIP non impostata - CDR userà solo prezzi originali")
        return False
    
    # Valori di default suggeriti
    defaults = {
        'voip_price_fixed_final': 0.02,    # 2 centesimi al minuto
        'voip_price_mobile_final': 0.15,   # 15 centesimi al minuto
        'voip_currency': 'EUR',
        'voip_price_unit': 'per_minute'
    }
    
    print("💡 Configurazione suggerita:")
    for key, value in defaults.items():
        print(f"   {key}: {value}")
    
    use_defaults = input("\nUsare questa configurazione? (S/n): ").lower()
    if use_defaults in ['', 's', 'si', 'y', 'yes']:
        # Applica configurazioni di default
        config.update_config(defaults)
        
        try:
            from config import save_config_to_env
            save_config_to_env(config, os.urandom(32).hex())
            print("✅ Configurazione VoIP di default applicata")
            return True
        except Exception as e:
            print(f"❌ Errore salvataggio configurazione: {e}")
            return False
    else:
        print("⚠️ Configurazione VoIP non impostata")
        return False

def test_cdr_processing():
    """Testa l'elaborazione CDR con VoIP"""
    print("\n🧪 Test elaborazione CDR con VoIP...")
    
    # Cerca file CDR di test
    output_dir = Path("output")
    test_files = []
    
    if output_dir.exists():
        for json_file in output_dir.glob("*.json"):
            if any(keyword in json_file.name.upper() for keyword in ['CDR', 'RIV']):
                test_files.append(json_file)
    
    if not test_files:
        print("⚠️ Nessun file CDR trovato per il test")
        print("💡 Esegui il download FTP per ottenere file CDR da testare")
        return create_sample_cdr_for_test()
    
    test_file = test_files[0]
    print(f"📊 Test con file: {test_file}")
    
    try:
        from cdr_analytics import process_cdr_standalone
        from config import SecureConfig
        
        # Carica configurazione VoIP
        config = SecureConfig()
        voip_config = config.get_config()
        
        # Esegui test
        result = process_cdr_standalone(str(test_file), "test_output", voip_config=voip_config)
        
        if result['success']:
            print("✅ Test elaborazione CDR completato!")
            print(f"   Contratti: {result['total_contracts']}")
            print(f"   Report generati: {len(result['generated_files'])}")
            print(f"   VoIP abilitato: {result.get('voip_pricing_enabled', False)}")
            
            if result.get('voip_pricing_enabled'):
                print("💰 Prezzi VoIP applicati correttamente!")
            
            return True
        else:
            print(f"❌ Test fallito: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante test: {e}")
        return False

def create_sample_cdr_for_test():
    """Crea un file CDR di esempio per test"""
    print("📝 Creazione file CDR di esempio per test...")
    
    sample_cdr = {
        "metadata": {
            "source_file": "test_sample.cdr",
            "total_records": 5,
            "file_type": "CDR"
        },
        "records": [
            {
                "data_ora_chiamata": "2025-01-15 10:30:00",
                "numero_chiamante": "0612345678",
                "numero_chiamato": "0698765432",
                "durata_secondi": 120,
                "tipo_chiamata": "INTERRURBANE URBANE",
                "operatore": "TEST",
                "costo_euro": 0.05,
                "codice_contratto": "12345",
                "codice_servizio": "1",
                "cliente_finale_comune": "Roma",
                "prefisso_chiamato": "06"
            },
            {
                "data_ora_chiamata": "2025-01-15 11:15:00",
                "numero_chiamante": "0612345678",
                "numero_chiamato": "3401234567",
                "durata_secondi": 180,
                "tipo_chiamata": "CELLULARE",
                "operatore": "TEST",
                "costo_euro": 0.15,
                "codice_contratto": "12345",
                "codice_servizio": "2",
                "cliente_finale_comune": "Roma",
                "prefisso_chiamato": "340"
            },
            {
                "data_ora_chiamata": "2025-01-15 14:20:00",
                "numero_chiamante": "0612345678",
                "numero_chiamato": "800123456",
                "durata_secondi": 60,
                "tipo_chiamata": "NUMERO VERDE",
                "operatore": "TEST",
                "costo_euro": 0.00,
                "codice_contratto": "12345",
                "codice_servizio": "3",
                "cliente_finale_comune": "Roma",
                "prefisso_chiamato": "800"
            },
            {
                "data_ora_chiamata": "2025-01-15 16:45:00",
                "numero_chiamante": "0612345678",
                "numero_chiamato": "0039335555555",
                "durata_secondi": 300,
                "tipo_chiamata": "INTERNAZIONALE",
                "operatore": "TEST",
                "costo_euro": 0.75,
                "codice_contratto": "67890",
                "codice_servizio": "4",
                "cliente_finale_comune": "Milano",
                "prefisso_chiamato": "0039"
            },
            {
                "data_ora_chiamata": "2025-01-15 18:10:00", 
                "numero_chiamante": "0612345678",
                "numero_chiamato": "0287654321",
                "durata_secondi": 90,
                "tipo_chiamata": "INTERRURBANE URBANE",
                "operatore": "TEST",
                "costo_euro": 0.03,
                "codice_contratto": "67890",
                "codice_servizio": "1",
                "cliente_finale_comune": "Milano",
                "prefisso_chiamato": "02"
            }
        ]
    }
    
    # Crea directory output se non esiste
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Salva file di esempio
    sample_file = output_dir / "sample_cdr_test.json"
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_cdr, f, indent=2, ensure_ascii=False)
    
    print(f"✅ File CDR di esempio creato: {sample_file}")
    print("📊 Contenuto: 5 chiamate di test con diversi tipi")
    
    # Ora testa con il file creato
    return test_sample_file(sample_file)

def test_sample_file(sample_file):
    """Testa il file CDR di esempio"""
    try:
        from cdr_analytics import process_cdr_standalone
        from config import SecureConfig
        
        config = SecureConfig()
        voip_config = config.get_config()
        
        print(f"🧪 Test file di esempio: {sample_file}")
        result = process_cdr_standalone(str(sample_file), "test_output", voip_config=voip_config)
        
        if result['success']:
            print("✅ Test file di esempio completato!")
            print(f"   VoIP abilitato: {result.get('voip_pricing_enabled', False)}")
            print(f"   Tipi chiamata trovati: {', '.join(result.get('call_types_found', []))}")
            return True
        else:
            print(f"❌ Test fallito: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test file esempio: {e}")
        return False

def show_integration_status():
    """Mostra lo stato dell'integrazione"""  
    print("\n📊 STATO INTEGRAZIONE CDR + VOIP")
    print("=" * 40)
    
    # Verifica moduli
    modules_status = {}
    
    try:
        from cdr_analytics import CDRAnalytics, VoIPPricingConfig
        modules_status['cdr_analytics'] = "✅ Disponibile"
    except ImportError as e:
        modules_status['cdr_analytics'] = f"❌ Errore: {e}"
    
    try:
        from integration_cdr_analytics import setup_cdr_analytics
        modules_status['integration'] = "✅ Disponibile"
    except ImportError as e:
        modules_status['integration'] = f"❌ Errore: {e}"
    
    try:
        from config import SecureConfig
        config = SecureConfig()
        voip_config = config.get_config()
        
        if all(voip_config.get(field) for field in ['voip_price_fixed_final', 'voip_price_mobile_final']):
            modules_status['voip_config'] = "✅ Configurato"
        else:
            modules_status['voip_config'] = "⚠️ Incompleto"
    except Exception as e:
        modules_status['voip_config'] = f"❌ Errore: {e}"
    
    for module, status in modules_status.items():
        print(f"{module:15}: {status}")
    
    # Verifica directory
    directories = ['output', 'output/cdr_analytics', 'templates']
    print(f"\n📁 Directory:")
    for dir_path in directories:
        exists = "✅" if Path(dir_path).exists() else "❌"
        print(f"{dir_path:20}: {exists}")

def main():
    """Funzione principale"""
    print("🚀 Setup Rapido CDR Analytics + VoIP")
    print("=" * 50)
    
    # 1. Verifica installazione
    if not check_current_installation():
        print("\n❌ Installazione incompleta. Assicurati di avere tutti i file necessari.")
        return
    
    # 2. Backup
    try:
        backup_dir, backed_up = backup_existing_files()
        print(f"💾 Backup creato: {len(backed_up)} file")
    except Exception as e:
        print(f"⚠️ Impossibile creare backup: {e}")
    
    # 3. Verifica configurazione VoIP
    voip_ok = check_voip_config()
    
    # 4. Test elaborazione
    if voip_ok:
        test_ok = test_cdr_processing()
    else:
        test_ok = False
    
    # 5. Stato finale
    show_integration_status()
    
    print(f"\n🎉 SETUP COMPLETATO")
    print("=" * 25)
    if voip_ok and test_ok:
        print("✅ CDR Analytics + VoIP configurato e testato correttamente!")
        print("\n📋 Prossimi passi:")
        print("1. Avvia l'applicazione: python app.py")
        print("2. Vai su http://localhost:5001/cdr_dashboard")
        print("3. Esegui download FTP per processare file CDR reali")
    else:
        print("⚠️ Setup parzialmente completato")
        if not voip_ok:
            print("   - Configura i prezzi VoIP in /config")
        if not test_ok:
            print("   - Verifica il test elaborazione CDR")

if __name__ == "__main__":
    main()