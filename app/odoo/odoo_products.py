"""
Odoo Products Manager v18.2+
Gestione prodotti, servizi e termini di pagamento
"""
from typing import List, Dict, Any
from .odoo_client import OdooClient
from .odoo_exceptions import OdooDataError

try:
    from logger_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

class OdooProductManager:
    """Manager per la gestione di prodotti e servizi Odoo"""
    
    def __init__(self, client: OdooClient):
        self.client = client
        self.logger = get_logger(__name__)
    
    def get_payment_terms(self) -> List[Dict[str, Any]]:
        """Modalità di pagamento per 18.2+"""
        try:
            payment_terms = self.client.execute(
                'account.payment.term',
                'search_read',
                [('active', '=', True)],
                fields=['id', 'name', 'note'],
                order='name asc'
            )
            
            result = []
            for term in payment_terms:
                result.append({
                    'id': term['id'],
                    'name': term['name'],
                    'note': term.get('note', ''),
                    'display_name': f"{term['name']}" + (f" - {term['note']}" if term.get('note') else "")
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Errore recupero modalità pagamento: {e}")
            raise OdooDataError(f"Errore modalità pagamento: {e}")
    
    def get_all_payment_terms_for_select(self) -> List[Dict[str, Any]]:
        """Payment Terms per Select2 ottimizzato per 18.2+"""
        try:
            search_filters = [('active', '=', True)]
            context = {'active_test': False}
            
            # Prima cerca gli ID con ordinamento
            payment_term_ids = self.client.execute(
                'account.payment.term',
                'search',
                search_filters,
                order='name asc',
                context=context
            )
            
            if not payment_term_ids:
                return []
            
            # Poi leggi i dati necessari
            payment_terms_data = self.client.execute(
                'account.payment.term',
                'read',
                payment_term_ids,
                fields=['id', 'name', 'display_name'],
                context=context
            )
            
            select_payment_terms = []
            for payment_term in payment_terms_data:
                select_payment_terms.append({
                    'id': payment_term.get('id'),
                    'name': payment_term.get('name', ''),
                    'display_name': payment_term.get('display_name', payment_term.get('name', ''))
                })
            
            self.logger.info(f"Recuperati {len(select_payment_terms)} payment terms per Select2")
            return select_payment_terms
            
        except Exception as e:
            self.logger.error(f"Errore recupero payment terms per Select2: {e}")
            raise OdooDataError(f"Errore recupero payment terms per Select2: {e}")
    
    def get_all_products_for_select(self) -> List[Dict[str, Any]]:
        """Prodotti per Select2 ottimizzato per 18.2+"""
        try:
            search_filters = [
                ('active', '=', True),
                ('sale_ok', '=', True)  # Solo prodotti vendibili
            ]
            
            context = {'active_test': False}
            
            # Prima cerca gli ID con ordinamento
            product_ids = self.client.execute(
                'product.product',
                'search',
                search_filters,
                order='name asc',
                context=context
            )
            
            if not product_ids:
                return []
            
            # Poi leggi i dati necessari
            products_data = self.client.execute(
                'product.product',
                'read',
                product_ids,
                fields=['id', 'name', 'display_name', 'default_code', 'list_price', 'uom_name'],
                context=context
            )
            
            select_products = []
            for product in products_data:
                # Costruisci un display_name più informativo se disponibile
                display_name = product.get('display_name', product.get('name', ''))
                if product.get('default_code'):
                    display_name = f"[{product['default_code']}] {display_name}"
                
                select_products.append({
                    'id': product.get('id'),
                    'name': product.get('name', ''),
                    'display_name': display_name,
                    'default_code': product.get('default_code', ''),
                    'list_price': product.get('list_price', 0.0),
                    'uom_name': product.get('uom_name', '')
                })
            
            self.logger.info(f"Recuperati {len(select_products)} prodotti per Select2")
            return select_products
            
        except Exception as e:
            self.logger.error(f"Errore recupero prodotti per Select2: {e}")
            raise OdooDataError(f"Errore recupero prodotti per Select2: {e}")