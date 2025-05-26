#!/usr/bin/env python3
"""
CDR Integration - Integrazione del nuovo sistema di categorie CDR
Modifica il sistema esistente per utilizzare le macro categorie configurabili
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import del nuovo manager categorie
from cdr_categories import CDRCategoriesManager

logger = logging.getLogger(__name__)

class CDRAnalyticsEnhanced:
    """
    Versione potenziata di CDRAnalytics che utilizza il nuovo sistema di categorie
    """
    
    def __init__(self, output_directory: str = "output"):
        self.output_directory = Path(output_directory)
        self.analytics_directory = self.output_directory / "cdr_analytics"
        self.analytics_directory.mkdir(exist_ok=True)
        
        # Inizializza il manager delle categorie
        categories_file = self.analytics_directory / "cdr_categories.json"
        self.categories_manager = CDRCategoriesManager(str(categories_file))
        
        logger.info("CDR Analytics Enhanced inizializzato con sistema categorie configurabile")
    
    def process_cdr_file(self, json_file_path: str) -> Dict[str, Any]:
        """
        Elabora un file CDR JSON usando il nuovo sistema di categorie
        """
        try:
            logger.info(f"🔍 Elaborazione file CDR con categorie configurabili: {json_file_path}")
            
            # Carica dati CDR
            cdr_data = self._load_cdr_data(json_file_path)
            if not cdr_data:
                return {'success': False, 'message': 'Impossibile caricare dati CDR'}
            
            metadata = cdr_data.get('metadata', {})
            records = cdr_data.get('records', [])
            
            if not records:
                logger.warning("Nessun record trovato nel file CDR")
                return {'success': False, 'message': 'Nessun record trovato'}
            
            logger.info(f"📊 Trovati {len(records)} record CDR")
            
            # ✅ NUOVO: Ricalcolo prezzi con categorie configurabili
            logger.info("💰 Ricalcolo prezzi con categorie configurabili")
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
            
            logger.info(f"🎉 Elaborazione CDR completata con sistema categorie: {len(generated_files)} file generati")
            return result
            
        except Exception as e:
            logger.error(f"❌ Errore nell'elaborazione CDR: {e}")
            return {
                'success': False, 
                'message': f'Errore elaborazione: {str(e)}',
                'source_file': json_file_path
            }
    
    def _enhance_records_with_categories(self, records: List[Dict]) -> List[Dict]:
        """
        Arricchisce i record CDR con informazioni sulle categorie e costi calcolati
        """
        enhanced_records = []
        category_usage = {}
        unmatched_types = set()
        
        for record in records:
            try:
                enhanced_record = record.copy()
                
                # Estrai dati base
                tipo_chiamata = record.get('tipo_chiamata', '')
                durata_secondi = int(record.get('durata_secondi', 0))
                costo_originale = float(record.get('costo_euro', 0.0))
                
                # Calcola costo con categoria
                cost_calculation = self.categories_manager.calculate_call_cost(
                    tipo_chiamata, 
                    durata_secondi,
                    unit='per_minute'  # Usa sempre per_minute per compatibilità
                )
                
                # Aggiungi informazioni categoria al record
                enhanced_record.update({
                    'categoria_cliente': cost_calculation['category_name'],
                    'categoria_display': cost_calculation['category_display_name'],
                    'prezzo_categoria': cost_calculation['price_per_minute'],
                    'costo_cliente_euro': cost_calculation['cost_calculated'],
                    'durata_fatturata_minuti': cost_calculation['duration_billed'],
                    'categoria_matched': cost_calculation['matched'],
                    'costo_originale_euro': costo_originale,
                    'differenza_costo': round(cost_calculation['cost_calculated'] - costo_originale, 4),
                    'valuta_cliente': cost_calculation['currency']
                })
                
                # Statistiche utilizzo categorie
                cat_name = cost_calculation['category_name']
                if cat_name not in category_usage:
                    category_usage[cat_name] = {
                        'count': 0,
                        'total_duration': 0,
                        'total_cost': 0.0,
                        'display_name': cost_calculation['category_display_name']
                    }
                
                category_usage[cat_name]['count'] += 1
                category_usage[cat_name]['total_duration'] += durata_secondi
                category_usage[cat_name]['total_cost'] += cost_calculation['cost_calculated']
                
                # Tieni traccia dei tipi non riconosciuti
                if not cost_calculation['matched']:
                    unmatched_types.add(tipo_chiamata)
                
                enhanced_records.append(enhanced_record)
                
            except Exception as e:
                logger.error(f"Errore elaborazione record: {e}")
                # In caso di errore, mantieni record originale
                enhanced_records.append(record)
        
        # Log statistiche
        logger.info(f"💰 Elaborazione categorie completata:")
        for cat_name, stats in category_usage.items():
            avg_cost = stats['total_cost'] / (stats['total_duration'] / 60) if stats['total_duration'] > 0 else 0
            logger.info(f"   {stats['display_name']}: {stats['count']} chiamate, {avg_cost:.4f} EUR/min medio")
        
        if unmatched_types:
            logger.warning(f"⚠️ Tipi chiamata non riconosciuti: {len(unmatched_types)}")
            for unmatched in sorted(unmatched_types):
                logger.warning(f"   - '{unmatched}'")
        
        return enhanced_records
    
    def _get_category_usage_stats(self, records: List[Dict]) -> Dict[str, Any]:
        """Genera statistiche sull'utilizzo delle categorie"""
        stats = {}
        total_records = len(records)
        
        for record in records:
            cat_name = record.get('categoria_cliente', 'ALTRO')
            cat_display = record.get('categoria_display', cat_name)
            
            if cat_name not in stats:
                stats[cat_name] = {
                    'display_name': cat_display,
                    'count': 0,
                    'percentage': 0.0,
                    'total_cost': 0.0,
                    'total_duration_minutes': 0.0,
                    'matched': record.get('categoria_matched', False)
                }
            
            stats[cat_name]['count'] += 1
            stats[cat_name]['total_cost'] += record.get('costo_cliente_euro', 0.0)
            stats[cat_name]['total_duration_minutes'] += record.get('durata_fatturata_minuti', 0.0)
        
        # Calcola percentuali
        for cat_name in stats:
            stats[cat_name]['percentage'] = round((stats[cat_name]['count'] / total_records) * 100, 2)
            stats[cat_name]['avg_cost_per_minute'] = (
                stats[cat_name]['total_cost'] / stats[cat_name]['total_duration_minutes'] 
                if stats[cat_name]['total_duration_minutes'] > 0 else 0
            )
        
        return stats
    
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
        from collections import defaultdict
        
        grouped = defaultdict(list)
        
        for record in records:
            contract_code = record.get('codice_contratto')
            if contract_code is not None:
                contract_key = str(contract_code)
                grouped[contract_key].append(record)
        
        logger.info(f"📋 Contratti raggruppati: {len(grouped)}")
        return dict(grouped)
    
    def _generate_contract_report(self, contract_code: str, records: List[Dict], metadata: Dict) -> Optional[str]:
        """Genera report per contratto con dati categorie"""
        try:
            from datetime import datetime
            
            # Aggrega dati con categorie
            aggregated_data = self._aggregate_contract_data_with_categories(records)
            
            # Nome file
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            current_month = now.strftime("%m")
            filename = f"{contract_code}_{current_month}_{timestamp}.json"
            filepath = self.analytics_directory / filename
            
            # Report completo
            report = {
                'metadata': {
                    'contract_code': contract_code,
                    'generation_timestamp': now.isoformat(),
                    'source_file': metadata.get('source_file', ''),
                    'contract_records': len(records),
                    'month': current_month,
                    'year': now.year,
                    'categories_system_enabled': True
                },
                'summary': aggregated_data,
                'category_breakdown': self._get_category_breakdown(records),
                'daily_breakdown': self._get_daily_breakdown_with_categories(records),
                'raw_records': records
            }
            
            # Salva file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Errore generazione report contratto {contract_code}: {e}")
            return None
    
    def _aggregate_contract_data_with_categories(self, records: List[Dict]) -> Dict[str, Any]:
        """Aggrega dati contratto includendo informazioni categorie"""
        from collections import defaultdict
        
        if not records:
            return {}
        
        # Informazioni base contratto
        first_record = records[0]
        contract_info = {
            'codice_contratto': first_record.get('codice_contratto', ''),
            'cliente_finale_comune': first_record.get('cliente_finale_comune', ''),
        }
        
        # Aggregazioni
        total_calls = len(records)
        total_duration = sum(int(r.get('durata_secondi', 0)) for r in records)
        total_cost_original = sum(float(r.get('costo_originale_euro', 0)) for r in records)
        total_cost_client = sum(float(r.get('costo_cliente_euro', 0)) for r in records)
        
        # Aggregazione per categoria
        category_stats = defaultdict(lambda: {
            'calls': 0,
            'duration_seconds': 0,
            'cost_client': 0.0,
            'cost_original': 0.0,
            'display_name': '',
            'avg_price_per_minute': 0.0
        })
        
        for record in records:
            cat_name = record.get('categoria_cliente', 'ALTRO')
            cat_display = record.get('categoria_display', cat_name)
            
            category_stats[cat_name]['calls'] += 1
            category_stats[cat_name]['duration_seconds'] += int(record.get('durata_secondi', 0))
            category_stats[cat_name]['cost_client'] += float(record.get('costo_cliente_euro', 0))
            category_stats[cat_name]['cost_original'] += float(record.get('costo_originale_euro', 0))
            category_stats[cat_name]['display_name'] = cat_display
            category_stats[cat_name]['avg_price_per_minute'] = float(record.get('prezzo_categoria', 0))
        
        # Calcola medie per categoria
        for cat_name, stats in category_stats.items():
            duration_minutes = stats['duration_seconds'] / 60.0
            stats['duration_minutes'] = round(duration_minutes, 2)
            stats['cost_client'] = round(stats['cost_client'], 4)
            stats['cost_original'] = round(stats['cost_original'], 4)
            stats['difference'] = round(stats['cost_client'] - stats['cost_original'], 4)
        
        # Risultato finale
        result = {
            **contract_info,
            'totale_chiamate': total_calls,
            'durata_totale_secondi': total_duration,
            'durata_totale_minuti': round(total_duration / 60, 2),
            'durata_totale_ore': round(total_duration / 3600, 2),
            'costo_originale_totale_euro': round(total_cost_original, 4),
            'costo_cliente_totale_euro': round(total_cost_client, 4),
            'differenza_totale_euro': round(total_cost_client - total_cost_original, 4),
            'risparmio_percentuale': round(((total_cost_client - total_cost_original) / total_cost_original) * 100, 2) if total_cost_original > 0 else 0,
            'categoria_breakdown': dict(category_stats)
        }
        
        return result
    
    def _get_category_breakdown(self, records: List[Dict]) -> Dict[str, Dict]:
        """Genera breakdown dettagliato per categoria"""
        from collections import defaultdict
        
        breakdown = defaultdict(lambda: {
            'numero_chiamate': 0,
            'durata_totale_secondi': 0,
            'durata_media_secondi': 0,
            'costo_cliente_totale_euro': 0.0,
            'costo_originale_totale_euro': 0.0,
            'costo_cliente_medio_euro': 0.0,
            'costo_al_minuto_cliente': 0.0,
            'prezzo_categoria_euro': 0.0,
            'categoria_display': '',
            'matched': True,
            'differenza_totale': 0.0
        })
        
        for record in records:
            cat_name = record.get('categoria_cliente', 'ALTRO')
            duration = int(record.get('durata_secondi', 0))
            cost_client = float(record.get('costo_cliente_euro', 0))
            cost_original = float(record.get('costo_originale_euro', 0))
            
            breakdown[cat_name]['numero_chiamate'] += 1
            breakdown[cat_name]['durata_totale_secondi'] += duration
            breakdown[cat_name]['costo_cliente_totale_euro'] += cost_client
            breakdown[cat_name]['costo_originale_totale_euro'] += cost_original
            breakdown[cat_name]['categoria_display'] = record.get('categoria_display', cat_name)
            breakdown[cat_name]['prezzo_categoria_euro'] = float(record.get('prezzo_categoria', 0))
            breakdown[cat_name]['matched'] = record.get('categoria_matched', False)
        
        # Calcola medie
        for cat_name, data in breakdown.items():
            if data['numero_chiamate'] > 0:
                data['durata_media_secondi'] = round(data['durata_totale_secondi'] / data['numero_chiamate'], 2)
                data['costo_cliente_medio_euro'] = round(data['costo_cliente_totale_euro'] / data['numero_chiamate'], 4)
                
                if data['durata_totale_secondi'] > 0:
                    data['costo_al_minuto_cliente'] = round((data['costo_cliente_totale_euro'] / (data['durata_totale_secondi'] / 60)), 4)
                
                data['differenza_totale'] = round(data['costo_cliente_totale_euro'] - data['costo_originale_totale_euro'], 4)
            
            # Arrotondamenti finali
            data['costo_cliente_totale_euro'] = round(data['costo_cliente_totale_euro'], 4)
            data['costo_originale_totale_euro'] = round(data['costo_originale_totale_euro'], 4)
        
        return dict(breakdown)
    
    def _get_daily_breakdown_with_categories(self, records: List[Dict]) -> Dict[str, Dict]:
        """Genera breakdown giornaliero con categorie"""
        from collections import defaultdict
        
        daily_data = defaultdict(lambda: {
            'chiamate': 0,
            'durata_secondi': 0,
            'costo_originale_euro': 0.0,
            'costo_cliente_euro': 0.0,
            'categorie': defaultdict(int)
        })
        
        for record in records:
            date_str = record.get('data_ora_chiamata', '')
            if date_str:
                date_key = date_str[:10] if len(date_str) >= 10 else date_str
                cat_name = record.get('categoria_cliente', 'ALTRO')
                
                daily_data[date_key]['chiamate'] += 1
                daily_data[date_key]['durata_secondi'] += int(record.get('durata_secondi', 0))
                daily_data[date_key]['costo_originale_euro'] += float(record.get('costo_originale_euro', 0))
                daily_data[date_key]['costo_cliente_euro'] += float(record.get('costo_cliente_euro', 0))
                daily_data[date_key]['categorie'][cat_name] += 1
        
        # Arrotonda e converte
        for day in daily_data:
            daily_data[day]['costo_originale_euro'] = round(daily_data[day]['costo_originale_euro'], 4)
            daily_data[day]['costo_cliente_euro'] = round(daily_data[day]['costo_cliente_euro'], 4)
            daily_data[day]['durata_minuti'] = round(daily_data[day]['durata_secondi'] / 60, 2)
            daily_data[day]['differenza_costo'] = round(daily_data[day]['costo_cliente_euro'] - daily_data[day]['costo_originale_euro'], 4)
            daily_data[day]['categorie'] = dict(daily_data[day]['categorie'])
        
        return dict(daily_data)
    
    def _generate_summary_report(self, grouped_data: Dict, metadata: Dict) -> Optional[str]:
        """Genera report riassuntivo con statistiche categorie"""
        try:
            from datetime import datetime
            
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            current_month = now.strftime("%m")
            filename = f"SUMMARY_CATEGORIES_{current_month}_{timestamp}.json"
            filepath = self.analytics_directory / filename
            
            # Aggrega dati globali
            contracts_summary = {}
            global_totals = {
                'total_contracts': len(grouped_data),
                'total_calls': 0,
                'total_duration_seconds': 0,
                'total_cost_original_euro': 0.0,
                'total_cost_client_euro': 0.0
            }
            
            # Totali globali per categoria
            from collections import defaultdict
            global_by_category = defaultdict(lambda: {
                'calls': 0,
                'duration_seconds': 0,
                'cost_client_euro': 0.0,
                'cost_original_euro': 0.0,
                'display_name': '',
                'price_per_minute': 0.0,
                'matched': True
            })
            
            for contract_code, records in grouped_data.items():
                contract_summary = self._aggregate_contract_data_with_categories(records)
                contracts_summary[contract_code] = contract_summary
                
                # Aggrega globali
                global_totals['total_calls'] += len(records)
                global_totals['total_duration_seconds'] += sum(int(r.get('durata_secondi', 0)) for r in records)
                global_totals['total_cost_original_euro'] += sum(float(r.get('costo_originale_euro', 0)) for r in records)
                global_totals['total_cost_client_euro'] += sum(float(r.get('costo_cliente_euro', 0)) for r in records)
                
                # Aggrega per categoria
                for record in records:
                    cat_name = record.get('categoria_cliente', 'ALTRO')
                    cat_display = record.get('categoria_display', cat_name)
                    duration = int(record.get('durata_secondi', 0))
                    cost_client = float(record.get('costo_cliente_euro', 0))
                    cost_original = float(record.get('costo_originale_euro', 0))
                    
                    global_by_category[cat_name]['calls'] += 1
                    global_by_category[cat_name]['duration_seconds'] += duration
                    global_by_category[cat_name]['cost_client_euro'] += cost_client
                    global_by_category[cat_name]['cost_original_euro'] += cost_original
                    global_by_category[cat_name]['display_name'] = cat_display
                    global_by_category[cat_name]['price_per_minute'] = float(record.get('prezzo_categoria', 0))
                    global_by_category[cat_name]['matched'] = record.get('categoria_matched', False)
            
            # Arrotonda totali globali
            for key in ['total_cost_original_euro', 'total_cost_client_euro']:
                global_totals[key] = round(global_totals[key], 4)
            
            global_totals['total_duration_minutes'] = round(global_totals['total_duration_seconds'] / 60, 2)
            global_totals['total_difference_euro'] = round(global_totals['total_cost_client_euro'] - global_totals['total_cost_original_euro'], 4)
            
            # Arrotonda totali per categoria
            for cat_name in global_by_category:
                data = global_by_category[cat_name]
                data['cost_client_euro'] = round(data['cost_client_euro'], 4)
                data['cost_original_euro'] = round(data['cost_original_euro'], 4)
                data['duration_minutes'] = round(data['duration_seconds'] / 60, 2)
                data['difference_euro'] = round(data['cost_client_euro'] - data['cost_original_euro'], 4)
                data['percentage_of_total'] = round((data['calls'] / global_totals['total_calls']) * 100, 2) if global_totals['total_calls'] > 0 else 0
            
            # Report finale
            summary_report = {
                'metadata': {
                    'generation_timestamp': now.isoformat(),
                    'source_file': metadata.get('source_file', ''),
                    'month': current_month,
                    'year': now.year,
                    'categories_system_enabled': True,
                    'categories_info': self.categories_manager.get_statistics()
                },
                'global_totals': global_totals,
                'global_by_category': dict(global_by_category),
                'contracts_summary': contracts_summary,
                'top_contracts': self._get_top_contracts_with_categories(contracts_summary),
                'category_performance': self._analyze_category_performance(dict(global_by_category))
            }
            
            # Salva file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📊 Report summary con categorie generato: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Errore generazione summary report: {e}")
            return None
    
    def _get_top_contracts_with_categories(self, contracts_summary: Dict) -> Dict:
        """Genera top contratti includendo metriche categorie"""
        try:
            contracts_list = []
            
            for contract_code, data in contracts_summary.items():
                contracts_list.append({
                    'codice_contratto': contract_code,
                    'cliente_finale_comune': data.get('cliente_finale_comune', ''),
                    'totale_chiamate': data.get('totale_chiamate', 0),
                    'durata_totale_secondi': data.get('durata_totale_secondi', 0),
                    'costo_originale_totale_euro': data.get('costo_originale_totale_euro', 0.0),
                    'costo_cliente_totale_euro': data.get('costo_cliente_totale_euro', 0.0),
                    'differenza_totale_euro': data.get('differenza_totale_euro', 0.0),
                    'risparmio_percentuale': data.get('risparmio_percentuale', 0.0)
                })
            
            return {
                'top_by_calls': sorted(contracts_list, key=lambda x: x['totale_chiamate'], reverse=True)[:10],
                'top_by_duration': sorted(contracts_list, key=lambda x: x['durata_totale_secondi'], reverse=True)[:10],
                'top_by_cost_client': sorted(contracts_list, key=lambda x: x['costo_cliente_totale_euro'], reverse=True)[:10],
                'top_by_savings': sorted(contracts_list, key=lambda x: x['differenza_totale_euro'], reverse=True)[:10],
                'top_by_savings_percent': sorted(contracts_list, key=lambda x: x['risparmio_percentuale'], reverse=True)[:10]
            }
        except Exception as e:
            logger.error(f"Errore calcolo top contracts: {e}")
            return {}
    
    def _analyze_category_performance(self, global_by_category: Dict) -> Dict:
        """Analizza performance delle categorie"""
        try:
            performance = {}
            
            for cat_name, data in global_by_category.items():
                avg_cost_per_call = data['cost_client_euro'] / data['calls'] if data['calls'] > 0 else 0
                avg_duration_per_call = data['duration_seconds'] / data['calls'] if data['calls'] > 0 else 0
                efficiency_ratio = data['cost_client_euro'] / (data['duration_minutes'] if data['duration_minutes'] > 0 else 1)
                
                performance[cat_name] = {
                    'display_name': data['display_name'],
                    'calls_count': data['calls'],
                    'avg_cost_per_call': round(avg_cost_per_call, 4),
                    'avg_duration_per_call_seconds': round(avg_duration_per_call, 2),
                    'efficiency_ratio_euro_per_minute': round(efficiency_ratio, 4),
                    'total_revenue_potential': round(data['cost_client_euro'], 4),
                    'category_matched': data['matched'],
                    'market_share_percentage': data['percentage_of_total']
                }
            
            # Ordina per revenue potential
            performance = dict(sorted(performance.items(), key=lambda x: x[1]['total_revenue_potential'], reverse=True))
            
            return performance
            
        except Exception as e:
            logger.error(f"Errore analisi performance categorie: {e}")
            return {}
    
    def list_generated_reports(self) -> List[Dict]:
        """Lista report generati"""
        reports = []
        
        try:
            for file_path in self.analytics_directory.glob("*.json"):
                if file_path.name == "cdr_categories.json":
                    continue  # Skip configuration file
                
                stat = file_path.stat()
                reports.append({
                    'filename': file_path.name,
                    'filepath': str(file_path),
                    'size_bytes': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'is_summary': file_path.name.startswith('SUMMARY_'),
                    'has_categories': 'CATEGORIES' in file_path.name or file_path.name.startswith('SUMMARY_')
                })
            
            reports.sort(key=lambda x: x['created'], reverse=True)
            
        except Exception as e:
            logger.error(f"Errore listing report: {e}")
        
        return reports
    
    def get_categories_manager(self) -> CDRCategoriesManager:
        """Restituisce il manager delle categorie per uso esterno"""
        return self.categories_manager


# Funzione di integrazione principale
def integrate_enhanced_cdr_system(app, processor):
    """
    Integra il sistema CDR potenziato nell'applicazione esistente
    """
    # Sostituisci il sistema CDR esistente con quello potenziato
    if hasattr(processor, 'cdr_analytics'):
        # Backup del vecchio sistema se necessario
        processor._old_cdr_analytics = processor.cdr_analytics
    
    # Inizializza il nuovo sistema
    processor.cdr_analytics = CDRAnalyticsEnhanced(processor.config['output_directory'])
    
    logger.info("🔧 Sistema CDR Enhanced integrato con categorie configurabili")
    
    return processor