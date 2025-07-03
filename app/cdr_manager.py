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
            'total_duration_seconds': sum(r['durata_secondi'] for r in type_records),
            'total_duration_minutes': round(sum(r['durata_secondi'] for r in type_records)/60,2),
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


#GESTIONE CON MARKUP ###################################################################################################################################


def analyze_cdr_data_with_markup(file_path: str, categories_file_path: str) -> Dict[str, Any]:
    """
    Analizza i dati CDR con calcolo del markup basato sulle categorie.
    Se il costo originale è 0, calcola il costo usando le tariffe delle categorie.
    
    Args:
        file_path: Percorso del file JSON CDR da analizzare
        categories_file_path: Percorso del file JSON delle categorie tariffarie
        
    Returns:
        Dict contenente i dati unificati per contratto con analisi dettagliate e markup
    """
    
    # Carica le categorie tariffarie
    try:
        with open(categories_file_path, 'r', encoding='utf-8') as file:
            categories = json.load(file)
        # Filtra solo le categorie attive
        active_categories = {k: v for k, v in categories.items() if v.get('is_active', False)}
    except Exception as e:
        raise ValueError(f"Errore nel caricamento del file categorie: {e}")
    
    # Carica i dati dal file JSON CDR
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
            'original_total_records': data['metadata']['total_records'],
            'categories_file_used': categories_file_path
        },
        'contracts': {},
        'global_summary': {}
    }
    
    # Analizza ogni contratto
    for contract_code, records in contracts_records.items():
        unified_data['contracts'][str(contract_code)] = _create_unified_contract_data_with_markup(
            contract_code, records, active_categories
        )
    
    # Genera sommario globale
    unified_data['global_summary'] = _generate_global_summary_with_markup(unified_data['contracts'])
    
    return unified_data


def _create_unified_contract_data_with_markup(contract_code: int, records: List[Dict], categories: Dict) -> Dict[str, Any]:
    """Crea la struttura unificata per un singolo contratto con calcolo del markup."""
    
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
    
    # Analisi dettagliate con markup
    call_types_analysis = _analyze_call_types_with_markup(records, categories)
    operators_analysis = _analyze_operators(records)
    geographic_analysis = _analyze_geography(records)
    temporal_analysis = _analyze_temporal_patterns(records)
    cost_analysis = _analyze_costs(records)
    duration_analysis = _analyze_durations(records)
    service_analysis = _analyze_services(records)
    
    # Calcola il costo totale finale per l'utente
    total_cost_final_user = sum(
        details.get('total_cost_final_user', details['total_cost'])
        for details in call_types_analysis['detailed_analysis'].values()
    )
    
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
            'total_cost_euro_final_user': round(total_cost_final_user, 2),
            'average_call_duration_seconds': round(total_duration / total_calls, 2) if total_calls > 0 else 0,
            'average_call_cost_euro': round(total_cost / total_calls, 4) if total_calls > 0 else 0,
            'average_call_cost_euro_final_user': round(total_cost_final_user / total_calls, 4) if total_calls > 0 else 0,
            'cost_per_minute': round((total_cost * 60) / total_duration, 4) if total_duration > 0 else 0,
            'cost_per_minute_final_user': round((total_cost_final_user * 60) / total_duration, 4) if total_duration > 0 else 0
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


def _analyze_call_types_with_markup(records: List[Dict], categories: Dict) -> Dict[str, Any]:
    """Analizza i tipi di chiamata con calcolo del markup quando il costo è 0."""
    call_types = Counter(r['tipo_chiamata'] for r in records)
    total = len(records)
    
    # Calcola costi e durate per tipo
    type_details = {}
    for call_type in call_types.keys():
        type_records = [r for r in records if r['tipo_chiamata'] == call_type]
        original_total_cost = sum(r['costo_euro'] for r in type_records)
        total_duration_minutes = sum(r['durata_secondi'] for r in type_records) / 60
        
        # Se il costo originale NON è 0, calcola usando le categorie
        if original_total_cost != 0:
            category_info = _find_matching_category(call_type, categories)
            if category_info:
                calculated_cost = total_duration_minutes * category_info['price_with_markup']
                markup_percent = category_info['custom_markup_percent']
            else:
                # Fallback su categoria N.D. se non trovata
                nd_category = categories.get('ND', {})
                calculated_cost = total_duration_minutes * nd_category.get('price_with_markup', 0)
                markup_percent = nd_category.get('custom_markup_percent', 0)
            
            final_cost = calculated_cost
        else:
            # Se il costo è 0, mantieni tutto invariato
            final_cost = original_total_cost
            markup_percent = 0  # Non c'è markup applicato
        
        type_details[call_type] = {
            'count': len(type_records),
            'percentage': round((len(type_records) / total) * 100, 2),
            'total_cost': round(original_total_cost, 2),
            'total_cost_final_user': round(final_cost, 2),
            'markup_percent': markup_percent,
            'total_duration_seconds': sum(r['durata_secondi'] for r in type_records),
            'total_duration_minutes': round(total_duration_minutes, 2),
            'average_cost': round(original_total_cost / len(type_records), 4) if len(type_records) > 0 else 0,
            'average_cost_final_user': round(final_cost / len(type_records), 4) if len(type_records) > 0 else 0,
            'average_duration': round(sum(r['durata_secondi'] for r in type_records) / len(type_records), 2)
        }
    
    return {
        'summary': {
            'total_types': len(call_types),
            'distribution': dict(call_types)
        },
        'detailed_analysis': type_details
    }


def _find_matching_category(call_type: str, categories: Dict) -> Optional[Dict]:
    """
    Trova la categoria corrispondente al tipo di chiamata.
    
    Args:
        call_type: Tipo di chiamata da cercare
        categories: Dizionario delle categorie attive
        
    Returns:
        Dizionario della categoria corrispondente o None se non trovata
    """
    for category_key, category_data in categories.items():
        patterns = category_data.get('patterns', [])
        # Verifica se almeno uno dei pattern corrisponde (case-insensitive)
        for pattern in patterns:
            if pattern.lower() == call_type.lower():
                return category_data
    
    return None


def _generate_global_summary_with_markup(contracts: Dict) -> Dict[str, Any]:
    """Genera un sommario globale di tutti i contratti con informazioni sui costi finali."""
    
    total_contracts = len(contracts)
    total_calls = sum(contract['aggregated_metrics']['total_calls'] for contract in contracts.values())
    total_cost = sum(contract['aggregated_metrics']['total_cost_euro'] for contract in contracts.values())
    total_cost_final_user = sum(
        contract['aggregated_metrics']['total_cost_euro_final_user'] for contract in contracts.values()
    )
    total_duration = sum(contract['aggregated_metrics']['total_duration_seconds'] for contract in contracts.values())
    
    # Top contratti per diverse metriche
    most_active_contracts = sorted(
        contracts.items(),
        key=lambda x: x[1]['aggregated_metrics']['total_calls'],
        reverse=True
    )[:10]
    
    most_expensive_contracts = sorted(
        contracts.items(),
        key=lambda x: x[1]['aggregated_metrics']['total_cost_euro_final_user'],
        reverse=True
    )[:10]
    
    highest_average_cost_contracts = sorted(
        contracts.items(),
        key=lambda x: x[1]['aggregated_metrics']['average_call_cost_euro_final_user'],
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
            'total_cost_euro_final_user': round(total_cost_final_user, 2),
            'total_markup_applied': round(total_cost_final_user - total_cost, 2),
            'total_duration_hours': round(total_duration / 3600, 2),
            'average_calls_per_contract': round(total_calls / total_contracts, 2) if total_contracts > 0 else 0,
            'average_cost_per_contract': round(total_cost / total_contracts, 2) if total_contracts > 0 else 0,
            'average_cost_per_contract_final_user': round(total_cost_final_user / total_contracts, 2) if total_contracts > 0 else 0,
            'average_cost_per_call': round(total_cost / total_calls, 4) if total_calls > 0 else 0,
            'average_cost_per_call_final_user': round(total_cost_final_user / total_calls, 4) if total_calls > 0 else 0
        },
        
        'top_contracts': {
            'most_active': [
                {
                    'codice_contratto': contract_id,
                    'total_calls': data['aggregated_metrics']['total_calls'],
                    'total_cost_euro': data['aggregated_metrics']['total_cost_euro'],
                    'total_cost_euro_final_user': data['aggregated_metrics']['total_cost_euro_final_user']
                }
                for contract_id, data in most_active_contracts
            ],
            'most_expensive_final_user': [
                {
                    'codice_contratto': contract_id,
                    'total_cost_euro_final_user': data['aggregated_metrics']['total_cost_euro_final_user'],
                    'total_cost_euro': data['aggregated_metrics']['total_cost_euro'],
                    'total_calls': data['aggregated_metrics']['total_calls']
                }
                for contract_id, data in most_expensive_contracts
            ],
            'highest_average_cost_final_user': [
                {
                    'codice_contratto': contract_id,
                    'average_call_cost_euro_final_user': data['aggregated_metrics']['average_call_cost_euro_final_user'],
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


def print_summary_with_markup(unified_data: Dict) -> None:
    """Stampa un riassunto dell'analisi CDR con informazioni sui markup."""
    summary = unified_data['global_summary']['overview']
    
    print("=== RIASSUNTO ANALISI CDR CON MARKUP ===")
    print(f"Totale contratti: {summary['total_contracts']}")
    print(f"Totale chiamate: {summary['total_calls']}")
    print(f"Costo totale originale: €{summary['total_cost_euro']}")
    print(f"Costo totale finale utente: €{summary['total_cost_euro_final_user']}")
    print(f"Markup totale applicato: €{summary['total_markup_applied']}")
    print(f"Durata totale: {summary['total_duration_hours']} ore")
    print(f"Costo medio per chiamata (originale): €{summary['average_cost_per_call']}")
    print(f"Costo medio per chiamata (finale): €{summary['average_cost_per_call_final_user']}")
    
    print("\n=== TOP 5 CONTRATTI PIÙ COSTOSI (COSTO FINALE) ===")
    for i, contract in enumerate(unified_data['global_summary']['top_contracts']['most_expensive_final_user'][:5], 1):
        print(f"{i}. Contratto {contract['codice_contratto']}: "
              f"€{contract['total_cost_euro_final_user']} (era €{contract['total_cost_euro']}), "
              f"{contract['total_calls']} chiamate")

# ESPORTAZIONE DEI SINGOLI CONTRATTI #########################################################################################
def export_contracts_to_files(unified_data: Dict[str, Any], output_directory: str, 
                              filename_template: str = "{contract_id}_contract.json") -> Dict[str, str]:
    """
    Esporta ogni contratto in un file JSON separato.
    
    Args:
        unified_data: Risultato di analyze_cdr_data_with_markup
        output_directory: Directory dove salvare i file
        filename_template: Template per il nome file. Usa {contract_id} per l'ID contratto
                          Es: "{contract_id}_test.json", "contratto_{contract_id}.json"
        
    Returns:
        Dict con mapping contract_id -> percorso_file_creato
        
    Raises:
        ValueError: Se la directory non esiste o non è accessibile
        OSError: Se non è possibile creare i file
    """
    
    # Verifica che la directory esista
    output_path = Path(output_directory)
    if not output_path.exists():
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Directory creata: {output_directory}")
        except Exception as e:
            raise ValueError(f"Impossibile creare la directory '{output_directory}': {e}")
    
    if not output_path.is_dir():
        raise ValueError(f"'{output_directory}' non è una directory")
    
    # Verifica che ci siano contratti da esportare
    contracts = unified_data.get('contracts', {})
    if not contracts:
        print("⚠️ Nessun contratto trovato nei dati forniti")
        return {}
    
    # Dizionario per tenere traccia dei file creati
    created_files = {}
    
    # Esporta ogni contratto
    for contract_id, contract_data in contracts.items():
        try:
            # Genera il nome del file
            filename = filename_template.format(contract_id=contract_id)
            file_path = output_path / filename
            
            # Crea la struttura dati per il singolo contratto
            single_contract_data = {
                'metadata': {
                    'exported_timestamp': datetime.now().isoformat(),
                    'contract_id': contract_id,
                    'source_analysis': unified_data.get('metadata', {}),
                    'export_info': {
                        'filename': filename,
                        'export_directory': str(output_directory)
                    }
                },
                'contract_data': contract_data
            }
            
            # Salva il file JSON
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(single_contract_data, file, indent=2, ensure_ascii=False)
            
            created_files[contract_id] = str(file_path)
            print(f"✅ Contratto {contract_id} esportato: {file_path}")
            
        except Exception as e:
            print(f"❌ Errore nell'esportazione del contratto {contract_id}: {e}")
            continue
    
    # Riepilogo
    # print(f"\n📊 RIEPILOGO ESPORTAZIONE:")
    # print(f"Contratti totali: {len(contracts)}")
    # print(f"File creati con successo: {len(created_files)}")
    # print(f"Directory di output: {output_directory}")
    
    return created_files


def export_single_contract(unified_data: Dict[str, Any], contract_id: str, 
                          output_file_path: str) -> bool:
    """
    Esporta un singolo contratto specificato in un file JSON.
    
    Args:
        unified_data: Risultato di analyze_cdr_data_with_markup
        contract_id: ID del contratto da esportare
        output_file_path: Percorso completo del file da creare
        
    Returns:
        True se l'esportazione è riuscita, False altrimenti
    """
    
    contracts = unified_data.get('contracts', {})
    
    # Verifica che il contratto esista
    if contract_id not in contracts:
        print(f"❌ Contratto {contract_id} non trovato nei dati")
        available_contracts = list(contracts.keys())
        print(f"Contratti disponibili: {available_contracts}")
        return False
    
    try:
        # Crea la directory se non esiste
        output_path = Path(output_file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Crea la struttura dati per il singolo contratto
        single_contract_data = {
            'metadata': {
                'exported_timestamp': datetime.now().isoformat(),
                'contract_id': contract_id,
                'source_analysis': unified_data.get('metadata', {}),
                'export_info': {
                    'filename': output_path.name,
                    'export_directory': str(output_path.parent)
                }
            },
            'contract_data': contracts[contract_id]
        }
        
        # Salva il file JSON
        with open(output_file_path, 'w', encoding='utf-8') as file:
            json.dump(single_contract_data, file, indent=2, ensure_ascii=False)
        
        print(f"✅ Contratto {contract_id} esportato: {output_file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Errore nell'esportazione del contratto {contract_id}: {e}")
        return False


def export_contracts_summary(unified_data: Dict[str, Any], output_file_path: str) -> bool:
    """
    Esporta un riepilogo di tutti i contratti con le metriche principali.
    
    Args:
        unified_data: Risultato di analyze_cdr_data_with_markup
        output_file_path: Percorso del file di riepilogo da creare
        
    Returns:
        True se l'esportazione è riuscita, False altrimenti
    """
    
    try:
        contracts = unified_data.get('contracts', {})
        
        # Crea il riepilogo
        summary_data = {
            'metadata': {
                'exported_timestamp': datetime.now().isoformat(),
                'total_contracts': len(contracts),
                'source_analysis': unified_data.get('metadata', {}),
                'export_info': {
                    'type': 'contracts_summary',
                    'filename': Path(output_file_path).name
                }
            },
            'global_summary': unified_data.get('global_summary', {}),
            'contracts_overview': {}
        }
        
        # Estrae le metriche principali per ogni contratto
        for contract_id, contract_data in contracts.items():
            contract_info = contract_data.get('contract_info', {})
            aggregated_metrics = contract_data.get('aggregated_metrics', {})
            
            summary_data['contracts_overview'][contract_id] = {
                'codice_contratto': contract_info.get('codice_contratto'),
                'total_calls': aggregated_metrics.get('total_calls', 0),
                'total_duration_hours': aggregated_metrics.get('total_duration_hours', 0),
                'total_cost_euro': aggregated_metrics.get('total_cost_euro', 0),
                'total_cost_euro_final_user': aggregated_metrics.get('total_cost_euro_final_user', 0),
                'average_call_cost_euro_final_user': aggregated_metrics.get('average_call_cost_euro_final_user', 0),
                'date_range': contract_info.get('date_range', {}),
                'unique_calling_numbers': contract_info.get('unique_calling_numbers', 0),
                'unique_called_numbers': contract_info.get('unique_called_numbers', 0)
            }
        
        # Crea la directory se non esiste
        output_path = Path(output_file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Salva il file JSON
        with open(output_file_path, 'w', encoding='utf-8') as file:
            json.dump(summary_data, file, indent=2, ensure_ascii=False)
        
        print(f"✅ Riepilogo contratti esportato: {output_file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Errore nell'esportazione del riepilogo: {e}")
        return False


# Funzione di utilità per generare nomi file personalizzati
def generate_contract_filename(contract_id: str, suffix: str = "contract", 
                              extension: str = "json") -> str:
    """
    Genera un nome file per il contratto.
    
    Args:
        contract_id: ID del contratto
        suffix: Suffisso da aggiungere al nome
        extension: Estensione del file (senza punto)
        
    Returns:
        Nome del file generato
    """
    return f"{contract_id}_{suffix}.{extension}"

# CONVERTE IL CDR IN JSON #################################################################################################################################

def convert_cdr_to_json(input_file_path: str, output_file_path: Optional[str] = None, 
                       encoding: str = 'utf-8') -> Dict[str, Any]:
    """
    Converte un singolo file CDR in formato JSON.
    
    Args:
        input_file_path: Percorso del file CDR da convertire
        output_file_path: Percorso del file JSON di output (opzionale)
        encoding: Encoding del file CDR (default: utf-8)
        
    Returns:
        Dict contenente i dati convertiti in formato JSON
        
    Raises:
        FileNotFoundError: Se il file CDR non esiste
        ValueError: Se il file ha formato non valido
    """
    
    # Verifica che il file esista
    input_path = Path(input_file_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Il file CDR '{input_file_path}' non esiste")
    
    # Leggi e converti il file
    try:
        with open(input_file_path, 'r', encoding=encoding) as file:
            lines = file.readlines()
    except Exception as e:
        raise ValueError(f"Errore nella lettura del file '{input_file_path}': {e}")
    
    # Converte le righe in record JSON
    records = []
    for line_number, line in enumerate(lines, 1):
        line = line.strip()
        if not line:  # Salta righe vuote
            continue
            
        try:
            record = _parse_cdr_line(line, line_number)
            if record:
                records.append(record)
        except Exception as e:
            print(f"⚠️ Errore nella riga {line_number}: {e}")
            continue
    
    # Crea la struttura JSON finale
    json_data = {
        "metadata": {
            "source_file": input_path.name,
            "conversion_timestamp": datetime.now().isoformat(),
            "total_records": len(records),
            "file_type": "CDR"
        },
        "records": records
    }
    
    # Salva il file JSON se specificato
    if output_file_path:
        _save_json_file(json_data, output_file_path)
        print(f"✅ File convertito: {output_file_path}")
    
    return json_data


def convert_multiple_cdr_to_json(input_files: List[str], output_directory: str, 
                                encoding: str = 'utf-8') -> Dict[str, str]:
    """
    Converte più file CDR in formato JSON.
    
    Args:
        input_files: Lista dei percorsi dei file CDR da convertire
        output_directory: Directory dove salvare i file JSON
        encoding: Encoding dei file CDR (default: utf-8)
        
    Returns:
        Dict con mapping file_cdr -> file_json_creato
    """
    
    # Crea la directory di output se non esiste
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    
    converted_files = {}
    
    for input_file in input_files:
        try:
            input_path = Path(input_file)
            
            # Genera il nome del file JSON
            json_filename = input_path.stem + '.json'
            output_file = output_path / json_filename
            
            # Converte il file
            convert_cdr_to_json(input_file, str(output_file), encoding)
            converted_files[input_file] = str(output_file)
            
        except Exception as e:
            print(f"❌ Errore nella conversione di '{input_file}': {e}")
            continue
    
    # print(f"\n📊 RIEPILOGO CONVERSIONE:")
    # print(f"File processati: {len(input_files)}")
    # print(f"Conversioni riuscite: {len(converted_files)}")
    # print(f"Directory di output: {output_directory}")
    
    return converted_files


def convert_cdr_directory(input_directory: str, output_directory: str, 
                         file_pattern: str = "*.CDR", encoding: str = 'utf-8') -> Dict[str, str]:
    """
    Converte tutti i file CDR di una directory in formato JSON.
    
    Args:
        input_directory: Directory contenente i file CDR
        output_directory: Directory dove salvare i file JSON
        file_pattern: Pattern per i file da convertire (default: *.CDR)
        encoding: Encoding dei file CDR (default: utf-8)
        
    Returns:
        Dict con mapping file_cdr -> file_json_creato
    """
    
    input_path = Path(input_directory)
    if not input_path.exists():
        raise FileNotFoundError(f"Directory '{input_directory}' non esiste")
    
    # Trova tutti i file CDR
    cdr_files = list(input_path.glob(file_pattern))
    
    if not cdr_files:
        print(f"⚠️ Nessun file trovato con pattern '{file_pattern}' in '{input_directory}'")
        return {}
    
    print(f"📁 Trovati {len(cdr_files)} file CDR da convertire")
    
    # Converte tutti i file
    return convert_multiple_cdr_to_json([str(f) for f in cdr_files], output_directory, encoding)


def _parse_cdr_line(line: str, line_number: int) -> Optional[Dict[str, Any]]:
    """
    Converte una riga CDR in un record JSON.
    
    Formato atteso:
    data_ora;numero_chiamante;numero_chiamato;durata;tipo_chiamata;operatore;costo;codice_contratto;codice_servizio;cliente_finale;prefisso;flag
    """
    
    # Rimuovi spazi e dividi per punto e virgola
    parts = [part.strip() for part in line.split(';')]
    
    # Verifica che ci siano almeno 11 campi (il flag finale può essere opzionale)
    if len(parts) < 11:
        raise ValueError(f"Formato riga non valido: attesi almeno 11 campi, trovati {len(parts)}")
    
    try:
        # Parsing dei campi
        data_ora_chiamata = parts[0]
        numero_chiamante = parts[1]
        numero_chiamato = parts[2]
        durata_secondi = int(parts[3])
        tipo_chiamata = parts[4]
        operatore = parts[5]
        
        # Parsing del costo (formato europeo con virgola)
        costo_str = parts[6].replace(',', '.')
        costo_euro = float(costo_str) if costo_str else 0.0
        
        codice_contratto = int(parts[7])
        codice_servizio = int(parts[8])
        cliente_finale_comune = parts[9]
        prefisso_chiamato = parts[10]
        
        # Campo flag opzionale (ultima colonna)
        flag = parts[11] if len(parts) > 11 else "0"
        
        # Crea il record JSON
        record = {
            "data_ora_chiamata": data_ora_chiamata,
            "numero_chiamante": numero_chiamante,
            "numero_chiamato": numero_chiamato,
            "durata_secondi": durata_secondi,
            "tipo_chiamata": tipo_chiamata,
            "operatore": operatore,
            "costo_euro": round(costo_euro, 3),
            "codice_contratto": codice_contratto,
            "codice_servizio": codice_servizio,
            "cliente_finale_comune": cliente_finale_comune,
            "prefisso_chiamato": prefisso_chiamato,
            "record_number": line_number,
            "raw_line": line
        }
        
        return record
        
    except (ValueError, IndexError) as e:
        raise ValueError(f"Errore nel parsing della riga: {e}")


def _save_json_file(data: Dict[str, Any], output_path: str) -> None:
    """Salva i dati in formato JSON con formattazione corretta."""
    
    try:
        # Crea la directory se non esiste
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Salva il file JSON
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            
    except Exception as e:
        raise ValueError(f"Errore nel salvataggio del file JSON '{output_path}': {e}")


def merge_cdr_files_to_json(input_files: List[str], output_file_path: str, 
                           encoding: str = 'utf-8') -> Dict[str, Any]:
    """
    Unisce più file CDR in un singolo file JSON.
    
    Args:
        input_files: Lista dei percorsi dei file CDR da unire
        output_file_path: Percorso del file JSON unificato di output
        encoding: Encoding dei file CDR (default: utf-8)
        
    Returns:
        Dict contenente tutti i dati unificati
    """
    
    all_records = []
    source_files = []
    total_records_per_file = {}
    
    for input_file in input_files:
        try:
            print(f"📄 Processando: {input_file}")
            
            # Converte il singolo file
            json_data = convert_cdr_to_json(input_file, encoding=encoding)
            
            # Aggiunge i record alla lista totale
            file_records = json_data['records']
            all_records.extend(file_records)
            
            # Tracking dei file sorgente
            source_files.append(Path(input_file).name)
            total_records_per_file[Path(input_file).name] = len(file_records)
            
        except Exception as e:
            print(f"❌ Errore nel processare '{input_file}': {e}")
            continue
    
    # Crea la struttura JSON unificata
    unified_data = {
        "metadata": {
            "source_files": source_files,
            "conversion_timestamp": datetime.now().isoformat(),
            "total_records": len(all_records),
            "total_source_files": len(source_files),
            "records_per_file": total_records_per_file,
            "file_type": "CDR_UNIFIED"
        },
        "records": all_records
    }
    
    # Salva il file unificato
    _save_json_file(unified_data, output_file_path)
    
    print(f"\n✅ File unificato creato: {output_file_path}")
    print(f"📊 Record totali: {len(all_records)}")
    print(f"📁 File sorgente: {len(source_files)}")
    
    return unified_data


def validate_cdr_file(file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
    """
    Valida un file CDR e restituisce statistiche.
    
    Args:
        file_path: Percorso del file CDR da validare
        encoding: Encoding del file (default: utf-8)
        
    Returns:
        Dict con statistiche di validazione
    """
    
    stats = {
        "file_path": file_path,
        "is_valid": True,
        "total_lines": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "empty_lines": 0,
        "errors": []
    }
    
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            lines = file.readlines()
        
        stats["total_lines"] = len(lines)
        
        for line_number, line in enumerate(lines, 1):
            line = line.strip()
            
            if not line:
                stats["empty_lines"] += 1
                continue
            
            try:
                _parse_cdr_line(line, line_number)
                stats["valid_records"] += 1
            except Exception as e:
                stats["invalid_records"] += 1
                stats["errors"].append({
                    "line": line_number,
                    "error": str(e),
                    "content": line[:100] + "..." if len(line) > 100 else line
                })
        
        if stats["invalid_records"] > 0:
            stats["is_valid"] = False
            
    except Exception as e:
        stats["is_valid"] = False
        stats["errors"].append({"general_error": str(e)})
    
    return stats

def complete_cdr_conversion(files: str, codifica):
    if files:
        import re
        from dotenv import load_dotenv
        from config import SecureConfig
        load_dotenv()
        secure_config = SecureConfig()
        
        output_path = secure_config.get_config().get('output_directory')
        analytics_output_folder = secure_config.get_config().get('analytics_output_folder')
        percorso_save = os.path.join(output_path, 'json_from_cdr')
        percorso_cdr = os.path.join(output_path, 'ftp_cdr')
        os.makedirs(percorso_save, exist_ok=True)
        cdr_files = [os.path.join(percorso_cdr, f) for f in files]
        converted = convert_multiple_cdr_to_json(cdr_files, percorso_save, codifica)    
        
        for file in files:
            match = re.search(r'MESE_(\d{2})_(\d{4})', file)
            if match:
                check_file = os.path.join(percorso_cdr, file)
                if os.path.exists(check_file):
                    mese = match.group(1)
                    anno = match.group(2)
                    anno_str = str(anno)
                    mese_str = str(mese).zfill(2)  # oppure: f"{mese:02}"
                    new_foldere = os.path.join(analytics_output_folder, anno_str, mese_str)
                    year_folder = os.path.join(analytics_output_folder, anno_str)
                    os.makedirs(new_foldere, exist_ok=True)
                    json_file = file.replace(".CDR", ".json")
                    
                    #Creo il json granulare mensile 
                    unified_data_with_markup_file = os.path.join(percorso_save, json_file)
                    categories_file = "config/cdr_categories.json"
                    unified_data_with_markup = analyze_cdr_data_with_markup(unified_data_with_markup_file, categories_file)
                    output_file_with_markup = os.path.join(year_folder, json_file)
                    save_unified_data(unified_data_with_markup, output_file_with_markup)
                    
                    #Creo il json granulare per ogni singolo contratto
                    created_files = export_contracts_to_files(unified_data_with_markup, new_foldere, '{contract_id}_report.json')
                    print(f"{created_files}" )

        return converted
    

# Esempi di utilizzo
if __name__ == "__main__":
    test = complete_cdr_conversion(['RIV_12345_MESE_05_2025-05-05-14.16.27.CDR',
                                    'RIV_12345_MESE_06_2025-06-05-14.16.27.CDR',
                                    'RIV_12345_MESE_07_2025-07-05-14.16.27.CDR',
                                    'RIV_12345_MESE_08_2025-08-05-14.16.27.CDR',
                                    'RIV_15232_MESE_11_2024-12-03-13.27.02.CDR',                                        
                                    ], 'latin-1')
    print(test)
    
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


    print(file_list[0])
  
    # # Analizza i dati
    input_file = file_list[0]  # Sostituisci con il tuo percorso
    
    try:
        # Analizza e unifica i dati
        
        unified_data = analyze_cdr_data(input_file)

        categories_file = "config/cdr_categories.json"
        unified_data_with_markup = analyze_cdr_data_with_markup(input_file, categories_file)

        # unified_data = json.loads(unified_data)
        print(unified_data)
        # # Stampa il riassunto
        # unified_data = json.loads(unified_data)
        # print_summary(unified_data)
        
        # # Salva i dati unificati
        output_file = "cdr_unified_analysis.json"
        output_file_with_markup = "cdr_unified_analysis_with_markup.json"
        save_unified_data(unified_data, output_file)
        save_unified_data(unified_data_with_markup, output_file_with_markup)
        # print(f"\nDati unificati salvati in: {output_file}")
        
        # # Esempio: accesso ai dati di un contratto specifico
        # contract_id = "63"
        # if contract_id in unified_data['contracts']:
        #     contract = unified_data['contracts'][contract_id]
        #     print(f"\n=== CONTRATTO {contract_id} ===")
        #     print(f"Record originali: {len(contract['original_records'])}")
        #     print(f"Chiamate totali: {contract['aggregated_metrics']['total_calls']}")
        #     print(f"Costo totale: €{contract['aggregated_metrics']['total_cost_euro']}")
    

        created_files = export_contracts_to_files(unified_data_with_markup, 'output/contratestcts', '{contract_id}_report.json')
        print(created_files)

    except FileNotFoundError:
        print(f"File non trovato: {input_file}")
    except Exception as e:
        print(f"Errore durante l'analisi: {e}")
