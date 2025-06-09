#!/usr/bin/env python3
"""
Odoo Integration v18 - VERSIONE CORRETTA per problema campo mobile
Correzione per gestire dinamicamente i campi disponibili in res.partner
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
    """Item fattura per Odoo 18"""
    product_id: int
    quantity: float
    price_unit: float
    name: str
    description: str = ""
    # Nuovi campi per Odoo 18
    account_id: Optional[int] = None  # Account contabile specifico
    analytic_account_id: Optional[int] = None  # Conto analitico
    tax_ids: Optional[List[int]] = None  # IVA applicabili

@dataclass  
class InvoiceData:
    """Dati fattura completi per Odoo 18"""
    partner_id: int
    items: List[InvoiceItem]
    due_days: Optional[int] = None
    manual_due_date: Optional[str] = None
    reference: str = ""
    # Nuovi campi per Odoo 18
    journal_id: Optional[int] = None  # Sezionale contabile
    payment_term_id: Optional[int] = None  # Condizioni di pagamento
    currency_id: Optional[int] = None  # Valuta
    company_id: Optional[int] = None  # Multi-company

class OdooClient:
    """Client Odoo ottimizzato per Odoo 18 con gestione dinamica campi"""
    
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
        # 🔧 CACHE per campi disponibili
        self._available_fields_cache = {}
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
        """Connessione e autenticazione Odoo 18"""
        try:
            self.common = xmlrpc.client.ServerProxy(
                f"{self.config['ODOO_URL']}/xmlrpc/2/common",
                allow_none=True  # Importante per Odoo 18
            )
            
            # Verifica versione server
            self.version_info = self.common.version()
            self.logger.info(f"Connessione a Odoo {self.version_info['server_version']}")
            
            # Verifica compatibilità
            if not self._check_version_compatibility():
                self.logger.warning("Versione Odoo potrebbe non essere completamente compatibile")
            
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
                allow_none=True
            )
            
            self.logger.info(f"Connesso ad Odoo con UID: {self.uid}")
            return True
            
        except Exception as e:
            error_msg = f"Errore connessione Odoo: {e}"
            self.logger.error(error_msg)
            raise OdooException(error_msg, 'CONNECTION_ERROR')
    
    def _check_version_compatibility(self) -> bool:
        """Verifica compatibilità versione Odoo"""
        if not self.version_info:
            return False
        
        version = self.version_info.get('server_version', '')
        
        # Verifica se è Odoo 18.x
        if version.startswith('18.'):
            return True
        elif version.startswith(('17.', '16.', '15.')):
            self.logger.warning(f"Versione {version} supportata ma potrebbero servire adattamenti")
            return True
        else:
            self.logger.warning(f"Versione {version} non testata")
            return False
    
    def execute(self, model: str, method: str, *args, **kwargs):
        """Wrapper per execute_kw con gestione errori migliorata per Odoo 18"""
        if not self.uid or not self.models:
            if not self.connect():
                raise OdooException("Impossibile connettersi ad Odoo", 'CONNECTION_ERROR')
        
        try:
            # Aggiunge context di default per Odoo 18
            if 'context' not in kwargs:
                kwargs['context'] = self._get_default_context()
            
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
        """Context di default per Odoo 18"""
        return {
            'lang': 'it_IT',
            'tz': 'Europe/Rome',
            'active_test': True,
            # Context specifici per Odoo 18
            'mail_create_nolog': True,  # Evita log automatici
            'mail_create_nosubscribe': True,  # Evita sottoscrizioni automatiche
        }
    
    def _get_available_fields(self, model: str) -> List[str]:
        """🔧 NUOVO: Ottiene dinamicamente i campi disponibili per un modello"""
        if model in self._available_fields_cache:
            return self._available_fields_cache[model]
        
        try:
            # Ottieni definizioni dei campi
            fields_info = self.execute(model, 'fields_get', [])
            available_fields = list(fields_info.keys())
            
            # Caching per performance
            self._available_fields_cache[model] = available_fields
            
            self.logger.debug(f"Campi disponibili per {model}: {len(available_fields)} campi")
            return available_fields
            
        except Exception as e:
            self.logger.error(f"Errore recupero campi per {model}: {e}")
            return []
    
    def _get_safe_partner_fields(self) -> List[str]:
        """🔧 NUOVO: Restituisce lista sicura di campi partner"""
        # Campi base sempre presenti
        base_fields = [
            'id', 'name', 'display_name', 'email', 'phone',
            'vat', 'is_company', 'customer_rank', 'supplier_rank',
            'street', 'street2', 'city', 'zip', 'state_id', 'country_id',
            'create_date', 'write_date', 'active', 'category_id',
            'commercial_partner_id', 'parent_id', 'lang', 'tz'
        ]
        
        # Ottieni campi disponibili dinamicamente
        available_fields = self._get_available_fields('res.partner')
        
        # Campi opzionali da verificare
        optional_fields = ['mobile', 'website', 'comment', 'ref', 'child_ids']
        
        # Aggiungi solo campi che esistono realmente
        safe_fields = base_fields.copy()
        for field in optional_fields:
            if field in available_fields:
                safe_fields.append(field)
                self.logger.debug(f"Campo {field} disponibile in res.partner")
            else:
                self.logger.debug(f"Campo {field} NON disponibile in res.partner")
        
        return safe_fields
    
    def create_invoice(self, invoice_data: InvoiceData) -> Optional[int]:
        """Crea fattura ottimizzata per Odoo 18"""
        try:
            # Prepara dati fattura
            invoice_vals = self._prepare_invoice_data(invoice_data)
            
            # Crea fattura con context specifico
            context = self._get_default_context()
            context.update({
                'default_move_type': 'out_invoice',
                'move_type': 'out_invoice'
            })
            
            invoice_id = self.execute(
                'account.move', 
                'create', 
                [invoice_vals],
                context=context
            )
            
            # In Odoo 18, create potrebbe restituire una lista
            if isinstance(invoice_id, list):
                invoice_id = invoice_id[0]
            
            self.logger.info(f"Fattura creata con ID: {invoice_id}")
            return invoice_id
            
        except Exception as e:
            self.logger.error(f"Errore creazione fattura: {e}")
            raise OdooException(f"Errore creazione fattura: {e}", 'INVOICE_CREATE_ERROR')
    
    def confirm_invoice(self, invoice_id: int) -> bool:
        """Conferma fattura per Odoo 18"""
        try:
            # Verifica stato fattura
            invoice_data = self.execute(
                'account.move', 
                'read', 
                [invoice_id], 
                fields=['state', 'name', 'move_type']
            )
            
            if not invoice_data:
                raise OdooException(f"Fattura {invoice_id} non trovata", 'INVOICE_NOT_FOUND')
            
            invoice = invoice_data[0]
            current_state = invoice.get('state', 'draft')
            
            if current_state == 'posted':
                self.logger.info('Fattura già confermata')
                return True
            elif current_state == 'draft':
                # In Odoo 18, il metodo potrebbe essere action_post
                try:
                    self.execute('account.move', 'action_post', [invoice_id])
                    self.logger.info('Fattura confermata con action_post')
                    return True
                except:
                    # Fallback per versioni precedenti
                    self.execute('account.move', 'post', [invoice_id])
                    self.logger.info('Fattura confermata con post')
                    return True
            else:
                self.logger.warning(f'Stato fattura non gestito: {current_state}')
                return False
                
        except Exception as e:
            self.logger.error(f'Errore conferma fattura: {e}')
            raise OdooException(f'Errore conferma fattura: {e}', 'INVOICE_CONFIRM_ERROR')
    
    def _prepare_invoice_data(self, invoice_data: InvoiceData) -> Dict[str, Any]:
        """Prepara dati per creazione fattura Odoo 18"""
        # Calcola data scadenza
        invoice_date = datetime.now().strftime('%Y-%m-%d')
        due_date = self._calculate_due_date(invoice_date, invoice_data)
        
        # Prepara righe fattura
        invoice_lines = []
        for item in invoice_data.items:
            line_vals = {
                'product_id': item.product_id,
                'quantity': item.quantity,
                'price_unit': item.price_unit,
                'name': item.name,
            }
            
            # Campi opzionali
            if item.description:
                line_vals['description'] = item.description
            
            if item.account_id:
                line_vals['account_id'] = item.account_id
            
            if item.analytic_account_id:
                line_vals['analytic_account_id'] = item.analytic_account_id
            
            if item.tax_ids:
                # In Odoo 18, formato corretto per many2many
                line_vals['tax_ids'] = [(6, 0, item.tax_ids)]
                
            invoice_lines.append((0, 0, line_vals))
        
        # Dati fattura base
        invoice_vals = {
            'partner_id': invoice_data.partner_id,
            'move_type': 'out_invoice',
            'invoice_date': invoice_date,
            'invoice_date_due': due_date,
            'invoice_line_ids': invoice_lines,
        }
        
        # Campi opzionali per Odoo 18
        if invoice_data.reference:
            invoice_vals['ref'] = invoice_data.reference
        
        if invoice_data.journal_id:
            invoice_vals['journal_id'] = invoice_data.journal_id
        
        if invoice_data.payment_term_id:
            invoice_vals['invoice_payment_term_id'] = invoice_data.payment_term_id
        
        if invoice_data.currency_id:
            invoice_vals['currency_id'] = invoice_data.currency_id
        
        if invoice_data.company_id:
            invoice_vals['company_id'] = invoice_data.company_id
        
        return invoice_vals
    
    def get_invoice_details(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Ottieni dettagli fattura per Odoo 18"""
        try:
            # Campi aggiornati per Odoo 18
            fields = [
                'name', 'partner_id', 'invoice_date', 'invoice_date_due', 
                'amount_total', 'state', 'move_type', 'currency_id',
                'payment_term_id', 'journal_id', 'company_id', 'ref',
                'amount_untaxed', 'amount_tax', 'invoice_payment_state'
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
                    'amount_total': inv.get('amount_total'),
                    'amount_untaxed': inv.get('amount_untaxed'),
                    'amount_tax': inv.get('amount_tax'),
                    'state': inv.get('state'),
                    'move_type': inv.get('move_type'),
                    'currency': inv['currency_id'][1] if inv.get('currency_id') else 'EUR',
                    'payment_state': inv.get('invoice_payment_state'),
                    'reference': inv.get('ref', ''),
                    'journal_name': inv['journal_id'][1] if inv.get('journal_id') else None,
                    'company_name': inv['company_id'][1] if inv.get('company_id') else None,
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Errore recupero dettagli fattura: {e}")
            raise OdooException(f"Errore recupero dettagli fattura: {e}", 'INVOICE_READ_ERROR')
    
    def get_partners_list(self, limit: int = 100, offset: int = 0, filters: List = None) -> List[Dict[str, Any]]:
        """🔧 CORRETTO: Ottiene lista partner con campi dinamici"""
        try:
            # 🔧 Usa campi sicuri dinamici
            base_fields = self._get_safe_partner_fields()
            
            # Filtri di default aggiornati per Odoo 18
            default_filters = [
                ('active', '=', True),
                ('customer_rank', '>', 0)
            ]
            
            if filters:
                search_filters = default_filters + filters
            else:
                search_filters = default_filters
            
            # Context specifico per la ricerca
            context = self._get_default_context()
            context.update({'active_test': False})
            
            # Cerca partner
            partner_ids = self.execute(
                'res.partner', 
                'search', 
                search_filters,
                limit=limit, 
                offset=offset,
                context=context
            )
            
            if not partner_ids:
                return []
            
            # Recupera dati completi con campi sicuri
            partners_data = self.execute(
                'res.partner', 
                'read', 
                partner_ids, 
                fields=base_fields,
                context=context
            )
            
            # Elabora dati
            processed_partners = []
            for partner in partners_data:
                processed_partner = self._process_partner_data(partner)
                processed_partners.append(processed_partner)
            
            self.logger.info(f"Recuperati {len(processed_partners)} partner da Odoo")
            return processed_partners
            
        except Exception as e:
            self.logger.error(f"Errore recupero lista partner: {e}")
            raise OdooException(f"Errore recupero partner: {e}", 'PARTNERS_READ_ERROR')
    
    def _process_partner_data(self, partner: Dict, extended: bool = False) -> Dict[str, Any]:
        """🔧 CORRETTO: Elabora dati partner gestendo campi mancanti"""
        try:
            # Verifica se mobile è disponibile nei dati
            has_mobile = 'mobile' in partner
            
            processed = {
                'id': partner.get('id'),
                'name': partner.get('name', ''),
                'display_name': partner.get('display_name', ''),
                'email': partner.get('email', ''),
                'phone': partner.get('phone', ''),
                'mobile': partner.get('mobile', '') if has_mobile else '',  # 🔧 Gestione condizionale
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
                
                # Date
                'create_date': partner.get('create_date', ''),
                'write_date': partner.get('write_date', ''),
                
                # Relazioni
                'categories': [cat[1] for cat in partner.get('category_id', [])] if partner.get('category_id') else [],
                'category_ids': [cat[0] for cat in partner.get('category_id', [])] if partner.get('category_id') else [],
                'parent_id': partner.get('parent_id')[0] if partner.get('parent_id') else None,
                'parent_name': partner.get('parent_id')[1] if partner.get('parent_id') else '',
                'commercial_partner_id': partner.get('commercial_partner_id')[0] if partner.get('commercial_partner_id') else None,
            }
            
            # 🔧 Campi opzionali se disponibili
            if 'website' in partner:
                processed['website'] = partner.get('website', '')
            
            if 'comment' in partner:
                processed['comment'] = partner.get('comment', '')
            
            if 'ref' in partner:
                processed['ref'] = partner.get('ref', '')
            
            # Genera indirizzo completo
            address_parts = [
                processed['street'],
                processed['street2'],
                processed['city'],
                processed['zip'],
                processed['state_name'],
                processed['country_name']
            ]
            processed['full_address'] = ', '.join([part for part in address_parts if part])
            
            # Tipo partner
            processed['partner_type'] = 'Azienda' if processed['is_company'] else 'Persona'
            
            # Status
            status_parts = []
            if processed['customer_rank'] > 0:
                status_parts.append('Cliente')
            if processed['supplier_rank'] > 0:
                status_parts.append('Fornitore')
            processed['partner_status'] = ' / '.join(status_parts) if status_parts else 'Contatto'
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Errore elaborazione dati partner: {e}")
            return {
                'id': partner.get('id'),
                'name': partner.get('name', 'N/A'),
                'display_name': partner.get('display_name', 'N/A'),
                'email': partner.get('email', ''),
                'mobile': '',
                'phone': partner.get('phone', ''),
                'error': str(e)
            }
    
    def get_company_info(self) -> Dict[str, Any]:
        """Ottiene informazioni azienda corrente per Odoo 18"""
        try:
            # Ottieni azienda dell'utente corrente
            user_data = self.execute('res.users', 'read', [self.uid], fields=['company_id'])
            company_id = user_data[0]['company_id'][0]
            
            # Ottieni dettagli azienda
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
    
    def get_products_list(self, limit: int = 100, filters: List = None) -> List[Dict[str, Any]]:
        """Ottiene lista prodotti per Odoo 18"""
        try:
            # Filtri di default per prodotti
            default_filters = [
                ('active', '=', True),
                ('sale_ok', '=', True)  # Solo prodotti vendibili
            ]
            
            if filters:
                search_filters = default_filters + filters
            else:
                search_filters = default_filters
            
            # Cerca prodotti
            product_ids = self.execute(
                'product.product', 
                'search', 
                search_filters,
                limit=limit
            )
            
            if not product_ids:
                return []
            
            # Campi prodotto per Odoo 18
            fields = [
                'id', 'name', 'display_name', 'default_code', 'barcode',
                'list_price', 'standard_price', 'currency_id', 'uom_id',
                'categ_id', 'active', 'sale_ok', 'purchase_ok',
                'type', 'invoice_policy', 'tracking'
            ]
            
            products_data = self.execute(
                'product.product', 
                'read', 
                product_ids, 
                fields=fields
            )
            
            processed_products = []
            for product in products_data:
                processed = {
                    'id': product.get('id'),
                    'name': product.get('name', ''),
                    'display_name': product.get('display_name', ''),
                    'default_code': product.get('default_code', ''),
                    'barcode': product.get('barcode', ''),
                    'list_price': product.get('list_price', 0.0),
                    'standard_price': product.get('standard_price', 0.0),
                    'currency': product.get('currency_id')[1] if product.get('currency_id') else 'EUR',
                    'uom': product.get('uom_id')[1] if product.get('uom_id') else '',
                    'category': product.get('categ_id')[1] if product.get('categ_id') else '',
                    'type': product.get('type', 'consu'),
                    'invoice_policy': product.get('invoice_policy', 'order'),
                    'tracking': product.get('tracking', 'none'),
                    'active': product.get('active', True),
                    'sale_ok': product.get('sale_ok', False),
                    'purchase_ok': product.get('purchase_ok', False)
                }
                processed_products.append(processed)
            
            self.logger.info(f"Recuperati {len(processed_products)} prodotti")
            return processed_products
            
        except Exception as e:
            self.logger.error(f"Errore recupero prodotti: {e}")
            raise OdooException(f"Errore recupero prodotti: {e}", 'PRODUCTS_READ_ERROR')
    
    def search_partners(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """🔧 CORRETTO: Cerca partner per nome, email o codice fiscale"""
        try:
            # Filtri di ricerca multipli
            search_filters = [
                ('active', '=', True),
                ('customer_rank', '>', 0),
                '|', '|', '|',  # OR logico tra i seguenti campi
                ('name', 'ilike', search_term),
                ('display_name', 'ilike', search_term),
                ('email', 'ilike', search_term),
                ('vat', 'ilike', search_term)
            ]
            
            return self.get_partners_list(limit=limit, filters=search_filters[2:])  # Esclude filtri base già inclusi
            
        except Exception as e:
            self.logger.error(f"Errore ricerca partner '{search_term}': {e}")
            raise OdooException(f"Errore ricerca partner: {e}", 'PARTNERS_SEARCH_ERROR')

    def get_partner_by_id(self, partner_id: int) -> Optional[Dict[str, Any]]:
        """🔧 CORRETTO: Ottiene un partner specifico per ID"""
        try:
            # Usa campi sicuri
            base_fields = self._get_safe_partner_fields()
            
            partner_data = self.execute('res.partner', 'read', [partner_id], fields=base_fields)
            
            if partner_data:
                return self._process_partner_data(partner_data[0], extended=True)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Errore recupero partner ID {partner_id}: {e}")
            raise OdooException(f"Errore recupero partner: {e}", 'PARTNER_READ_ERROR')

    def get_partners_count(self, filters: List = None) -> int:
        """Conta il numero totale di partner che corrispondono ai filtri"""
        try:
            # Filtri di default
            default_filters = [
                ('active', '=', True),
                ('customer_rank', '>', 0)
            ]
            
            if filters:
                search_filters = default_filters + filters
            else:
                search_filters = default_filters
            
            count = self.execute('res.partner', 'search_count', search_filters)
            
            self.logger.info(f"Numero totale partner: {count}")
            return count
            
        except Exception as e:
            self.logger.error(f"Errore conteggio partner: {e}")
            raise OdooException(f"Errore conteggio partner: {e}", 'PARTNERS_COUNT_ERROR')

    def get_partners_summary(self) -> Dict[str, Any]:
        """🔧 CORRETTO: Ottiene statistiche riassuntive sui partner con gestione mobile"""
        try:
            # Conteggi per tipo
            total_customers = self.get_partners_count()
            
            # Aziende vs persone
            companies_count = self.get_partners_count([('is_company', '=', True)])
            individuals_count = total_customers - companies_count
            
            # Partner con email
            with_email_count = self.get_partners_count([('email', '!=', False)])
            
            # 🔧 Partner con telefono - gestione dinamica del campo mobile
            available_fields = self._get_available_fields('res.partner')
            
            if 'mobile' in available_fields:
                # Se mobile esiste, usa entrambi i campi
                try:
                    with_phone_count = self.get_partners_count([
                        '|', 
                        ('phone', '!=', False), 
                        ('mobile', '!=', False)
                    ])
                    phone_fields_used = "phone, mobile"
                except:
                    # Fallback a solo phone se la query con mobile fallisce
                    with_phone_count = self.get_partners_count([('phone', '!=', False)])
                    phone_fields_used = "phone"
            else:
                # Solo phone se mobile non esiste
                with_phone_count = self.get_partners_count([('phone', '!=', False)])
                phone_fields_used = "phone"
            
            summary = {
                'total_customers': total_customers,
                'companies': companies_count,
                'individuals': individuals_count,
                'with_email': with_email_count,
                'with_phone': with_phone_count,
                'email_coverage': round((with_email_count / total_customers) * 100, 1) if total_customers > 0 else 0,
                'phone_coverage': round((with_phone_count / total_customers) * 100, 1) if total_customers > 0 else 0,
                'phone_fields_used': phone_fields_used,  # Info su quali campi sono stati usati
                'mobile_field_available': 'mobile' in available_fields,
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Statistiche partner generate: {total_customers} clienti totali")
            return summary
            
        except Exception as e:
            self.logger.error(f"Errore generazione statistiche partner: {e}")
            raise OdooException(f"Errore statistiche partner: {e}", 'PARTNERS_STATS_ERROR')

    def test_connection(self) -> Dict[str, Any]:
        """🔧 CORRETTO: Test connessione completo per Odoo 18"""
        try:
            # Test connessione base
            if not self.connect():
                return {'success': False, 'error': 'Connessione fallita'}
            
            # Test lettura dati base
            user_data = self.execute('res.users', 'read', [self.uid], fields=['name', 'login'])
            company_info = self.get_company_info()
            
            # Test conteggi
            partners_count = self.execute('res.partner', 'search_count', [('customer_rank', '>', 0)])
            products_count = self.execute('product.product', 'search_count', [('sale_ok', '=', True)])
            
            # 🔧 Test campi disponibili
            available_partner_fields = self._get_available_fields('res.partner')
            mobile_available = 'mobile' in available_partner_fields
            
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
                'field_compatibility': {
                    'mobile_field_available': mobile_available,
                    'total_partner_fields': len(available_partner_fields),
                    'safe_fields_count': len(self._get_safe_partner_fields())
                },
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    # Metodi helper per compatibilità
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
        """Crea e conferma fattura in un unico passaggio"""
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

    def get_all_partners_for_select(self) -> List[Dict[str, Any]]:
        try:
            # Filtri minimal per clienti attivi
            search_filters = [
                ('active', '=', True),
                ('customer_rank', '>', 0)
            ]
            
            # Context minimal per performance
            context = {'active_test': False}
            
            # Recupera tutti gli ID senza limite
            partner_ids = self.execute(
                'res.partner', 
                'search', 
                search_filters,
                context=context
            )
            
            if not partner_ids:
                self.logger.warning("Nessun partner trovato per Select2")
                return []
            
            # Leggi solo i campi necessari per Select2
            minimal_fields = ['commercial_partner_id', 'display_name']
            
            partners_data = self.execute(
                'res.partner', 
                'read', 
                partner_ids, 
                fields=minimal_fields,
                context=context
            )
            
            # Elabora dati per Select2
            select_partners = []
            for partner in partners_data:
                # Estrai commercial_partner_id (può essere una tupla [id, name] o solo id)
                commercial_id = partner.get('commercial_partner_id')
                if isinstance(commercial_id, list) and len(commercial_id) > 0:
                    commercial_partner_id = commercial_id[0]
                else:
                    commercial_partner_id = commercial_id
                
                select_partners.append({
                    'commercial_partner_id': commercial_partner_id,
                    'display_name': partner.get('display_name', '')
                })
            
            self.logger.info(f"Recuperati {len(select_partners)} partner per Select2")
            return select_partners
            
        except Exception as e:
            self.logger.error(f"Errore recupero partner per Select2: {e}")
            raise OdooException(f"Errore recupero partner per Select2: {e}", 'PARTNERS_SELECT_ERROR')    


def create_odoo_client(config: Dict[str, Any]) -> OdooClient:
    """Factory function per creare client Odoo 18"""
    return OdooClient(config)


def example_test_mobile_field():
    """🆕 Esempio per testare la gestione del campo mobile"""
    # Configurazione (normalmente da SecureConfig)
    config = {
        'ODOO_URL': 'https://mysite.odoo.com/',
        'ODOO_DB': 'mydb',
        'ODOO_USERNAME': 'user@domain.com',
        'ODOO_API_KEY': 'api_key_here'
    }
    
    try:
        # Crea client
        client = create_odoo_client(config)
        
        # Test connessione con info sui campi
        print("🔌 Test connessione con verifica campi:")
        test_result = client.test_connection()
        
        if test_result['success']:
            print(f"✅ Connesso a {test_result['connection_info']['server_version']}")
            
            # Info compatibilità campi
            field_info = test_result['field_compatibility']
            print(f"📋 Campo mobile disponibile: {field_info['mobile_field_available']}")
            print(f"📋 Campi partner totali: {field_info['total_partner_fields']}")
            print(f"📋 Campi sicuri utilizzati: {field_info['safe_fields_count']}")
            
        else:
            print(f"❌ Errore connessione: {test_result['error']}")
            return
        
        # Test lista partner (dovrebbe funzionare ora)
        print("\n👥 Test lista partner (primi 5):")
        partners = client.get_partners_list(limit=5)
        
        for partner in partners:
            print(f"   {partner['id']}: {partner['display_name']}")
            if partner['email']:
                print(f"      📧 {partner['email']}")
            if partner['phone']:
                print(f"      📞 {partner['phone']}")
            if partner['mobile']:
                print(f"      📱 {partner['mobile']}")
            else:
                print(f"      📱 Mobile: non disponibile")
        
        # Test statistiche con info sui campi usati
        print("\n📊 Statistiche con info campi:")
        summary = client.get_partners_summary()
        print(f"   Totale clienti: {summary['total_customers']}")
        print(f"   Con telefono: {summary['with_phone']} ({summary['phone_coverage']}%)")
        print(f"   Campi telefono usati: {summary['phone_fields_used']}")
        print(f"   Campo mobile disponibile: {summary['mobile_field_available']}")
            
    except OdooException as e:
        print(f"❌ Errore Odoo: {e}")
    except Exception as e:
        print(f"❌ Errore generico: {e}")


def example_field_detection():
    """🆕 Esempio per vedere tutti i campi disponibili in res.partner"""
    config = {
        'ODOO_URL': 'https://mysite.odoo.com/',
        'ODOO_DB': 'mydb',
        'ODOO_USERNAME': 'user@domain.com',
        'ODOO_API_KEY': 'api_key_here'
    }
    
    try:
        client = create_odoo_client(config)
        
        # Ottieni tutti i campi disponibili
        print("🔍 Rilevamento campi res.partner:")
        available_fields = client._get_available_fields('res.partner')
        
        # Campi che il nostro codice cerca
        expected_fields = ['mobile', 'website', 'comment', 'ref', 'child_ids']
        
        print(f"📋 Campi totali disponibili: {len(available_fields)}")
        print("\n🔎 Verifica campi opzionali:")
        
        for field in expected_fields:
            status = "✅ Disponibile" if field in available_fields else "❌ Non disponibile"
            print(f"   {field}: {status}")
        
        # Campi sicuri che verranno usati
        safe_fields = client._get_safe_partner_fields()
        print(f"\n📝 Campi sicuri utilizzati ({len(safe_fields)}):")
        for field in safe_fields:
            print(f"   - {field}")
            
        # Test con partner reale
        print(f"\n👤 Test lettura partner (primi 2):")
        partners = client.get_partners_list(limit=2)
        
        for partner in partners[:2]:  # Solo primi 2 per brevità
            print(f"\nPartner {partner['id']}: {partner['name']}")
            print(f"   Email: {partner.get('email', 'N/A')}")
            print(f"   Phone: {partner.get('phone', 'N/A')}")
            print(f"   Mobile: {partner.get('mobile', 'Campo non disponibile')}")
            print(f"   Città: {partner.get('city', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Errore: {e}")


if __name__ == '__main__':
    print("🚀 Test Odoo Integration v18 - VERSIONE CORRETTA")
    print("=" * 60)
    
    # Test gestione campo mobile
    example_test_mobile_field()
    
    print("\n" + "=" * 60)
    print("🔍 Test rilevamento campi")
    example_field_detection()