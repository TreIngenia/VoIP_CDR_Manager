#!/usr/bin/env python3
"""
CDR Categories Enhanced - Sistema unificato per gestione categorie CDR e analytics
Unisce la gestione delle macro categorie con il sistema di elaborazione CDR avanzato
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class CDRCategory:
    """Classe per rappresentare una categoria CDR con markup personalizzabile"""
    name: str
    display_name: str
    price_per_minute: float
    currency: str
    patterns: List[str]
    description: str = ""
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    custom_markup_percent: Optional[float] = None
    price_with_markup: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        
        if self.price_with_markup is None:
            self._calculate_price_with_markup()
    
    def _calculate_price_with_markup(self, global_markup_percent: float = 0.0):
        """Calcola il prezzo finale applicando il markup"""
        try:
            markup_to_apply = self.custom_markup_percent if self.custom_markup_percent is not None else global_markup_percent
            markup_multiplier = 1 + (markup_to_apply / 100)
            self.price_with_markup = round(self.price_per_minute * markup_multiplier, 4)
            logger.debug(f"Categoria {self.name}: prezzo base {self.price_per_minute} + {markup_to_apply}% = {self.price_with_markup}")
        except Exception as e:
            logger.error(f"Errore calcolo markup per categoria {self.name}: {e}")
            self.price_with_markup = self.price_per_minute
    
    def update_markup(self, custom_markup_percent: Optional[float] = None, global_markup_percent: float = 0.0):
        """Aggiorna il markup per questa categoria"""
        self.custom_markup_percent = custom_markup_percent
        self._calculate_price_with_markup(global_markup_percent)
        self.updated_at = datetime.now().isoformat()
    
    def get_effective_markup_percent(self, global_markup_percent: float = 0.0) -> float:
        """Restituisce il markup effettivo utilizzato"""
        return self.custom_markup_percent if self.custom_markup_percent is not None else global_markup_percent
    
    def get_pricing_info(self, global_markup_percent: float = 0.0) -> Dict[str, Any]:
        """Restituisce informazioni complete sui prezzi"""
        effective_markup = self.get_effective_markup_percent(global_markup_percent)
        
        return {
            'price_base': self.price_per_minute,
            'markup_percent': effective_markup,
            'markup_source': 'custom' if self.custom_markup_percent is not None else 'global',
            'price_with_markup': self.price_with_markup,
            'markup_amount': round(self.price_with_markup - self.price_per_minute, 4),
            'currency': self.currency
        }
    
    def matches_pattern(self, call_type: str) -> bool:
        """Verifica se un tipo di chiamata corrisponde ai pattern della categoria"""
        if not call_type or not self.patterns:
            return False
        
        call_type_upper = call_type.upper().strip()
        
        for pattern in self.patterns:
            if pattern.upper().strip() in call_type_upper:
                return True
        
        return False
    
    def calculate_cost(self, duration_seconds: int, unit: str = 'per_minute', use_markup: bool = True) -> Dict[str, Any]:
        """Calcola il costo per una chiamata con opzione markup"""
        price_to_use = self.price_with_markup if use_markup and self.price_with_markup else self.price_per_minute
        
        if unit == 'per_second':
            cost = price_to_use * (duration_seconds / 60.0)
            duration_billed = duration_seconds
            unit_label = 'secondi'
        else:
            duration_minutes = duration_seconds / 60.0
            cost = price_to_use * duration_minutes
            duration_billed = duration_minutes
            unit_label = 'minuti'
        
        return {
            'category_name': self.name,
            'category_display_name': self.display_name,
            'price_per_minute': self.price_per_minute,
            'price_per_minute_base': self.price_per_minute,
            'price_per_minute_with_markup': self.price_with_markup,
            'price_per_minute_used': price_to_use,
            'markup_applied': use_markup,
            'duration_billed': round(duration_billed, 4),
            'unit_label': unit_label,
            'cost_calculated': round(cost, 4),
            'currency': self.currency
        }


class CDRCategoriesManager:
    """Manager per gestire le categorie CDR con supporto markup personalizzabili"""
    
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
    
    def __init__(self, config_file: str = None, secure_config: 'SecureConfig' = None):
        """Inizializza il manager con configurazione da .env"""
        
        if config_file is not None:
            self.config_file = Path(config_file)
            self.global_markup_percent = 0.0
        elif secure_config is not None:
            self.config_file = secure_config.get_config_file_path()
            secure_config.ensure_config_directory()
            config = secure_config.get_config()
            self.global_markup_percent = float(config.get('voip_markup_percent', 0.0))
        else:
            import os
            config_dir = Path(os.getenv('CONFIG_DIRECTORY', 'config'))
            config_dir.mkdir(parents=True, exist_ok=True)
            categories_file = os.getenv('CATEGORIES_CONFIG_FILE', 'cdr_categories.json')
            self.config_file = config_dir / categories_file
            self.global_markup_percent = float(os.getenv('VOIP_MARKUP_PERCENT', 0.0))
        
        self.categories: Dict[str, CDRCategory] = {}
        logger.info(f"🔧 CDR Categories Manager - File config: {self.config_file}")
        logger.info(f"💰 Markup globale da config: {self.global_markup_percent}%")
        self.load_categories()

    def load_categories(self):
        """Carica le categorie dal file di configurazione"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.categories = {}
                for cat_name, cat_data in data.items():
                    if isinstance(cat_data, dict):
                        if 'custom_markup_percent' not in cat_data:
                            cat_data['custom_markup_percent'] = None
                        if 'price_with_markup' not in cat_data:
                            cat_data['price_with_markup'] = None
                        
                        category = CDRCategory(**cat_data)
                        category._calculate_price_with_markup(self.global_markup_percent)
                        self.categories[cat_name] = category
                    else:
                        logger.warning(f"Categoria {cat_name} ha formato non valido")
                
                logger.info(f"Caricate {len(self.categories)} categorie CDR da {self.config_file}")
            else:
                logger.info("File categorie non trovato, creo categorie di default")
                self.categories = self.DEFAULT_CATEGORIES.copy()
                for category in self.categories.values():
                    category._calculate_price_with_markup(self.global_markup_percent)
                self.save_categories()
                
        except Exception as e:
            logger.error(f"Errore caricamento categorie: {e}")
            logger.info("Uso categorie di default")
            self.categories = self.DEFAULT_CATEGORIES.copy()
            for category in self.categories.values():
                category._calculate_price_with_markup(self.global_markup_percent)
    
    def save_categories(self):
        """Salva le categorie nel file di configurazione"""
        try:
            if self.config_file.exists():
                backup_file = Path(str(self.config_file) + f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                import shutil
                shutil.copy2(self.config_file, backup_file)
                logger.info(f"Backup categorie creato: {backup_file}")
            
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

    # [INCLUDI TUTTI GLI ALTRI METODI DEL CDRCategoriesManager...]
    def add_category(self, name: str, display_name: str, price_per_minute: float, 
                    patterns: List[str], currency: str = 'EUR', description: str = '',
                    custom_markup_percent: Optional[float] = None) -> bool:
        """Aggiunge una nuova categoria"""
        try:
            if not name or not name.strip():
                raise ValueError("Nome categoria obbligatorio")
            
            name = name.upper().strip()
            
            if name in self.categories:
                raise ValueError(f"Categoria {name} già esistente")
            
            if price_per_minute < 0:
                raise ValueError("Prezzo deve essere positivo")
            
            if not patterns or not any(p.strip() for p in patterns):
                raise ValueError("Almeno un pattern è obbligatorio")
            
            if custom_markup_percent is not None:
                if custom_markup_percent < -100:
                    raise ValueError("Markup non può essere inferiore a -100%")
                if custom_markup_percent > 1000:
                    raise ValueError("Markup troppo alto (massimo 1000%)")
            
            clean_patterns = [p.strip() for p in patterns if p.strip()]
            
            category = CDRCategory(
                name=name,
                display_name=display_name.strip(),
                price_per_minute=float(price_per_minute),
                currency=currency,
                patterns=clean_patterns,
                description=description.strip(),
                custom_markup_percent=custom_markup_percent
            )
            
            category._calculate_price_with_markup(self.global_markup_percent)
            
            self.categories[name] = category
            
            if self.save_categories():
                logger.info(f"Categoria {name} aggiunta con successo")
                return True
            else:
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
            price_changed = False
            markup_changed = False
            
            if 'display_name' in kwargs:
                category.display_name = kwargs['display_name'].strip()
            
            if 'price_per_minute' in kwargs:
                price = float(kwargs['price_per_minute'])
                if price < 0:
                    raise ValueError("Prezzo deve essere positivo")
                category.price_per_minute = price
                price_changed = True
            
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
            
            if 'custom_markup_percent' in kwargs:
                new_markup = kwargs['custom_markup_percent']
                if new_markup is not None:
                    new_markup = float(new_markup)
                    if new_markup < -100:
                        raise ValueError("Markup non può essere inferiore a -100%")
                    if new_markup > 1000:
                        raise ValueError("Markup troppo alto (massimo 1000%)")
                
                if category.custom_markup_percent != new_markup:
                    category.custom_markup_percent = new_markup
                    markup_changed = True
            
            if price_changed or markup_changed:
                category._calculate_price_with_markup(self.global_markup_percent)
            
            category.updated_at = datetime.now().isoformat()
            
            if self.save_categories():
                logger.info(f"Categoria {name} aggiornata con successo")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Errore aggiornamento categoria {name}: {e}")
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
    
    def get_all_categories_with_pricing(self) -> Dict[str, Dict[str, Any]]:
        """Ottiene tutte le categorie con informazioni pricing complete"""
        result = {}
        for name, category in self.categories.items():
            category_data = asdict(category)
            category_data['pricing_info'] = category.get_pricing_info(self.global_markup_percent)
            result[name] = category_data
        
        return result
    
    def classify_call_type(self, call_type: str) -> Optional[CDRCategory]:
        """Classifica un tipo di chiamata e restituisce la categoria corrispondente"""
        if not call_type:
            return None
        
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
            result['markup_percent_applied'] = category.get_effective_markup_percent(self.global_markup_percent)
            result['markup_source'] = 'custom' if category.custom_markup_percent is not None else 'global'
        else:
            result = {
                'category_name': 'ALTRO',
                'category_display_name': 'Altro/Sconosciuto',
                'price_per_minute': 0.0,
                'duration_billed': duration_seconds / 60.0 if unit == 'per_minute' else duration_seconds,
                'unit_label': 'minuti' if unit == 'per_minute' else 'secondi',
                'cost_calculated': 0.0,
                'currency': 'EUR',
                'matched': False,
                'original_call_type': call_type,
                'markup_percent_applied': 0.0,
                'markup_source': 'none'
            }
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Ottiene statistiche sulle categorie"""
        active_count = sum(1 for cat in self.categories.values() if cat.is_active)
        total_patterns = sum(len(cat.patterns) for cat in self.categories.values())
        
        custom_markup_count = sum(1 for cat in self.categories.values() if cat.custom_markup_percent is not None)
        global_markup_count = sum(1 for cat in self.categories.values() if cat.custom_markup_percent is None)
        
        price_range = {
            'min': min((cat.price_per_minute for cat in self.categories.values()), default=0),
            'max': max((cat.price_per_minute for cat in self.categories.values()), default=0),
            'avg': sum(cat.price_per_minute for cat in self.categories.values()) / len(self.categories) if self.categories else 0,
            'min_base': min((cat.price_per_minute for cat in self.categories.values()), default=0),
            'max_base': max((cat.price_per_minute for cat in self.categories.values()), default=0),
            'min_with_markup': min((cat.price_with_markup for cat in self.categories.values()), default=0),
            'max_with_markup': max((cat.price_with_markup for cat in self.categories.values()), default=0),
            'avg_base': sum(cat.price_per_minute for cat in self.categories.values()) / len(self.categories) if self.categories else 0,
            'avg_with_markup': sum(cat.price_with_markup for cat in self.categories.values()) / len(self.categories) if self.categories else 0
        }
        
        return {
            'total_categories': len(self.categories),
            'active_categories': active_count,
            'inactive_categories': len(self.categories) - active_count,
            'total_patterns': total_patterns,
            'price_range': price_range,
            'currencies': list(set(cat.currency for cat in self.categories.values())),
            'last_modified': max((cat.updated_at for cat in self.categories.values()), default=None),
            'markup_statistics': {
                'global_markup_percent': self.global_markup_percent,
                'categories_using_global_markup': global_markup_count,
                'categories_using_custom_markup': custom_markup_count,
                'custom_markup_range': {
                    'min': min((cat.custom_markup_percent for cat in self.categories.values() if cat.custom_markup_percent is not None), default=None),
                    'max': max((cat.custom_markup_percent for cat in self.categories.values() if cat.custom_markup_percent is not None), default=None),
                }
            }
        }
    
    def validate_patterns_conflicts(self) -> List[Dict[str, Any]]:
        """Verifica conflitti tra pattern delle categorie"""
        conflicts = []
        
        categories_list = list(self.categories.values())
        
        for i, cat1 in enumerate(categories_list):
            for j, cat2 in enumerate(categories_list[i+1:], i+1):
                if not cat1.is_active or not cat2.is_active:
                    continue
                
                common_patterns = set(p.upper() for p in cat1.patterns) & set(p.upper() for p in cat2.patterns)
                
                if common_patterns:
                    conflicts.append({
                        'category1': cat1.name,
                        'category2': cat2.name,
                        'common_patterns': list(common_patterns),
                        'severity': 'high' if len(common_patterns) > 1 else 'medium'
                    })
        
        return conflicts
    
    def update_global_markup(self, new_global_markup_percent: float) -> bool:
        """Aggiorna il markup globale e ricalcola tutti i prezzi delle categorie che lo utilizzano"""
        try:
            old_markup = self.global_markup_percent
            self.global_markup_percent = float(new_global_markup_percent)
            
            # Ricalcola prezzi per tutte le categorie che usano markup globale
            categories_updated = 0
            for category in self.categories.values():
                if category.custom_markup_percent is None:  # Usa markup globale
                    old_price = category.price_with_markup
                    category._calculate_price_with_markup(self.global_markup_percent)
                    if old_price != category.price_with_markup:
                        categories_updated += 1
            
            if self.save_categories():
                logger.info(f"Markup globale aggiornato da {old_markup}% a {self.global_markup_percent}%")
                logger.info(f"Prezzi ricalcolati per {categories_updated} categorie")
                return True
            else:
                # Rollback
                self.global_markup_percent = old_markup
                return False
                
        except Exception as e:
            logger.error(f"Errore aggiornamento markup globale: {e}")
            return False

    def get_category_with_pricing(self, name: str) -> Optional[Dict[str, Any]]:
        """Ottiene una categoria con informazioni complete sui prezzi"""
        category = self.get_category(name)
        if not category:
            return None
        
        # Restituisce tutte le info pricing
        category_data = asdict(category)
        category_data['pricing_info'] = category.get_pricing_info(self.global_markup_percent)
        category_data['global_markup_percent'] = self.global_markup_percent
        
        return category_data

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
            writer.writerow(['Name', 'Display Name', 'Price per Minute', 'Custom Markup %', 'Price With Markup', 'Currency', 
                        'Patterns', 'Description', 'Active', 'Created', 'Updated'])
            
            # Data
            for category in self.categories.values():
                writer.writerow([
                    category.name,
                    category.display_name,
                    category.price_per_minute,
                    category.custom_markup_percent if category.custom_markup_percent is not None else 'Global',
                    category.price_with_markup,
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
                        # Gestione retrocompatibilità
                        if 'custom_markup_percent' not in cat_data:
                            cat_data['custom_markup_percent'] = None
                        if 'price_with_markup' not in cat_data:
                            cat_data['price_with_markup'] = None
                        
                        category = CDRCategory(**cat_data)
                        # Ricalcola markup
                        category._calculate_price_with_markup(self.global_markup_percent)
                        self.categories[cat_name.upper()] = category
                
                return self.save_categories()
            else:
                raise ValueError(f"Formato {format} non supportato per l'import")
                
        except Exception as e:
            logger.error(f"Errore import categorie: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """Ripristina le categorie di default"""
        try:
            self.categories = self.DEFAULT_CATEGORIES.copy()
            # Applica markup globale alle categorie default
            for category in self.categories.values():
                category._calculate_price_with_markup(self.global_markup_percent)
            if self.save_categories():
                logger.info("Categorie ripristinate ai valori di default")
                return True
            return False
        except Exception as e:
            logger.error(f"Errore ripristino categorie default: {e}")
            return False


class CDRAnalyticsEnhanced:
    """Sistema CDR integrato che utilizza CDRCategoriesManager per classificazione e pricing"""
    
    def __init__(self, output_directory: str = "output", secure_config: 'SecureConfig' = None):
        self.output_directory = Path(output_directory)
        self.analytics_directory = self.output_directory / "cdr_analytics"
        self.analytics_directory.mkdir(exist_ok=True)
        
        # Inizializza manager con configurazione da .env
        self.categories_manager = CDRCategoriesManager(secure_config=secure_config)
        
        logger.info("🔧 CDR Analytics Enhanced inizializzato con configurazione da .env")

    def process_cdr_file(self, json_file_path: str) -> Dict[str, Any]:
        """Elabora un file CDR JSON utilizzando il sistema di categorie configurabile"""
        try:
            logger.info(f"🔍 Elaborazione file CDR con categorie: {json_file_path}")
            
            cdr_data = self._load_cdr_data(json_file_path)
            if not cdr_data:
                return {'success': False, 'message': 'Impossibile caricare dati CDR'}
            
            metadata = cdr_data.get('metadata', {})
            records = cdr_data.get('records', [])
            
            if not records:
                logger.warning("Nessun record trovato nel file CDR")
                return {'success': False, 'message': 'Nessun record trovato'}
            
            logger.info(f"📊 Trovati {len(records)} record CDR")
            
            # Elaborazione con categorie configurabili
            logger.info("💰 Calcolo costi con categorie configurabili")
            enhanced_records = self._enhance_records_with_categories(records)
            
            # Raggruppa per codice_contratto
            grouped_data = self._group_by_contract(enhanced_records)
            
            # Genera report per ogni contratto
            generated_files = []
            total_contracts = len(grouped_data)
            
            for contract_code, contract_records in grouped_data.items():
                try:
                    report_file = self._generate_contract_report(
                        contract_code, 
                        contract_records, 
                        metadata
                    )
                    if report_file:
                        generated_files.append(report_file)
                        logger.info(f"✅ Report generato per contratto {contract_code}: {report_file}")
                except Exception as e:
                    logger.error(f"❌ Errore generazione report contratto {contract_code}: {e}")
            
            # Genera report riassuntivo
            summary_file = self._generate_summary_report(grouped_data, metadata)
            if summary_file:
                generated_files.append(summary_file)
            
            # Statistiche categorie utilizzate
            category_stats = self._get_category_usage_stats(enhanced_records)
            
            result = {
                'success': True,
                'message': f'Elaborazione completata: {len(generated_files)} file generati',
                'source_file': json_file_path,
                'total_records': len(records),
                'total_contracts': total_contracts,
                'generated_files': generated_files,
                'category_stats': category_stats,
                'categories_system_enabled': True,
                'processing_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"🎉 Elaborazione CDR completata: {len(generated_files)} file generati")
            return result
            
        except Exception as e:
            logger.error(f"❌ Errore nell'elaborazione CDR: {e}")
            return {
                'success': False, 
                'message': f'Errore elaborazione: {str(e)}',
                'source_file': json_file_path
            }
    
    def _enhance_records_with_categories(self, records: List[Dict]) -> List[Dict]:
        """Arricchisce i record CDR con informazioni categorie e costi calcolati"""
        enhanced_records = []
        category_usage = defaultdict(lambda: {
            'count': 0, 
            'total_cost': 0.0, 
            'total_duration': 0,
            'total_duration_seconds': 0
        })
        unmatched_types = set()
        
        for record in records:
            try:
                enhanced_record = record.copy()
                
                tipo_chiamata = record.get('tipo_chiamata', '')
                durata_secondi = int(record.get('durata_secondi', 0))
                costo_originale = float(record.get('costo_euro', 0.0))
                
                # Calcola costo con sistema categorie
                cost_calculation = self.categories_manager.calculate_call_cost(
                    tipo_chiamata, 
                    durata_secondi,
                    unit='per_minute'
                )
                
                # Arricchisci record con informazioni categoria
                enhanced_record.update({
                    'categoria_cliente': cost_calculation['category_name'],
                    'categoria_display': cost_calculation['category_display_name'],
                    'prezzo_categoria_per_minuto': cost_calculation['price_per_minute'],
                    'costo_cliente_euro': cost_calculation['cost_calculated'],
                    'durata_fatturata_minuti': cost_calculation['duration_billed'],
                    'categoria_matched': cost_calculation['matched'],
                    'valuta_categoria': cost_calculation['currency'],
                    
                    'costo_originale_euro': costo_originale,
                    'differenza_costo_euro': round(cost_calculation['cost_calculated'] - costo_originale, 4),
                    'risparmio_percentuale': round(
                        ((cost_calculation['cost_calculated'] - costo_originale) / costo_originale * 100) 
                        if costo_originale > 0 else 0, 2
                    ),
                    
                    'tipo_chiamata_originale': tipo_chiamata,
                    'processed_timestamp': datetime.now().isoformat()
                })
                
                # Statistiche utilizzo categorie
                cat_name = cost_calculation['category_name']
                category_usage[cat_name]['count'] += 1
                category_usage[cat_name]['total_cost'] += cost_calculation['cost_calculated']
                category_usage[cat_name]['total_duration'] += durata_secondi
                category_usage[cat_name]['total_duration_seconds'] += durata_secondi
                category_usage[cat_name]['display_name'] = cost_calculation['category_display_name']
                
                if not cost_calculation['matched']:
                    unmatched_types.add(tipo_chiamata)
                
                enhanced_records.append(enhanced_record)
                
            except Exception as e:
                logger.error(f"Errore elaborazione record: {e}")
                record['categoria_cliente'] = 'ERRORE'
                record['costo_cliente_euro'] = float(record.get('costo_euro', 0.0))
                enhanced_records.append(record)
        
        # Log statistiche dettagliate
        logger.info(f"💰 Elaborazione categorie completata:")
        for cat_name, stats in category_usage.items():
            avg_cost_per_min = (stats['total_cost'] / (stats['total_duration_seconds'] / 60)) if stats['total_duration_seconds'] > 0 else 0
            duration_minutes = stats['total_duration_seconds'] / 60
            logger.info(f"   {stats['display_name']}: {stats['count']} chiamate, "
                    f"{duration_minutes:.1f} min, €{avg_cost_per_min:.4f}/min medio, totale €{stats['total_cost']:.2f}")
        
        if unmatched_types:
            logger.warning(f"⚠️ Tipi chiamata non riconosciuti ({len(unmatched_types)}):")
            for unmatched in sorted(unmatched_types):
                logger.warning(f"   - '{unmatched}'")
        
        return enhanced_records
    
    def _load_cdr_data(self, json_file_path: str) -> Optional[Dict]:
        """Carica dati dal file JSON CDR"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Errore caricamento file {json_file_path}: {e}")
            return None
    
    def _group_by_contract(self, records: List[Dict]) -> Dict[str, List[Dict]]:
        """Raggruppa record per codice contratto"""        
        grouped = defaultdict(list)
        
        for record in records:
            contract_code = record.get('codice_contratto')
            if contract_code is not None:
                contract_key = str(contract_code)
                grouped[contract_key].append(record)
        
        logger.info(f"📋 Contratti raggruppati: {len(grouped)}")
        return dict(grouped)
    
    def _aggregate_contract_data_with_categories(self, records: List[Dict]) -> Dict[str, Any]:
        """Aggrega dati contratto con breakdown per categoria"""
        if not records:
            return {}
        
        first_record = records[0]
        contract_info = {
            'codice_contratto': first_record.get('codice_contratto', ''),
            'cliente_finale_comune': first_record.get('cliente_finale_comune', ''),
        }
        
        total_calls = len(records)
        total_duration = sum(int(r.get('durata_secondi', 0)) for r in records)
        total_cost_original = sum(float(r.get('costo_originale_euro', 0)) for r in records)
        total_cost_client = sum(float(r.get('costo_cliente_euro', 0)) for r in records)
        
        # Aggregazione per categoria
        costo_cliente_totale_euro_by_category = defaultdict(float)
        category_breakdown = defaultdict(lambda: {
            'calls': 0,
            'duration_seconds': 0,
            'duration_minutes': 0.0,
            'cost_client_euro': 0.0,
            'cost_original_euro': 0.0,
            'display_name': '',
            'price_per_minute': 0.0,
            'matched_calls': 0
        })
        
        for record in records:
            cat_name = record.get('categoria_cliente', 'ALTRO')
            cat_display = record.get('categoria_display', cat_name)
            duration = int(record.get('durata_secondi', 0))
            cost_client = float(record.get('costo_cliente_euro', 0))
            cost_original = float(record.get('costo_originale_euro', 0))
            price_per_min = float(record.get('prezzo_categoria_per_minuto', 0))
            matched = record.get('categoria_matched', False)
            
            costo_cliente_totale_euro_by_category[cat_name] += cost_client
            
            category_breakdown[cat_name]['calls'] += 1
            category_breakdown[cat_name]['duration_seconds'] += duration
            category_breakdown[cat_name]['cost_client_euro'] += cost_client
            category_breakdown[cat_name]['cost_original_euro'] += cost_original
            category_breakdown[cat_name]['display_name'] = cat_display
            category_breakdown[cat_name]['price_per_minute'] = price_per_min
            if matched:
                category_breakdown[cat_name]['matched_calls'] += 1
        
        # Finalizza calcoli per categoria
        for cat_name, data in category_breakdown.items():
            data['duration_minutes'] = round(data['duration_seconds'] / 60, 2)
            data['cost_client_euro'] = round(data['cost_client_euro'], 4)
            data['cost_original_euro'] = round(data['cost_original_euro'], 4)
            data['difference_euro'] = round(data['cost_client_euro'] - data['cost_original_euro'], 4)
            data['avg_cost_per_call'] = round(data['cost_client_euro'] / data['calls'], 4) if data['calls'] > 0 else 0
            data['avg_duration_per_call'] = round(data['duration_seconds'] / data['calls'], 1) if data['calls'] > 0 else 0
            data['match_rate'] = round((data['matched_calls'] / data['calls']) * 100, 1) if data['calls'] > 0 else 0
        
        result = {
            **contract_info,
            'totale_chiamate': total_calls,
            'durata_totale_secondi': total_duration,
            'durata_totale_minuti': round(total_duration / 60, 2),
            'durata_totale_ore': round(total_duration / 3600, 2),
            'costo_originale_totale_euro': round(total_cost_original, 4),
            'costo_cliente_totale_euro': round(total_cost_client, 4),
            'differenza_totale_euro': round(total_cost_client - total_cost_original, 4),
            'risparmio_percentuale': round(
                ((total_cost_client - total_cost_original) / total_cost_original * 100) 
                if total_cost_original > 0 else 0, 2
            ),
            
            'costo_cliente_totale_euro_by_category': dict(costo_cliente_totale_euro_by_category),
            'categoria_breakdown_dettagliato': dict(category_breakdown)
        }
        
        return result
    
    def _generate_contract_report(self, contract_code: str, records: List[Dict], metadata: Dict) -> Optional[str]:
        """Genera report per contratto con categorizzazione completa"""
        try:
            aggregated_data = self._aggregate_contract_data_with_categories(records)
            
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            current_month = now.strftime("%m")
            filename = f"{contract_code}_{current_month}_categories.json"
            filepath = self.analytics_directory / filename
            
            report = {
                'metadata': {
                    'contract_code': contract_code,
                    'generation_timestamp': now.isoformat(),
                    'source_file': metadata.get('source_file', ''),
                    'contract_records': len(records),
                    'month': current_month,
                    'year': now.year,
                    'categories_system_version': '2.0',
                    'categories_enabled': True
                },
                'summary': aggregated_data,
                'category_analysis': {
                    'total_categories_found': len(aggregated_data.get('costo_cliente_totale_euro_by_category', {})),
                    'category_distribution': self._calculate_category_distribution(records),
                    'top_categories_by_cost': self._get_top_categories_by_cost(aggregated_data.get('costo_cliente_totale_euro_by_category', {})),
                    'unmatched_call_types': self._get_unmatched_call_types(records)
                },
                'daily_breakdown': self._get_daily_breakdown_with_categories(records),
                'call_types_detailed': self._get_call_types_breakdown_enhanced(records),
                'raw_records': records
            }
            
            report['categories_configuration'] = {
                'active_categories': len(self.categories_manager.get_active_categories()),
                'total_categories': len(self.categories_manager.get_all_categories()),
                'categories_statistics': self.categories_manager.get_statistics()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📄 Report contratto con categorie salvato: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Errore generazione report contratto {contract_code}: {e}")
            return None
    
    def _generate_summary_report(self, grouped_data: Dict, metadata: Dict) -> Optional[str]:
        """Genera report riassuntivo globale con breakdown per categoria"""
        try:
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            current_month = now.strftime("%m")
            filename = f"SUMMARY_CATEGORIES_{current_month}.json"
            filepath = self.analytics_directory / filename
            
            contracts_summary = {}
            global_totals = {
                'total_contracts': len(grouped_data),
                'total_calls': 0,
                'total_duration_seconds': 0,
                'total_cost_original_euro': 0.0,
                'total_cost_client_euro': 0.0
            }
            
            global_costo_cliente_totale_euro_by_category = defaultdict(float)
            global_category_stats = defaultdict(lambda: {
                'calls': 0,
                'duration_seconds': 0,
                'cost_client_euro': 0.0,
                'cost_original_euro': 0.0,
                'display_name': '',
                'contracts_using': set(),
                'matched_calls': 0,
                'price_per_minute': 0.0
            })
            
            for contract_code, records in grouped_data.items():
                contract_summary = self._aggregate_contract_data_with_categories(records)
                contracts_summary[contract_code] = contract_summary
                
                global_totals['total_calls'] += len(records)
                global_totals['total_duration_seconds'] += sum(int(r.get('durata_secondi', 0)) for r in records)
                global_totals['total_cost_original_euro'] += sum(float(r.get('costo_originale_euro', 0)) for r in records)
                global_totals['total_cost_client_euro'] += sum(float(r.get('costo_cliente_euro', 0)) for r in records)
                
                contract_category_costs = contract_summary.get('costo_cliente_totale_euro_by_category', {})
                for cat_name, cost in contract_category_costs.items():
                    global_costo_cliente_totale_euro_by_category[cat_name] += cost
                
                for record in records:
                    cat_name = record.get('categoria_cliente', 'ALTRO')
                    cat_display = record.get('categoria_display', cat_name)
                    duration = int(record.get('durata_secondi', 0))
                    cost_client = float(record.get('costo_cliente_euro', 0))
                    cost_original = float(record.get('costo_originale_euro', 0))
                    matched = record.get('categoria_matched', False)
                    price_per_min = float(record.get('prezzo_categoria_per_minuto', 0))
                    
                    global_category_stats[cat_name]['calls'] += 1
                    global_category_stats[cat_name]['duration_seconds'] += duration
                    global_category_stats[cat_name]['cost_client_euro'] += cost_client
                    global_category_stats[cat_name]['cost_original_euro'] += cost_original
                    global_category_stats[cat_name]['display_name'] = cat_display
                    global_category_stats[cat_name]['contracts_using'].add(contract_code)
                    global_category_stats[cat_name]['price_per_minute'] = price_per_min
                    if matched:
                        global_category_stats[cat_name]['matched_calls'] += 1
            
            # Finalizza totali globali
            for key in ['total_cost_original_euro', 'total_cost_client_euro']:
                global_totals[key] = round(global_totals[key], 4)
            
            global_totals['total_duration_minutes'] = round(global_totals['total_duration_seconds'] / 60, 2)
            global_totals['total_difference_euro'] = round(global_totals['total_cost_client_euro'] - global_totals['total_cost_original_euro'], 4)
            global_totals['average_cost_per_call'] = round(global_totals['total_cost_client_euro'] / global_totals['total_calls'], 4) if global_totals['total_calls'] > 0 else 0
            
            global_costo_cliente_totale_euro_by_category = {
                cat: round(cost, 4) for cat, cost in global_costo_cliente_totale_euro_by_category.items()
            }
            
            # Finalizza statistiche categorie globali
            for cat_name, data in global_category_stats.items():
                data['cost_client_euro'] = round(data['cost_client_euro'], 4)
                data['cost_original_euro'] = round(data['cost_original_euro'], 4)
                data['duration_minutes'] = round(data['duration_seconds'] / 60, 2)
                data['difference_euro'] = round(data['cost_client_euro'] - data['cost_original_euro'], 4)
                data['percentage_of_total'] = round((data['calls'] / global_totals['total_calls']) * 100, 2) if global_totals['total_calls'] > 0 else 0
                data['contracts_count'] = len(data['contracts_using'])
                data['avg_cost_per_call'] = round(data['cost_client_euro'] / data['calls'], 4) if data['calls'] > 0 else 0
                data['match_rate'] = round((data['matched_calls'] / data['calls']) * 100, 1) if data['calls'] > 0 else 0
                data['contracts_using'] = list(data['contracts_using'])
            
            summary_report = {
                'metadata': {
                    'generation_timestamp': now.isoformat(),
                    'source_file': metadata.get('source_file', ''),
                    'month': current_month,
                    'year': now.year,
                    'categories_system_version': '2.0',
                    'categories_enabled': True,
                    'total_categories_found': len(global_costo_cliente_totale_euro_by_category),
                    'categories_info': self.categories_manager.get_statistics()
                },
                'global_totals': global_totals,
                'global_costo_cliente_totale_euro_by_category': global_costo_cliente_totale_euro_by_category,
                'global_categories_detailed': dict(global_category_stats),
                'contracts_summary': contracts_summary,
                'top_analysis': {
                    'top_contracts_by_cost': self._get_top_contracts_enhanced(contracts_summary, 'costo_cliente_totale_euro'),
                    'top_contracts_by_calls': self._get_top_contracts_enhanced(contracts_summary, 'totale_chiamate'),
                    'top_categories_by_cost': self._get_top_categories_global(global_costo_cliente_totale_euro_by_category),
                    'top_categories_by_usage': self._get_top_categories_by_usage(global_category_stats)
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📊 Report summary globale con categorie generato: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Errore generazione summary report: {e}")
            return None
    
    def get_categories_manager(self) -> CDRCategoriesManager:
        """Restituisce il manager delle categorie"""
        return self.categories_manager
    
    def list_generated_reports(self) -> List[Dict]:
        """Lista report generati con info categorie"""
        reports = []
        
        try:
            for file_path in self.analytics_directory.glob("*.json"):
                if file_path.name == "cdr_categories.json":
                    continue
                
                stat = file_path.stat()
                reports.append({
                    'filename': file_path.name,
                    'filepath': str(file_path),
                    'size_bytes': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'is_summary': file_path.name.startswith('SUMMARY_'),
                    'has_categories': 'categories' in file_path.name.lower() or file_path.name.startswith('SUMMARY_'),
                    'categories_version': '2.0' if 'categories' in file_path.name.lower() else '1.0'
                })
            
            reports.sort(key=lambda x: x['created'], reverse=True)
            
        except Exception as e:
            logger.error(f"Errore listing report: {e}")
        
        return reports
    
    # Helper methods per i report
    def _calculate_category_distribution(self, records: List[Dict]) -> Dict[str, Any]:
        """Calcola distribuzione percentuale delle categorie"""
        total_records = len(records)
        category_counts = defaultdict(int)
        
        for record in records:
            cat_name = record.get('categoria_cliente', 'ALTRO')
            category_counts[cat_name] += 1
        
        distribution = {}
        for cat_name, count in category_counts.items():
            percentage = round((count / total_records) * 100, 2)
            distribution[cat_name] = {
                'count': count,
                'percentage': percentage,
                'display_name': self._get_category_display_name(cat_name)
            }
        
        return distribution
    
    def _get_category_display_name(self, cat_name: str) -> str:
        """Ottiene il nome display di una categoria"""
        category = self.categories_manager.get_category(cat_name)
        return category.display_name if category else cat_name
    
    def _get_top_categories_by_cost(self, costo_by_category: Dict[str, float]) -> List[Dict[str, Any]]:
        """Restituisce top categorie per costo"""
        sorted_categories = sorted(costo_by_category.items(), key=lambda x: x[1], reverse=True)
        
        top_categories = []
        for cat_name, cost in sorted_categories[:5]:
            top_categories.append({
                'category_name': cat_name,
                'display_name': self._get_category_display_name(cat_name),
                'total_cost_euro': round(cost, 4)
            })
        
        return top_categories
    
    def _get_unmatched_call_types(self, records: List[Dict]) -> List[str]:
        """Restituisce tipi di chiamata non riconosciuti"""
        unmatched = set()
        for record in records:
            if not record.get('categoria_matched', True):
                unmatched.add(record.get('tipo_chiamata_originale', ''))
        
        return sorted(list(unmatched))
    
    def _get_daily_breakdown_with_categories(self, records: List[Dict]) -> Dict[str, Dict]:
        """Genera breakdown giornaliero con categorie"""
        daily_data = defaultdict(lambda: {
            'chiamate': 0,
            'durata_secondi': 0,
            'costo_originale_euro': 0.0,
            'costo_cliente_euro': 0.0,
            'categorie': defaultdict(lambda: {
                'count': 0, 
                'cost': 0.0,
                'duration_seconds': 0
            })
        })
        
        for record in records:
            date_str = record.get('data_ora_chiamata', '')
            if date_str:
                date_key = date_str[:10] if len(date_str) >= 10 else date_str
                cat_name = record.get('categoria_cliente', 'ALTRO')
                duration = int(record.get('durata_secondi', 0))
                cost = float(record.get('costo_cliente_euro', 0))
                
                daily_data[date_key]['chiamate'] += 1
                daily_data[date_key]['durata_secondi'] += duration
                daily_data[date_key]['costo_originale_euro'] += float(record.get('costo_originale_euro', 0))
                daily_data[date_key]['costo_cliente_euro'] += cost
                
                daily_data[date_key]['categorie'][cat_name]['count'] += 1
                daily_data[date_key]['categorie'][cat_name]['cost'] += cost
                daily_data[date_key]['categorie'][cat_name]['duration_seconds'] += duration
        
        # Arrotonda e converte
        for day in daily_data:
            daily_data[day]['costo_originale_euro'] = round(daily_data[day]['costo_originale_euro'], 4)
            daily_data[day]['costo_cliente_euro'] = round(daily_data[day]['costo_cliente_euro'], 4)
            daily_data[day]['durata_minuti'] = round(daily_data[day]['durata_secondi'] / 60, 2)
            daily_data[day]['differenza_costo'] = round(
                daily_data[day]['costo_cliente_euro'] - daily_data[day]['costo_originale_euro'], 4
            )
            
            daily_data[day]['categorie'] = {
                cat: {
                    'count': data['count'], 
                    'cost': round(data['cost'], 4),
                    'duration_seconds': data['duration_seconds']
                }
                for cat, data in daily_data[day]['categorie'].items()
            }
        
        return dict(daily_data)
    
    def _get_call_types_breakdown_enhanced(self, records: List[Dict]) -> Dict[str, Dict]:
        """Breakdown dettagliato per tipo di chiamata con informazioni categoria"""
        breakdown = defaultdict(lambda: {
            'numero_chiamate': 0,
            'durata_totale_secondi': 0,
            'costo_cliente_totale_euro': 0.0,
            'costo_originale_totale_euro': 0.0,
            'categoria_assegnata': '',
            'categoria_display': '',
            'matched': True,
            'price_per_minute': 0.0
        })
        
        for record in records:
            call_type = record.get('tipo_chiamata_originale', record.get('tipo_chiamata', ''))
            if call_type:
                duration = int(record.get('durata_secondi', 0))
                cost_client = float(record.get('costo_cliente_euro', 0))
                cost_original = float(record.get('costo_originale_euro', 0))
                
                breakdown[call_type]['numero_chiamate'] += 1
                breakdown[call_type]['durata_totale_secondi'] += duration
                breakdown[call_type]['costo_cliente_totale_euro'] += cost_client
                breakdown[call_type]['costo_originale_totale_euro'] += cost_original
                breakdown[call_type]['categoria_assegnata'] = record.get('categoria_cliente', 'ALTRO')
                breakdown[call_type]['categoria_display'] = record.get('categoria_display', '')
                breakdown[call_type]['matched'] = record.get('categoria_matched', False)
                breakdown[call_type]['price_per_minute'] = float(record.get('prezzo_categoria_per_minuto', 0))
        
        # Finalizza calcoli
        for call_type, data in breakdown.items():
            data['durata_media_secondi'] = round(data['durata_totale_secondi'] / data['numero_chiamate'], 2) if data['numero_chiamate'] > 0 else 0
            data['costo_cliente_totale_euro'] = round(data['costo_cliente_totale_euro'], 4)
            data['costo_originale_totale_euro'] = round(data['costo_originale_totale_euro'], 4)
            data['differenza_totale_euro'] = round(data['costo_cliente_totale_euro'] - data['costo_originale_totale_euro'], 4)
            data['costo_medio_per_chiamata'] = round(data['costo_cliente_totale_euro'] / data['numero_chiamate'], 4) if data['numero_chiamate'] > 0 else 0
            
            if data['durata_totale_secondi'] > 0:
                data['costo_al_minuto_effettivo'] = round((data['costo_cliente_totale_euro'] / (data['durata_totale_secondi'] / 60)), 4)
            else:
                data['costo_al_minuto_effettivo'] = 0
        
        return dict(breakdown)
    
    def _get_category_usage_stats(self, records: List[Dict]) -> Dict[str, Any]:
        """Genera statistiche utilizzo categorie"""
        stats = defaultdict(lambda: {
            'calls': 0,
            'total_cost': 0.0,
            'total_duration_minutes': 0.0,
            'total_duration_seconds': 0,
            'matched': 0,
            'display_name': ''
        })
        
        total_records = len(records)
        
        for record in records:
            cat_name = record.get('categoria_cliente', 'ALTRO')
            cat_display = record.get('categoria_display', cat_name)
            cost = float(record.get('costo_cliente_euro', 0))
            duration_min = float(record.get('durata_fatturata_minuti', 0))
            duration_sec = int(record.get('durata_secondi', 0))
            matched = record.get('categoria_matched', False)
            
            stats[cat_name]['calls'] += 1
            stats[cat_name]['total_cost'] += cost
            stats[cat_name]['total_duration_minutes'] += duration_min
            stats[cat_name]['total_duration_seconds'] += duration_sec
            stats[cat_name]['display_name'] = cat_display
            if matched:
                stats[cat_name]['matched'] += 1
        
        # Calcola percentuali e medie
        for cat_name, data in stats.items():
            data['percentage'] = round((data['calls'] / total_records) * 100, 2)
            data['avg_cost_per_call'] = round(data['total_cost'] / data['calls'], 4) if data['calls'] > 0 else 0
            data['avg_cost_per_minute'] = round(data['total_cost'] / data['total_duration_minutes'], 4) if data['total_duration_minutes'] > 0 else 0
            data['avg_duration_seconds'] = round(data['total_duration_seconds'] / data['calls'], 1) if data['calls'] > 0 else 0
            data['match_rate'] = round((data['matched'] / data['calls']) * 100, 1) if data['calls'] > 0 else 0
            data['total_cost'] = round(data['total_cost'], 4)
            data['total_duration_minutes'] = round(data['total_duration_minutes'], 2)
        
        return dict(stats)
    
    def _get_top_contracts_enhanced(self, contracts_summary: Dict, sort_by: str) -> List[Dict]:
        """Genera top contratti con informazioni categorie"""
        try:
            contracts_list = []
            
            for contract_code, data in contracts_summary.items():
                contract_data = {
                    'codice_contratto': contract_code,
                    'cliente_finale_comune': data.get('cliente_finale_comune', ''),
                    'totale_chiamate': data.get('totale_chiamate', 0),
                    'durata_totale_secondi': data.get('durata_totale_secondi', 0),
                    'costo_originale_totale_euro': data.get('costo_originale_totale_euro', 0.0),
                    'costo_cliente_totale_euro': data.get('costo_cliente_totale_euro', 0.0),
                    'differenza_totale_euro': data.get('differenza_totale_euro', 0.0),
                    'risparmio_percentuale': data.get('risparmio_percentuale', 0.0),
                    'top_category': self._get_top_category_for_contract(data.get('costo_cliente_totale_euro_by_category', {})),
                    'categories_count': len(data.get('costo_cliente_totale_euro_by_category', {}))
                }
                contracts_list.append(contract_data)
            
            return sorted(contracts_list, key=lambda x: x.get(sort_by, 0), reverse=True)[:10]
            
        except Exception as e:
            logger.error(f"Errore calcolo top contracts: {e}")
            return []
    
    def _get_top_category_for_contract(self, category_costs: Dict[str, float]) -> Dict[str, Any]:
        """Restituisce la categoria principale per un contratto"""
        if not category_costs:
            return {'name': 'N/A', 'cost': 0.0}
        
        top_cat = max(category_costs.items(), key=lambda x: x[1])
        return {
            'name': top_cat[0],
            'display_name': self._get_category_display_name(top_cat[0]),
            'cost': round(top_cat[1], 4)
        }
    
    def _get_top_categories_global(self, global_costs: Dict[str, float]) -> List[Dict]:
        """Top categorie per costo globale"""
        sorted_categories = sorted(global_costs.items(), key=lambda x: x[1], reverse=True)
        
        top_categories = []
        for cat_name, cost in sorted_categories:
            top_categories.append({
                'category_name': cat_name,
                'display_name': self._get_category_display_name(cat_name),
                'total_cost_euro': cost,
                'percentage_of_total': 0
            })
        
        return top_categories
    
    def _get_top_categories_by_usage(self, global_stats: Dict) -> List[Dict]:
        """Top categorie per utilizzo (numero chiamate)"""
        sorted_by_usage = sorted(global_stats.items(), key=lambda x: x[1]['calls'], reverse=True)
        
        top_usage = []
        for cat_name, stats in sorted_by_usage:
            top_usage.append({
                'category_name': cat_name,
                'display_name': stats['display_name'],
                'total_calls': stats['calls'],
                'total_cost_euro': stats['cost_client_euro'],
                'contracts_using': stats['contracts_count'],
                'match_rate': stats['match_rate']
            })
        
        return top_usage


# Funzioni di integrazione per mantenere compatibilità con app.py
def integrate_enhanced_cdr_system(app, processor, secure_config):
    """
    Integra il sistema CDR potenziato nell'applicazione esistente
    Sostituisce completamente il vecchio sistema con quello basato su categorie
    """
    # Backup del vecchio sistema se presente
    if hasattr(processor, 'cdr_analytics'):
        processor._old_cdr_analytics = processor.cdr_analytics

    # Sostituisce con il nuovo sistema integrato
    processor.cdr_analytics = CDRAnalyticsEnhanced(
        processor.config['output_directory'], 
        secure_config=secure_config
    )
    
    # Modifica il process_files per usare il nuovo sistema
    def enhanced_process_files_with_categories(self):
        """
        Versione potenziata che usa il sistema categorie per l'elaborazione CDR
        """
        try:
            logger.info("🚀 Avvio elaborazione file con sistema categorie CDR 2.0")
            
            # Esegui processo originale di download
            result = self._original_process_files()
            
            if result.get('success') and result.get('converted_files'):
                logger.info("📊 Avvio analisi CDR con sistema categorie configurabili")
                
                cdr_results = []
                
                for json_file in result['converted_files']:
                    if self._is_cdr_file(json_file):
                        logger.info(f"🔍 Analisi CDR con categorie per: {json_file}")
                        
                        cdr_result = self.cdr_analytics.process_cdr_file(json_file)
                        cdr_results.append(cdr_result)
                        
                        if cdr_result.get('success'):
                            logger.info(f"✅ Analisi completata: {len(cdr_result.get('generated_files', []))} report con categorie")
                            
                            # Log campo richiesto
                            stats = cdr_result.get('category_stats', {})
                            if stats:
                                logger.info("💰 Breakdown costi per categoria:")
                                for cat_name, cat_stats in stats.items():
                                    logger.info(f"   {cat_stats.get('display_name', cat_name)}: €{cat_stats.get('total_cost', 0):.2f}")
                        else:
                            logger.warning(f"⚠️ Analisi CDR fallita per {json_file}: {cdr_result.get('message')}")
                
                # Risultato finale con info categorie
                if cdr_results:
                    result['cdr_analytics'] = {
                        'processed_files': len(cdr_results),
                        'successful_analyses': sum(1 for r in cdr_results if r.get('success')),
                        'total_reports_generated': sum(len(r.get('generated_files', [])) for r in cdr_results),
                        'categories_system_enabled': True,
                        'categories_version': '2.0',
                        'results': cdr_results
                    }
                    
                    logger.info(f"📈 Analisi CDR con categorie completata: {result['cdr_analytics']['total_reports_generated']} report generati")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Errore processo CDR con categorie: {e}")
            return getattr(self, '_original_process_files', lambda: {'success': False, 'message': str(e)})()
    
    def _is_cdr_file_enhanced(self, json_file_path):
        """Determina se un file JSON è un file CDR (versione migliorata)"""
        try:
            filename = Path(json_file_path).name.upper()
            
            # Check nome file
            if any(keyword in filename for keyword in ['CDR', 'RIV', 'CALL', 'DETAIL']):
                return True
            
            # Check contenuto
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check metadati
            metadata = data.get('metadata', {})
            if metadata.get('file_type') == 'CDR':
                return True
            
            # Check struttura record
            records = data.get('records', [])
            if records and len(records) > 0:
                first_record = records[0]
                cdr_fields = [
                    'data_ora_chiamata', 'numero_chiamante', 'numero_chiamato', 
                    'durata_secondi', 'tipo_chiamata', 'costo_euro', 'codice_contratto'
                ]
                
                matching_fields = sum(1 for field in cdr_fields if field in first_record)
                return matching_fields >= 5
            
            return False
            
        except Exception as e:
            logger.error(f"Errore verifica file CDR {json_file_path}: {e}")
            return False
    
    # Sostituisce i metodi del processore
    processor._original_process_files = processor.process_files
    processor.process_files = enhanced_process_files_with_categories.__get__(processor, type(processor))
    processor._is_cdr_file = _is_cdr_file_enhanced.__get__(processor, type(processor))
    
    logger.info("🔧 Sistema CDR Integrato 2.0 con categorie configurabili attivato")
    
    return processor


# Funzione standalone per test
def process_cdr_with_categories_standalone(json_file_path: str, output_directory: str = "output") -> Dict:
    """
    Elabora un file CDR in modalità standalone con sistema categorie
    """
    analytics = CDRAnalyticsEnhanced(output_directory)
    return analytics.process_cdr_file(json_file_path)


if __name__ == "__main__":
    # Test standalone
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"🧪 Test elaborazione CDR con categorie: {file_path}")
        
        result = process_cdr_with_categories_standalone(file_path)
        
        if result['success']:
            print(f"✅ Elaborazione completata!")
            print(f"📊 Contratti elaborati: {result['total_contracts']}")
            print(f"📁 File generati: {len(result['generated_files'])}")
            print(f"🏷️ Sistema categorie: {result.get('categories_system_enabled', False)}")
            
            # Mostra campo richiesto
            stats = result.get('category_stats', {})
            if stats:
                print(f"💰 Breakdown costi per categoria:")
                for cat_name, cat_stats in stats.items():
                    print(f"   {cat_stats.get('display_name', cat_name)}: €{cat_stats.get('total_cost', 0):.2f} ({cat_stats.get('calls', 0)} chiamate)")
            
            for file_path in result['generated_files']:
                print(f"   📄 {file_path}")
        else:
            print(f"❌ Errore: {result['message']}")
    else:
        print("Uso: python cdr_categories_enhanced.py <file_cdr.json>")
        print("Esempio: python cdr_categories_enhanced.py output/RIV_12345_MESE_05_2024-06-05-14.16.27.json")