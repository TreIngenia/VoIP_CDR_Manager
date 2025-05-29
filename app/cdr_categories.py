#!/usr/bin/env python3
"""
CDR Categories Manager - Gestione Macro Categorie per CDR Analytics
Modulo per gestire categorie di chiamate con prezzi specifici e pattern di riconoscimento
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class CDRCategory:
    """Classe per rappresentare una categoria CDR"""
    name: str
    display_name: str
    price_per_minute: float
    currency: str
    patterns: List[str]
    description: str = ""
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def matches_pattern(self, call_type: str) -> bool:
        """Verifica se un tipo di chiamata corrisponde ai pattern della categoria"""
        if not call_type or not self.patterns:
            return False
        
        call_type_upper = call_type.upper().strip()
        
        for pattern in self.patterns:
            if pattern.upper().strip() in call_type_upper:
                return True
        
        return False
    
    def calculate_cost(self, duration_seconds: int, unit: str = 'per_minute') -> Dict[str, Any]:
        """Calcola il costo per una chiamata"""
        if unit == 'per_second':
            cost = self.price_per_minute * (duration_seconds / 60.0)
            duration_billed = duration_seconds
            unit_label = 'secondi'
        else:  # per_minute (default)
            duration_minutes = duration_seconds / 60.0
            cost = self.price_per_minute * duration_minutes
            duration_billed = duration_minutes
            unit_label = 'minuti'
        
        return {
            'category_name': self.name,
            'category_display_name': self.display_name,
            'price_per_minute': self.price_per_minute,
            'duration_billed': round(duration_billed, 4),
            'unit_label': unit_label,
            'cost_calculated': round(cost, 4),
            'currency': self.currency
        }


class CDRCategoriesManager:
    """Manager per gestire le categorie CDR"""
    
    DEFAULT_CATEGORIES = {
        'FISSI': CDRCategory(
            name='FISSI',
            display_name='Chiamate Fisso',
            price_per_minute=0.02,
            currency='EUR',
            patterns=['INTERRURBANE URBANE', 'INTERURBANE URBANE', 'URBANE', 'FISSO', 'RETE FISSA', 'TELEFONIA FISSA', 'LOCALE', 'DISTRETTUALE'],
            description='Chiamate verso numeri fissi nazionali'
        ),
        'MOBILI': CDRCategory(
            name='MOBILI',
            display_name='Chiamate Mobile',
            price_per_minute=0.15,
            currency='EUR',
            patterns=['CELLULARE', 'MOBILE', 'RETE MOBILE', 'TELEFONIA MOBILE', 'GSM', 'UMTS', 'LTE', 'WIND', 'TIM', 'VODAFONE', 'ILIAD'],
            description='Chiamate verso numeri mobili'
        ),
        'FAX': CDRCategory(
            name='FAX',
            display_name='Servizi Fax',
            price_per_minute=0.02,
            currency='EUR',
            patterns=['FAX', 'TELEFAX', 'FACSIMILE'],
            description='Servizi di fax'
        ),
        'NUMERI_VERDI': CDRCategory(
            name='NUMERI_VERDI',
            display_name='Numeri Verdi',
            price_per_minute=0.00,
            currency='EUR',
            patterns=['NUMERO VERDE', 'VERDE', '800', 'GRATUITO', 'TOLL FREE'],
            description='Numeri verdi e gratuiti'
        ),
        'INTERNAZIONALI': CDRCategory(
            name='INTERNAZIONALI',
            display_name='Chiamate Internazionali',
            price_per_minute=0.25,
            currency='EUR',
            patterns=['INTERNAZIONALE', 'INTERNATIONAL', 'ESTERO', 'UE', 'EUROPA', 'MONDO', 'ROAMING', 'EXTRA UE'],
            description='Chiamate internazionali'
        )
    }
    
    # def __init__(self, config_file: str = 'cdr_categories.json'):
    #     self.config_file = Path(config_file)
    #     self.categories: Dict[str, CDRCategory] = {}
    #     self.load_categories()
    
    def __init__(self, config_file: str = None, secure_config: 'SecureConfig' = None):
        """
        Inizializza il manager con configurazione da .env
        
        Args:
            config_file: Percorso specifico del file (opzionale)
            secure_config: Istanza SecureConfig per leggere configurazione da .env
        """
        
        if config_file is not None:
            # Percorso specifico fornito
            self.config_file = Path(config_file)
        elif secure_config is not None:
            # Usa configurazione da .env tramite SecureConfig
            self.config_file = secure_config.get_config_file_path()
            secure_config.ensure_config_directory()
        else:
            # ✅ FALLBACK: Leggi direttamente da variabili d'ambiente
            import os
            config_dir = Path(os.getenv('CONFIG_DIRECTORY', 'config'))
            config_dir.mkdir(parents=True, exist_ok=True)
            categories_file = os.getenv('CATEGORIES_CONFIG_FILE', 'cdr_categories.json')
            self.config_file = config_dir / categories_file
        
        self.categories: Dict[str, CDRCategory] = {}
        logger.info(f"🔧 CDR Categories Manager - File config: {self.config_file}")
        self.load_categories()

    def load_categories(self):
        """Carica le categorie dal file di configurazione"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.categories = {}
                for cat_name, cat_data in data.items():
                    # Converti il dizionario in CDRCategory
                    if isinstance(cat_data, dict):
                        self.categories[cat_name] = CDRCategory(**cat_data)
                    else:
                        logger.warning(f"Categoria {cat_name} ha formato non valido")
                
                logger.info(f"Caricate {len(self.categories)} categorie CDR da {self.config_file}")
            else:
                # Prima esecuzione: usa categorie di default
                logger.info("File categorie non trovato, creo categorie di default")
                self.categories = self.DEFAULT_CATEGORIES.copy()
                self.save_categories()
                
        except Exception as e:
            logger.error(f"Errore caricamento categorie: {e}")
            logger.info("Uso categorie di default")
            self.categories = self.DEFAULT_CATEGORIES.copy()
    
    def save_categories(self):
        """Salva le categorie nel file di configurazione"""
        try:
            # Crea backup se esiste già
            if self.config_file.exists():
                backup_file = Path(str(self.config_file) + f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                import shutil
                shutil.copy2(self.config_file, backup_file)
                logger.info(f"Backup categorie creato: {backup_file}")
            
            # Converte le categorie in dizionari per il JSON
            data = {}
            for cat_name, category in self.categories.items():
                data[cat_name] = asdict(category)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Categorie salvate in {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Errore salvataggio categorie: {e}")
            return False
    
    def add_category(self, name: str, display_name: str, price_per_minute: float, 
                    patterns: List[str], currency: str = 'EUR', description: str = '') -> bool:
        """Aggiunge una nuova categoria"""
        try:
            # Validazioni
            if not name or not name.strip():
                raise ValueError("Nome categoria obbligatorio")
            
            name = name.upper().strip()
            
            if name in self.categories:
                raise ValueError(f"Categoria {name} già esistente")
            
            if price_per_minute < 0:
                raise ValueError("Prezzo deve essere positivo")
            
            if not patterns or not any(p.strip() for p in patterns):
                raise ValueError("Almeno un pattern è obbligatorio")
            
            # Pulisci i pattern
            clean_patterns = [p.strip() for p in patterns if p.strip()]
            
            # Crea categoria
            category = CDRCategory(
                name=name,
                display_name=display_name.strip(),
                price_per_minute=float(price_per_minute),
                currency=currency,
                patterns=clean_patterns,
                description=description.strip()
            )
            
            self.categories[name] = category
            
            if self.save_categories():
                logger.info(f"Categoria {name} aggiunta con successo")
                return True
            else:
                # Rollback in caso di errore salvataggio
                del self.categories[name]
                return False
                
        except Exception as e:
            logger.error(f"Errore aggiunta categoria {name}: {e}")
            return False
    
    def update_category(self, name: str, **kwargs) -> bool:
        """Aggiorna una categoria esistente"""
        try:
            name = name.upper().strip()
            
            if name not in self.categories:
                raise ValueError(f"Categoria {name} non trovata")
            
            category = self.categories[name]
            
            # Aggiorna i campi forniti
            if 'display_name' in kwargs:
                category.display_name = kwargs['display_name'].strip()
            
            if 'price_per_minute' in kwargs:
                price = float(kwargs['price_per_minute'])
                if price < 0:
                    raise ValueError("Prezzo deve essere positivo")
                category.price_per_minute = price
            
            if 'patterns' in kwargs:
                patterns = kwargs['patterns']
                if not patterns or not any(p.strip() for p in patterns):
                    raise ValueError("Almeno un pattern è obbligatorio")
                category.patterns = [p.strip() for p in patterns if p.strip()]
            
            if 'currency' in kwargs:
                category.currency = kwargs['currency']
            
            if 'description' in kwargs:
                category.description = kwargs['description'].strip()
            
            if 'is_active' in kwargs:
                category.is_active = bool(kwargs['is_active'])
            
            # Aggiorna timestamp
            category.updated_at = datetime.now().isoformat()
            
            if self.save_categories():
                logger.info(f"Categoria {name} aggiornata con successo")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Errore aggiornamento categoria {name}: {e}")
            return False
    
    def delete_category(self, name: str) -> bool:
        """Elimina una categoria"""
        try:
            name = name.upper().strip()
            
            if name not in self.categories:
                raise ValueError(f"Categoria {name} non trovata")
            
            # Non permettere eliminazione delle categorie di default essenziali
            essential_categories = ['FISSI', 'MOBILI']
            if name in essential_categories:
                raise ValueError(f"Non è possibile eliminare la categoria essenziale {name}")
            
            del self.categories[name]
            
            if self.save_categories():
                logger.info(f"Categoria {name} eliminata con successo")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Errore eliminazione categoria {name}: {e}")
            return False
    
    def get_category(self, name: str) -> Optional[CDRCategory]:
        """Ottiene una categoria per nome"""
        return self.categories.get(name.upper().strip())
    
    def get_all_categories(self) -> Dict[str, CDRCategory]:
        """Ottiene tutte le categorie"""
        return self.categories.copy()
    
    def get_active_categories(self) -> Dict[str, CDRCategory]:
        """Ottiene solo le categorie attive"""
        return {name: cat for name, cat in self.categories.items() if cat.is_active}
    
    def classify_call_type(self, call_type: str) -> Optional[CDRCategory]:
        """Classifica un tipo di chiamata e restituisce la categoria corrispondente"""
        if not call_type:
            return None
        
        # Cerca nelle categorie attive
        for category in self.categories.values():
            if category.is_active and category.matches_pattern(call_type):
                return category
        
        return None
    
    def calculate_call_cost(self, call_type: str, duration_seconds: int, unit: str = 'per_minute') -> Dict[str, Any]:
        """Calcola il costo di una chiamata basato sulla categoria"""
        category = self.classify_call_type(call_type)
        
        if category:
            result = category.calculate_cost(duration_seconds, unit)
            result['matched'] = True
            result['original_call_type'] = call_type
        else:
            # Fallback: categoria sconosciuta
            result = {
                'category_name': 'ALTRO',
                'category_display_name': 'Altro/Sconosciuto',
                'price_per_minute': 0.0,
                'duration_billed': duration_seconds / 60.0 if unit == 'per_minute' else duration_seconds,
                'unit_label': 'minuti' if unit == 'per_minute' else 'secondi',
                'cost_calculated': 0.0,
                'currency': 'EUR',
                'matched': False,
                'original_call_type': call_type
            }
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Ottiene statistiche sulle categorie"""
        active_count = sum(1 for cat in self.categories.values() if cat.is_active)
        total_patterns = sum(len(cat.patterns) for cat in self.categories.values())
        
        price_range = {
            'min': min((cat.price_per_minute for cat in self.categories.values()), default=0),
            'max': max((cat.price_per_minute for cat in self.categories.values()), default=0),
            'avg': sum(cat.price_per_minute for cat in self.categories.values()) / len(self.categories) if self.categories else 0
        }
        
        return {
            'total_categories': len(self.categories),
            'active_categories': active_count,
            'inactive_categories': len(self.categories) - active_count,
            'total_patterns': total_patterns,
            'price_range': price_range,
            'currencies': list(set(cat.currency for cat in self.categories.values())),
            'last_modified': max((cat.updated_at for cat in self.categories.values()), default=None)
        }
    
    def export_categories(self, format: str = 'json') -> str:
        """Esporta le categorie in vari formati"""
        data = {name: asdict(cat) for name, cat in self.categories.items()}
        
        if format.lower() == 'json':
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format.lower() == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(['Name', 'Display Name', 'Price per Minute', 'Currency', 
                           'Patterns', 'Description', 'Active', 'Created', 'Updated'])
            
            # Data
            for category in self.categories.values():
                writer.writerow([
                    category.name,
                    category.display_name,
                    category.price_per_minute,
                    category.currency,
                    '; '.join(category.patterns),
                    category.description,
                    category.is_active,
                    category.created_at,
                    category.updated_at
                ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Formato {format} non supportato")
    
    def import_categories(self, data: str, format: str = 'json', merge: bool = True) -> bool:
        """Importa categorie da dati esterni"""
        try:
            if format.lower() == 'json':
                imported_data = json.loads(data)
                
                if not merge:
                    self.categories.clear()
                
                for cat_name, cat_data in imported_data.items():
                    if isinstance(cat_data, dict):
                        category = CDRCategory(**cat_data)
                        self.categories[cat_name.upper()] = category
                
                return self.save_categories()
            else:
                raise ValueError(f"Formato {format} non supportato per l'import")
                
        except Exception as e:
            logger.error(f"Errore import categorie: {e}")
            return False
    
    def validate_patterns_conflicts(self) -> List[Dict[str, Any]]:
        """Verifica conflitti tra pattern delle categorie"""
        conflicts = []
        
        categories_list = list(self.categories.values())
        
        for i, cat1 in enumerate(categories_list):
            for j, cat2 in enumerate(categories_list[i+1:], i+1):
                if not cat1.is_active or not cat2.is_active:
                    continue
                
                # Cerca pattern in comune
                common_patterns = set(p.upper() for p in cat1.patterns) & set(p.upper() for p in cat2.patterns)
                
                if common_patterns:
                    conflicts.append({
                        'category1': cat1.name,
                        'category2': cat2.name,
                        'common_patterns': list(common_patterns),
                        'severity': 'high' if len(common_patterns) > 1 else 'medium'
                    })
        
        return conflicts
    
    def reset_to_defaults(self) -> bool:
        """Ripristina le categorie di default"""
        try:
            self.categories = self.DEFAULT_CATEGORIES.copy()
            if self.save_categories():
                logger.info("Categorie ripristinate ai valori di default")
                return True
            return False
        except Exception as e:
            logger.error(f"Errore ripristino categorie default: {e}")
            return False


# Funzioni helper per l'integrazione
def get_categories_manager(config_file: str = 'cdr_categories.json') -> CDRCategoriesManager:
    """Factory function per ottenere il manager delle categorie"""
    return CDRCategoriesManager(config_file)

def test_category_classification():
    """Funzione di test per la classificazione"""
    manager = CDRCategoriesManager()
    
    test_calls = [
        'INTERRURBANE URBANE',
        'CELLULARE TIM',
        'FAX NAZIONALE',
        'NUMERO VERDE 800',
        'INTERNAZIONALE FRANCIA',
        'CHIAMATA SCONOSCIUTA'
    ]
    
    print("Test Classificazione Categorie CDR:")
    print("=" * 50)
    
    for call_type in test_calls:
        result = manager.calculate_call_cost(call_type, 300)  # 5 minuti
        print(f"Tipo: {call_type}")
        print(f"  Categoria: {result['category_display_name']}")
        print(f"  Prezzo: {result['price_per_minute']} {result['currency']}/min")
        print(f"  Costo 5 min: {result['cost_calculated']} {result['currency']}")
        print(f"  Match: {'✅' if result['matched'] else '❌'}")
        print()

if __name__ == "__main__":
    test_category_classification()
