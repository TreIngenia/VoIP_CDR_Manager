#!/usr/bin/env python3
"""
CDR Contracts Service - Servizio per gestire i dati dei contratti CDR
Converte i dati per DataTables in formato serverside e ajax
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

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
            notes = contract_data.get('notes', "")
            
            # Assicurati che tutti i valori siano stringhe per evitare errori di serializzazione
            return {
                'contract_code': str(contract_code) if contract_code is not None else "",
                'phone_number': str(first_phone) if first_phone is not None else "",
                'contract_name': str(contract_name) if contract_name is not None else "",
                'odoo_client_id': str(odoo_client_id) if odoo_client_id is not None else "",
                'contract_type': str(contract_type) if contract_type is not None else "",
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


def test_contracts_service():
    """Funzione di test per il servizio"""
    try:
        print("🧪 Test CDR Contracts Service")
        print("=" * 50)
        print("⚠️  Nota: Per il test completo è necessaria un'istanza Flask attiva")
        print("   Il test può essere eseguito dall'interno dell'applicazione principale")
        
    except Exception as e:
        print(f"❌ Errore nel test: {e}")


if __name__ == "__main__":
    test_contracts_service()