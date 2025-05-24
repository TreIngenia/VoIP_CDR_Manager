#!/usr/bin/env python3
"""
CDR Analytics Module - Elaborazione e analisi file CDR
Modulo per analizzare file CDR (Call Detail Record) e generare report aggregati
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class CDRAnalytics:
    """
    Classe per l'analisi e elaborazione dei file CDR
    """
    
    def __init__(self, output_directory: str = "output"):
        """
        Inizializza il processore CDR
        
        Args:
            output_directory: Directory dove salvare i report generati
        """
        self.output_directory = Path(output_directory)
        self.analytics_directory = self.output_directory / "cdr_analytics"
        self.analytics_directory.mkdir(exist_ok=True)
        
        # Tipi di chiamata supportati (verranno rilevati automaticamente)
        self.call_types = set()
        
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
        
        # Informazioni contratto (dal primo record)
        first_record = records[0] if records else {}
        contract_info = {
            'codice_contratto': first_record.get('codice_contratto', ''),
            'cliente_finale_comune': first_record.get('cliente_finale_comune', ''),
        }
        
        # Aggrega dati per tipo di chiamata
        total_duration = 0
        total_cost = 0.0
        total_calls = len(records)
        
        for record in records:
            tipo_chiamata = record.get('tipo_chiamata', '').upper()
            durata = int(record.get('durata_secondi', 0))
            costo = float(record.get('costo_euro', 0.0))
            
            # Accumula per tipo
            durata_per_tipo[tipo_chiamata] += durata
            costo_per_tipo[tipo_chiamata] += costo
            
            # Accumula totali
            total_duration += durata
            total_cost += costo
        
        # Costruisci risultato
        result = {
            **contract_info,
            'totale_chiamate': total_calls,
            'durata_totale_secondi': total_duration,
            'durata_totale_minuti': round(total_duration / 60, 2),
            'durata_totale_ore': round(total_duration / 3600, 2),
            'costo_totale_euro': round(total_cost, 4),
        }
        
        # Aggiungi dati per tipo di chiamata
        for call_type in sorted(self.call_types):
            if call_type:  # Skip tipi vuoti
                # Normalizza nome per campo JSON
                safe_type = self._normalize_field_name(call_type)
                
                result[f'durata_secondi_{safe_type}'] = durata_per_tipo.get(call_type, 0)
                result[f'durata_minuti_{safe_type}'] = round(durata_per_tipo.get(call_type, 0) / 60, 2)
                result[f'costo_euro_{safe_type}'] = round(costo_per_tipo.get(call_type, 0.0), 4)
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
        return name.lower().replace(' ', '_').replace('-', '_')
    
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
                    'year': now.year
                },
                'summary': aggregated_data,
                'call_types_breakdown': self._get_call_types_breakdown(records),
                'daily_breakdown': self._get_daily_breakdown(records),
                'raw_records': records  # Include record originali per riferimento
            }
            
            # Salva file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Errore generazione report contratto {contract_code}: {e}")
            return None
    
    def _get_call_types_breakdown(self, records: List[Dict]) -> Dict[str, Dict]:
        """Genera breakdown dettagliato per tipo di chiamata"""
        breakdown = {}
        
        for call_type in self.call_types:
            if not call_type:
                continue
                
            type_records = [r for r in records if r.get('tipo_chiamata', '').upper() == call_type]
            
            if type_records:
                total_duration = sum(int(r.get('durata_secondi', 0)) for r in type_records)
                total_cost = sum(float(r.get('costo_euro', 0.0)) for r in type_records)
                
                breakdown[call_type] = {
                    'numero_chiamate': len(type_records),
                    'durata_totale_secondi': total_duration,
                    'durata_media_secondi': round(total_duration / len(type_records), 2) if type_records else 0,
                    'costo_totale_euro': round(total_cost, 4),
                    'costo_medio_euro': round(total_cost / len(type_records), 4) if type_records else 0,
                    'costo_al_minuto': round((total_cost / (total_duration / 60)), 4) if total_duration > 0 else 0
                }
        
        return breakdown
    
    def _get_daily_breakdown(self, records: List[Dict]) -> Dict[str, Dict]:
        """Genera breakdown giornaliero"""
        daily_data = defaultdict(lambda: {
            'chiamate': 0,
            'durata_secondi': 0,
            'costo_euro': 0.0
        })
        
        for record in records:
            date_str = record.get('data_ora_chiamata', '')
            if date_str:
                # Estrai solo la data (primi 10 caratteri: YYYY-MM-DD)
                date_key = date_str[:10] if len(date_str) >= 10 else date_str
                
                daily_data[date_key]['chiamate'] += 1
                daily_data[date_key]['durata_secondi'] += int(record.get('durata_secondi', 0))
                daily_data[date_key]['costo_euro'] += float(record.get('costo_euro', 0.0))
        
        # Arrotonda i costi
        for day in daily_data:
            daily_data[day]['costo_euro'] = round(daily_data[day]['costo_euro'], 4)
            daily_data[day]['durata_minuti'] = round(daily_data[day]['durata_secondi'] / 60, 2)
        
        return dict(daily_data)
    
    def _generate_summary_report(self, grouped_data: Dict, metadata: Dict) -> Optional[str]:
        """
        Genera report riassuntivo generale
        
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
                'total_cost_euro': 0.0
            }
            
            # Totali per tipo di chiamata (globali)
            global_by_type = defaultdict(lambda: {
                'calls': 0,
                'duration_seconds': 0,
                'cost_euro': 0.0
            })
            
            for contract_code, records in grouped_data.items():
                # Aggrega per contratto
                contract_summary = self._aggregate_contract_data(records)
                contracts_summary[contract_code] = contract_summary
                
                # Aggrega globali
                global_totals['total_calls'] += len(records)
                global_totals['total_duration_seconds'] += sum(int(r.get('durata_secondi', 0)) for r in records)
                global_totals['total_cost_euro'] += sum(float(r.get('costo_euro', 0.0)) for r in records)
                
                # Aggrega per tipo
                for record in records:
                    call_type = record.get('tipo_chiamata', '').upper()
                    if call_type:
                        global_by_type[call_type]['calls'] += 1
                        global_by_type[call_type]['duration_seconds'] += int(record.get('durata_secondi', 0))
                        global_by_type[call_type]['cost_euro'] += float(record.get('costo_euro', 0.0))
            
            # Arrotonda totali globali
            global_totals['total_cost_euro'] = round(global_totals['total_cost_euro'], 4)
            global_totals['total_duration_minutes'] = round(global_totals['total_duration_seconds'] / 60, 2)
            global_totals['total_duration_hours'] = round(global_totals['total_duration_seconds'] / 3600, 2)
            
            # Arrotonda totali per tipo
            for call_type in global_by_type:
                global_by_type[call_type]['cost_euro'] = round(global_by_type[call_type]['cost_euro'], 4)
                global_by_type[call_type]['duration_minutes'] = round(global_by_type[call_type]['duration_seconds'] / 60, 2)
            
            # Crea report summary
            summary_report = {
                'metadata': {
                    'generation_timestamp': now.isoformat(),
                    'source_file': metadata.get('source_file', ''),
                    'source_total_records': metadata.get('total_records', 0),
                    'month': current_month,
                    'year': now.year,
                    'call_types_found': sorted(list(self.call_types))
                },
                'global_totals': global_totals,
                'global_by_call_type': dict(global_by_type),
                'contracts_summary': contracts_summary,
                'top_contracts': self._get_top_contracts(contracts_summary)
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
        """Genera top contratti per varie metriche"""
        try:
            contracts_list = []
            
            for contract_code, data in contracts_summary.items():
                contracts_list.append({
                    'codice_contratto': contract_code,
                    'cliente_finale_comune': data.get('cliente_finale_comune', ''),
                    'totale_chiamate': data.get('totale_chiamate', 0),
                    'durata_totale_secondi': data.get('durata_totale_secondi', 0),
                    'costo_totale_euro': data.get('costo_totale_euro', 0.0)
                })
            
            return {
                'top_by_calls': sorted(contracts_list, key=lambda x: x['totale_chiamate'], reverse=True)[:10],
                'top_by_duration': sorted(contracts_list, key=lambda x: x['durata_totale_secondi'], reverse=True)[:10],
                'top_by_cost': sorted(contracts_list, key=lambda x: x['costo_totale_euro'], reverse=True)[:10]
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


def integrate_cdr_analytics_into_processor(processor_instance):
    """
    Integra CDR Analytics nel FTPProcessor esistente
    
    Args:
        processor_instance: Istanza di FTPProcessor da estendere
    """
    
    # Aggiungi istanza CDR Analytics al processore
    processor_instance.cdr_analytics = CDRAnalytics(processor_instance.config['output_directory'])
    
    def enhanced_process_files(self):
        """
        Versione potenziata del process_files che include analisi CDR
        """
        try:
            logger.info("🚀 Inizio processo elaborazione file con analisi CDR")
            
            # Esegui processo originale
            result = self._original_process_files()
            
            if result.get('success') and result.get('converted_files'):
                logger.info("📊 Inizio analisi CDR dei file convertiti")
                
                # Analizza ogni file JSON convertito
                cdr_results = []
                
                for json_file in result['converted_files']:
                    # Controlla se è un file CDR (basandosi sul nome o contenuto)
                    if self._is_cdr_file(json_file):
                        logger.info(f"🔍 Analisi CDR file: {json_file}")
                        
                        cdr_result = self.cdr_analytics.process_cdr_file(json_file)
                        cdr_results.append(cdr_result)
                        
                        if cdr_result.get('success'):
                            logger.info(f"✅ Analisi CDR completata: {len(cdr_result.get('generated_files', []))} report generati")
                        else:
                            logger.warning(f"⚠️ Analisi CDR fallita per {json_file}: {cdr_result.get('message')}")
                
                # Aggiungi risultati CDR al risultato principale
                if cdr_results:
                    result['cdr_analytics'] = {
                        'processed_files': len(cdr_results),
                        'successful_analyses': sum(1 for r in cdr_results if r.get('success')),
                        'total_reports_generated': sum(len(r.get('generated_files', [])) for r in cdr_results),
                        'results': cdr_results
                    }
                    
                    logger.info(f"📈 Analisi CDR completata: {result['cdr_analytics']['total_reports_generated']} report totali generati")
            
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
    
    logger.info("🔧 CDR Analytics integrato nel FTPProcessor")


# Funzione per uso standalone
def process_cdr_standalone(json_file_path: str, output_directory: str = "output") -> Dict:
    """
    Elabora un file CDR in modalità standalone
    
    Args:
        json_file_path: Percorso del file JSON CDR
        output_directory: Directory di output per i report
        
    Returns:
        Dict con risultati elaborazione
    """
    analytics = CDRAnalytics(output_directory)
    return analytics.process_cdr_file(json_file_path)


if __name__ == "__main__":
    # Test standalone con file di esempio
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"🧪 Test elaborazione CDR: {file_path}")
        
        result = process_cdr_standalone(file_path)
        
        if result['success']:
            print(f"✅ Elaborazione completata!")
            print(f"📊 Contratti elaborati: {result['total_contracts']}")
            print(f"📁 File generati: {len(result['generated_files'])}")
            print(f"📞 Tipi chiamata: {', '.join(result['call_types_found'])}")
            
            for file_path in result['generated_files']:
                print(f"   📄 {file_path}")
        else:
            print(f"❌ Errore: {result['message']}")
    else:
        print("Uso: python cdr_analytics.py <file_cdr.json>")
        print("Esempio: python cdr_analytics.py output/RIV_12345_MESE_05_2024-06-05-14.16.27.json")