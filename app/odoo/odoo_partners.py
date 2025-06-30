"""
Odoo Partners Manager v18.2+ - VERSIONE MIGLIORATA
Gestione completa dei partner Odoo con rate limiting e gestione errori robusta
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from .odoo_client import OdooClient
from .odoo_exceptions import OdooDataError
from .odoo_utils import retry_on_connection_error, with_rate_limit

try:
    from logger_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

class OdooPartnerManager:
    """Manager per la gestione dei partner Odoo con rate limiting"""
    
    def __init__(self, client: OdooClient):
        self.client = client
        self.logger = get_logger(__name__)
    
    @retry_on_connection_error(max_retries=3, delay=0.5)
    @with_rate_limit
    def get_safe_partner_fields(self) -> List[str]:
        """Restituisce campi partner sicuri per Odoo 18.2+"""
        fields_info = self.client.get_model_fields('res.partner')
        
        # Campi base sempre presenti in 18.2+
        base_fields = [
            'id', 'name', 'display_name', 'email', 'phone',
            'vat', 'is_company', 'customer_rank', 'supplier_rank',
            'street', 'street2', 'city', 'zip', 'state_id', 'country_id',
            'create_date', 'write_date', 'active', 'category_id',
            'commercial_partner_id', 'parent_id', 'lang', 'tz'
        ]
        
        # Campi opzionali da verificare dinamicamente
        optional_fields = [
            'mobile', 'website', 'comment', 'ref', 'child_ids',
            'bank_ids', 'user_ids', 'property_payment_term_id'
        ]
        
        safe_fields = base_fields.copy()
        for field in optional_fields:
            if field in fields_info:
                safe_fields.append(field)
                self.logger.debug(f"Campo {field} disponibile")
            else:
                self.logger.debug(f"Campo {field} non disponibile")
        
        return safe_fields
    
    def _process_partner_data_v18_2(self, partner: Dict) -> Dict[str, Any]:
        """Elabora dati partner per Odoo 18.2+"""
        try:
            processed = {
                'id': partner.get('id'),
                'name': partner.get('name', ''),
                'display_name': partner.get('display_name', ''),
                'email': partner.get('email', ''),
                'phone': partner.get('phone', ''),
                'mobile': partner.get('mobile', ''),
                'vat': partner.get('vat', ''),
                'is_company': partner.get('is_company', False),
                'customer_rank': partner.get('customer_rank', 0),
                'supplier_rank': partner.get('supplier_rank', 0),
                'active': partner.get('active', True),
                'lang': partner.get('lang', 'it_IT'),
                'tz': partner.get('tz', 'Europe/Rome'),
                
                # Indirizzo
                'street': partner.get('street', ''),
                'street2': partner.get('street2', ''),
                'city': partner.get('city', ''),
                'zip': partner.get('zip', ''),
                'state_name': partner.get('state_id')[1] if partner.get('state_id') else '',
                'state_id': partner.get('state_id')[0] if partner.get('state_id') else None,
                'country_name': partner.get('country_id')[1] if partner.get('country_id') else '',
                'country_id': partner.get('country_id')[0] if partner.get('country_id') else None,
                
                # Relazioni
                'commercial_partner_id': partner.get('commercial_partner_id')[0] if partner.get('commercial_partner_id') else partner.get('id'),
                'parent_id': partner.get('parent_id')[0] if partner.get('parent_id') else None,
                'parent_name': partner.get('parent_id')[1] if partner.get('parent_id') else '',
                
                # Campi opzionali
                'website': partner.get('website', ''),
                'comment': partner.get('comment', ''),
                'ref': partner.get('ref', ''),
                
                # Date
                'create_date': partner.get('create_date', ''),
                'write_date': partner.get('write_date', ''),
            }
            
            # Categorie
            categories = partner.get('category_id', [])
            if categories:
                processed['categories'] = [cat[1] for cat in categories]
                processed['category_ids'] = [cat[0] for cat in categories]
            else:
                processed['categories'] = []
                processed['category_ids'] = []
            
            # Indirizzo completo
            address_parts = [
                processed['street'], processed['street2'], processed['city'],
                processed['zip'], processed['state_name'], processed['country_name']
            ]
            processed['full_address'] = ', '.join([part for part in address_parts if part])
            
            # Tipo e status
            processed['partner_type'] = 'Azienda' if processed['is_company'] else 'Persona'
            
            status_parts = []
            if processed['customer_rank'] > 0:
                status_parts.append('Cliente')
            if processed['supplier_rank'] > 0:
                status_parts.append('Fornitore')
            processed['partner_status'] = ' / '.join(status_parts) if status_parts else 'Contatto'
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Errore elaborazione partner {partner.get('id')}: {e}")
            return {
                'id': partner.get('id'),
                'name': partner.get('name', 'N/A'),
                'display_name': partner.get('display_name', 'N/A'),
                'email': partner.get('email', ''),
                'phone': partner.get('phone', ''),
                'mobile': '',
                'error': str(e)
            }
    
    @retry_on_connection_error(max_retries=3, delay=0.5)
    @with_rate_limit
    def get_partners_list(self, limit: int = 100, offset: int = 0, filters: List = None) -> List[Dict[str, Any]]:
        """Ottiene lista partner per Odoo 18.2+ con gestione errori migliorata"""
        try:
            safe_fields = self.get_safe_partner_fields()
            
            # Filtri ottimizzati per 18.2+
            default_filters = [
                ('active', '=', True),
                ('customer_rank', '>', 0)
            ]
            
            search_filters = default_filters + (filters or [])
            
            # Context ottimizzato
            context = self.client._get_default_context()
            context.update({'active_test': False})
            
            # Ricerca con ordinamento per performance
            partner_ids = self.client.execute(
                'res.partner',
                'search',
                search_filters,
                limit=limit,
                offset=offset,
                order='name asc',
                context=context
            )
            
            if not partner_ids:
                return []
            
            # Lettura batch per performance
            partners_data = self.client.execute(
                'res.partner',
                'read',
                partner_ids,
                fields=safe_fields,
                context=context
            )
            
            # Elaborazione ottimizzata
            processed_partners = []
            for partner in partners_data:
                processed_partner = self._process_partner_data_v18_2(partner)
                processed_partners.append(processed_partner)
            
            self.logger.info(f"Recuperati {len(processed_partners)} partner")
            return processed_partners
            
        except Exception as e:
            self.logger.error(f"Errore recupero lista partner: {e}")
            raise OdooDataError(f"Errore recupero partner: {e}")
    
    @retry_on_connection_error(max_retries=3, delay=0.5)
    @with_rate_limit
    def search_partners(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Cerca partner ottimizzato per 18.2+"""
        try:
            search_filters = [
                ('active', '=', True),
                ('customer_rank', '>', 0),
                '|', '|', '|',
                ('name', 'ilike', search_term),
                ('display_name', 'ilike', search_term),
                ('email', 'ilike', search_term),
                ('vat', 'ilike', search_term)
            ]
            
            return self.get_partners_list(limit=limit, filters=search_filters[2:])
            
        except Exception as e:
            self.logger.error(f"Errore ricerca partner '{search_term}': {e}")
            raise OdooDataError(f"Errore ricerca partner: {e}")
    
    @retry_on_connection_error(max_retries=3, delay=0.5)
    @with_rate_limit
    def get_partner_by_id(self, partner_id: int) -> Optional[Dict[str, Any]]:
        """Ottiene partner specifico per ID"""
        try:
            safe_fields = self.get_safe_partner_fields()
            partner_data = self.client.execute('res.partner', 'read', [partner_id], fields=safe_fields)
            
            if partner_data:
                return self._process_partner_data_v18_2(partner_data[0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Errore recupero partner ID {partner_id}: {e}")
            raise OdooDataError(f"Errore recupero partner: {e}")
    
    @retry_on_connection_error(max_retries=3, delay=0.5)
    @with_rate_limit
    def get_partners_count(self, filters: List = None) -> int:
        """Conta partner con filtri"""
        try:
            default_filters = [('active', '=', True), ('customer_rank', '>', 0)]
            search_filters = default_filters + (filters or [])
            
            count = self.client.execute('res.partner', 'search_count', search_filters)
            return count
            
        except Exception as e:
            self.logger.error(f"Errore conteggio partner: {e}")
            raise OdooDataError(f"Errore conteggio partner: {e}")
    
    @retry_on_connection_error(max_retries=3, delay=0.5)
    @with_rate_limit
    def get_partners_summary(self) -> Dict[str, Any]:
        """Statistiche partner per 18.2+"""
        try:
            total_customers = self.get_partners_count()
            companies_count = self.get_partners_count([('is_company', '=', True)])
            individuals_count = total_customers - companies_count
            with_email_count = self.get_partners_count([('email', '!=', False)])
            
            # Gestione telefoni con verifica campi disponibili
            fields_info = self.client.get_model_fields('res.partner')
            mobile_available = 'mobile' in fields_info
            
            if mobile_available:
                try:
                    with_phone_count = self.get_partners_count([
                        '|', ('phone', '!=', False), ('mobile', '!=', False)
                    ])
                    phone_fields = "phone, mobile"
                except:
                    with_phone_count = self.get_partners_count([('phone', '!=', False)])
                    phone_fields = "phone"
            else:
                with_phone_count = self.get_partners_count([('phone', '!=', False)])
                phone_fields = "phone"
            
            return {
                'total_customers': total_customers,
                'companies': companies_count,
                'individuals': individuals_count,
                'with_email': with_email_count,
                'with_phone': with_phone_count,
                'email_coverage': round((with_email_count / total_customers) * 100, 1) if total_customers > 0 else 0,
                'phone_coverage': round((with_phone_count / total_customers) * 100, 1) if total_customers > 0 else 0,
                'phone_fields_used': phone_fields,
                'mobile_field_available': mobile_available,
                'odoo_version': '18.2+',
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Errore statistiche partner: {e}")
            raise OdooDataError(f"Errore statistiche partner: {e}")
    
    @retry_on_connection_error(max_retries=3, delay=0.5)
    @with_rate_limit
    def get_all_partners_for_select(self) -> List[Dict[str, Any]]:
        """Partner per Select2 ottimizzato per 18.2+ con rate limiting"""
        try:
            search_filters = [
                ('active', '=', True),
                ('customer_rank', '>=', 0)
            ]
            
            context = {'active_test': False}
            
            # Prima cerca gli ID con ordinamento corretto
            partner_ids = self.client.execute(
                'res.partner',
                'search',
                search_filters,
                order='name asc',
                context=context
            )
            
            if not partner_ids:
                return []
            
            # Poi leggi i dati necessari in chunks per evitare timeout
            chunk_size = 200
            select_partners = []
            
            for i in range(0, len(partner_ids), chunk_size):
                chunk_ids = partner_ids[i:i + chunk_size]
                
                partners_data = self.client.execute(
                    'res.partner',
                    'read',
                    chunk_ids,
                    fields=['commercial_partner_id', 'display_name'],
                    context=context
                )
                
                for partner in partners_data:
                    commercial_id = partner.get('commercial_partner_id')
                    if isinstance(commercial_id, list) and len(commercial_id) > 0:
                        commercial_partner_id = commercial_id[0]
                    else:
                        commercial_partner_id = commercial_id or partner.get('id')
                    
                    select_partners.append({
                        'commercial_partner_id': commercial_partner_id,
                        'display_name': partner.get('display_name', '')
                    })
            
            self.logger.info(f"Recuperati {len(select_partners)} partner per Select2")
            return select_partners
            
        except Exception as e:
            self.logger.error(f"Errore recupero partner per Select2: {e}")
            raise OdooDataError(f"Errore recupero partner per Select2: {e}")