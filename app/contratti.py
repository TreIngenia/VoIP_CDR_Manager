#!/usr/bin/env python3
"""
CDR Contracts Service - Servizio per gestire i dati dei contratti CDR
Converte i dati per DataTables in formato serverside e ajax
"""
import requests
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class CDRContractsService:
    """Servizio per gestire i contratti CDR e convertirli per DataTables"""
    
    def __init__(self, app=None):
        """
        Inizializza il servizio
        
        Args:
            app: Istanza Flask per determinare automaticamente l'URL
        """
        self.app = app
        self.contracts_api_url = "/api/cdr/contracts_config"  # URL relativo
    
    def _fetch_contracts_data(self) -> Optional[Dict[str, Any]]:
        """
        Recupera i dati dei contratti dall'API usando richiesta interna Flask
        
        Returns:
            Dict con i dati dei contratti o None se errore
        """
        try:
            if not self.app:
                logger.error("App Flask non disponibile per richiesta interna")
                return None
            
            logger.info(f"Recuperando dati contratti da: {self.contracts_api_url}")
            
            # Usa il test client di Flask per richieste interne
            with self.app.test_client() as client:
                response = client.get(self.contracts_api_url)
                
                if response.status_code != 200:
                    logger.error(f"API response status: {response.status_code}")
                    return None
                
                data = response.get_json()
                
                if not data.get('success', False):
                    logger.error(f"API response non successful: {data.get('message', 'Unknown error')}")
                    return None
                
                return data.get('data', {})
            
        except Exception as e:
            logger.error(f"Errore nella richiesta API interna: {e}")
            return None
    
    def _extract_contract_fields(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estrae i campi necessari da un singolo contratto
        
        Args:
            contract_data: Dati del singolo contratto
            
        Returns:
            Dict con i campi estratti
        """
        try:
            # Estrai il primo numero di telefono dall'array phone_numbers
            phone_numbers = contract_data.get('phone_numbers', [])
            # first_phone = phone_numbers[0] if phone_numbers and len(phone_numbers) > 0 else ""
            first_phone = phone_numbers
            # Gestisci valori None o mancanti
            contract_code = contract_data.get('contract_code', "")
            contract_name = contract_data.get('contract_name', "")
            odoo_client_id = contract_data.get('odoo_client_id', "")
            contract_type = contract_data.get('contract_type', "")
            payment_term = contract_data.get('payment_term', "")
            notes = contract_data.get('notes', "")
            
            # Assicurati che tutti i valori siano stringhe per evitare errori di serializzazione
            return {
                'contract_code': str(contract_code) if contract_code is not None else "",
                'phone_number': str(first_phone) if first_phone is not None else "",
                'contract_name': str(contract_name) if contract_name is not None else "",
                'odoo_client_id': str(odoo_client_id) if odoo_client_id is not None else "",
                'contract_type': str(contract_type) if contract_type is not None else "",
                'payment_term': str(payment_term) if payment_term is not None else "",
                'notes': str(notes) if notes is not None else ""
            }
            
        except Exception as e:
            logger.error(f"Errore estrazione campi contratto: {e}")
            # Restituisci campi vuoti in caso di errore
            return {
                'contract_code': "",
                'phone_number': "",
                'contract_name': "",
                'odoo_client_id': "",
                'contract_type': "",
                'payment_term':"",
                'notes': ""
            }
    
    def get_contracts_for_ajax(self) -> Dict[str, Any]:
        """
        Converte i dati dei contratti nel formato AJAX per DataTables
        
        Returns:
            Dict nel formato richiesto per DataTables AJAX
        """
        try:
            logger.info("Preparazione dati contratti per formato AJAX")
            
            # Recupera dati dall'API
            api_data = self._fetch_contracts_data()
            if not api_data:
                logger.error("Impossibile recuperare dati dall'API")
                return {'data': []}
            
            # Estrai i contratti
            contracts = api_data.get('contracts', {})
            if not contracts:
                logger.warning("Nessun contratto trovato nei dati")
                return {'data': []}
            
            # Converti ogni contratto nel formato richiesto
            ajax_data = []
            
            for contract_id, contract_info in contracts.items():
                try:
                    extracted_fields = self._extract_contract_fields(contract_info)
                    
                    # Formato AJAX: oggetto con campi nominati
                    contract_ajax = {
                        'id': contract_id,
                        'contract_code': extracted_fields['contract_code'],
                        'phone_number': extracted_fields['phone_number'],
                        'contract_name': extracted_fields['contract_name'],
                        'odoo_client_id': extracted_fields['odoo_client_id'],
                        'contract_type': extracted_fields['contract_type'],
                        'payment_term': extracted_fields['payment_term'],
                        'notes': extracted_fields['notes']
                    }
                    
                    ajax_data.append(contract_ajax)
                    
                except Exception as e:
                    logger.error(f"Errore elaborazione contratto {contract_id}: {e}")
                    continue
            
            logger.info(f"Convertiti {len(ajax_data)} contratti in formato AJAX")
            
            return {
                'data':ajax_data,
                # 'recordsTotal': len(ajax_data),
                # 'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Errore nella conversione AJAX: {e}")
            return {'data': []}
    
    def get_contracts_for_serverside(self, draw: int = 1, start: int = 0, 
                                   length: int = 10, search_value: str = "",
                                   order_column: int = 0, order_dir: str = "asc") -> Dict[str, Any]:
        """
        Converte i dati dei contratti nel formato Server-side per DataTables
        
        Args:
            draw: Numero richiesta DataTables
            start: Indice di partenza per la paginazione
            length: Numero di record per pagina
            search_value: Valore di ricerca
            order_column: Indice colonna per ordinamento
            order_dir: Direzione ordinamento (asc/desc)
            
        Returns:
            Dict nel formato richiesto per DataTables Server-side
        """
        try:
            logger.info(f"Preparazione dati contratti per formato Server-side - draw: {draw}, start: {start}, length: {length}")
            
            # Recupera dati dall'API
            api_data = self._fetch_contracts_data()
            if not api_data:
                logger.error("Impossibile recuperare dati dall'API")
                return {
                    'draw': draw,
                    'recordsTotal': 0,
                    'recordsFiltered': 0,
                    'data': []
                }
            
            # Estrai i contratti
            contracts = api_data.get('contracts', {})
            if not contracts:
                logger.warning("Nessun contratto trovato nei dati")
                return {
                    'draw': draw,
                    'recordsTotal': 0,
                    'recordsFiltered': 0,
                    'data': []
                }
            
            # Converti ogni contratto in array per server-side
            all_data = []
            
            for contract_id, contract_info in contracts.items():
                try:
                    extracted_fields = self._extract_contract_fields(contract_info)
                    
                    # Formato Server-side: array di valori
                    contract_array = [
                        extracted_fields['contract_code'],
                        extracted_fields['phone_number'],
                        extracted_fields['contract_name'],
                        extracted_fields['odoo_client_id'],
                        extracted_fields['contract_type'],
                        extracted_fields['notes']
                    ]
                    
                    all_data.append(contract_array)
                    
                except Exception as e:
                    logger.error(f"Errore elaborazione contratto {contract_id}: {e}")
                    continue
            
            # Applica filtro di ricerca se presente
            filtered_data = all_data
            if search_value and search_value.strip():
                search_lower = search_value.lower().strip()
                filtered_data = []
                
                for row in all_data:
                    # Cerca in tutti i campi della riga
                    row_text = " ".join(str(cell).lower() for cell in row)
                    if search_lower in row_text:
                        filtered_data.append(row)
            
            # Applica ordinamento
            if order_column < len(filtered_data[0]) if filtered_data else False:
                reverse_order = (order_dir.lower() == 'desc')
                try:
                    filtered_data.sort(key=lambda x: str(x[order_column]).lower(), reverse=reverse_order)
                except Exception as e:
                    logger.warning(f"Errore ordinamento: {e}")
            
            # Applica paginazione
            total_records = len(all_data)
            total_filtered = len(filtered_data)
            
            end_index = start + length
            paginated_data = filtered_data[start:end_index]
            
            logger.info(f"Server-side: {total_records} totali, {total_filtered} filtrati, {len(paginated_data)} in pagina")
            
            return {
                'draw': draw,
                'recordsTotal': total_records,
                'recordsFiltered': total_filtered,
                'data': paginated_data
            }
            
        except Exception as e:
            logger.error(f"Errore nella conversione Server-side: {e}")
            return {
                'draw': draw,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': []
            }
    
    def get_contracts_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto dei contratti
        
        Returns:
            Dict con statistiche sui contratti
        """
        try:
            api_data = self._fetch_contracts_data()
            if not api_data:
                return {'error': 'Impossibile recuperare dati'}
            
            contracts = api_data.get('contracts', {})
            metadata = api_data.get('metadata', {})
            
            # Calcola statistiche
            total_contracts = len(contracts)
            contracts_with_name = sum(1 for c in contracts.values() if c.get('contract_name', '').strip())
            contracts_with_odoo_id = sum(1 for c in contracts.values() if c.get('odoo_client_id', '').strip())
            contracts_with_phone = sum(1 for c in contracts.values() if c.get('phone_numbers', []))
            
            return {
                'total_contracts': total_contracts,
                'contracts_with_name': contracts_with_name,
                'contracts_with_odoo_id': contracts_with_odoo_id,
                'contracts_with_phone': contracts_with_phone,
                'last_updated': metadata.get('last_updated', ''),
                'version': metadata.get('version', ''),
                'source': 'CDR Contracts API'
            }
            
        except Exception as e:
            logger.error(f"Errore nel calcolo statistiche: {e}")
            return {'error': str(e)}


# Factory function per creare il servizio
def create_contracts_service(app=None) -> CDRContractsService:
    """
    Crea un'istanza del servizio contratti
    
    Args:
        app: Istanza Flask per richieste interne
        
    Returns:
        Istanza di CDRContractsService
    """
    return CDRContractsService(app)


class ElaborazioneContratti:
    """Classe per elaborare contratti recuperati da API"""
    
    def __init__(self, api_url: str = "http://127.0.0.1:5001/api/contracts/datatable/ajax"):
        """
        Inizializza la classe
        
        Args:
            api_url: URL dell'API per recuperare i contratti
        """
        self.api_url = api_url
    
    def elabora_tutti_contratti(self, processor_func: Callable, timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Recupera contratti dall'API e processa quelli validi
        
        Args:
            processor_func: Funzione che riceve (contract_code, contract_type, odoo_client_id)
            timeout: Timeout richiesta in secondi
            
        Returns:
            Lista risultati elaborazione
        """
        try:
            # Recupera dati dall'API
            logger.info(f"🌐 Recupero contratti da: {self.api_url}")
            response = requests.get(self.api_url, timeout=timeout)
            response.raise_for_status()
            
            contracts = response.json().get('data', [])
            logger.info(f"📊 Contratti ricevuti: {len(contracts)}")
            
            # Filtra e processa contratti validi
            results = []
            valid_count = 0
            
            for contract in contracts:
                # Verifica validità
                odoo_id = contract.get('odoo_client_id', '').strip()
                contract_type = contract.get('contract_type', '').strip()
                contract_code = contract.get('contract_code', '')
                
                if not odoo_id or not contract_type:
                    logger.debug(f"⚠️ Contratto {contract_code} saltato: odoo_id='{odoo_id}', type='{contract_type}'")
                    continue
                
                # Processa contratto valido
                try:
                    valid_count += 1
                    result = processor_func(contract_code, contract_type, odoo_id)
                    results.append(result)
                    logger.info(f"✅ Processato contratto {contract_code}")
                    
                except Exception as e:
                    logger.error(f"❌ Errore processing {contract_code}: {e}")
                    results.append({
                        'contract_code': contract_code,
                        'error': str(e),
                        'status': 'failed'
                    })
            
            logger.info(f"🎯 Completato: {valid_count}/{len(contracts)} contratti validi processati")
            return results
            
        except Exception as e:
            logger.error(f"❌ Errore generale: {e}")
            return []
        
    def elabora_tutti_contratti_get(self, timeout: int = 30) -> Dict[str, Any]:
        print(self.api_url)
        """
        Elabora tutti i contratti validi - VERSIONE SEMPLIFICATA
        
        Args:
            timeout: Timeout in secondi
            
        Returns:
            Dict con risultati
        """
        try:
            logger.info(f"🔄 Elaborazione contratti...")
            
            # Recupera contratti
            response = requests.get(self.api_url, timeout=timeout)
            contracts = response.json().get('data', [])
            
            # Elabora contratti validi
            results = []
            # print(contracts)
            for contract in contracts:
                odoo_id = contract.get('odoo_client_id', '').strip()
                contract_type = contract.get('contract_type', '').strip()
                contract_code = contract.get('contract_code', '')
                
                if odoo_id and contract_type:  # Se valido
                    # QUI AGGIUNGI LA TUA LOGICA:
                    # generate_report(contract_code)
                    # send_email(contract_code)
                    # etc.
                    
                    results.append({
                        'contract_code': contract_code,
                        'odoo_id': odoo_id,
                        'contract_type': contract_type,
                        'status': 'ok'
                    })
                    logger.info(f"✅ {contract_code}")
            
            return {
                'success': True,
                'total': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"❌ Errore: {e}")
            return {'success': False, 'error': str(e)}
    
        
    def ottieni_info_contratti(self) -> Dict[str, Any]:
        """
        Ottieni informazioni sui contratti senza processarli
        
        Returns:
            Statistiche sui contratti
        """
        try:
            response = requests.get(self.api_url, timeout=30)
            response.raise_for_status()
            
            contracts = response.json().get('data', [])
            
            # Conta contratti validi/invalidi
            valid = 0
            contract_types = {}
            
            for contract in contracts:
                odoo_id = contract.get('odoo_client_id', '').strip()
                contract_type = contract.get('contract_type', '').strip()
                
                if odoo_id and contract_type:
                    valid += 1
                    contract_types[contract_type] = contract_types.get(contract_type, 0) + 1
            
            return {
                'total': len(contracts),
                'valid': valid,
                'invalid': len(contracts) - valid,
                'types': contract_types
            }
            
        except Exception as e:
            logger.error(f"❌ Errore info contratti: {e}")
            return {'error': str(e)}

class CDRContractsServiceStandalone:
    """Servizio contratti completamente autonomo - senza richieste HTTP"""
    
    def __init__(self, contracts_data_source: Optional[Dict[str, Any]] = None):
        """
        Inizializza il servizio autonomo
        
        Args:
            contracts_data_source: Dati dei contratti già caricati (opzionale)
        """
        self.contracts_data = contracts_data_source
        self._cached_contracts = None
    
    def set_contracts_data(self, contracts_data: Dict[str, Any]) -> None:
        """
        Imposta i dati dei contratti
        
        Args:
            contracts_data: Dizionario con i dati dei contratti
        """
        self.contracts_data = contracts_data
        self._cached_contracts = None  # Reset cache
    
    def load_contracts_from_file(self, file_path: str) -> bool:
        """
        Carica i contratti da un file JSON
        
        Args:
            file_path: Percorso del file JSON con i contratti
            
        Returns:
            True se il caricamento è riuscito, False altrimenti
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.contracts_data = json.load(file)
            self._cached_contracts = None
            logger.info(f"✅ Contratti caricati da file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Errore caricamento file {file_path}: {e}")
            return False
    
    def _extract_contract_fields(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estrae i campi necessari da un singolo contratto
        
        Args:
            contract_data: Dati del singolo contratto
            
        Returns:
            Dict con i campi estratti
        """
        try:
            # Gestisce diversi formati di phone_numbers
            phone_numbers = contract_data.get('phone_numbers', [])
            if isinstance(phone_numbers, list):
                first_phone = phone_numbers[0] if phone_numbers else ""
            else:
                first_phone = str(phone_numbers) if phone_numbers else ""
            
            # Estrae tutti i campi necessari
            contract_code = contract_data.get('contract_code', "")
            contract_name = contract_data.get('contract_name', "")
            odoo_client_id = contract_data.get('odoo_client_id', "")
            contract_type = contract_data.get('contract_type', "")
            payment_term = contract_data.get('payment_term', "")
            notes = contract_data.get('notes', "")
            
            # Assicura che tutti i valori siano stringhe
            return {
                'contract_code': str(contract_code) if contract_code is not None else "",
                'phone_number': str(first_phone) if first_phone is not None else "",
                'contract_name': str(contract_name) if contract_name is not None else "",
                'odoo_client_id': str(odoo_client_id) if odoo_client_id is not None else "",
                'contract_type': str(contract_type) if contract_type is not None else "",
                'payment_term': str(payment_term) if payment_term is not None else "",
                'notes': str(notes) if notes is not None else ""
            }
            
        except Exception as e:
            logger.error(f"Errore estrazione campi contratto: {e}")
            return {
                'contract_code': "",
                'phone_number': "",
                'contract_name': "",
                'odoo_client_id': "",
                'contract_type': "",
                'payment_term': "",
                'notes': ""
            }
    
    def get_contracts_list(self) -> List[Dict[str, Any]]:
        """
        Restituisce la lista dei contratti in formato standard
        
        Returns:
            Lista di contratti con campi estratti
        """
        if not self.contracts_data:
            logger.warning("Nessun dato contratti disponibile")
            return []
        
        if self._cached_contracts is not None:
            return self._cached_contracts
        
        try:
            # Estrae i contratti dal formato API
            contracts = self.contracts_data.get('contracts', {})
            if not contracts:
                logger.warning("Nessun contratto trovato nei dati")
                return []
            
            # Converte ogni contratto nel formato standard
            contracts_list = []
            
            for contract_id, contract_info in contracts.items():
                try:
                    extracted_fields = self._extract_contract_fields(contract_info)
                    
                    # Aggiunge l'ID del contratto
                    contract_standard = {
                        'id': contract_id,
                        **extracted_fields
                    }
                    
                    contracts_list.append(contract_standard)
                    
                except Exception as e:
                    logger.error(f"Errore elaborazione contratto {contract_id}: {e}")
                    continue
            
            # Cache del risultato
            self._cached_contracts = contracts_list
            logger.info(f"📋 Elaborati {len(contracts_list)} contratti")
            
            return contracts_list
            
        except Exception as e:
            logger.error(f"Errore nella conversione contratti: {e}")
            return []


class ElaborazioneContrattiStandalone:
    """Classe per elaborare contratti senza richieste HTTP - Solo funzioni interne"""
    
    def __init__(self, contracts_service: Optional[CDRContractsServiceStandalone] = None):
        """
        Inizializza la classe
        
        Args:
            contracts_service: Istanza del servizio contratti
        """
        self.contracts_service = contracts_service or CDRContractsServiceStandalone()
    
    def set_contracts_data(self, contracts_data: Dict[str, Any]) -> None:
        """
        Imposta i dati dei contratti direttamente
        
        Args:
            contracts_data: Dati dei contratti
        """
        self.contracts_service.set_contracts_data(contracts_data)
    
    def load_contracts_from_file(self, file_path: str) -> bool:
        """
        Carica i contratti da file
        
        Args:
            file_path: Percorso del file JSON
            
        Returns:
            True se caricamento riuscito
        """
        return self.contracts_service.load_contracts_from_file(file_path)
    
    def elabora_tutti_contratti_standalone(self, processor_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Elabora tutti i contratti validi - VERSIONE COMPLETAMENTE AUTONOMA
        
        Args:
            processor_callback: Funzione opzionale per elaborazione personalizzata
                               Riceve il dict del contratto, restituisce il risultato
            
        Returns:
            Dict con risultati elaborazione
        """
        try:
            logger.info(f"🔄 Elaborazione contratti standalone...")
            
            # Recupera contratti tramite funzione interna
            contracts = self.contracts_service.get_contracts_list()
            
            if not contracts:
                logger.warning("Nessun contratto disponibile per l'elaborazione")
                return {
                    'success': True,
                    'total_received': 0,
                    'total_processed': 0,
                    'total_skipped': 0,
                    'total_errors': 0,
                    'results': [],
                    'message': 'Nessun contratto disponibile'
                }
            
            logger.info(f"📊 Contratti da elaborare: {len(contracts)}")
            
            # Elabora contratti validi
            results = []
            valid_count = 0
            invalid_count = 0
            error_count = 0
            
            for contract in contracts:
                try:
                    odoo_id = contract.get('odoo_client_id', '').strip()
                    contract_type = contract.get('contract_type', '').strip()
                    contract_code = contract.get('contract_code', '').strip()
                    contract_name = contract.get('contract_name', '').strip()
                    phone_number = contract.get('phone_number', '').strip()
                    
                    # Verifica validità del contratto
                    if odoo_id and contract_type and contract_code:
                        valid_count += 1
                        
                        # Se c'è un callback personalizzato, usalo
                        if processor_callback and callable(processor_callback):
                            try:
                                custom_result = processor_callback(contract)
                                results.append(custom_result)
                                logger.info(f"✅ Callback completato per contratto {contract_code}")
                                continue
                            except Exception as e:
                                logger.error(f"❌ Errore callback per contratto {contract_code}: {e}")
                                error_count += 1
                                results.append({
                                    'contract_code': contract_code,
                                    'status': 'callback_error',
                                    'error': str(e),
                                    'processed_at': datetime.now().isoformat()
                                })
                                continue
                        
                        # Elaborazione standard (se nessun callback)
                        elaboration_result = self._elabora_contratto_standard(contract)
                        results.append(elaboration_result)
                        logger.info(f"✅ Processato contratto {contract_code} - {contract_name}")
                        
                    else:
                        invalid_count += 1
                        logger.debug(f"⚠️ Contratto {contract_code} saltato: "
                                   f"odoo_id='{odoo_id}', type='{contract_type}', code='{contract_code}'")
                        
                        results.append({
                            'contract_code': contract_code,
                            'contract_name': contract_name,
                            'status': 'skipped',
                            'reason': 'Missing required fields (odoo_id, contract_type, or contract_code)',
                            'missing_fields': {
                                'odoo_id': not bool(odoo_id),
                                'contract_type': not bool(contract_type),
                                'contract_code': not bool(contract_code)
                            },
                            'processed_at': datetime.now().isoformat()
                        })
                
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Errore nell'elaborazione del contratto {contract.get('contract_code', 'Unknown')}: {e}")
                    results.append({
                        'contract_code': contract.get('contract_code', 'Unknown'),
                        'status': 'error',
                        'error': str(e),
                        'processed_at': datetime.now().isoformat()
                    })
            
            # Riepilogo finale
            total_processed = len([r for r in results if r.get('status') == 'processed'])
            logger.info(f"🎯 Elaborazione completata:")
            logger.info(f"   - Totali ricevuti: {len(contracts)}")
            logger.info(f"   - Validi processati: {total_processed}")
            logger.info(f"   - Invalidi/saltati: {invalid_count}")
            logger.info(f"   - Errori: {error_count}")
            
            return {
                'success': True,
                'total_received': len(contracts),
                'total_processed': total_processed,
                'total_skipped': invalid_count,
                'total_errors': error_count,
                'results': results,
                'summary': {
                    'processed_contracts': [r for r in results if r.get('status') == 'processed'],
                    'skipped_contracts': [r for r in results if r.get('status') == 'skipped'],
                    'error_contracts': [r for r in results if r.get('status') == 'error'],
                    'callback_error_contracts': [r for r in results if r.get('status') == 'callback_error']
                },
                'processing_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Errore generale nell'elaborazione: {e}")
            return {
                'success': False, 
                'error': str(e),
                'error_type': 'general_error',
                'processing_timestamp': datetime.now().isoformat()
            }
    
    def _elabora_contratto_standard(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """
        Elaborazione standard di un contratto (da personalizzare)
        
        Args:
            contract: Dati del contratto
            
        Returns:
            Risultato dell'elaborazione
        """
        contract_code = contract.get('contract_code', '')
        contract_name = contract.get('contract_name', '')
        contract_type = contract.get('contract_type', '')
        odoo_id = contract.get('odoo_client_id', '')
        phone_number = contract.get('phone_number', '')
        
        # QUI AGGIUNGI LA TUA LOGICA DI ELABORAZIONE:
        # Esempi:
        # - generate_report(contract_code, contract_type, odoo_id)
        # - send_email(contract_code, contract_name)
        # - update_database(contract_code, odoo_id)
        # - create_invoice(contract_code, contract_type)
        # - sync_with_external_system(odoo_id, contract_data)
        
        # Per ora restituisce un risultato di esempio
        return {
            'contract_code': contract_code,
            'contract_name': contract_name,
            'contract_type': contract_type,
            'odoo_id': odoo_id,
            'phone_number': phone_number,
            'status': 'processed',
            'processed_at': datetime.now().isoformat(),
            'elaboration_notes': f"Contratto {contract_code} elaborato con successo",
            'actions_performed': [
                'validation_completed',
                'data_extracted',
                'processing_logged'
                # Aggiungi qui le azioni che hai effettivamente eseguito
            ]
        }
    
    def get_contracts_statistics(self) -> Dict[str, Any]:
        """
        Ottieni statistiche sui contratti senza elaborarli
        
        Returns:
            Statistiche sui contratti
        """
        try:
            contracts = self.contracts_service.get_contracts_list()
            
            if not contracts:
                return {
                    'total': 0,
                    'valid': 0,
                    'invalid': 0,
                    'types': {},
                    'message': 'Nessun contratto disponibile'
                }
            
            # Conta contratti validi/invalidi
            valid = 0
            contract_types = {}
            odoo_ids = set()
            
            for contract in contracts:
                odoo_id = contract.get('odoo_client_id', '').strip()
                contract_type = contract.get('contract_type', '').strip()
                contract_code = contract.get('contract_code', '').strip()
                
                if odoo_id and contract_type and contract_code:
                    valid += 1
                    contract_types[contract_type] = contract_types.get(contract_type, 0) + 1
                    odoo_ids.add(odoo_id)
            
            return {
                'total': len(contracts),
                'valid': valid,
                'invalid': len(contracts) - valid,
                'types': contract_types,
                'unique_odoo_ids': len(odoo_ids),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Errore calcolo statistiche: {e}")
            return {'error': str(e)}
                
# Esempio di utilizzo
if __name__ == "__main__":
    try:
        print("🧪 Test CDR Contracts Service")
        print("=" * 50)
        print("⚠️  Nota: Per il test completo è necessaria un'istanza Flask attiva")
        print("   Il test può essere eseguito dall'interno dell'applicazione principale")
        # Funzioni.test()
    except Exception as e:
        print(f"❌ Errore nel test: {e}")


    # logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # # Inizializza la classe
    # elaboratore = ElaborazioneContratti()
    
    # # Definisci la tua funzione di elaborazione
    # def my_processor(contract_code: str, contract_type: str, odoo_client_id: str):
    #     """La tua logica di elaborazione"""
    #     print(f"Elaborando: {contract_code} - {contract_type} - Cliente: {odoo_client_id}")
        
    #     # QUI AGGIUNGI LA TUA LOGICA
    #     # Es: generate_report(contract_code, contract_type, odoo_client_id)
        
    #     return {
    #         'contract_code': contract_code,
    #         'status': 'success'
    #     }
    
    # # Visualizza info contratti
    # print("📊 Info contratti:")
    # info = elaboratore.ottieni_info_contratti()
    # print(f"   Totali: {info.get('total', 0)}")
    # print(f"   Validi: {info.get('valid', 0)}")
    # print(f"   Tipi: {info.get('types', {})}")
    
    # # Processa tutti i contratti validi
    # print("\n🔄 Inizio elaborazione...")
    # results = elaboratore.elabora_tutti_contratti(my_processor)
    
    # print(f"\n✅ Elaborati {len(results)} contratti")
    
    # # Mostra primi 3 risultati
    # for result in results[:3]:
    #     print(f"   {result}")