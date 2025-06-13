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
            first_phone = phone_numbers[0] if phone_numbers and len(phone_numbers) > 0 else ""
            
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
            print(contracts)
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