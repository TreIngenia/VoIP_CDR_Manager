#!/usr/bin/env python3
"""
CDR Analytics Module - Elaborazione e analisi file CDR con calcolo prezzi VoIP
Modulo per analizzare file CDR (Call Detail Record) e generare report aggregati
Versione aggiornata con calcolo prezzi basato su configurazione VoIP
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class VoIPPricingConfig:
    """Configurazione per i prezzi VoIP e mapping tipologie chiamate"""
    
    # Mapping default delle tipologie di chiamata
    CALL_TYPE_MAPPING = {
        'FISSI': [
            'INTERRURBANE URBANE', 'INTERURBANE URBANE', 'URBANE', 'FISSO',
            'RETE FISSA', 'TELEFONIA FISSA', 'LOCALE', 'DISTRETTUALE'
        ],
        'MOBILI': [
            'CELLULARE', 'MOBILE', 'RETE MOBILE', 'TELEFONIA MOBILE',
            'GSM', 'UMTS', 'LTE', 'WIND', 'TIM', 'VODAFONE', 'ILIAD'
        ],
        'FAX': [
            'FAX', 'TELEFAX', 'FACSIMILE'
        ],
        'NUMERI_VERDI': [
            'NUMERO VERDE', 'VERDE', '800', 'GRATUITO', 'TOLL FREE'
        ],
        'INTERNAZIONALI': [
            'INTERNAZIONALE', 'INTERNATIONAL', 'ESTERO', 'UE', 'EUROPA',
            'MONDO', 'ROAMING', 'EXTRA UE'
        ]
    }
    
    def __init__(self, voip_config: Dict[str, Any]):
        """
        Inizializza la configurazione prezzi VoIP
        
        Args:
            voip_config: Dizionario con configurazione VoIP dall'app
        """
        self.config = voip_config
        self.errors = []
        self._validate_config()
    
    def _validate_config(self):
        """Valida la configurazione VoIP"""
        required_fields = [
            'voip_price_fixed_final', 'voip_price_mobile_final',
            'voip_currency', 'voip_price_unit'
        ]
        
        for field in required_fields:
            if field not in self.config or self.config[field] is None:
                self.errors.append(f"Campo VoIP mancante o nullo: {field}")
        
        # Valida che i prezzi siano numerici e positivi
        price_fields = ['voip_price_fixed_final', 'voip_price_mobile_final']
        for field in price_fields:
            if field in self.config:
                try:
                    price = float(self.config[field])
                    if price < 0:
                        self.errors.append(f"Prezzo {field} deve essere positivo")
                except (ValueError, TypeError):
                    self.errors.append(f"Prezzo {field} deve essere numerico")
        
        # Valida unità di prezzo
        valid_units = ['per_minute', 'per_second']
        if (self.config.get('voip_price_unit') and 
            self.config['voip_price_unit'] not in valid_units):
            self.errors.append(f"Unità prezzo deve essere una di: {valid_units}")
    
    def is_valid(self) -> bool:
        """Verifica se la configurazione è valida"""
        return len(self.errors) == 0
    
    def get_errors(self) -> List[str]:
        """Restituisce lista errori di validazione"""
        return self.errors.copy()
    
    def classify_call_type(self, tipo_chiamata: str) -> str:
        """
        Classifica il tipo di chiamata in una macrocategoria
        
        Args:
            tipo_chiamata: Tipo chiamata dal record CDR
            
        Returns:
            Macrocategoria (FISSI, MOBILI, FAX, NUMERI_VERDI, INTERNAZIONALI, ALTRO)
        """
        if not tipo_chiamata:
            return 'ALTRO'
        
        tipo_upper = tipo_chiamata.upper().strip()
        
        for categoria, patterns in self.CALL_TYPE_MAPPING.items():
            for pattern in patterns:
                if pattern in tipo_upper:
                    return categoria
        
        logger.debug(f"Tipo chiamata non classificato: '{tipo_chiamata}' -> ALTRO")
        return 'ALTRO'
    
    def get_price_for_category(self, categoria: str) -> float:
        """
        Ottiene il prezzo per una categoria di chiamata
        
        Args:
            categoria: Categoria chiamata (FISSI, MOBILI, etc.)
            
        Returns:
            Prezzo per la categoria
        """
        # Mapping categorie -> prezzi
        price_mapping = {
            'FISSI': self.config.get('voip_price_fixed_final', 0),
            'MOBILI': self.config.get('voip_price_mobile_final', 0),
            'FAX': self.config.get('voip_price_fixed_final', 0),  # FAX come fisso
            'NUMERI_VERDI': 0,  # Numeri verdi gratuiti
            'INTERNAZIONALI': self.config.get('voip_price_mobile_final', 0),  # Internazionali come mobile
            'ALTRO': self.config.get('voip_price_fixed_final', 0)  # Default fisso
        }
        
        return float(price_mapping.get(categoria, 0))
    
    def calculate_cost(self, tipo_chiamata: str, durata_secondi: int) -> Dict[str, Any]:
        """
        Calcola il costo di una chiamata basato sulla configurazione VoIP
        
        Args:
            tipo_chiamata: Tipo di chiamata
            durata_secondi: Durata in secondi
            
        Returns:
            Dict con dettagli calcolo
        """
        categoria = self.classify_call_type(tipo_chiamata)
        prezzo_unitario = self.get_price_for_category(categoria)
        unit = self.config.get('voip_price_unit', 'per_minute')
        
        # Calcola costo basato sull'unità
        if unit == 'per_second':
            costo_calcolato = prezzo_unitario * durata_secondi
            durata_fatturata = durata_secondi
            unita_fatturazione = 'secondi'
        else:  # per_minute (default)
            durata_minuti = durata_secondi / 60.0
            costo_calcolato = prezzo_unitario * durata_minuti
            durata_fatturata = durata_minuti
            unita_fatturazione = 'minuti'
        
        return {
            'categoria': categoria,
            'prezzo_unitario': prezzo_unitario,
            'durata_fatturata': round(durata_fatturata, 4),
            'unita_fatturazione': unita_fatturazione,
            'costo_cliente_euro': round(costo_calcolato, 4),
            'valuta': self.config.get('voip_currency', 'EUR')
        }
    
    def add_custom_mapping(self, categoria: str, patterns: List[str]):
        """
        Aggiunge mapping personalizzato per una categoria
        
        Args:
            categoria: Nome categoria (es. 'SMS', 'VIDEOCHIAMATE')
            patterns: Lista pattern da riconoscere
        """
        if categoria not in self.CALL_TYPE_MAPPING:
            self.CALL_TYPE_MAPPING[categoria] = []
        
        # Aggiungi pattern evitando duplicati
        for pattern in patterns:
            if pattern not in self.CALL_TYPE_MAPPING[categoria]:
                self.CALL_TYPE_MAPPING[categoria].append(pattern.upper())
        
        logger.info(f"Aggiunto mapping personalizzato per {categoria}: {patterns}")
    
    def get_all_categories(self) -> List[str]:
        """Restituisce tutte le categorie disponibili"""
        return list(self.CALL_TYPE_MAPPING.keys()) + ['ALTRO']
    
    def get_category_patterns(self, categoria: str) -> List[str]:
        """Restituisce i pattern per una categoria"""
        return self.CALL_TYPE_MAPPING.get(categoria, [])


class CDRAnalytics:
    """
    Classe per l'analisi e elaborazione dei file CDR con calcolo prezzi VoIP
    """
    
    def __init__(self, output_directory: str = "output", voip_config: Dict[str, Any] = None):
        """
        Inizializza il processore CDR
        
        Args:
            output_directory: Directory dove salvare i report generati
            voip_config: Configurazione prezzi VoIP
        """
        self.output_directory = Path(output_directory)
        self.analytics_directory = self.output_directory / "cdr_analytics"
        self.analytics_directory.mkdir(exist_ok=True)
        
        # Tipi di chiamata supportati (verranno rilevati automaticamente)
        self.call_types = set()
        
        # Configurazione prezzi VoIP
        self.voip_config = None
        if voip_config:
            self.voip_config = VoIPPricingConfig(voip_config)
            if not self.voip_config.is_valid():
                error_msg = f"Configurazione VoIP non valida: {'; '.join(self.voip_config.get_errors())}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        else:
            logger.warning("Configurazione VoIP non fornita - verrà usato solo il costo originale")
    
    def process_cdr_file(self, json_file_path: str) -> Dict[str, Any]:
        """
        Elabora un file CDR JSON e genera i report aggregati
        
        Args:
            json_file_path: Percorso del file JSON CDR da elaborare
            
        Returns:
            Dict con informazioni sui file generati e statistiche
        """
        try:
            logger.info(f"🔍 Inizio elaborazione file CDR: {json_file_path}")
            
            # Carica dati JSON
            cdr_data = self._load_cdr_data(json_file_path)
            if not cdr_data:
                return {'success': False, 'message': 'Impossibile caricare dati CDR'}
            
            # Estrai metadati e record
            metadata = cdr_data.get('metadata', {})
            records = cdr_data.get('records', [])
            
            if not records:
                logger.warning("Nessun record trovato nel file CDR")
                return {'success': False, 'message': 'Nessun record trovato'}
            
            logger.info(f"📊 Trovati {len(records)} record CDR")
            
            # ✅ NUOVA FUNZIONALITÀ: Ricalcolo prezzi con configurazione VoIP
            if self.voip_config:
                logger.info("💰 Ricalcolo prezzi con configurazione VoIP")
                records = self._recalculate_costs(records)
            else:
                logger.warning("⚠️ Configurazione VoIP mancante - mantengo prezzi originali")
            
            # Raggruppa per codice_contratto
            grouped_data = self._group_by_contract(records)
            
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
            
            # Genera report riassuntivo generale
            summary_file = self._generate_summary_report(grouped_data, metadata)
            if summary_file:
                generated_files.append(summary_file)
            
            result = {
                'success': True,
                'message': f'Elaborazione completata: {len(generated_files)} file generati',
                'source_file': json_file_path,
                'total_records': len(records),
                'total_contracts': total_contracts,
                'generated_files': generated_files,
                'call_types_found': list(self.call_types),
                'voip_pricing_enabled': self.voip_config is not None,
                'processing_timestamp': datetime.now().isoformat()
            }
            
            # Aggiungi info configurazione VoIP se disponibile
            if self.voip_config:
                result['voip_config_summary'] = {
                    'currency': self.voip_config.config.get('voip_currency'),
                    'unit': self.voip_config.config.get('voip_price_unit'),
                    'categories': self.voip_config.get_all_categories()
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
        
    def _recalculate_costs(self, records: List[Dict]) -> List[Dict]:
        """
        Ricalcola i costi dei record CDR usando la configurazione VoIP
        
        Args:
            records: Lista record CDR originali
            
        Returns:
            Lista record CDR con costi ricalcolati
        """
        updated_records = []
        pricing_stats = defaultdict(int)
        
        for record in records:
            try:
                # Mantieni record originale
                updated_record = record.copy()
                
                # Estrai dati necessari
                tipo_chiamata = record.get('tipo_chiamata', '')
                durata_secondi = int(record.get('durata_secondi', 0))
                costo_originale = float(record.get('costo_euro', 0.0))
                
                # Calcola nuovo costo
                calcolo = self.voip_config.calculate_cost(tipo_chiamata, durata_secondi)
                
                # Aggiungi nuovi campi mantenendo compatibilità
                updated_record['costo_cliente_euro'] = calcolo['costo_cliente_euro']
                updated_record['categoria_chiamata'] = calcolo['categoria']
                updated_record['prezzo_unitario_config'] = calcolo['prezzo_unitario']
                updated_record['durata_fatturata'] = calcolo['durata_fatturata']
                updated_record['unita_fatturazione'] = calcolo['unita_fatturazione']
                updated_record['valuta_config'] = calcolo['valuta']
                
                # Mantieni costo originale per confronto
                updated_record['costo_euro_originale'] = costo_originale
                
                # Statistiche
                pricing_stats[calcolo['categoria']] += 1
                
                updated_records.append(updated_record)
                
            except Exception as e:
                logger.error(f"Errore ricalcolo costo per record: {e}")
                # In caso di errore, mantieni record originale
                updated_records.append(record)
        
        logger.info(f"💰 Ricalcolo prezzi completato:")
        for categoria, count in pricing_stats.items():
            prezzo = self.voip_config.get_price_for_category(categoria)
            logger.info(f"   {categoria}: {count} chiamate @ {prezzo} {self.voip_config.config.get('voip_currency', 'EUR')}")
        
        return updated_records
    
    def _load_cdr_data(self, json_file_path: str) -> Optional[Dict]:
        """Carica dati dal file JSON CDR"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Errore caricamento file {json_file_path}: {e}")
            return None
    
    def _group_by_contract(self, records: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Raggruppa i record per codice_contratto
        
        Args:
            records: Lista dei record CDR
            
        Returns:
            Dict con chiave codice_contratto e valore lista record
        """
        grouped = defaultdict(list)
        
        for record in records:
            contract_code = record.get('codice_contratto')
            if contract_code is not None:
                # Converti in stringa per consistenza
                contract_key = str(contract_code)
                grouped[contract_key].append(record)
                
                # Traccia tipi di chiamata trovati
                call_type = record.get('tipo_chiamata', '').upper()
                if call_type:
                    self.call_types.add(call_type)
        
        logger.info(f"📋 Contratti raggruppati: {len(grouped)}")
        logger.info(f"📞 Tipi chiamata trovati: {sorted(self.call_types)}")
        
        return dict(grouped)
    
    def _aggregate_contract_data(self, records: List[Dict]) -> Dict[str, Any]:
        """
        Aggrega i dati per un singolo contratto
        
        Args:
            records: Lista record per un contratto
            
        Returns:
            Dict con dati aggregati
        """
        # Inizializza strutture per aggregazione
        durata_per_tipo = defaultdict(int)  # durata_secondi per tipo_chiamata
        costo_per_tipo = defaultdict(float)  # costo_euro per tipo_chiamata
        costo_cliente_per_tipo = defaultdict(float)  # ✅ NUOVO: costo_cliente_euro per tipo
        categoria_per_tipo = defaultdict(int)  # ✅ NUOVO: conteggio per categoria
        
        # Informazioni contratto (dal primo record)
        first_record = records[0] if records else {}
        contract_info = {
            'codice_contratto': first_record.get('codice_contratto', ''),
            'cliente_finale_comune': first_record.get('cliente_finale_comune', ''),
        }
        
        # Aggrega dati per tipo di chiamata
        total_duration = 0
        total_cost = 0.0
        total_cost_cliente = 0.0  # ✅ NUOVO
        total_calls = len(records)
        
        for record in records:
            tipo_chiamata = record.get('tipo_chiamata', '').upper()
            durata = int(record.get('durata_secondi', 0))
            costo_originale = float(record.get('costo_euro', 0.0))
            costo_cliente = float(record.get('costo_cliente_euro', costo_originale))  # ✅ NUOVO
            categoria = record.get('categoria_chiamata', 'ALTRO')  # ✅ NUOVO
            
            # Accumula per tipo
            durata_per_tipo[tipo_chiamata] += durata
            costo_per_tipo[tipo_chiamata] += costo_originale
            costo_cliente_per_tipo[tipo_chiamata] += costo_cliente  # ✅ NUOVO
            
            # Accumula per categoria  # ✅ NUOVO
            categoria_per_tipo[categoria] += 1
            
            # Accumula totali
            total_duration += durata
            total_cost += costo_originale
            total_cost_cliente += costo_cliente  # ✅ NUOVO
        
        # Costruisci risultato
        result = {
            **contract_info,
            'totale_chiamate': total_calls,
            'durata_totale_secondi': total_duration,
            'durata_totale_minuti': round(total_duration / 60, 2),
            'durata_totale_ore': round(total_duration / 3600, 2),
            'costo_totale_euro': round(total_cost, 4),
            'costo_cliente_totale_euro': round(total_cost_cliente, 4),  # ✅ NUOVO
        }
        
        # ✅ NUOVO: Aggiungi breakdown per categoria
        if self.voip_config:
            result['categoria_breakdown'] = {}
            for categoria, count in categoria_per_tipo.items():
                # Calcola totali per categoria
                categoria_records = [r for r in records if r.get('categoria_chiamata') == categoria]
                categoria_durata = sum(int(r.get('durata_secondi', 0)) for r in categoria_records)
                categoria_costo_cliente = sum(float(r.get('costo_cliente_euro', 0)) for r in categoria_records)
                
                result['categoria_breakdown'][categoria] = {
                    'chiamate': count,
                    'durata_secondi': categoria_durata,
                    'durata_minuti': round(categoria_durata / 60, 2),
                    'costo_cliente_euro': round(categoria_costo_cliente, 4),
                    'prezzo_medio_minuto': round(categoria_costo_cliente / (categoria_durata / 60), 4) if categoria_durata > 0 else 0
                }
        
        # Aggiungi dati per tipo di chiamata (mantieni compatibilità)
        for call_type in sorted(self.call_types):
            if call_type:  # Skip tipi vuoti
                # Normalizza nome per campo JSON
                safe_type = self._normalize_field_name(call_type)
                
                result[f'durata_secondi_{safe_type}'] = durata_per_tipo.get(call_type, 0)
                result[f'durata_minuti_{safe_type}'] = round(durata_per_tipo.get(call_type, 0) / 60, 2)
                result[f'costo_euro_{safe_type}'] = round(costo_per_tipo.get(call_type, 0.0), 4)
                result[f'costo_cliente_euro_{safe_type}'] = round(costo_cliente_per_tipo.get(call_type, 0.0), 4)  # ✅ NUOVO
                result[f'chiamate_{safe_type}'] = sum(1 for r in records if r.get('tipo_chiamata', '').upper() == call_type)
        
        return result
    
    def _normalize_field_name(self, name: str) -> str:
        """
        Normalizza un nome per uso come campo JSON
        
        Args:
            name: Nome da normalizzare
            
        Returns:
            Nome normalizzato (lowercase, underscore)
        """
        return name.lower().replace(' ', '_').replace('-', '_').replace('à', 'a').replace('è', 'e').replace('ì', 'i').replace('ò', 'o').replace('ù', 'u')
    
    def _generate_contract_report(self, contract_code: str, records: List[Dict], metadata: Dict) -> Optional[str]:
        """
        Genera report per un singolo contratto
        
        Args:
            contract_code: Codice del contratto
            records: Record del contratto
            metadata: Metadati del file sorgente
            
        Returns:
            Percorso del file generato o None se errore
        """
        try:
            # Aggrega dati
            aggregated_data = self._aggregate_contract_data(records)
            
            # Crea timestamp per filename
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            current_month = now.strftime("%m")
            
            # Nome file: codice_contratto_mese_data_ora
            filename = f"{contract_code}_{current_month}_{timestamp}.json"
            filepath = self.analytics_directory / filename
            
            # Crea report completo
            report = {
                'metadata': {
                    'contract_code': contract_code,
                    'generation_timestamp': now.isoformat(),
                    'source_file': metadata.get('source_file', ''),
                    'source_total_records': metadata.get('total_records', 0),
                    'contract_records': len(records),
                    'month': current_month,
                    'year': now.year,
                    'voip_pricing_enabled': self.voip_config is not None  # ✅ NUOVO
                },
                'summary': aggregated_data,
                'call_types_breakdown': self._get_call_types_breakdown(records),
                'daily_breakdown': self._get_daily_breakdown(records),
                'raw_records': records  # Include record originali per riferimento
            }
            
            # ✅ NUOVO: Aggiungi informazioni configurazione VoIP se disponibile
            if self.voip_config:
                report['voip_config'] = {
                    'currency': self.voip_config.config.get('voip_currency'),
                    'price_unit': self.voip_config.config.get('voip_price_unit'),
                    'price_fixed_final': self.voip_config.config.get('voip_price_fixed_final'),
                    'price_mobile_final': self.voip_config.config.get('voip_price_mobile_final'),
                    'categories_mapping': {cat: self.voip_config.get_price_for_category(cat) 
                                         for cat in self.voip_config.get_all_categories()}
                }
            
            # Salva file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Errore generazione report contratto {contract_code}: {e}")
            return None    
    
    def _get_call_types_breakdown(self, records: List[Dict]) -> Dict[str, Dict]:
        """Genera breakdown dettagliato per tipo di chiamata con prezzi VoIP"""
        breakdown = {}
        
        for call_type in self.call_types:
            if not call_type:
                continue
                
            type_records = [r for r in records if r.get('tipo_chiamata', '').upper() == call_type]
            
            if type_records:
                total_duration = sum(int(r.get('durata_secondi', 0)) for r in type_records)
                total_cost = sum(float(r.get('costo_euro', 0.0)) for r in type_records)
                total_cost_cliente = sum(float(r.get('costo_cliente_euro', 0.0)) for r in type_records)  # ✅ NUOVO
                
                # ✅ NUOVO: Categoria e prezzo VoIP
                categoria = 'ALTRO'
                prezzo_voip = 0
                if self.voip_config and type_records:
                    categoria = type_records[0].get('categoria_chiamata', 'ALTRO')
                    prezzo_voip = self.voip_config.get_price_for_category(categoria)
                
                breakdown[call_type] = {
                    'numero_chiamate': len(type_records),
                    'durata_totale_secondi': total_duration,
                    'durata_media_secondi': round(total_duration / len(type_records), 2) if type_records else 0,
                    'costo_totale_euro': round(total_cost, 4),
                    'costo_medio_euro': round(total_cost / len(type_records), 4) if type_records else 0,
                    'costo_al_minuto': round((total_cost / (total_duration / 60)), 4) if total_duration > 0 else 0,
                    # ✅ NUOVI CAMPI
                    'costo_cliente_totale_euro': round(total_cost_cliente, 4),
                    'costo_cliente_medio_euro': round(total_cost_cliente / len(type_records), 4) if type_records else 0,
                    'costo_cliente_al_minuto': round((total_cost_cliente / (total_duration / 60)), 4) if total_duration > 0 else 0,
                    'categoria_voip': categoria,
                    'prezzo_voip_configurato': prezzo_voip,
                    'differenza_costo_euro': round(total_cost_cliente - total_cost, 4),
                    'valuta': self.voip_config.config.get('voip_currency', 'EUR') if self.voip_config else 'EUR'
                }
        
        return breakdown
    
    def _get_daily_breakdown(self, records: List[Dict]) -> Dict[str, Dict]:
        """Genera breakdown giornaliero con costi VoIP"""
        daily_data = defaultdict(lambda: {
            'chiamate': 0,
            'durata_secondi': 0,
            'costo_euro': 0.0,
            'costo_cliente_euro': 0.0  # ✅ NUOVO
        })
        
        for record in records:
            date_str = record.get('data_ora_chiamata', '')
            if date_str:
                # Estrai solo la data (primi 10 caratteri: YYYY-MM-DD)
                date_key = date_str[:10] if len(date_str) >= 10 else date_str
                
                daily_data[date_key]['chiamate'] += 1
                daily_data[date_key]['durata_secondi'] += int(record.get('durata_secondi', 0))
                daily_data[date_key]['costo_euro'] += float(record.get('costo_euro', 0.0))
                daily_data[date_key]['costo_cliente_euro'] += float(record.get('costo_cliente_euro', 0.0))  # ✅ NUOVO
        
        # Arrotonda i costi
        for day in daily_data:
            daily_data[day]['costo_euro'] = round(daily_data[day]['costo_euro'], 4)
            daily_data[day]['costo_cliente_euro'] = round(daily_data[day]['costo_cliente_euro'], 4)  # ✅ NUOVO
            daily_data[day]['durata_minuti'] = round(daily_data[day]['durata_secondi'] / 60, 2)
            daily_data[day]['differenza_costo'] = round(daily_data[day]['costo_cliente_euro'] - daily_data[day]['costo_euro'], 4)  # ✅ NUOVO
        
        return dict(daily_data)
    
    def _generate_summary_report(self, grouped_data: Dict, metadata: Dict) -> Optional[str]:
        """
        Genera report riassuntivo generale con prezzi VoIP
        
        Args:
            grouped_data: Dati raggruppati per contratto
            metadata: Metadati file sorgente
            
        Returns:
            Percorso del file generato o None se errore
        """
        try:
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            current_month = now.strftime("%m")
            
            filename = f"SUMMARY_{current_month}_{timestamp}.json"
            filepath = self.analytics_directory / filename
            
            # Aggrega dati globali
            contracts_summary = {}
            global_totals = {
                'total_contracts': len(grouped_data),
                'total_calls': 0,
                'total_duration_seconds': 0,
                'total_cost_euro': 0.0,
                'total_cost_cliente_euro': 0.0  # ✅ NUOVO
            }
            
            # Totali per tipo di chiamata (globali)
            global_by_type = defaultdict(lambda: {
                'calls': 0,
                'duration_seconds': 0,
                'cost_euro': 0.0,
                'cost_cliente_euro': 0.0  # ✅ NUOVO
            })
            
            # ✅ NUOVO: Totali per categoria VoIP
            global_by_category = defaultdict(lambda: {
                'calls': 0,
                'duration_seconds': 0,
                'cost_cliente_euro': 0.0,
                'prezzo_configurato': 0.0
            })
            
            for contract_code, records in grouped_data.items():
                # Aggrega per contratto
                contract_summary = self._aggregate_contract_data(records)
                contracts_summary[contract_code] = contract_summary
                
                # Aggrega globali
                global_totals['total_calls'] += len(records)
                global_totals['total_duration_seconds'] += sum(int(r.get('durata_secondi', 0)) for r in records)
                global_totals['total_cost_euro'] += sum(float(r.get('costo_euro', 0.0)) for r in records)
                global_totals['total_cost_cliente_euro'] += sum(float(r.get('costo_cliente_euro', 0.0)) for r in records)  # ✅ NUOVO
                
                # Aggrega per tipo
                for record in records:
                    call_type = record.get('tipo_chiamata', '').upper()
                    if call_type:
                        global_by_type[call_type]['calls'] += 1
                        global_by_type[call_type]['duration_seconds'] += int(record.get('durata_secondi', 0))
                        global_by_type[call_type]['cost_euro'] += float(record.get('costo_euro', 0.0))
                        global_by_type[call_type]['cost_cliente_euro'] += float(record.get('costo_cliente_euro', 0.0))  # ✅ NUOVO
                    
                    # ✅ NUOVO: Aggrega per categoria VoIP
                    categoria = record.get('categoria_chiamata', 'ALTRO')
                    global_by_category[categoria]['calls'] += 1
                    global_by_category[categoria]['duration_seconds'] += int(record.get('durata_secondi', 0))
                    global_by_category[categoria]['cost_cliente_euro'] += float(record.get('costo_cliente_euro', 0.0))
                    if self.voip_config:
                        global_by_category[categoria]['prezzo_configurato'] = self.voip_config.get_price_for_category(categoria)
            
            # Arrotonda totali globali
            global_totals['total_cost_euro'] = round(global_totals['total_cost_euro'], 4)
            global_totals['total_cost_cliente_euro'] = round(global_totals['total_cost_cliente_euro'], 4)  # ✅ NUOVO
            global_totals['total_duration_minutes'] = round(global_totals['total_duration_seconds'] / 60, 2)
            global_totals['total_duration_hours'] = round(global_totals['total_duration_seconds'] / 3600, 2)
            global_totals['differenza_costo_totale'] = round(global_totals['total_cost_cliente_euro'] - global_totals['total_cost_euro'], 4)  # ✅ NUOVO
            
            # Arrotonda totali per tipo
            for call_type in global_by_type:
                global_by_type[call_type]['cost_euro'] = round(global_by_type[call_type]['cost_euro'], 4)
                global_by_type[call_type]['cost_cliente_euro'] = round(global_by_type[call_type]['cost_cliente_euro'], 4)  # ✅ NUOVO
                global_by_type[call_type]['duration_minutes'] = round(global_by_type[call_type]['duration_seconds'] / 60, 2)
                global_by_type[call_type]['differenza_costo'] = round(global_by_type[call_type]['cost_cliente_euro'] - global_by_type[call_type]['cost_euro'], 4)  # ✅ NUOVO
            
            # ✅ NUOVO: Arrotonda totali per categoria
            for categoria in global_by_category:
                global_by_category[categoria]['cost_cliente_euro'] = round(global_by_category[categoria]['cost_cliente_euro'], 4)
                global_by_category[categoria]['duration_minutes'] = round(global_by_category[categoria]['duration_seconds'] / 60, 2)
            
            # Crea report summary
            summary_report = {
                'metadata': {
                    'generation_timestamp': now.isoformat(),
                    'source_file': metadata.get('source_file', ''),
                    'source_total_records': metadata.get('total_records', 0),
                    'month': current_month,
                    'year': now.year,
                    'call_types_found': sorted(list(self.call_types)),
                    'voip_pricing_enabled': self.voip_config is not None  # ✅ NUOVO
                },
                'global_totals': global_totals,
                'global_by_call_type': dict(global_by_type),
                'global_by_category': dict(global_by_category),  # ✅ NUOVO
                'contracts_summary': contracts_summary,
                'top_contracts': self._get_top_contracts(contracts_summary)
            }
            
            # ✅ NUOVO: Aggiungi configurazione VoIP al summary
            if self.voip_config:
                summary_report['voip_configuration'] = {
                    'currency': self.voip_config.config.get('voip_currency'),
                    'price_unit': self.voip_config.config.get('voip_price_unit'),
                    'price_fixed_final': self.voip_config.config.get('voip_price_fixed_final'),
                    'price_mobile_final': self.voip_config.config.get('voip_price_mobile_final'),
                    'categories_pricing': {cat: self.voip_config.get_price_for_category(cat) 
                                         for cat in self.voip_config.get_all_categories()},
                    'call_type_mapping': self.voip_config.CALL_TYPE_MAPPING
                }
            
            # Salva file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📊 Report summary generato: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Errore generazione summary report: {e}")
            return None
    
    def _get_top_contracts(self, contracts_summary: Dict) -> Dict:
        """Genera top contratti per varie metriche incluso costo cliente"""
        try:
            contracts_list = []
            
            for contract_code, data in contracts_summary.items():
                contracts_list.append({
                    'codice_contratto': contract_code,
                    'cliente_finale_comune': data.get('cliente_finale_comune', ''),
                    'totale_chiamate': data.get('totale_chiamate', 0),
                    'durata_totale_secondi': data.get('durata_totale_secondi', 0),
                    'costo_totale_euro': data.get('costo_totale_euro', 0.0),
                    'costo_cliente_totale_euro': data.get('costo_cliente_totale_euro', 0.0)  # ✅ NUOVO
                })
            
            return {
                'top_by_calls': sorted(contracts_list, key=lambda x: x['totale_chiamate'], reverse=True)[:10],
                'top_by_duration': sorted(contracts_list, key=lambda x: x['durata_totale_secondi'], reverse=True)[:10],
                'top_by_cost': sorted(contracts_list, key=lambda x: x['costo_totale_euro'], reverse=True)[:10],
                'top_by_cost_cliente': sorted(contracts_list, key=lambda x: x['costo_cliente_totale_euro'], reverse=True)[:10]  # ✅ NUOVO
            }
        except Exception as e:
            logger.error(f"Errore calcolo top contracts: {e}")
            return {}
    
    def list_generated_reports(self) -> List[Dict]:
        """
        Lista tutti i report generati nella directory analytics
        
        Returns:
            Lista di dict con informazioni sui file
        """
        reports = []
        
        try:
            for file_path in self.analytics_directory.glob("*.json"):
                stat = file_path.stat()
                reports.append({
                    'filename': file_path.name,
                    'filepath': str(file_path),
                    'size_bytes': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'is_summary': file_path.name.startswith('SUMMARY_')
                })
            
            # Ordina per data di creazione (più recenti prima)
            reports.sort(key=lambda x: x['created'], reverse=True)
            
        except Exception as e:
            logger.error(f"Errore listing report: {e}")
        
        return reports
    
    def add_custom_call_type_mapping(self, categoria: str, patterns: List[str]):
        """
        Aggiunge mapping personalizzato per tipologie di chiamata
        
        Args:
            categoria: Nome categoria (es. 'SMS', 'VIDEOCHIAMATE', 'SERVIZI_PREMIUM')
            patterns: Lista pattern da riconoscere
        """
        if not self.voip_config:
            logger.warning("Configurazione VoIP non disponibile per aggiungere mapping personalizzato")
            return False
        
        self.voip_config.add_custom_mapping(categoria, patterns)
        logger.info(f"✅ Aggiunto mapping personalizzato: {categoria} -> {patterns}")
        return True
    
    def get_voip_categories_info(self) -> Dict[str, Any]:
        """
        Restituisce informazioni sulle categorie VoIP configurate
        
        Returns:
            Dict con info categorie e prezzi
        """
        if not self.voip_config:
            return {'error': 'Configurazione VoIP non disponibile'}
        
        return {
            'categories': self.voip_config.get_all_categories(),
            'mapping': self.voip_config.CALL_TYPE_MAPPING,
            'pricing': {cat: self.voip_config.get_price_for_category(cat) 
                       for cat in self.voip_config.get_all_categories()},
            'config': {
                'currency': self.voip_config.config.get('voip_currency'),
                'unit': self.voip_config.config.get('voip_price_unit'),
                'fixed_price': self.voip_config.config.get('voip_price_fixed_final'),
                'mobile_price': self.voip_config.config.get('voip_price_mobile_final')
            }
        }


# ========== FUNZIONI DI INTEGRAZIONE ==========

def integrate_cdr_analytics_into_processor(processor_instance):
    """
    Integra CDR Analytics nel FTPProcessor esistente con supporto VoIP
    
    Args:
        processor_instance: Istanza di FTPProcessor da estendere
    """
    
    # Aggiungi istanza CDR Analytics al processore con configurazione VoIP
    voip_config = processor_instance.config
    processor_instance.cdr_analytics = CDRAnalytics(
        processor_instance.config['output_directory'],
        voip_config=voip_config
    )
    
    def enhanced_process_files(self):
        """
        Versione potenziata del process_files che include analisi CDR con prezzi VoIP
        """
        try:
            logger.info("🚀 Inizio processo elaborazione file con analisi CDR e prezzi VoIP")
            
            # Esegui processo originale
            result = self._original_process_files()
            
            if result.get('success') and result.get('converted_files'):
                logger.info("📊 Inizio analisi CDR dei file convertiti")
                
                # Analizza ogni file JSON convertito
                cdr_results = []
                
                for json_file in result['converted_files']:
                    # Controlla se è un file CDR (basandosi sul nome o contenuto)
                    if self._is_cdr_file(json_file):
                        logger.info(f"🔍 Analisi CDR con prezzi VoIP per file: {json_file}")
                        
                        cdr_result = self.cdr_analytics.process_cdr_file(json_file)
                        cdr_results.append(cdr_result)
                        
                        if cdr_result.get('success'):
                            logger.info(f"✅ Analisi CDR completata: {len(cdr_result.get('generated_files', []))} report generati")
                            if cdr_result.get('voip_pricing_enabled'):
                                logger.info("💰 Prezzi VoIP applicati con successo")
                        else:
                            logger.warning(f"⚠️ Analisi CDR fallita per {json_file}: {cdr_result.get('message')}")
                
                # Aggiungi risultati CDR al risultato principale
                if cdr_results:
                    result['cdr_analytics'] = {
                        'processed_files': len(cdr_results),
                        'successful_analyses': sum(1 for r in cdr_results if r.get('success')),
                        'total_reports_generated': sum(len(r.get('generated_files', [])) for r in cdr_results),
                        'voip_pricing_enabled': any(r.get('voip_pricing_enabled') for r in cdr_results),
                        'results': cdr_results
                    }
                    
                    logger.info(f"📈 Analisi CDR completata: {result['cdr_analytics']['total_reports_generated']} report totali generati")
                    if result['cdr_analytics']['voip_pricing_enabled']:
                        logger.info("💰 Prezzi VoIP applicati a tutti i report")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Errore nel processo CDR integrato: {e}")
            # Ritorna risultato originale anche in caso di errore CDR
            return getattr(self, '_original_process_files', lambda: {'success': False, 'message': str(e)})()
    
    def _is_cdr_file(self, json_file_path):
        """
        Determina se un file JSON è un file CDR
        
        Args:
            json_file_path: Percorso del file JSON
            
        Returns:
            True se è un file CDR
        """
        try:
            # Controlla il nome del file
            filename = Path(json_file_path).name.upper()
            if 'CDR' in filename or 'RIV' in filename:
                return True
            
            # Controlla il contenuto (primi record)
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Controlla metadati
            metadata = data.get('metadata', {})
            if metadata.get('file_type') == 'CDR':
                return True
            
            # Controlla struttura record
            records = data.get('records', [])
            if records and len(records) > 0:
                first_record = records[0]
                # Cerca campi tipici CDR
                cdr_fields = ['data_ora_chiamata', 'numero_chiamante', 'numero_chiamato', 
                             'durata_secondi', 'tipo_chiamata', 'costo_euro', 'codice_contratto']
                
                matching_fields = sum(1 for field in cdr_fields if field in first_record)
                return matching_fields >= 5  # Se almeno 5 campi corrispondono
            
            return False
            
        except Exception as e:
            logger.error(f"Errore verifica file CDR {json_file_path}: {e}")
            return False
    
    # Salva metodo originale e sostituisci
    processor_instance._original_process_files = processor_instance.process_files
    processor_instance.process_files = enhanced_process_files.__get__(processor_instance, type(processor_instance))
    processor_instance._is_cdr_file = _is_cdr_file.__get__(processor_instance, type(processor_instance))
    
    logger.info("🔧 CDR Analytics con supporto prezzi VoIP integrato nel FTPProcessor")


# Funzione per uso standalone
def process_cdr_standalone(json_file_path: str, output_directory: str = "output", voip_config: Dict = None) -> Dict:
    """
    Elabora un file CDR in modalità standalone con supporto VoIP
    
    Args:
        json_file_path: Percorso del file JSON CDR
        output_directory: Directory di output per i report
        voip_config: Configurazione prezzi VoIP
        
    Returns:
        Dict con risultati elaborazione
    """
    analytics = CDRAnalytics(output_directory, voip_config=voip_config)
    return analytics.process_cdr_file(json_file_path)


if __name__ == "__main__":
    # Test standalone con file di esempio
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"🧪 Test elaborazione CDR: {file_path}")
        
        # Configurazione VoIP di esempio per test
        test_voip_config = {
            'voip_price_fixed_final': 0.02,
            'voip_price_mobile_final': 0.15,
            'voip_currency': 'EUR',
            'voip_price_unit': 'per_minute'
        }
        
        result = process_cdr_standalone(file_path, voip_config=test_voip_config)
        
        if result['success']:
            print(f"✅ Elaborazione completata!")
            print(f"📊 Contratti elaborati: {result['total_contracts']}")
            print(f"📁 File generati: {len(result['generated_files'])}")
            print(f"📞 Tipi chiamata: {', '.join(result['call_types_found'])}")
            print(f"💰 Prezzi VoIP: {result.get('voip_pricing_enabled', False)}")
            
            for file_path in result['generated_files']:
                print(f"   📄 {file_path}")
        else:
            print(f"❌ Errore: {result['message']}")
    else:
        print("Uso: python cdr_analytics.py <file_cdr.json>")
        print("Esempio: python cdr_analytics.py output/RIV_12345_MESE_05_2024-06-05-14.16.27.json")