#!/usr/bin/env python3
"""
Odoo Integration v18.2+ - VERSIONE COMPLETAMENTE CORRETTA
Integrazione ottimizzata per Odoo SaaS~18.2+ con gestione dinamica dei campi
e correzioni specifiche per l'ultima versione
"""

import xmlrpc.client
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

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
    
    def create_invoice(self, invoice_data: InvoiceData) -> Optional[int]:
        """Crea fattura ottimizzata per Odoo 18.2+"""
        try:
            invoice_vals = self._prepare_invoice_data_v18_2(invoice_data)
            
            # Context specifico per creazione fatture in 18.2+
            context = self._get_default_context()
            context.update({
                'default_move_type': 'out_invoice',
                'move_type': 'out_invoice',
                'check_move_validity': False,  # Velocizza creazione
                'skip_account_move_synchronization': True  # Evita sync automatica
            })
            
            invoice_id = self.execute(
                'account.move', 
                'create', 
                [invoice_vals],
                context=context
            )
            
            # Gestione risposta (lista o singolo ID)
            if isinstance(invoice_id, list):
                invoice_id = invoice_id[0] if invoice_id else None
            
            if invoice_id:
                self.logger.info(f"Fattura creata con ID: {invoice_id}")
                return invoice_id
            else:
                raise OdooException("Creazione fattura fallita", 'INVOICE_CREATE_ERROR')
            
        except Exception as e:
            self.logger.error(f"Errore creazione fattura: {e}")
            raise OdooException(f"Errore creazione fattura: {e}", 'INVOICE_CREATE_ERROR')
    
    def _prepare_invoice_data_v18_2(self, invoice_data: InvoiceData) -> Dict[str, Any]:
        """Prepara dati fattura specifici per Odoo 18.2+ con gestione errori migliorata"""
        invoice_date = datetime.now().strftime('%Y-%m-%d')
        due_date = self._calculate_due_date(invoice_date, invoice_data)
        
        # Prepara righe fattura con controlli di sicurezza
        invoice_lines = []
        for item in invoice_data.items:
            line_vals = {
                'product_id': item.product_id,
                'quantity': item.quantity,
                'price_unit': item.price_unit,
                'name': item.name,
            }
            
            # Verifica e ottieni account di default se non specificato
            if item.account_id:
                line_vals['account_id'] = item.account_id
            else:
                # Prova a ottenere account di default dal prodotto
                try:
                    product_data = self.execute(
                        'product.product',
                        'read',
                        [item.product_id],
                        fields=['categ_id']
                    )
                    
                    if product_data and product_data[0].get('categ_id'):
                        categ_id = product_data[0]['categ_id'][0]
                        categ_data = self.execute(
                            'product.category',
                            'read',
                            [categ_id],
                            fields=['property_account_income_categ_id']
                        )
                        
                        if categ_data and categ_data[0].get('property_account_income_categ_id'):
                            line_vals['account_id'] = categ_data[0]['property_account_income_categ_id'][0]
                            self.logger.info(f"Account automatico trovato: {line_vals['account_id']}")
                    
                except Exception as e:
                    self.logger.warning(f"Impossibile ottenere account automatico: {e}")
                    # Odoo userà l'account di default se non specificato
            
            # Gestione analitici per 18.2+
            if item.analytic_distribution:
                line_vals['analytic_distribution'] = item.analytic_distribution
            
            # Gestione tasse
            if item.tax_ids:
                line_vals['tax_ids'] = [(6, 0, item.tax_ids)]
                
            invoice_lines.append((0, 0, line_vals))
        
        # Verifica che ci siano righe
        if not invoice_lines:
            raise OdooException("Nessuna riga fattura valida trovata", 'INVALID_INVOICE_LINES')
        
        # Dati fattura base per 18.2+
        invoice_vals = {
            'partner_id': invoice_data.partner_id,
            'move_type': 'out_invoice',
            'invoice_date': invoice_date,
            'invoice_date_due': due_date,
            'invoice_line_ids': invoice_lines,
            'state': 'draft',  # Sempre draft inizialmente
        }
        
        # Campi opzionali con validazione
        if invoice_data.reference:
            invoice_vals['ref'] = invoice_data.reference[:64]  # Limita lunghezza
        
        if invoice_data.journal_id:
            # Verifica che il journal esista
            try:
                journal_exists = self.execute(
                    'account.journal',
                    'search_count',
                    [('id', '=', invoice_data.journal_id), ('type', '=', 'sale')]
                )
                if journal_exists > 0:
                    invoice_vals['journal_id'] = invoice_data.journal_id
                else:
                    self.logger.warning(f"Journal {invoice_data.journal_id} non trovato, uso default")
            except:
                self.logger.warning(f"Errore verifica journal {invoice_data.journal_id}")
        
        # Campo payment term corretto per 18.2+
        if invoice_data.payment_term_id:
            try:
                term_exists = self.execute(
                    'account.payment.term',
                    'search_count',
                    [('id', '=', invoice_data.payment_term_id)]
                )
                if term_exists > 0:
                    invoice_vals['invoice_payment_term_id'] = invoice_data.payment_term_id
                else:
                    self.logger.warning(f"Payment term {invoice_data.payment_term_id} non trovato")
            except:
                self.logger.warning(f"Errore verifica payment term {invoice_data.payment_term_id}")
        
        if invoice_data.currency_id:
            try:
                currency_exists = self.execute(
                    'res.currency',
                    'search_count',
                    [('id', '=', invoice_data.currency_id)]
                )
                if currency_exists > 0:
                    invoice_vals['currency_id'] = invoice_data.currency_id
            except:
                pass
        
        if invoice_data.company_id:
            try:
                company_exists = self.execute(
                    'res.company',
                    'search_count',
                    [('id', '=', invoice_data.company_id)]
                )
                if company_exists > 0:
                    invoice_vals['company_id'] = invoice_data.company_id
            except:
                pass
        
        self.logger.info(f"Dati fattura preparati con {len(invoice_lines)} righe")
        return invoice_vals
    
    def confirm_invoice(self, invoice_id: int) -> bool:
        """Conferma fattura per Odoo 18.2+"""
        try:
            # Verifica stato attuale
            invoice_data = self.execute(
                'account.move', 
                'read', 
                [invoice_id], 
                fields=['state', 'name']
            )
            
            if not invoice_data:
                raise OdooException(f"Fattura {invoice_id} non trovata", 'INVOICE_NOT_FOUND')
            
            current_state = invoice_data[0].get('state', 'draft')
            
            if current_state == 'posted':
                self.logger.info('Fattura già confermata')
                return True
            elif current_state == 'draft':
                # In 18.2+ usa sempre action_post
                self.execute('account.move', 'action_post', [invoice_id])
                self.logger.info(f'Fattura {invoice_id} confermata')
                return True
            else:
                self.logger.warning(f'Stato fattura non gestito: {current_state}')
                return False
                
        except Exception as e:
            self.logger.error(f'Errore conferma fattura {invoice_id}: {e}')
            raise OdooException(f'Errore conferma fattura: {e}', 'INVOICE_CONFIRM_ERROR')
    
    def get_invoice_details(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Ottieni dettagli fattura per Odoo 18.2+"""
        try:
            # Campi verificati per 18.2+
            fields = [
                'name', 'partner_id', 'invoice_date', 'invoice_date_due', 
                'amount_total', 'state', 'move_type', 'currency_id',
                'invoice_payment_term_id', 'journal_id', 'company_id', 'ref',
                'amount_untaxed', 'amount_tax', 'payment_state'
            ]
            
            invoice_data = self.execute(
                'account.move', 
                'read', 
                [invoice_id],
                fields=fields
            )
            
            if invoice_data:
                inv = invoice_data[0]
                return {
                    'id': invoice_id,
                    'name': inv.get('name'),
                    'partner_name': inv['partner_id'][1] if inv.get('partner_id') else None,
                    'partner_id': inv['partner_id'][0] if inv.get('partner_id') else None,
                    'invoice_date': inv.get('invoice_date'),
                    'due_date': inv.get('invoice_date_due'),
                    'amount_total': inv.get('amount_total', 0.0),
                    'amount_untaxed': inv.get('amount_untaxed', 0.0),
                    'amount_tax': inv.get('amount_tax', 0.0),
                    'state': inv.get('state'),
                    'move_type': inv.get('move_type'),
                    'currency': inv['currency_id'][1] if inv.get('currency_id') else 'EUR',
                    'payment_state': inv.get('payment_state'),
                    'reference': inv.get('ref', ''),
                    'journal_name': inv['journal_id'][1] if inv.get('journal_id') else None,
                    'company_name': inv['company_id'][1] if inv.get('company_id') else None,
                    'payment_term_id': inv['invoice_payment_term_id'][0] if inv.get('invoice_payment_term_id') else None,
                    'payment_term_name': inv['invoice_payment_term_id'][1] if inv.get('invoice_payment_term_id') else None,
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Errore recupero dettagli fattura: {e}")
            raise OdooException(f"Errore recupero dettagli fattura: {e}", 'INVOICE_READ_ERROR')
    
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
    
    def get_available_services(self, limit: int = 100, search_term: str = "") -> List[Dict[str, Any]]:
        """Servizi/prodotti vendibili per 18.2+"""
        try:
            filters = [
                ('active', '=', True),
                ('sale_ok', '=', True)
            ]
            
            if search_term:
                filters.append(('name', 'ilike', search_term))
            
            service_ids = self.execute(
                'product.product',
                'search',
                filters,
                limit=limit,
                order='name asc'
            )
            
            if not service_ids:
                return []
            
            # Campi verificati per 18.2+
            fields = [
                'id', 'name', 'display_name', 'list_price', 'standard_price', 
                'type', 'default_code', 'sale_ok', 'categ_id', 'uom_id',
                'taxes_id'  # IVA di vendita
            ]
            
            services = self.execute(
                'product.product',
                'read',
                service_ids,
                fields=fields
            )
            
            result = []
            for service in services:
                result.append({
                    'id': service['id'],
                    'name': service['name'],
                    'display_name': service['display_name'],
                    'default_code': service.get('default_code', ''),
                    'list_price': service.get('list_price', 0.0),
                    'standard_price': service.get('standard_price', 0.0),
                    'type': service.get('type', 'service'),
                    'category': service.get('categ_id')[1] if service.get('categ_id') else '',
                    'uom': service.get('uom_id')[1] if service.get('uom_id') else '',
                    'taxes': [tax[1] for tax in service.get('taxes_id', [])],
                    'tax_ids': [tax[0] for tax in service.get('taxes_id', [])],
                    'sale_ok': service.get('sale_ok', False),
                    'suggested_price': service.get('list_price', 0.0)
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Errore recupero servizi: {e}")
            raise OdooException(f"Errore servizi: {e}", 'SERVICES_ERROR')
    
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
    
    def create_service_invoice(self, 
                            partner_id: int,
                            service_id: int,
                            service_description: str,
                            price_without_tax: float,
                            payment_term_id: Optional[int] = None,
                            create_draft: bool = False,
                            due_days: Optional[int] = None,
                            reference: str = "") -> Dict[str, Any]:
        """Crea fattura servizio ottimizzata per 18.2+ con gestione errori migliorata"""
        try:
            self.logger.info(f"Creazione fattura servizio - Cliente: {partner_id}, Servizio: {service_id}")
            
            # 1. Verifica partner
            partner_data = self.get_partner_by_id(partner_id)
            if not partner_data:
                raise OdooException(f"Cliente {partner_id} non trovato", 'PARTNER_NOT_FOUND')
            
            # 2. Verifica servizio con campi minimi sicuri
            try:
                service_data = self.execute(
                    'product.product', 
                    'read', 
                    [service_id],
                    fields=['id', 'name', 'sale_ok', 'list_price', 'taxes_id', 'categ_id', 'uom_id']
                )
                
                if not service_data:
                    raise OdooException(f"Servizio {service_id} non trovato", 'SERVICE_NOT_FOUND')
                
                service = service_data[0]
                if not service.get('sale_ok', False):
                    raise OdooException(f"Servizio {service_id} non vendibile", 'SERVICE_NOT_SALEABLE')
                
            except Exception as e:
                self.logger.error(f"Errore verifica servizio {service_id}: {e}")
                raise OdooException(f"Errore verifica servizio: {e}", 'SERVICE_VALIDATION_ERROR')
            
            # 3. Ottieni tasse del servizio
            tax_ids = [tax[0] for tax in service.get('taxes_id', [])]
            self.logger.info(f"Tasse trovate per servizio: {tax_ids}")
            
            # 4. Determina modalità pagamento con fallback sicuro
            final_payment_term_id = payment_term_id
            if not final_payment_term_id:
                # Prova a usare modalità pagamento del cliente
                try:
                    partner_payment_term = self.execute(
                        'res.partner',
                        'read',
                        [partner_id],
                        fields=['property_payment_term_id']
                    )
                    if partner_payment_term and partner_payment_term[0].get('property_payment_term_id'):
                        final_payment_term_id = partner_payment_term[0]['property_payment_term_id'][0]
                except:
                    # Se fallisce, usa None (default di sistema)
                    final_payment_term_id = None
            
            # 5. Ottieni account di default per il prodotto
            try:
                default_account = None
                if service.get('categ_id'):
                    categ_data = self.execute(
                        'product.category',
                        'read',
                        [service['categ_id'][0]],
                        fields=['property_account_income_categ_id']
                    )
                    if categ_data and categ_data[0].get('property_account_income_categ_id'):
                        default_account = categ_data[0]['property_account_income_categ_id'][0]
            except:
                default_account = None
            
            # 6. Crea item fattura con dati sicuri
            invoice_item = InvoiceItem(
                product_id=service_id,
                quantity=1.0,
                price_unit=price_without_tax,
                name=service_description,
                tax_ids=tax_ids if tax_ids else None
            )
            
            # Aggiungi account se disponibile
            if default_account:
                invoice_item.account_id = default_account
            
            # 7. Crea dati fattura con gestione sicura dei campi
            invoice_data = InvoiceData(
                partner_id=partner_id,
                items=[invoice_item],
                due_days=due_days,
                reference=reference,
                payment_term_id=final_payment_term_id
            )
            
            # 8. Crea fattura con gestione errori dettagliata
            try:
                if create_draft:
                    invoice_id = self.create_invoice(invoice_data)
                    status = "draft"
                    self.logger.info(f"Fattura bozza creata: {invoice_id}")
                else:
                    invoice_id = self.create_and_confirm_invoice(invoice_data)
                    status = "posted"
                    self.logger.info(f"Fattura confermata creata: {invoice_id}")
                
                if not invoice_id:
                    raise OdooException("Creazione fattura fallita - ID nullo", 'INVOICE_CREATION_FAILED')
                
            except Exception as e:
                self.logger.error(f"Errore dettagliato creazione fattura: {e}")
                # Prova a creare sempre come bozza se la conferma fallisce
                if not create_draft:
                    self.logger.warning("Tentativo creazione come bozza dopo fallimento conferma")
                    try:
                        invoice_id = self.create_invoice(invoice_data)
                        status = "draft"
                        self.logger.info(f"Fattura bozza creata come fallback: {invoice_id}")
                    except Exception as e2:
                        raise OdooException(f"Creazione fattura fallita completamente: {e2}", 'INVOICE_CREATION_FAILED')
                else:
                    raise OdooException(f"Creazione fattura fallita: {e}", 'INVOICE_CREATION_FAILED')
            
            # 9. Ottieni dettagli fattura con fallback
            try:
                invoice_details = self.get_invoice_details(invoice_id)
            except Exception as e:
                self.logger.warning(f"Errore recupero dettagli fattura {invoice_id}: {e}")
                # Crea dettagli minimi di fallback
                invoice_details = {
                    'id': invoice_id,
                    'name': f'Fattura {invoice_id}',
                    'state': status,
                    'partner_name': partner_data.get('display_name'),
                    'amount_total': price_without_tax * 1.22,  # Stima con IVA 22%
                    'amount_untaxed': price_without_tax,
                    'amount_tax': price_without_tax * 0.22,
                    'error': 'Dettagli parziali - recupero completo fallito'
                }
            
            # 10. Prepara risposta completa
            result = {
                'success': True,
                'invoice_id': invoice_id,
                'status': status,
                'message': f"Fattura {'bozza' if create_draft or status == 'draft' else 'confermata'} creata con successo",
                'invoice_details': invoice_details,
                'service_info': {
                    'service_id': service_id,
                    'service_name': service.get('name'),
                    'service_description': service_description,
                    'price_without_tax': price_without_tax,
                    'taxes_applied': len(tax_ids) if tax_ids else 0,
                    'default_account': default_account
                },
                'partner_info': {
                    'partner_id': partner_id,
                    'partner_name': partner_data.get('display_name'),
                    'partner_email': partner_data.get('email')
                },
                'payment_info': {
                    'payment_term_id': final_payment_term_id,
                    'due_date': invoice_details.get('due_date') if invoice_details else None,
                    'payment_term_source': 'custom' if payment_term_id else 'partner_default_or_system'
                },
                'debug_info': {
                    'taxes_found': tax_ids,
                    'account_used': default_account,
                    'fallback_used': status == 'draft' and not create_draft
                },
                'created_at': datetime.now().isoformat()
            }
            
            return result
            
        except OdooException:
            raise
        except Exception as e:
            error_msg = f"Errore generale creazione fattura servizio: {e}"
            self.logger.error(error_msg)
            raise OdooException(error_msg, 'SERVICE_INVOICE_ERROR')
    
    def get_all_partners_for_select(self) -> List[Dict[str, Any]]:
        """Partner per Select2 ottimizzato per 18.2+"""
        try:
            search_filters = [
                ('active', '=', True),
                ('customer_rank', '>', 0)
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
    
    def create_and_confirm_invoice(self, invoice_data: InvoiceData) -> Optional[int]:
        """Crea e conferma fattura"""
        try:
            invoice_id = self.create_invoice(invoice_data)
            
            if not invoice_id:
                return None
            
            if self.confirm_invoice(invoice_id):
                self.logger.info(f"Fattura {invoice_id} creata e confermata")
                return invoice_id
            else:
                self.logger.warning(f"Fattura {invoice_id} creata ma non confermata")
                return invoice_id
                
        except Exception as e:
            self.logger.error(f"Errore creazione e conferma fattura: {e}")
            raise
    
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


# Esempi di utilizzo per test
def test_odoo_18_2_compatibility():
    """Test compatibilità completa per Odoo 18.2+"""
    config = {
        'ODOO_URL': 'https://your-instance.odoo.com',
        'ODOO_DB': 'your-database',
        'ODOO_USERNAME': 'your-username',
        'ODOO_API_KEY': 'your-api-key'
    }
    
    try:
        print("🚀 Test Odoo SaaS~18.2+ Integration")
        print("=" * 50)
        
        # Crea client
        client = create_odoo_client(config)
        
        # Test connessione
        print("🔌 Test connessione:")
        test_result = client.test_connection()
        
        if test_result['success']:
            version = test_result['connection_info']['server_version']
            print(f"✅ Connesso a Odoo {version}")
            
            # Mostra compatibilità
            compat = test_result['compatibility']
            print(f"📱 Campo mobile: {'✅' if compat['mobile_field_available'] else '❌'}")
            print(f"💳 Campo payment_term: {'✅' if compat['invoice_payment_term_id_available'] else '❌'}")
            print(f"📊 Campo analytic_distribution: {'✅' if compat['analytic_distribution_available'] else '❌'}")
            
        else:
            print(f"❌ Errore connessione: {test_result['error']}")
            return
        
        # Test lettura partner
        print(f"\n👥 Test partner (primi 3):")
        partners = client.get_partners_list(limit=3)
        
        for partner in partners:
            print(f"   {partner['id']}: {partner['display_name']}")
            print(f"      📧 {partner['email'] or 'N/A'}")
            print(f"      📞 {partner['phone'] or 'N/A'}")
            print(f"      📱 {partner['mobile'] or 'N/A'}")
        
        # Test servizi
        print(f"\n🛍️ Test servizi (primi 3):")
        services = client.get_available_services(limit=3)
        
        for service in services:
            print(f"   {service['id']}: {service['name']}")
            print(f"      💰 Prezzo: {service['list_price']} EUR")
            print(f"      🏷️ Categoria: {service['category']}")
        
        # Test debug campi
        print(f"\n🔍 Debug campi modelli:")
        
        for model in ['res.partner', 'account.move', 'account.move.line']:
            debug_info = client.debug_model_fields(model)
            if debug_info['success']:
                print(f"   {model}: {debug_info['total_fields']} campi")
                print(f"      Campi chiave: {', '.join(debug_info['key_fields'][:5])}")
            
        print(f"\n✅ Test completato con successo!")
            
    except OdooException as e:
        print(f"❌ Errore Odoo: {e}")
    except Exception as e:
        print(f"❌ Errore generico: {e}")


if __name__ == '__main__':
    test_odoo_18_2_compatibility()