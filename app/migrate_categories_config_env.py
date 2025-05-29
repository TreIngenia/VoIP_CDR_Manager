"""
Script di migrazione per configurazione da .env
"""

import os
from pathlib import Path
from datetime import datetime
import shutil

def migrate_to_env_config():
    """Migra configurazione utilizzando variabili .env"""
    
    print("🔄 Migrazione configurazione categorie con .env")
    print("=" * 50)
    
    # Leggi configurazione da .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        config_dir = Path(os.getenv('CONFIG_DIRECTORY', 'config'))
        categories_file = os.getenv('CATEGORIES_CONFIG_FILE', 'cdr_categories.json')
        
        print(f"📁 Directory config da .env: {config_dir}")
        print(f"📄 File categorie da .env: {categories_file}")
        
    except ImportError:
        print("⚠️ python-dotenv non disponibile, uso valori default")
        config_dir = Path('config')
        categories_file = 'cdr_categories.json'
    
    # Percorsi
    old_path = Path("output/cdr_analytics/cdr_categories.json")
    new_path = config_dir / categories_file
    
    # Crea directory config
    config_dir.mkdir(exist_ok=True)
    print(f"✅ Directory config: {config_dir.resolve()}")
    
    # Migrazione file se esiste
    if old_path.exists():
        print(f"📁 File esistente trovato: {old_path}")
        
        # Backup se necessario
        if new_path.exists():
            backup_path = config_dir / f"cdr_categories_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            shutil.copy2(new_path, backup_path)
            print(f"💾 Backup creato: {backup_path}")
        
        # Copia file
        shutil.copy2(old_path, new_path)
        print(f"✅ File migrato: {new_path}")
        
        # Rinomina vecchio file
        backup_old = old_path.parent / f"cdr_categories_migrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.move(old_path, backup_old)
        print(f"💾 Vecchio file archiviato: {backup_old}")
        
    else:
        print("ℹ️ Nessun file da migrare")
        
        if not new_path.exists():
            print("🆕 Creazione configurazione default...")
            # Importa dopo aver impostato le variabili d'ambiente
            from cdr_categories import CDRCategoriesManager
            manager = CDRCategoriesManager()
            print(f"✅ Configurazione default creata: {new_path}")
    
    # Verifica finale
    print(f"\n✅ Migrazione completata!")
    print(f"📍 File configurazione: {new_path.resolve()}")
    print(f"📏 Dimensione: {new_path.stat().st_size if new_path.exists() else 0} bytes")
    
    # Test configurazione
    try:
        from cdr_categories import CDRCategoriesManager
        manager = CDRCategoriesManager()
        categories_count = len(manager.get_all_categories())
        print(f"🧪 Test: {categories_count} categorie caricate correttamente")
    except Exception as e:
        print(f"⚠️ Errore test: {e}")

if __name__ == "__main__":
    migrate_to_env_config()