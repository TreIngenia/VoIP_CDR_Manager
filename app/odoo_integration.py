"""
Odoo Integration v18.2+ - VERSIONE COMPLETAMENTE CORRETTA
Integrazione ottimizzata per Odoo SaaS~18.2+ con gestione dinamica dei campi
e correzioni specifiche per l'ultima versione
"""
import os
import xmlrpc.client
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from flask import jsonify
import logging
import json

# Import dei moduli del progetto
try:
    from logger_config import get_logger
    from exception_handler import OdooException
except ImportError:
    # Fallback se i moduli non sono disponibili
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
class OdooException(Exception):
    def __init__(self, message: str, error_code: str = 'ODOO_ERROR'):
        super().__init__(message)
        self.error_code = error_code

def get_odoo_client(secure_config):
        """Helper per creare client Odoo con configurazione"""
        try:
            config = secure_config.get_config()
            odoo_config = {
                'ODOO_URL': config.get('ODOO_URL', ''),
                'ODOO_DB': config.get('ODOO_DB', ''),
                'ODOO_USERNAME': config.get('ODOO_USERNAME', ''),
                'ODOO_API_KEY': config.get('ODOO_API_KEY', '')
            }
            
            # Verifica configurazione
            missing = [k for k, v in odoo_config.items() if not v]
            if missing:
                raise Exception(f"Configurazione Odoo incompleta: {missing}")
            
            return create_odoo_client(odoo_config)
            
        except Exception as e:
            logger.error(f"Errore creazione client Odoo: {e}")
            raise

@dataclass
class InvoiceItem:
    """Item fattura per Odoo 18.2+ - Campi verificati e corretti"""
    product_id: int
    quantity: float
    price_unit: float
    name: str
    # Campi opzionali per Odoo 18.2+
    account_id: Optional[int] = None
    analytic_distribution: Optional[Dict[str, float]] = None  # Nuovo formato per analitici in 18.2+
    tax_ids: Optional[List[int]] = None

@dataclass  
class InvoiceData:
    """Dati fattura completi per Odoo 18.2+"""
    partner_id: int
    items: List[InvoiceItem]
    due_days: Optional[int] = None
    manual_due_date: Optional[str] = None
    reference: str = ""
    # Campi per Odoo 18.2+
    journal_id: Optional[int] = None
    payment_term_id: Optional[int] = None  # Corretto per 18.2+
    currency_id: Optional[int] = None
    company_id: Optional[int] = None

class OdooClient:
    """Client Odoo ottimizzato per Odoo SaaS~18.2+ con gestione avanzata dei campi"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        try:
            self.logger = get_logger(__name__)
        except:
            self.logger = logging.getLogger(__name__)
        
        self.uid = None
        self.models = None
        self.common = None
        self.version_info = None
        # Cache per ottimizzazione performance
        self._field_cache = {}
        self._model_cache = {}
        self._validate_config()
    
    def _validate_config(self):
        """Valida configurazione Odoo"""
        required_keys = ['ODOO_URL', 'ODOO_DB', 'ODOO_USERNAME', 'ODOO_API_KEY']
        missing = [k for k in required_keys if not self.config.get(k)]
        
        if missing:
            raise OdooException(f"Configurazione Odoo incompleta: {missing}", 'CONFIG_ERROR')
        
        # Verifica formato URL
        if not self.config['ODOO_URL'].startswith(('http://', 'https://')):
            raise OdooException("URL Odoo deve iniziare con http:// o https://", 'CONFIG_ERROR')
    
    def connect(self) -> bool:
        """Connessione ottimizzata per Odoo 18.2+"""
        try:
            self.common = xmlrpc.client.ServerProxy(
                f"{self.config['ODOO_URL']}/xmlrpc/2/common",
                allow_none=True,
                use_datetime=True  # Importante per 18.2+
            )
            
            # Verifica versione server
            self.version_info = self.common.version()
            server_version = self.version_info.get('server_version', '')
            self.logger.info(f"Connessione a Odoo {server_version}")
            
            # Verifica compatibilità specifica per 18.2+
            if not self._check_version_compatibility(server_version):
                self.logger.warning(f"Versione {server_version} potrebbe richiedere adattamenti")
            
            # Autenticazione
            self.uid = self.common.authenticate(
                self.config['ODOO_DB'],
                self.config['ODOO_USERNAME'], 
                self.config['ODOO_API_KEY'],
                {}
            )
            
            if not self.uid:
                raise OdooException("Autenticazione Odoo fallita", 'AUTH_ERROR')
            
            self.models = xmlrpc.client.ServerProxy(
                f"{self.config['ODOO_URL']}/xmlrpc/2/object",
                allow_none=True,
                use_datetime=True
            )
            
            self.logger.info(f"Connesso ad Odoo 18.2+ con UID: {self.uid}")
            return True
            
        except Exception as e:
            error_msg = f"Errore connessione Odoo: {e}"
            self.logger.error(error_msg)
            raise OdooException(error_msg, 'CONNECTION_ERROR')
    
    def _check_version_compatibility(self, version: str) -> bool:
        """Verifica compatibilità specifica per 18.2+"""
        if version.startswith('18.'):
            # Estrai numero di versione minore
            try:
                major, minor = version.split('.')[:2]
                minor_num = float(minor)
                if minor_num >= 2:
                    self.logger.info("Versione 18.2+ rilevata - compatibilità completa")
                    return True
                else:
                    self.logger.warning(f"Versione 18.{minor} - alcune funzionalità potrebbero differire")
                    return True
            except:
                return True
        elif version.startswith(('17.', '16.')):
            self.logger.warning(f"Versione {version} - compatibilità parziale")
            return True
        else:
            self.logger.warning(f"Versione {version} non testata")
            return False
    
    def execute(self, model: str, method: str, *args, **kwargs):
        """Wrapper ottimizzato per execute_kw con gestione errori per 18.2+"""
        if not self.uid or not self.models:
            if not self.connect():
                raise OdooException("Impossibile connettersi ad Odoo", 'CONNECTION_ERROR')
        
        try:
            # Context ottimizzato per 18.2+
            if 'context' not in kwargs:
                kwargs['context'] = self._get_default_context()
            
            # Gestione timeout migliorata per operazioni lunghe
            if method in ['create', 'write', 'unlink'] and 'timeout' not in kwargs:
                kwargs['timeout'] = 300  # 5 minuti per operazioni di scrittura
            
            if kwargs:
                return self.models.execute_kw(
                    self.config['ODOO_DB'], 
                    self.uid, 
                    self.config['ODOO_API_KEY'],
                    model, 
                    method, 
                    list(args), 
                    kwargs
                )
            else:
                return self.models.execute_kw(
                    self.config['ODOO_DB'], 
                    self.uid, 
                    self.config['ODOO_API_KEY'],
                    model, 
                    method, 
                    list(args)
                )
        except Exception as e:
            error_msg = f"Errore esecuzione {model}.{method}: {e}"
            self.logger.error(error_msg)
            raise OdooException(error_msg, 'EXECUTION_ERROR')
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Context ottimizzato per Odoo 18.2+"""
        return {
            'lang': 'it_IT',
            'tz': 'Europe/Rome',
            'active_test': True,
            # Context specifici per 18.2+
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'tracking_disable': True,  # Disabilita tracking per performance
            'mail_notify_force_send': False,  # Evita invio email immediate
        }
    
    def get_model_fields(self, model: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Ottiene definizioni campi per un modello con caching ottimizzato"""
        if model in self._field_cache and not force_refresh:
            return self._field_cache[model]
        
        try:
            fields_info = self.execute(model, 'fields_get', [])
            self._field_cache[model] = fields_info
            
            self.logger.debug(f"Campi per {model}: {len(fields_info)} disponibili")
            return fields_info
            
        except Exception as e:
            self.logger.error(f"Errore recupero campi per {model}: {e}")
            return {}
    
    def get_safe_partner_fields(self) -> List[str]:
        """Restituisce campi partner sicuri per Odoo 18.2+"""
        fields_info = self.get_model_fields('res.partner')
        
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
    
    def get_partners_list(self, limit: int = 100, offset: int = 0, filters: List = None) -> List[Dict[str, Any]]:
        """Ottiene lista partner per Odoo 18.2+"""
        try:
            safe_fields = self.get_safe_partner_fields()
            
            # Filtri ottimizzati per 18.2+
            default_filters = [
                ('active', '=', True),
                ('customer_rank', '>', 0)
            ]
            
            search_filters = default_filters + (filters or [])
            
            # Context ottimizzato
            context = self._get_default_context()
            context.update({'active_test': False})
            
            # Ricerca con ordinamento per performance
            partner_ids = self.execute(
                'res.partner', 
                'search', 
                search_filters,
                limit=limit, 
                offset=offset,
                order='name asc',  # Ordinamento per consistenza
                context=context
            )
            
            if not partner_ids:
                return []
            
            # Lettura batch per performance
            partners_data = self.execute(
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
            raise OdooException(f"Errore recupero partner: {e}", 'PARTNERS_READ_ERROR')
    
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
            raise OdooException(f"Errore ricerca partner: {e}", 'PARTNERS_SEARCH_ERROR')

    def get_partner_by_id(self, partner_id: int) -> Optional[Dict[str, Any]]:
        """Ottiene partner specifico per ID"""
        try:
            safe_fields = self.get_safe_partner_fields()
            partner_data = self.execute('res.partner', 'read', [partner_id], fields=safe_fields)
            
            if partner_data:
                return self._process_partner_data_v18_2(partner_data[0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Errore recupero partner ID {partner_id}: {e}")
            raise OdooException(f"Errore recupero partner: {e}", 'PARTNER_READ_ERROR')

    def get_partners_count(self, filters: List = None) -> int:
        """Conta partner con filtri"""
        try:
            default_filters = [('active', '=', True), ('customer_rank', '>', 0)]
            search_filters = default_filters + (filters or [])
            
            count = self.execute('res.partner', 'search_count', search_filters)
            return count
            
        except Exception as e:
            self.logger.error(f"Errore conteggio partner: {e}")
            raise OdooException(f"Errore conteggio partner: {e}", 'PARTNERS_COUNT_ERROR')

    def get_partners_summary(self) -> Dict[str, Any]:
        """Statistiche partner per 18.2+"""
        try:
            total_customers = self.get_partners_count()
            companies_count = self.get_partners_count([('is_company', '=', True)])
            individuals_count = total_customers - companies_count
            with_email_count = self.get_partners_count([('email', '!=', False)])
            
            # Gestione telefoni con verifica campi disponibili
            fields_info = self.get_model_fields('res.partner')
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
            raise OdooException(f"Errore statistiche partner: {e}", 'PARTNERS_STATS_ERROR')

    def test_connection(self) -> Dict[str, Any]:
        """Test connessione completo per 18.2+"""
        try:
            if not self.connect():
                return {'success': False, 'error': 'Connessione fallita'}
            
            # Test dati base
            user_data = self.execute('res.users', 'read', [self.uid], fields=['name', 'login'])
            company_info = self.get_company_info()
            
            # Conteggi
            partners_count = self.execute('res.partner', 'search_count', [('customer_rank', '>', 0)])
            products_count = self.execute('product.product', 'search_count', [('sale_ok', '=', True)])
            
            # Test compatibilità campi
            partner_fields = self.get_model_fields('res.partner')
            move_fields = self.get_model_fields('account.move')
            
            return {
                'success': True,
                'connection_info': {
                    'server_version': self.version_info.get('server_version'),
                    'protocol_version': self.version_info.get('protocol_version'),
                    'user_name': user_data[0]['name'],
                    'user_login': user_data[0]['login'],
                    'company_name': company_info['name'],
                    'database': self.config['ODOO_DB'],
                    'uid': self.uid
                },
                'stats': {
                    'customers_count': partners_count,
                    'products_count': products_count
                },
                'compatibility': {
                    'mobile_field_available': 'mobile' in partner_fields,
                    'invoice_payment_term_id_available': 'invoice_payment_term_id' in move_fields,
                    'analytic_distribution_available': 'analytic_distribution' in self.get_model_fields('account.move.line'),
                    'partner_fields_count': len(partner_fields),
                    'move_fields_count': len(move_fields)
                },
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def get_company_info(self) -> Dict[str, Any]:
        """Informazioni azienda per 18.2+"""
        try:
            user_data = self.execute('res.users', 'read', [self.uid], fields=['company_id'])
            company_id = user_data[0]['company_id'][0]
            
            company_data = self.execute(
                'res.company', 
                'read', 
                [company_id],
                fields=[
                    'name', 'email', 'phone', 'website', 'vat',
                    'street', 'street2', 'city', 'zip', 'state_id', 'country_id',
                    'currency_id', 'logo'
                ]
            )[0]
            
            return {
                'id': company_id,
                'name': company_data.get('name'),
                'email': company_data.get('email'),
                'phone': company_data.get('phone'),
                'website': company_data.get('website'),
                'vat': company_data.get('vat'),
                'address': {
                    'street': company_data.get('street', ''),
                    'street2': company_data.get('street2', ''),
                    'city': company_data.get('city', ''),
                    'zip': company_data.get('zip', ''),
                    'state': company_data.get('state_id')[1] if company_data.get('state_id') else '',
                    'country': company_data.get('country_id')[1] if company_data.get('country_id') else '',
                },
                'currency': company_data.get('currency_id')[1] if company_data.get('currency_id') else 'EUR',
                'has_logo': bool(company_data.get('logo'))
            }
            
        except Exception as e:
            self.logger.error(f"Errore recupero info azienda: {e}")
            raise OdooException(f"Errore recupero info azienda: {e}", 'COMPANY_READ_ERROR')
    
    
    
    def get_payment_terms(self) -> List[Dict[str, Any]]:
        """Modalità di pagamento per 18.2+"""
        try:
            payment_terms = self.execute(
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
            raise OdooException(f"Errore modalità pagamento: {e}", 'PAYMENT_TERMS_ERROR')
    
    
    
    def get_all_partners_for_select(self) -> List[Dict[str, Any]]:
        """Partner per Select2 ottimizzato per 18.2+"""
        try:
            search_filters = [
                ('active', '=', True),
                ('customer_rank', '>=', 0)
            ]
            
            context = {'active_test': False}
            
            # Prima cerca gli ID con ordinamento corretto
            partner_ids = self.execute(
                'res.partner', 
                'search', 
                search_filters,
                order='name asc',  # Usa 'name' invece di 'display_name' per l'ordinamento
                context=context
            )
            
            if not partner_ids:
                return []
            
            # Poi leggi i dati necessari
            partners_data = self.execute(
                'res.partner', 
                'read', 
                partner_ids,
                fields=['commercial_partner_id', 'display_name'],
                context=context
            )
            
            select_partners = []
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
            raise OdooException(f"Errore recupero partner per Select2: {e}", 'PARTNERS_SELECT_ERROR')
    

    def get_all_payment_terms_for_select(self) -> List[Dict[str, Any]]:
        """Payment Terms per Select2 ottimizzato per 18.2+"""
        try:
            search_filters = [
                ('active', '=', True)
            ]
            
            context = {'active_test': False}
            
            # Prima cerca gli ID con ordinamento corretto
            payment_term_ids = self.execute(
                'account.payment.term',
                'search',
                search_filters,
                order='name asc',  # Ordinamento per nome
                context=context
            )
            
            if not payment_term_ids:
                return []
            
            # Poi leggi i dati necessari
            payment_terms_data = self.execute(
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
            raise OdooException(f"Errore recupero payment terms per Select2: {e}", 'PAYMENT_TERMS_SELECT_ERROR')

    def get_all_products_for_select(self) -> List[Dict[str, Any]]:
        """Prodotti per Select2 ottimizzato per 18.2+"""
        try:
            search_filters = [
                ('active', '=', True),
                ('sale_ok', '=', True)  # Solo prodotti vendibili
            ]
            
            context = {'active_test': False}
            
            # Prima cerca gli ID con ordinamento corretto
            product_ids = self.execute(
                'product.product',
                'search',
                search_filters,
                order='name asc',  # Ordinamento per nome
                context=context
            )
            
            if not product_ids:
                return []
            
            # Poi leggi i dati necessari
            products_data = self.execute(
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
            raise OdooException(f"Errore recupero prodotti per Select2: {e}", 'PRODUCTS_SELECT_ERROR')
            
    # Metodi helper
    def _calculate_due_date(self, invoice_date: str, invoice_data: InvoiceData) -> str:
        """Calcola data scadenza fattura"""
        invoice_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
        
        if invoice_data.manual_due_date:
            return invoice_data.manual_due_date
        elif invoice_data.due_days:
            due_dt = invoice_dt + timedelta(days=invoice_data.due_days)
            return due_dt.strftime('%Y-%m-%d')
        else:
            due_dt = invoice_dt + timedelta(days=30)
            return due_dt.strftime('%Y-%m-%d')
    
    
    
    # Metodi di debug per 18.2+
    def debug_model_fields(self, model: str) -> Dict[str, Any]:
        """Debug campi modello per 18.2+"""
        try:
            fields_info = self.get_model_fields(model)
            
            # Analizza tipi di campo
            field_types = {}
            required_fields = []
            readonly_fields = []
            
            for field_name, field_info in fields_info.items():
                field_type = field_info.get('type', 'unknown')
                field_types[field_type] = field_types.get(field_type, 0) + 1
                
                if field_info.get('required', False):
                    required_fields.append(field_name)
                
                if field_info.get('readonly', False):
                    readonly_fields.append(field_name)
            
            return {
                'success': True,
                'model': model,
                'total_fields': len(fields_info),
                'field_types': field_types,
                'required_fields': required_fields,
                'readonly_fields': readonly_fields,
                'key_fields': self._get_key_fields_for_model(model, fields_info)
            }
            
        except Exception as e:
            return {
                'success': False,
                'model': model,
                'error': str(e)
            }
    
    def _get_key_fields_for_model(self, model: str, fields_info: Dict) -> List[str]:
        """Identifica campi chiave per un modello"""
        key_patterns = {
            'res.partner': ['name', 'email', 'phone', 'mobile', 'vat', 'customer_rank'],
            'account.move': ['name', 'partner_id', 'state', 'amount_total', 'invoice_payment_term_id'],
            'account.move.line': ['name', 'product_id', 'quantity', 'price_unit', 'analytic_distribution'],
            'product.product': ['name', 'list_price', 'sale_ok', 'type']
        }
        
        patterns = key_patterns.get(model, [])
        key_fields = []
        
        for pattern in patterns:
            if pattern in fields_info:
                key_fields.append(pattern)
        
        return key_fields

def create_odoo_client(config: Dict[str, Any]) -> OdooClient:
    """Factory function per creare client Odoo 18.2+"""
    return OdooClient(config)


# Carica variabili dal file .env (opzionale)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Carica variabili dal file .env
    print("📁 File .env caricato")
except ImportError:
    print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")

# Configurazione tramite variabili d'ambiente (più sicuro)
url = os.getenv('ODOO_URL')
db = os.getenv('ODOO_DB')
username = os.getenv('ODOO_USERNAME')  # Valore di default aggiunto
api_key = os.getenv('ODOO_API_KEY')  # Legge da variabile d'ambiente

if not api_key:
    raise ValueError("ODOO_API_KEY environment variable is required")

class OdooAPI:

    """
    Classe per gestire connessioni Odoo in modo sicuro
    """
    
    def __init__(self, url, db, username, api_key):
        self.url = url
        self.db = db
        self.username = username
        self.api_key = api_key
        self.uid = None
        self.common = None
        self.models = None
        
    def connect(self):
        """
        Connessione e autenticazione
        """
        try:
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = self.common.authenticate(self.db, self.username, self.api_key, {})
            
            if not self.uid:
                raise Exception("Autenticazione fallita - controlla username e API key")
                
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"✅ Connesso con UID: {self.uid}")
            return True
            
        except Exception as e:
            print(f"❌ Errore connessione: {e}")
            return False
    
    def execute(self, model, method, *args, **kwargs):
        """
        Wrapper per execute_kw con gestione corretta dei parametri
        """
        if not self.uid or not self.models:
            raise Exception("Non ancora connesso - chiama connect() prima")
        
        # Se ci sono kwargs, li passiamo come ultimo parametro
        if kwargs:
            return self.models.execute_kw(
                self.db, self.uid, self.api_key, 
                model, method, list(args), kwargs
            )
        else:
            return self.models.execute_kw(
                self.db, self.uid, self.api_key, 
                model, method, list(args)
            )
    
    def get_partner_payment_terms(self, partner_id):
        """
        Ottieni i termini di pagamento del cliente
        """
        try:
            partner_data = self.execute('res.partner', 'read', partner_id, 
                fields=['property_payment_term_id', 'name'])
            
            # Gestisci sia il caso di singolo record che lista
            partner = partner_data[0] if isinstance(partner_data, list) else partner_data
            
            if partner and partner['property_payment_term_id']:
                payment_term_id = partner['property_payment_term_id'][0]
                payment_term_name = partner['property_payment_term_id'][1]
                
                print(f"👤 Cliente: {partner['name']}")
                print(f"💰 Termini di pagamento: {payment_term_name} (ID: {payment_term_id})")
                
                return payment_term_id, payment_term_name
            else:
                print(f"👤 Cliente: {partner['name'] if partner else 'Sconosciuto'}")
                print("⚠️ Nessun termine di pagamento impostato per questo cliente")
                return None, None
                
        except Exception as e:
            print(f"❌ Errore nel recupero termini pagamento: {e}")
            return None, None

    def calculate_due_date_from_terms(self, invoice_date_str, payment_term_id):
        """
        Calcola la data di scadenza basata sui termini di pagamento
        Versione semplificata che usa direttamente i giorni del termine
        """
        try:
            # Per ora usiamo un mapping semplice basato sui termini più comuni
            # Questo evita problemi con i campi delle righe dei termini di pagamento
            common_terms = {
                1: 0,   # Immediate Payment
                2: 15,  # 15 Days
                3: 30,  # 30 Days  
                4: 60,  # 60 Days
                5: 45,  # 45 Days
                6: 90,  # 90 Days
            }
            
            days = common_terms.get(payment_term_id, 30)  # Default 30 giorni
            
            # Calcola la data di scadenza
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d')
            due_date = invoice_date + timedelta(days=days)
            
            print(f"📅 Calcolato automaticamente: {days} giorni → scadenza {due_date.strftime('%Y-%m-%d')}")
            
            return due_date.strftime('%Y-%m-%d')
            
        except Exception as e:
            print(f"❌ Errore nel calcolo data scadenza: {e}")
            return None

    def calculate_due_date_manual(self, invoice_date_str, days_offset):
        """
        Calcola la data di scadenza aggiungendo giorni alla data fattura (metodo manuale)
        """
        invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d')
        due_date = invoice_date + timedelta(days=days_offset)
        return due_date.strftime('%Y-%m-%d')
    
    def create_invoice(self, partner_id, items, due_days=None, manual_due_date=None):
        """
        Crea una fattura con gestione intelligente della data di scadenza
        
        Args:
            partner_id: ID del cliente
            items: Lista di prodotti/servizi per la fattura
            due_days: Giorni manuali per la scadenza (opzionale)
            manual_due_date: Data di scadenza specifica (formato 'YYYY-MM-DD', opzionale)
        """
        invoice_date = datetime.now().strftime('%Y-%m-%d')
        due_date = None
        force_due_date = False  # Flag per forzare la data dopo la creazione
        
        print("=" * 50)
        print("🧾 CREAZIONE FATTURA")
        print("=" * 50)
        
        # LOGICA PER LA DATA DI SCADENZA (PRIORITÀ CORRETTA):
        # 1. PRIORITÀ MASSIMA: Data manuale specificata
        # 2. PRIORITÀ ALTA: Giorni manuali specificati
        # 3. PRIORITÀ MEDIA: Termini di pagamento del cliente
        # 4. FALLBACK: 30 giorni di default
        
        if manual_due_date is not None and manual_due_date != '':
            # Opzione 1: Data manuale specificata (PRIORITÀ MASSIMA)
            due_date = manual_due_date
            force_due_date = True  # Forza la data dopo la creazione
            print(f"📅 ✅ Usando data di scadenza manuale: {due_date}")
            
        elif due_days is not None:
            # Opzione 2: Giorni manuali specificati (PRIORITÀ ALTA)
            due_date = self.calculate_due_date_manual(invoice_date, due_days)
            force_due_date = True  # Forza la data dopo la creazione
            print(f"📅 ✅ Usando giorni manuali: {due_days} giorni → {due_date}")
            
        else:
            # Opzione 3: Prova a usare i termini di pagamento del cliente (PRIORITÀ MEDIA)
            print("🔍 Controllo termini di pagamento del cliente...")
            payment_term_id, payment_term_name = self.get_partner_payment_terms(partner_id)
            
            if payment_term_id:
                due_date = self.calculate_due_date_from_terms(invoice_date, payment_term_id)
                
            if not due_date:
                # Opzione 4: Fallback a 30 giorni (ULTIMA RISORSA)
                due_date = self.calculate_due_date_manual(invoice_date, 30)
                print(f"📅 Usando fallback: 30 giorni → {due_date}")
        
        # SOLUZIONE: Se dobbiamo forzare la data, creiamo la fattura senza termini di pagamento
        if force_due_date:
            print(f"🔧 Creando fattura con data personalizzata...")
            
            invoice_data = {
                'partner_id': partner_id,
                'move_type': 'out_invoice',
                'invoice_date': invoice_date,
                'invoice_date_due': due_date,
                'invoice_payment_term_id': False,  # ← CHIAVE: Nessun termine di pagamento
                'invoice_line_ids': [(0, 0, item) for item in items],
            }
        else:
            # Creazione normale con termini di pagamento del cliente
            invoice_data = {
                'partner_id': partner_id,
                'move_type': 'out_invoice',
                'invoice_date': invoice_date,
                'invoice_date_due': due_date,
                'invoice_line_ids': [(0, 0, item) for item in items],
            }
        
        invoice_id = self.execute('account.move', 'create', [invoice_data])
        
        print(f'✅ Fattura (bozza) creata con ID: {invoice_id}')
        print(f'📅 Data fattura: {invoice_date}')
        print(f'📅 Data scadenza: {due_date}')
        
        # VERIFICA: Leggi immediatamente la fattura creata per confermare le date
        try:
            created_invoice = self.execute('account.move', 'read', invoice_id, 
                fields=['invoice_date', 'invoice_date_due', 'name'])
            created = created_invoice[0] if isinstance(created_invoice, list) else created_invoice
            print(f"✅ Fattura verificata:")
            print(f"  - Nome: {created.get('name', 'Bozza')}")
            print(f"  - Data fattura: {created.get('invoice_date', 'N/A')}")
            print(f"  - Data scadenza: {created.get('invoice_date_due', 'N/A')}")
        except:
            print(f"✅ Fattura creata con successo")
        
        print("=" * 50)
        
        return invoice_id
    
    def confirm_invoice(self, invoice_id, expected_due_date=None):
        """
        Conferma una fattura (la passa da bozza a confermata/posted)
        
        Args:
            invoice_id: ID della fattura
            expected_due_date: Data di scadenza attesa (per verifica)
        """
        try:
            # Prima verifica lo stato della fattura
            invoice_data = self.execute('account.move', 'read', invoice_id, 
                fields=['state', 'name', 'invoice_date_due'])
            
            invoice = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
            current_state = invoice.get('state', 'draft')
            invoice_name = invoice.get('name', 'N/A')
            
            print(f"📄 Fattura {invoice_name} - Stato attuale: {current_state}")
            
            if current_state == 'posted':
                print('✅ La fattura è già confermata.')
                return True
            elif current_state == 'draft':
                print('🔄 Confermando la fattura...')
                # Usa action_post per confermare la fattura
                self.execute('account.move', 'action_post', invoice_id)
                print('✅ Fattura confermata e numerata.')
                return True
            else:
                print(f'⚠️ Stato fattura non gestito: {current_state}')
                return False
                
        except Exception as e:
            print(f'❌ Errore nella conferma della fattura: {e}')
            return False

    def create_and_confirm_invoice(self, partner_id, items, due_days=None, manual_due_date=None):
        """
        Crea e conferma una fattura in un unico passaggio
        
        Args:
            partner_id: ID del cliente
            items: Lista di prodotti/servizi per la fattura
            due_days: Giorni manuali per la scadenza (opzionale)
            manual_due_date: Data di scadenza specifica (formato 'YYYY-MM-DD', opzionale)
        """
        print("=" * 50)
        print("🧾 CREAZIONE E CONFERMA FATTURA")
        print("=" * 50)
        
        # Determina la data attesa
        expected_due_date = None
        if manual_due_date is not None and manual_due_date != '':
            expected_due_date = manual_due_date
        elif due_days is not None:
            invoice_date = datetime.now().strftime('%Y-%m-%d')
            expected_due_date = self.calculate_due_date_manual(invoice_date, due_days)
        
        # Step 1: Crea la fattura (bozza)
        invoice_id = self.create_invoice(
            partner_id=partner_id, 
            items=items, 
            due_days=due_days,
            manual_due_date=manual_due_date
        )
        
        if not invoice_id:
            print("❌ Errore nella creazione della fattura")
            return None
        
        # Step 2: Conferma la fattura
        if self.confirm_invoice(invoice_id, expected_due_date):
            print("🎉 Fattura creata e confermata con successo!")
            return invoice_id
        else:
            print("⚠️ Fattura creata ma non confermata")
            return invoice_id
    
    def get_invoice_details(self, invoice_id):
        """
        Ottieni dettagli di una fattura
        """
        try:
            invoice_data = self.execute('account.move', 'read', invoice_id, 
                fields=['name', 'partner_id', 'invoice_date', 'invoice_date_due', 'amount_total', 'state'])
            
            if invoice_data:
                inv = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
                print(f"📄 Fattura: {inv['name']}")
                print(f"👤 Cliente: {inv['partner_id'][1] if inv['partner_id'] else 'N/A'}")
                print(f"📅 Data: {inv['invoice_date']}")
                print(f"📅 Scadenza: {inv['invoice_date_due']}")
                print(f"💰 Totale: €{inv['amount_total']}")
                print(f"📊 Stato: {inv['state']}")
                
                return inv
            
        except Exception as e:
            print(f"❌ Errore recupero dettagli fattura: {e}")
            return None

    def check_email_configuration(self):
        """
        Verifica la configurazione email di Odoo
        """
        try:
            # Controlla se ci sono server email configurati
            smtp_servers = self.execute('ir.mail_server', 'search_read', [], 
                fields=['name', 'smtp_host', 'smtp_port'])
            
            if not smtp_servers:
                print("⚠️ PROBLEMA: Nessun server SMTP configurato in Odoo")
                return False
            
            print(f"📧 Server SMTP trovati: {len(smtp_servers)}")
            for server in smtp_servers:
                print(f"  - {server['name']}: {server['smtp_host']}:{server['smtp_port']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Errore nel controllo configurazione email: {e}")
            return False

    def send_invoice_email_method1(self, invoice_id):
        """
        Metodo 1: Invio tramite message_post con email
        """
        try:
            # Ottieni i dati della fattura
            invoice_data = self.execute('account.move', 'read', invoice_id, 
                fields=['partner_id', 'name', 'amount_total', 'invoice_date'])
            
            invoice = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
            
            if not invoice:
                print("Fattura non trovata")
                return False
                
            partner_id = invoice['partner_id'][0] if invoice['partner_id'] else False
            
            if not partner_id:
                print("Partner non trovato")
                return False
            
            # Ottieni l'email del partner
            partner_data = self.execute('res.partner', 'read', partner_id, 
                fields=['email', 'name'])
            
            partner = partner_data[0] if isinstance(partner_data, list) else partner_data
            
            if not partner or not partner['email']:
                print("Email del cliente non trovata")
                return False
                
            partner_email = partner['email']
            partner_name = partner['name']
            invoice_name = invoice['name']
            
            # Invia email tramite message_post con notifica email
            self.execute('account.move', 'message_post', invoice_id, 
                body=f'<p>Gentile {partner_name},</p><p>La fattura {invoice_name} è pronta per il download.</p>',
                subject=f'Fattura {invoice_name}',
                message_type='email',
                subtype_xmlid='mail.mt_comment',
                partner_ids=[partner_id]
            )
            
            print(f'📧 Fattura {invoice_id} inviata via email a {partner_email} (Metodo 1).')
            return True
            
        except Exception as e:
            print(f"❌ Errore nell'invio della fattura per email (Metodo 1): {e}")
            return False

    def send_invoice_email_method2(self, invoice_id):
        """
        Metodo 2: Invio manuale tramite creazione diretta mail.mail
        """
        try:
            # Ottieni i dati della fattura e del partner
            invoice_data = self.execute('account.move', 'read', invoice_id, 
                fields=['partner_id', 'name', 'amount_total', 'invoice_date'])
            
            invoice = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
            
            if not invoice:
                print("Fattura non trovata")
                return False
                
            partner_id = invoice['partner_id'][0] if invoice['partner_id'] else False
            if not partner_id:
                print("Partner non trovato")
                return False
            
            partner_data = self.execute('res.partner', 'read', partner_id, 
                fields=['email', 'name'])
            
            partner = partner_data[0] if isinstance(partner_data, list) else partner_data
            
            if not partner or not partner['email']:
                print("Email del cliente non trovata")
                return False
            
            partner_email = partner['email']
            partner_name = partner['name']
            invoice_name = invoice['name']
            amount = invoice['amount_total']
            date = invoice['invoice_date']
            
            # Crea email manualmente
            mail_data = {
                'subject': f'Fattura {invoice_name}',
                'body_html': f'''
                    <p>Gentile {partner_name},</p>
                    <p>Le inviamo in allegato la fattura <strong>{invoice_name}</strong> del {date} per un importo di <strong>€ {amount}</strong>.</p>
                    <p>Cordiali saluti</p>
                ''',
                'email_to': partner_email,
                'model': 'account.move',
                'res_id': invoice_id,
                'auto_delete': True,
            }
            
            # Crea e invia
            mail_id = self.execute('mail.mail', 'create', [mail_data])
            
            self.execute('mail.mail', 'send', mail_id)
            
            print(f'📧 Fattura {invoice_id} inviata via email a {partner_email} (Metodo 2).')
            return True
            
        except Exception as e:
            print(f"❌ Errore nell'invio della fattura per email (Metodo 2): {e}")
            return False

    def send_invoice_email_method3(self, invoice_id):
        """
        Metodo 3: Invio tramite mail.template con force_send
        """
        try:
            # Cerca template per fatture
            template_ids = self.execute('mail.template', 'search',
                [['model', '=', 'account.move']])
            
            if not template_ids:
                print("Nessun template email trovato")
                return False
                
            template_id = template_ids[0]
            
            # Invia email con force_send=True
            self.execute('mail.template', 'send_mail', 
                template_id, invoice_id, 
                force_send=True, raise_exception=True)
            
            print(f'📧 Fattura {invoice_id} inviata via email (Metodo 3).')
            return True
            
        except Exception as e:
            print(f"❌ Errore nell'invio della fattura per email (Metodo 3): {e}")
            return False

    def send_invoice_email(self, invoice_id):
        """
        Funzione principale che prova diversi metodi per inviare l'email
        """
        print("📧 Tentativo di invio email...")
        
        # Prima verifica la configurazione email
        if not self.check_email_configuration():
            print("⚠️ ATTENZIONE: La configurazione email potrebbe non essere visibile via API.")
        
        # Prova il Metodo 1 (message_post)
        if self.send_invoice_email_method1(invoice_id):
            return True
        
        # Se il Metodo 1 fallisce, prova il Metodo 2 (mail.mail diretto)
        if self.send_invoice_email_method2(invoice_id):
            return True
        
        # Se anche il Metodo 2 fallisce, prova il Metodo 3 (template)
        if self.send_invoice_email_method3(invoice_id):
            return True
        
        print("❌ Tutti i metodi di invio email hanno fallito.")
        print("💡 Suggerimento: Prova a inviare manualmente la fattura dall'interfaccia web di Odoo per confermare che funzioni.")
        return False
    
    def gen_fattura(fact_data):
        # print (fact_data['partner_id'])
        partner_id = fact_data['partner_id']
        
        if fact_data['due_days'] != "":
            due_days = fact_data['due_days']
        else:
            due_days = ""    
        manual_due_date = fact_data['manual_due_date']
        items = fact_data['items']
        da_confermare = fact_data['da_confermare']
        # return
        print("🚀 Sistema Fatturazione Odoo con API Key")
        
        # Inizializza connessione Odoo
        odoo = OdooAPI(url, db, username, api_key)
        
        if not odoo.connect():
            return
        result = False
        if da_confermare not in ["SI",""]:
            if due_days != "":
                invoice_id = odoo.create_and_confirm_invoice(partner_id=partner_id, items=items, due_days=due_days)
            else:
                invoice_id = odoo.create_and_confirm_invoice(partner_id=partner_id, items=items, manual_due_date=manual_due_date)
                
            # Visualizza dettagli fattura creata
            odoo.get_invoice_details(invoice_id)
            # Invia email
            result = odoo.send_invoice_email(invoice_id)
        else:
            if due_days:
                invoice_id = odoo.create_invoice(partner_id=partner_id, items=items, due_days=due_days)
            else:
                invoice_id = odoo.create_invoice(partner_id=partner_id, items=items, manual_due_date=manual_due_date)
        if not invoice_id:
            print("❌ Impossibile creare la fattura")
            return

        # Visualizza dettagli fattura creata
        print(f"DATI DI ODOO: | {result}")
        
        if result:
            print("✅ Email inviata con successo!")
            print(result)
        else:
            result=False
            print("⚠️ Problema con l'invio email - controlla la configurazione SMTP")
        json_result= {
            "invoice_id": invoice_id,
            "send_email": result,
            "partner_id": partner_id,
            "due_days": due_days,
            "manual_due_date": manual_due_date,
            "items": items,
            "da_confermare": da_confermare
        }
        print("\n🎉 Processo completato!")
        return jsonify(json_result)

class SubscriptionExtractor:
    def __init__(self):
        self.odoo = None
        
    def connect_odoo(self):
        """Connessione a Odoo"""
        try:
            self.odoo = OdooAPI(
                url=os.getenv('ODOO_URL'),
                db=os.getenv('ODOO_DB'),
                username=os.getenv('ODOO_USERNAME'),
                api_key=os.getenv('ODOO_API_KEY')
            )
            
            if not self.odoo.connect():
                raise ConnectionError("Impossibile connettersi a Odoo")
                
            return True
            
        except Exception as e:
            print(f"❌ Errore connessione Odoo: {e}")
            return False
    
    def get_available_fields(self):
        """Recupera i campi disponibili per sale.order"""
        try:
            fields_info = self.odoo.execute('sale.order', 'fields_get', [])
            return list(fields_info.keys())
        except:
            return []
    
    def find_recurring_fields(self, available_fields):
        """Identifica i campi che indicano ricorrenza"""
        possible_fields = [
            'is_subscription', 'subscription', 'recurring', 'ricorrente',
            'subscription_management', 'subscription_id', 'recurrence_id',
            'is_recurring', 'subscription_template_id', 'subscription_state'
        ]
        
        return [field for field in possible_fields if field in available_fields]
    
    def get_orders_with_filters(self, partner_id=None, limit=100):
        """Recupera ordini con filtri di ricorrenza"""
        available_fields = self.get_available_fields()
        recurring_fields = self.find_recurring_fields(available_fields)
        
        # Costruisce filtri
        domain = [('state', 'in', ['sale', 'done'])]
        
        # Aggiunge filtri per ricorrenza
        if 'is_subscription' in available_fields:
            domain.append(('is_subscription', '=', True))
        elif 'subscription' in available_fields:
            domain.append(('subscription', '!=', False))
        
        # Filtro per partner specifico
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        
        # Campi da recuperare
        fields_to_get = [
            'id', 'name', 'partner_id', 'state', 'amount_total',
            'date_order', 'invoice_status', 'order_line', 'currency_id'
        ] + recurring_fields
        
        # Recupera ordini
        orders = self.odoo.execute('sale.order', 'search_read',
            domain,
            fields=fields_to_get,
            order='date_order desc',
            limit=limit
        )
        
        return orders, recurring_fields
    
    def identify_subscriptions_manually(self, orders):
        """Identifica abbonamenti manualmente se non trovati con filtri diretti"""
        subscriptions = []
        
        for order in orders:
            is_subscription = False
            
            # Criterio 1: Cliente con più ordini
            partner_id = order['partner_id'][0] if order['partner_id'] else None
            if partner_id:
                similar_orders = self.odoo.execute('sale.order', 'search_count',
                    [
                        ('partner_id', '=', partner_id),
                        ('state', 'in', ['sale', 'done']),
                        ('id', '!=', order['id'])
                    ])
                
                if similar_orders >= 2:
                    is_subscription = True
            
            # Criterio 2: Analisi prodotti per termini di abbonamento
            if order.get('order_line') and not is_subscription:
                try:
                    lines = self.odoo.execute('sale.order.line', 'search_read',
                        [('order_id', '=', order['id'])],
                        fields=['name', 'product_id'])
                    
                    subscription_terms = [
                        'abbonamento', 'subscription', 'piano', 'canone',
                        'mensile', 'annuale', 'ricorrente', 'voip'
                    ]
                    
                    for line in lines:
                        line_name = (line.get('name', '') or '').lower()
                        product_name = ''
                        if line.get('product_id') and isinstance(line['product_id'], list):
                            product_name = (line['product_id'][1] or '').lower()
                        
                        if any(term in line_name or term in product_name for term in subscription_terms):
                            is_subscription = True
                            break
                            
                except Exception:
                    pass
            
            # Criterio 3: Righe con traffico extra
            if order.get('order_line') and not is_subscription:
                try:
                    extra_lines = self.odoo.execute('sale.order.line', 'search_count',
                        [
                            ('order_id', '=', order['id']),
                            ('name', 'like', 'EXTRA_TRAFFIC_')
                        ])
                    
                    if extra_lines > 0:
                        is_subscription = True
                        
                except:
                    pass
            
            if is_subscription:
                subscriptions.append(order)
        
        return subscriptions
    
    def analyze_order_lines(self, order_id):
        """Analizza le righe di un ordine"""
        try:
            lines = self.odoo.execute('sale.order.line', 'search_read',
                [('order_id', '=', order_id)],
                fields=['name', 'price_unit', 'product_uom_qty', 'price_subtotal', 'product_id'])
            
            extra_lines = []
            regular_lines = []
            
            for line in lines:
                # Aggiunge informazioni prodotto
                product_info = None
                if line.get('product_id'):
                    if isinstance(line['product_id'], list) and len(line['product_id']) > 1:
                        product_info = {
                            'id': line['product_id'][0],
                            'name': line['product_id'][1]
                        }
                    elif isinstance(line['product_id'], int):
                        product_info = {
                            'id': line['product_id'],
                            'name': 'N/A'
                        }
                
                line['product_info'] = product_info
                
                if 'EXTRA_TRAFFIC_' in line['name']:
                    extra_lines.append(line)
                else:
                    regular_lines.append(line)
            
            return {
                'total_lines': len(lines),
                'extra_lines': len(extra_lines),
                'regular_lines': len(regular_lines),
                'extra_amount': sum(line['price_subtotal'] for line in extra_lines),
                'regular_amount': sum(line['price_subtotal'] for line in regular_lines),
                'extra_details': extra_lines,
                'regular_details': regular_lines,
                'all_lines': lines
            }
            
        except Exception:
            return None
    
    def format_date(self, date_string):
        """Formatta date per JSON"""
        if date_string:
            try:
                date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                return {
                    "iso": date_obj.isoformat(),
                    "formatted": date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                    "date_only": date_obj.strftime('%Y-%m-%d')
                }
            except:
                return {"raw": date_string}
        return None
    
    def get_subscriptions_json(self, partner_id=None, limit=100):
        """Recupera abbonamenti e restituisce JSON"""
        if not self.connect_odoo():
            return None
        
        # Prova prima con filtri diretti
        orders, recurring_fields = self.get_orders_with_filters(partner_id, limit)
        
        # Se non trova niente, prova ricerca manuale
        if not orders:
            alternative_domain = [('state', 'in', ['sale', 'done'])]
            if partner_id:
                alternative_domain.append(('partner_id', '=', partner_id))
            
            all_orders = self.odoo.execute('sale.order', 'search_read',
                alternative_domain,
                fields=[
                    'id', 'name', 'partner_id', 'state', 'amount_total',
                    'date_order', 'invoice_status', 'order_line', 'currency_id'
                ],
                order='date_order desc',
                limit=limit * 2
            )
            
            orders = self.identify_subscriptions_manually(all_orders)
        
        if not orders:
            return {
                "export_info": {
                    "export_date": datetime.now().isoformat(),
                    "total_subscriptions": 0,
                    "partner_filter": partner_id,
                    "status": "no_subscriptions_found"
                },
                "summary": {
                    "total_subscriptions": 0,
                    "total_amount": 0
                },
                "subscriptions": []
            }
        
        # Costruisce JSON
        json_data = {
            "export_info": {
                "export_date": datetime.now().isoformat(),
                "total_subscriptions": len(orders),
                "partner_filter": partner_id,
                "odoo_connection": {
                    "url": os.getenv('ODOO_URL'),
                    "database": os.getenv('ODOO_DB')
                }
            },
            "summary": {
                "total_subscriptions": len(orders),
                "total_amount": 0,
                "total_extra_traffic": 0,
                "subscriptions_with_extra": 0,
                "currency_breakdown": {},
                "partner_breakdown": {}
            },
            "subscriptions": []
        }
        
        total_amount = 0
        total_extra = 0
        subscriptions_with_extra = 0
        
        # Processa ogni abbonamento
        for order in orders:
            partner_info = {
                "id": order['partner_id'][0] if order['partner_id'] else None,
                "name": order['partner_id'][1] if order['partner_id'] else None
            }
            
            currency_info = {
                "id": order['currency_id'][0] if order.get('currency_id') else None,
                "name": order['currency_id'][1] if order.get('currency_id') else 'EUR'
            }
            
            # Analizza righe
            lines_analysis = self.analyze_order_lines(order['id']) if order.get('order_line') else None
            
            # Aggiorna statistiche
            amount = order.get('amount_total', 0)
            total_amount += amount
            
            if lines_analysis and lines_analysis['extra_lines'] > 0:
                total_extra += lines_analysis['extra_amount']
                subscriptions_with_extra += 1
            
            # Breakdown per valuta
            currency_name = currency_info['name']
            if currency_name not in json_data['summary']['currency_breakdown']:
                json_data['summary']['currency_breakdown'][currency_name] = {
                    "count": 0,
                    "total_amount": 0
                }
            json_data['summary']['currency_breakdown'][currency_name]['count'] += 1
            json_data['summary']['currency_breakdown'][currency_name]['total_amount'] += amount
            
            # Breakdown per partner
            partner_name = partner_info['name'] or 'Unknown'
            if partner_name not in json_data['summary']['partner_breakdown']:
                json_data['summary']['partner_breakdown'][partner_name] = {
                    "partner_id": partner_info['id'],
                    "subscriptions_count": 0,
                    "total_amount": 0
                }
            json_data['summary']['partner_breakdown'][partner_name]['subscriptions_count'] += 1
            json_data['summary']['partner_breakdown'][partner_name]['total_amount'] += amount
            
            # Campi ricorrenza
            recurring_info = {}
            for field_name in recurring_fields:
                if field_name in order and order[field_name]:
                    recurring_info[field_name] = order[field_name]
            
            # Struttura abbonamento
            subscription = {
                "id": order['id'],
                "name": order['name'],
                "partner": partner_info,
                "state": order['state'],
                "amount_total": amount,
                "currency": currency_info,
                "dates": {
                    "order_date": self.format_date(order.get('date_order'))
                },
                "invoice_status": order.get('invoice_status'),
                "recurring_fields": recurring_info,
                "has_extra_traffic": False,
                "extra_traffic_amount": 0,
                "lines_summary": {
                    "total_lines": 0,
                    "regular_lines": 0,
                    "extra_lines": 0,
                    "regular_amount": 0,
                    "extra_amount": 0
                }
            }
            
            # Aggiunge analisi righe
            if lines_analysis:
                subscription.update({
                    "has_extra_traffic": lines_analysis['extra_lines'] > 0,
                    "extra_traffic_amount": lines_analysis['extra_amount'],
                    "lines_summary": {
                        "total_lines": lines_analysis['total_lines'],
                        "regular_lines": lines_analysis['regular_lines'],
                        "extra_lines": lines_analysis['extra_lines'],
                        "regular_amount": lines_analysis['regular_amount'],
                        "extra_amount": lines_analysis['extra_amount']
                    }
                })
                
                # Dettagli traffico extra
                if lines_analysis['extra_details']:
                    subscription['extra_traffic_details'] = []
                    for line in lines_analysis['extra_details']:
                        line_detail = {
                            "name": line['name'],
                            "amount": line['price_subtotal'],
                            "quantity": line.get('product_uom_qty', 1),
                            "unit_price": line.get('price_unit', 0),
                            "product": line.get('product_info')
                        }
                        
                        # Estrae periodo se possibile
                        if 'EXTRA_TRAFFIC_' in line['name']:
                            try:
                                parts = line['name'].split('EXTRA_TRAFFIC_')[1].split('_')
                                if len(parts) >= 2:
                                    line_detail['traffic_period'] = {
                                        "year": int(parts[0]),
                                        "month": int(parts[1]),
                                        "period_string": f"{parts[1]}/{parts[0]}"
                                    }
                            except:
                                pass
                        
                        subscription['extra_traffic_details'].append(line_detail)
                
                # Dettagli righe regolari (prodotti abbonamento)
                if lines_analysis['regular_details']:
                    subscription['subscription_products'] = []
                    for line in lines_analysis['regular_details']:
                        product_detail = {
                            "name": line['name'],
                            "amount": line['price_subtotal'],
                            "quantity": line.get('product_uom_qty', 1),
                            "unit_price": line.get('price_unit', 0),
                            "product": line.get('product_info')
                        }
                        subscription['subscription_products'].append(product_detail)
                
                # Riepilogo tutti i prodotti
                subscription['all_products'] = []
                for line in lines_analysis['all_lines']:
                    product_summary = {
                        "name": line['name'],
                        "amount": line['price_subtotal'],
                        "quantity": line.get('product_uom_qty', 1),
                        "unit_price": line.get('price_unit', 0),
                        "product": line.get('product_info'),
                        "type": "extra_traffic" if 'EXTRA_TRAFFIC_' in line['name'] else "subscription"
                    }
                    subscription['all_products'].append(product_summary)
            
            json_data['subscriptions'].append(subscription)
        
        # Aggiorna summary
        json_data['summary'].update({
            'total_amount': total_amount,
            'total_extra_traffic': total_extra,
            'subscriptions_with_extra': subscriptions_with_extra,
            'extra_traffic_percentage': (total_extra / total_amount * 100) if total_amount > 0 else 0
        })
        
        return json_data




















# Esempi di utilizzo per test
# def test_odoo_18_2_compatibility():
#     """Test compatibilità completa per Odoo 18.2+"""
#     config = {
#         'ODOO_URL': 'https://your-instance.odoo.com',
#         'ODOO_DB': 'your-database',
#         'ODOO_USERNAME': 'your-username',
#         'ODOO_API_KEY': 'your-api-key'
#     }
    
#     try:
#         print("🚀 Test Odoo SaaS~18.2+ Integration")
#         print("=" * 50)
        
#         # Crea client
#         client = create_odoo_client(config)
        
#         # Test connessione
#         print("🔌 Test connessione:")
#         test_result = client.test_connection()
        
#         if test_result['success']:
#             version = test_result['connection_info']['server_version']
#             print(f"✅ Connesso a Odoo {version}")
            
#             # Mostra compatibilità
#             compat = test_result['compatibility']
#             print(f"📱 Campo mobile: {'✅' if compat['mobile_field_available'] else '❌'}")
#             print(f"💳 Campo payment_term: {'✅' if compat['invoice_payment_term_id_available'] else '❌'}")
#             print(f"📊 Campo analytic_distribution: {'✅' if compat['analytic_distribution_available'] else '❌'}")
            
#         else:
#             print(f"❌ Errore connessione: {test_result['error']}")
#             return
        
#         # Test lettura partner
#         print(f"\n👥 Test partner (primi 3):")
#         partners = client.get_partners_list(limit=3)
        
#         for partner in partners:
#             print(f"   {partner['id']}: {partner['display_name']}")
#             print(f"      📧 {partner['email'] or 'N/A'}")
#             print(f"      📞 {partner['phone'] or 'N/A'}")
#             print(f"      📱 {partner['mobile'] or 'N/A'}")
        
#         # Test servizi
#         print(f"\n🛍️ Test servizi (primi 3):")
#         services = client.get_available_services(limit=3)
        
#         for service in services:
#             print(f"   {service['id']}: {service['name']}")
#             print(f"      💰 Prezzo: {service['list_price']} EUR")
#             print(f"      🏷️ Categoria: {service['category']}")
        
#         # Test debug campi
#         print(f"\n🔍 Debug campi modelli:")
        
#         for model in ['res.partner', 'account.move', 'account.move.line']:
#             debug_info = client.debug_model_fields(model)
#             if debug_info['success']:
#                 print(f"   {model}: {debug_info['total_fields']} campi")
#                 print(f"      Campi chiave: {', '.join(debug_info['key_fields'][:5])}")
            
#         print(f"\n✅ Test completato con successo!")
            
#     except OdooException as e:
#         print(f"❌ Errore Odoo: {e}")
#     except Exception as e:
#         print(f"❌ Errore generico: {e}")


# if __name__ == '__main__':
#     # test_odoo_18_2_compatibility()
#     # Carica variabili dal file .env (opzionale)
#     import os
#     try:
#         from dotenv import load_dotenv
#         load_dotenv()  # Carica variabili dal file .env
#         print("📁 File .env caricato")
#     except ImportError:
#         print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")

#     # Configurazione tramite variabili d'ambiente (più sicuro)
#     url = os.getenv('ODOO_URL')
#     db = os.getenv('ODOO_DB')
#     username = os.getenv('ODOO_USERNAME')  # Valore di default aggiunto
#     api_key = os.getenv('ODOO_API_KEY')  # Legge da variabile d'ambiente
    
#     def get_odoo_client():
#         """Helper per creare client Odoo con configurazione"""
#         try:

#             odoo_config = {
#                 'ODOO_URL': url,
#                 'ODOO_DB': db,
#                 'ODOO_USERNAME': username,
#                 'ODOO_API_KEY': api_key
#             }
            
#             # Verifica configurazione
#             missing = [k for k, v in odoo_config.items() if not v]
#             if missing:
#                 raise Exception(f"Configurazione Odoo incompleta: {missing}")
            
#             return create_odoo_client(odoo_config)
            
#         except Exception as e:
#             logger.error(f"Errore creazione client Odoo: {e}")
#             raise

#     client = get_odoo_client()
#     client.get_all_products_for_select()