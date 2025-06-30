import os
import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from collections import defaultdict, Counter
import statistics

try:
    from dotenv import load_dotenv
    load_dotenv()  # Carica variabili dal file .env
    print("📁 File .env caricato")
    cdr_folder = os.getenv('OUTPUT_DIRECTORY')
except ImportError:
    print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")


def leggi_file_directory(
    directory: str,
    estensioni: Optional[Union[str, List[str]]] = None,
    ricorsivo: bool = False,
    solo_nomi: bool = False,
    include_nascosti: bool = False,
    formato_json: bool = True
) -> Union[str, List[str]]:
    """
    Legge tutti i file di una directory con possibilità di filtrarli per tipologia.
    
    Args:
        directory (str): Percorso della directory da leggere
        estensioni (str, List[str], optional): Estensione/i file da filtrare
                                             Es: '.txt', ['.txt', '.json', '.csv']
                                             Se None, restituisce tutti i file
        ricorsivo (bool): Se True, cerca anche nelle sottodirectory (default: False)
        solo_nomi (bool): Se True, restituisce solo i nomi dei file senza percorso completo (default: False)
        include_nascosti (bool): Se True, include anche i file nascosti (che iniziano con .) (default: False)
        formato_json (bool): Se True, restituisce la lista in formato JSON string (default: True)
    
    Returns:
        Union[str, List[str]]: Lista dei percorsi dei file trovati in formato JSON o come lista Python
        
    Raises:
        ValueError: Se la directory non esiste
        PermissionError: Se non si hanno i permessi per accedere alla directory
    """
    
    # Verifica che la directory esista
    directory_path = Path(directory)
    if not directory_path.exists():
        raise ValueError(f"La directory '{directory}' non esiste")
    
    if not directory_path.is_dir():
        raise ValueError(f"'{directory}' non è una directory")
    
    # Normalizza le estensioni
    if estensioni is not None:
        if isinstance(estensioni, str):
            estensioni = [estensioni]
        # Assicurati che le estensioni inizino con un punto
        estensioni = [ext if ext.startswith('.') else f'.{ext}' for ext in estensioni]
        # Converti in minuscolo per confronto case-insensitive
        estensioni = [ext.lower() for ext in estensioni]
    
    file_trovati = []
    
    try:
        if ricorsivo:
            # Usa rglob per ricerca ricorsiva
            pattern = "**/*" if estensioni is None else "**/*"
            for item in directory_path.rglob(pattern):
                if item.is_file():
                    # Controlla se il file è nascosto
                    if not include_nascosti and item.name.startswith('.'):
                        continue
                    
                    # Filtra per estensioni se specificate
                    if estensioni is not None:
                        if item.suffix.lower() not in estensioni:
                            continue
                    
                    # Aggiungi il file alla lista
                    if solo_nomi:
                        file_trovati.append(item.name)
                    else:
                        file_trovati.append(str(item))
        else:
            # Leggi solo la directory corrente
            for item in directory_path.iterdir():
                if item.is_file():
                    # Controlla se il file è nascosto
                    if not include_nascosti and item.name.startswith('.'):
                        continue
                    
                    # Filtra per estensioni se specificate
                    if estensioni is not None:
                        if item.suffix.lower() not in estensioni:
                            continue
                    
                    # Aggiungi il file alla lista
                    if solo_nomi:
                        file_trovati.append(item.name)
                    else:
                        file_trovati.append(str(item))
    
    except PermissionError as e:
        raise PermissionError(f"Permessi insufficienti per accedere alla directory '{directory}': {e}")
    
    # Ordina la lista per avere un output consistente
    file_trovati.sort()
    
    # Restituisce in formato JSON se richiesto
    if formato_json:
        return json.dumps(file_trovati, indent=2, ensure_ascii=False)
    else:
        return file_trovati


def leggi_file_directory_con_info(
    directory: str,
    estensioni: Optional[Union[str, List[str]]] = None,
    ricorsivo: bool = False,
    include_nascosti: bool = False,
    formato_json: bool = True
) -> Union[str, List[dict]]:
    """
    Versione estesa che restituisce informazioni dettagliate sui file.
    
    Args:
        directory (str): Percorso della directory da leggere
        estensioni (str, List[str], optional): Estensione/i file da filtrare
        ricorsivo (bool): Se True, cerca anche nelle sottodirectory
        include_nascosti (bool): Se True, include anche i file nascosti
        formato_json (bool): Se True, restituisce la lista in formato JSON string (default: True)
    
    Returns:
        Union[str, List[dict]]: Lista di dizionari con informazioni sui file in formato JSON o lista Python:
                               - nome: nome del file
                               - percorso_completo: percorso completo del file
                               - estensione: estensione del file
                               - dimensione: dimensione in bytes
                               - ultima_modifica: timestamp ultima modifica
    """
    
    directory_path = Path(directory)
    if not directory_path.exists():
        raise ValueError(f"La directory '{directory}' non esiste")
    
    if not directory_path.is_dir():
        raise ValueError(f"'{directory}' non è una directory")
    
    # Normalizza le estensioni
    if estensioni is not None:
        if isinstance(estensioni, str):
            estensioni = [estensioni]
        estensioni = [ext if ext.startswith('.') else f'.{ext}' for ext in estensioni]
        estensioni = [ext.lower() for ext in estensioni]
    
    file_info = []
    
    try:
        if ricorsivo:
            pattern = "**/*"
            for item in directory_path.rglob(pattern):
                if item.is_file():
                    if not include_nascosti and item.name.startswith('.'):
                        continue
                    
                    if estensioni is not None:
                        if item.suffix.lower() not in estensioni:
                            continue
                    
                    stat_info = item.stat()
                    file_info.append({
                        'nome': item.name,
                        'percorso_completo': str(item),
                        'estensione': item.suffix,
                        'dimensione': stat_info.st_size,
                        'ultima_modifica': stat_info.st_mtime
                    })
        else:
            for item in directory_path.iterdir():
                if item.is_file():
                    if not include_nascosti and item.name.startswith('.'):
                        continue
                    
                    if estensioni is not None:
                        if item.suffix.lower() not in estensioni:
                            continue
                    
                    stat_info = item.stat()
                    file_info.append({
                        'nome': item.name,
                        'percorso_completo': str(item),
                        'estensione': item.suffix,
                        'dimensione': stat_info.st_size,
                        'ultima_modifica': stat_info.st_mtime
                    })
    
    except PermissionError as e:
        raise PermissionError(f"Permessi insufficienti per accedere alla directory '{directory}': {e}")
    
    # Ordina per nome
    file_info.sort(key=lambda x: x['nome'])
    
    # Restituisce in formato JSON se richiesto
    if formato_json:
        return json.dumps(file_info, indent=2, ensure_ascii=False)
    else:
        return file_info


# Funzione di utilità per creare JSON strutturato
def leggi_file_directory_json_strutturato(
    directory: str,
    estensioni: Optional[Union[str, List[str]]] = None,
    ricorsivo: bool = False,
    include_nascosti: bool = False
) -> str:
    """
    Restituisce un JSON strutturato con metadati e lista dei file.
    
    Returns:
        str: JSON strutturato con:
             - metadata: informazioni sulla scansione
             - files: lista dei file trovati
    """
    try:
        file_list = leggi_file_directory(
            directory, estensioni, ricorsivo, False, include_nascosti, formato_json=False
        )
        
        risultato = {
            "metadata": {
                "directory": directory,
                "estensioni_filtro": estensioni,
                "ricorsivo": ricorsivo,
                "include_nascosti": include_nascosti,
                "totale_file": len(file_list),
                "timestamp_scansione": __import__('datetime').datetime.now().isoformat()
            },
            "files": file_list
        }
        
        return json.dumps(risultato, indent=2, ensure_ascii=False)
        
    except Exception as e:
        errore = {
            "error": True,
            "message": str(e),
            "directory": directory,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        return json.dumps(errore, indent=2, ensure_ascii=False)


### ANALISI CDR ###
def analyze_cdr_data(file_path: str) -> Dict[str, Any]:
    """
    Analizza i dati CDR e li unifica per codice_contratto mantenendo tutti i dati originali.
    
    Args:
        file_path: Percorso del file JSON da analizzare
        
    Returns:
        Dict contenente i dati unificati per contratto con analisi dettagliate
    """
    
    # Carica i dati dal file JSON
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Raggruppa i record per codice_contratto
    contracts_records = defaultdict(list)
    for record in data['records']:
        contracts_records[record['codice_contratto']].append(record)
    
    # Struttura il risultato finale
    unified_data = {
        'metadata': {
            **data['metadata'],
            'analysis_timestamp': datetime.now().isoformat(),
            'total_contracts_found': len(contracts_records),
            'original_total_records': data['metadata']['total_records']
        },
        'contracts': {},
        'global_summary': {}
    }
    
    # Analizza ogni contratto
    for contract_code, records in contracts_records.items():
        unified_data['contracts'][str(contract_code)] = _create_unified_contract_data(contract_code, records)
    
    # Genera sommario globale
    unified_data['global_summary'] = _generate_global_summary(unified_data['contracts'])
    
    # return json.dumps(unified_data, indent=2, ensure_ascii=False)
    return unified_data


def _create_unified_contract_data(contract_code: int, records: List[Dict]) -> Dict[str, Any]:
    """Crea la struttura unificata per un singolo contratto con tutti i dati originali e analisi."""
    
    # Dati originali unificati
    unified_records = []
    unique_callers = set()
    unique_called_numbers = set()
    service_codes = set()
    
    for record in records:
        unified_records.append(record)
        unique_callers.add(record['numero_chiamante'])
        unique_called_numbers.add(record['numero_chiamato'])
        service_codes.add(record['codice_servizio'])
    
    # Calcoli base
    total_calls = len(records)
    total_duration = sum(r['durata_secondi'] for r in records)
    total_cost = sum(r['costo_euro'] for r in records)
    
    # Analisi dettagliate
    call_types_analysis = _analyze_call_types(records)
    operators_analysis = _analyze_operators(records)
    geographic_analysis = _analyze_geography(records)
    temporal_analysis = _analyze_temporal_patterns(records)
    cost_analysis = _analyze_costs(records)
    duration_analysis = _analyze_durations(records)
    service_analysis = _analyze_services(records)
    
    return {
        'contract_info': {
            'codice_contratto': contract_code,
            'total_records': total_calls,
            'unique_calling_numbers': len(unique_callers),
            'unique_called_numbers': len(unique_called_numbers),
            'unique_service_codes': len(service_codes),
            'date_range': {
                'first_call': min(r['data_ora_chiamata'] for r in records),
                'last_call': max(r['data_ora_chiamata'] for r in records)
            }
        },
        
        'aggregated_metrics': {
            'total_calls': total_calls,
            'total_duration_seconds': total_duration,
            'total_duration_minutes': round(total_duration / 60, 2),
            'total_duration_hours': round(total_duration / 3600, 2),
            'total_cost_euro': round(total_cost, 2),
            'average_call_duration_seconds': round(total_duration / total_calls, 2) if total_calls > 0 else 0,
            'average_call_cost_euro': round(total_cost / total_calls, 4) if total_calls > 0 else 0,
            'cost_per_minute': round((total_cost * 60) / total_duration, 4) if total_duration > 0 else 0
        },
        
        'call_types_analysis': call_types_analysis,
        'operators_analysis': operators_analysis,
        'geographic_analysis': geographic_analysis,
        'temporal_analysis': temporal_analysis,
        'cost_analysis': cost_analysis,
        'duration_analysis': duration_analysis,
        'service_analysis': service_analysis,
        
        'top_records': {
            'most_expensive_calls': _get_top_calls_by_cost(records, 10),
            'longest_calls': _get_top_calls_by_duration(records, 10),
            'most_frequent_destinations': _get_most_frequent_destinations(records, 10),
            'most_frequent_callers': _get_most_frequent_callers(records, 10)
        },
        
        'original_records': unified_records
    }


def _analyze_call_types(records: List[Dict]) -> Dict[str, Any]:
    """Analizza i tipi di chiamata."""
    call_types = Counter(r['tipo_chiamata'] for r in records)
    total = len(records)
    
    # Calcola costi e durate per tipo
    type_details = {}
    for call_type in call_types.keys():
        type_records = [r for r in records if r['tipo_chiamata'] == call_type]
        type_details[call_type] = {
            'count': len(type_records),
            'percentage': round((len(type_records) / total) * 100, 2),
            'total_cost': round(sum(r['costo_euro'] for r in type_records), 2),
            'total_duration': sum(r['durata_secondi'] for r in type_records),
            'average_cost': round(sum(r['costo_euro'] for r in type_records) / len(type_records), 4),
            'average_duration': round(sum(r['durata_secondi'] for r in type_records) / len(type_records), 2)
        }
    
    return {
        'summary': {
            'total_types': len(call_types),
            'distribution': dict(call_types)
        },
        'detailed_analysis': type_details
    }


def _analyze_operators(records: List[Dict]) -> Dict[str, Any]:
    """Analizza la distribuzione degli operatori."""
    operators = Counter(r['operatore'] for r in records)
    total = len(records)
    
    operator_details = {}
    for operator in operators.keys():
        op_records = [r for r in records if r['operatore'] == operator]
        operator_details[operator] = {
            'count': len(op_records),
            'percentage': round((len(op_records) / total) * 100, 2),
            'total_cost': round(sum(r['costo_euro'] for r in op_records), 2),
            'average_cost_per_call': round(sum(r['costo_euro'] for r in op_records) / len(op_records), 4)
        }
    
    return {
        'summary': {
            'total_operators': len(operators),
            'distribution': dict(operators)
        },
        'detailed_analysis': operator_details,
        'top_operators': operators.most_common(5)
    }


def _analyze_geography(records: List[Dict]) -> Dict[str, Any]:
    """Analizza la distribuzione geografica."""
    cities = Counter(r['cliente_finale_comune'] for r in records)
    prefixes = Counter(r['prefisso_chiamato'] for r in records)
    
    return {
        'cities': {
            'total_cities': len(cities),
            'distribution': dict(cities),
            'top_cities': cities.most_common(10)
        },
        'prefixes': {
            'total_prefixes': len(prefixes),
            'distribution': dict(prefixes),
            'top_prefixes': prefixes.most_common(10)
        }
    }


def _analyze_temporal_patterns(records: List[Dict]) -> Dict[str, Any]:
    """Analizza i pattern temporali."""
    hours = []
    days_of_week = []
    dates = []
    
    for record in records:
        dt = datetime.strptime(record['data_ora_chiamata'], '%Y-%m-%d-%H.%M.%S')
        hours.append(dt.hour)
        days_of_week.append(dt.strftime('%A'))
        dates.append(dt.date().isoformat())
    
    hour_distribution = Counter(hours)
    day_distribution = Counter(days_of_week)
    daily_calls = Counter(dates)
    
    return {
        'hourly_distribution': {
            'by_hour': dict(hour_distribution),
            'peak_hours': hour_distribution.most_common(5),
            'busiest_hour': hour_distribution.most_common(1)[0] if hour_distribution else None
        },
        'daily_distribution': {
            'by_day_of_week': dict(day_distribution),
            'busiest_day_type': day_distribution.most_common(1)[0] if day_distribution else None
        },
        'date_distribution': {
            'calls_per_date': dict(daily_calls),
            'busiest_dates': daily_calls.most_common(10)
        }
    }


def _analyze_costs(records: List[Dict]) -> Dict[str, Any]:
    """Analizza le statistiche sui costi."""
    costs = [r['costo_euro'] for r in records]
    
    if not costs:
        return {'no_data': True}
    
    sorted_costs = sorted(costs)
    
    return {
        'basic_stats': {
            'min_cost': min(costs),
            'max_cost': max(costs),
            'total_cost': round(sum(costs), 2),
            'average_cost': round(statistics.mean(costs), 4),
            'median_cost': round(statistics.median(costs), 4)
        },
        'advanced_stats': {
            'standard_deviation': round(statistics.stdev(costs), 4) if len(costs) > 1 else 0,
            'percentile_25': round(statistics.quantiles(costs, n=4)[0], 4) if len(costs) >= 4 else sorted_costs[0],
            'percentile_75': round(statistics.quantiles(costs, n=4)[2], 4) if len(costs) >= 4 else sorted_costs[-1]
        },
        'cost_ranges': {
            'free_calls': len([c for c in costs if c == 0]),
            'low_cost_calls': len([c for c in costs if 0 < c <= 0.05]),
            'medium_cost_calls': len([c for c in costs if 0.05 < c <= 0.15]),
            'high_cost_calls': len([c for c in costs if c > 0.15])
        }
    }


def _analyze_durations(records: List[Dict]) -> Dict[str, Any]:
    """Analizza le statistiche sulle durate."""
    durations = [r['durata_secondi'] for r in records]
    
    if not durations:
        return {'no_data': True}
    
    return {
        'basic_stats': {
            'min_duration': min(durations),
            'max_duration': max(durations),
            'total_duration': sum(durations),
            'average_duration': round(statistics.mean(durations), 2),
            'median_duration': round(statistics.median(durations), 2)
        },
        'advanced_stats': {
            'standard_deviation': round(statistics.stdev(durations), 2) if len(durations) > 1 else 0
        },
        'duration_ranges': {
            'very_short_calls': len([d for d in durations if d <= 30]),     # <= 30 secondi
            'short_calls': len([d for d in durations if 30 < d <= 120]),    # 30s - 2min
            'medium_calls': len([d for d in durations if 120 < d <= 600]),  # 2min - 10min
            'long_calls': len([d for d in durations if d > 600])            # > 10min
        }
    }


def _analyze_services(records: List[Dict]) -> Dict[str, Any]:
    """Analizza i codici servizio."""
    services = Counter(r['codice_servizio'] for r in records)
    
    service_details = {}
    for service_code in services.keys():
        service_records = [r for r in records if r['codice_servizio'] == service_code]
        service_details[service_code] = {
            'count': len(service_records),
            'total_cost': round(sum(r['costo_euro'] for r in service_records), 2),
            'average_cost': round(sum(r['costo_euro'] for r in service_records) / len(service_records), 4)
        }
    
    return {
        'summary': {
            'total_services': len(services),
            'distribution': dict(services)
        },
        'detailed_analysis': service_details,
        'top_services': services.most_common(10)
    }


def _get_top_calls_by_cost(records: List[Dict], limit: int) -> List[Dict]:
    """Restituisce le chiamate più costose."""
    return sorted(records, key=lambda x: x['costo_euro'], reverse=True)[:limit]


def _get_top_calls_by_duration(records: List[Dict], limit: int) -> List[Dict]:
    """Restituisce le chiamate più lunghe."""
    return sorted(records, key=lambda x: x['durata_secondi'], reverse=True)[:limit]


def _get_most_frequent_destinations(records: List[Dict], limit: int) -> List[Dict]:
    """Restituisce le destinazioni più frequenti."""
    destinations = Counter(r['numero_chiamato'] for r in records)
    return [{'numero': num, 'count': count} for num, count in destinations.most_common(limit)]


def _get_most_frequent_callers(records: List[Dict], limit: int) -> List[Dict]:
    """Restituisce i chiamanti più frequenti."""
    callers = Counter(r['numero_chiamante'] for r in records)
    return [{'numero': num, 'count': count} for num, count in callers.most_common(limit)]


def _generate_global_summary(contracts: Dict) -> Dict[str, Any]:
    """Genera un sommario globale di tutti i contratti."""
    
    total_contracts = len(contracts)
    total_calls = sum(contract['aggregated_metrics']['total_calls'] for contract in contracts.values())
    total_cost = sum(contract['aggregated_metrics']['total_cost_euro'] for contract in contracts.values())
    total_duration = sum(contract['aggregated_metrics']['total_duration_seconds'] for contract in contracts.values())
    
    # Top contratti per diverse metriche
    most_active_contracts = sorted(
        contracts.items(),
        key=lambda x: x[1]['aggregated_metrics']['total_calls'],
        reverse=True
    )[:10]
    
    most_expensive_contracts = sorted(
        contracts.items(),
        key=lambda x: x[1]['aggregated_metrics']['total_cost_euro'],
        reverse=True
    )[:10]
    
    highest_average_cost_contracts = sorted(
        contracts.items(),
        key=lambda x: x[1]['aggregated_metrics']['average_call_cost_euro'],
        reverse=True
    )[:10]
    
    # Analisi globale dei tipi di chiamata
    all_call_types = Counter()
    all_operators = Counter()
    
    for contract in contracts.values():
        for call_type, data in contract['call_types_analysis']['detailed_analysis'].items():
            all_call_types[call_type] += data['count']
        for operator, data in contract['operators_analysis']['detailed_analysis'].items():
            all_operators[operator] += data['count']
    
    return {
        'overview': {
            'total_contracts': total_contracts,
            'total_calls': total_calls,
            'total_cost_euro': round(total_cost, 2),
            'total_duration_hours': round(total_duration / 3600, 2),
            'average_calls_per_contract': round(total_calls / total_contracts, 2) if total_contracts > 0 else 0,
            'average_cost_per_contract': round(total_cost / total_contracts, 2) if total_contracts > 0 else 0,
            'average_cost_per_call': round(total_cost / total_calls, 4) if total_calls > 0 else 0
        },
        
        'top_contracts': {
            'most_active': [
                {
                    'codice_contratto': contract_id,
                    'total_calls': data['aggregated_metrics']['total_calls'],
                    'total_cost_euro': data['aggregated_metrics']['total_cost_euro']
                }
                for contract_id, data in most_active_contracts
            ],
            'most_expensive': [
                {
                    'codice_contratto': contract_id,
                    'total_cost_euro': data['aggregated_metrics']['total_cost_euro'],
                    'total_calls': data['aggregated_metrics']['total_calls']
                }
                for contract_id, data in most_expensive_contracts
            ],
            'highest_average_cost': [
                {
                    'codice_contratto': contract_id,
                    'average_call_cost_euro': data['aggregated_metrics']['average_call_cost_euro'],
                    'total_calls': data['aggregated_metrics']['total_calls']
                }
                for contract_id, data in highest_average_cost_contracts
            ]
        },
        
        'global_distributions': {
            'call_types': dict(all_call_types),
            'operators': dict(all_operators)
        }
    }


def save_unified_data(unified_data: Dict, output_path: str) -> None:
    """Salva i dati unificati in un file JSON."""
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(unified_data, file, indent=2, ensure_ascii=False)


def print_summary(unified_data: Dict) -> None:
    """Stampa un riassunto dell'analisi."""
    summary = unified_data['global_summary']['overview']
    
    print("=== RIASSUNTO ANALISI CDR UNIFICATA ===")
    print(f"Totale contratti: {summary['total_contracts']}")
    print(f"Totale chiamate: {summary['total_calls']}")
    print(f"Costo totale: €{summary['total_cost_euro']}")
    print(f"Durata totale: {summary['total_duration_hours']} ore")
    print(f"Costo medio per chiamata: €{summary['average_cost_per_call']}")
    
    print("\n=== TOP 5 CONTRATTI PIÙ ATTIVI ===")
    for i, contract in enumerate(unified_data['global_summary']['top_contracts']['most_active'][:5], 1):
        print(f"{i}. Contratto {contract['codice_contratto']}: "
              f"{contract['total_calls']} chiamate, €{contract['total_cost_euro']}")



# Esempi di utilizzo
if __name__ == "__main__":
    # Esempio 1: Tutti i file in formato JSON (default)
    # try:
    #     json_result = leggi_file_directory(cdr_folder)
    #     print("JSON result:")
    #     print(json_result)
        
    #     # Per ottenere la lista Python normale
    #     python_list = leggi_file_directory(cdr_folder, formato_json=False)
    #     print("Python list:", python_list)
    # except Exception as e:
    #     print(f"Errore: {e}")
    
    # Esempio 2: Solo file JSON in formato JSON
    try:
        file_json = leggi_file_directory(cdr_folder, estensioni='.json')
        print("File JSON (formato JSON):")
        file_list = json.loads(file_json)
        print(file_list[0])
    except Exception as e:
        print(f"Errore: {e}")
    
    # Esempio 3: JSON strutturato con metadati
    # try:
    #     json_strutturato = leggi_file_directory_json_strutturato(
    #         cdr_folder, 
    #         estensioni=['.json'],
    #         ricorsivo=False
    #     )
    #     print("JSON strutturato:")
    #     print(json_strutturato)
    # except Exception as e:
    #     print(f"Errore: {e}")
    
    # # Esempio 4: Informazioni dettagliate in formato JSON
    # try:
    #     file_dettagliati_json = leggi_file_directory_con_info(
    #         cdr_folder,
    #         estensioni=['.json']
    #     )
    #     print("File con info dettagliate (JSON):")
    #     print(file_dettagliati_json)
    # except Exception as e:
    #     print(f"Errore: {e}")




    # # Analizza i dati
    input_file = file_list[0]  # Sostituisci con il tuo percorso
    
    try:
        # Analizza e unifica i dati
        unified_data = analyze_cdr_data(input_file)
        # unified_data = json.loads(unified_data)
        print(unified_data)
        # # Stampa il riassunto
        # unified_data = json.loads(unified_data)
        # print_summary(unified_data)
        
        # # Salva i dati unificati
        # output_file = "cdr_unified_analysis.json"
        # save_unified_data(unified_data, output_file)
        # print(f"\nDati unificati salvati in: {output_file}")
        
        # # Esempio: accesso ai dati di un contratto specifico
        # contract_id = "63"
        # if contract_id in unified_data['contracts']:
        #     contract = unified_data['contracts'][contract_id]
        #     print(f"\n=== CONTRATTO {contract_id} ===")
        #     print(f"Record originali: {len(contract['original_records'])}")
        #     print(f"Chiamate totali: {contract['aggregated_metrics']['total_calls']}")
        #     print(f"Costo totale: €{contract['aggregated_metrics']['total_cost_euro']}")
            
    except FileNotFoundError:
        print(f"File non trovato: {input_file}")
    except Exception as e:
        print(f"Errore durante l'analisi: {e}")
