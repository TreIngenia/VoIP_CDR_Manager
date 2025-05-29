#!/usr/bin/env python3
"""
Odoo Integration - Client Odoo integrato nel sistema principale
Sostituisce gen_odoo_invoice_token.py con architettura migliorata
"""

import xmlrpc.client
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from logger_config import get_logger
from exception_handler import OdooException

@dataclass
class InvoiceItem:
    """Item fattura"""
    product_id: int
    quantity: float
    price_unit: float
    name: str
    description: str = ""

@dataclass  
class InvoiceData:
    """Dati fattura completi"""
    partner_id: int
    items: List[InvoiceItem]
    due_days: Optional[int] = None
    manual_due_date: Optional[str] = None
    reference: str = ""

class OdooClient:
    """Client Odoo integrato e migliorato"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(__name__)
        self.uid = None
        self.models = None
        self.common = None
        self._validate_config()
    
    def _validate_config(self):
        """Valida configurazione Odoo"""
        required_keys = ['ODOO_URL', 'ODOO_DB', 'ODOO_USERNAME', 'ODOO_API_KEY']
        missing = [k for k in required_keys if not self.config.get(k)]
        
        if missing:
            raise OdooException(f"Configurazione Odoo incompleta: {missing}", 'CONFIG_ERROR')
    
    def connect(self) -> bool:
        """Connessione e autenticazione Odoo"""
        try:
            self.common = xmlrpc.client.ServerProxy(f"{self.config['ODOO_URL']}/xmlrpc/2/common")
            
            self.uid = self.common.authenticate(
                self.config['ODOO_DB'],
                self.config['ODOO_USERNAME'], 
                self.config['ODOO_API_KEY'],
                {}
            )
            
            if not self.uid:
                raise OdooException("Autenticazione Odoo fallita", 'AUTH_ERROR')
            
            self.models = xmlrpc.client.ServerProxy(f"{self.config['ODOO_URL']}/xmlrpc/2/object")
            self.logger.info(f"Connesso ad Odoo con UID: {self.uid}")
            return True
            
        except Exception as e:
            error_msg = f"Errore connessione Odoo: {e}"
            self.logger.error(error_msg)
            raise OdooException(error_msg, 'CONNECTION_ERROR')
    
    def execute(self, model: str, method: str, *args, **kwargs):
        """Wrapper per execute_kw con gestione errori"""
        if not self.uid or not self.models:
            if not self.connect():
                raise OdooException("Impossibile connettersi ad Odoo", 'CONNECTION_ERROR')
        
        try:
            if kwargs:
                return self.models.execute_kw(
                    self.config['ODOO_DB'], self.uid, self.config['ODOO_API_KEY'],
                    model, method, list(args), kwargs
                )
            else:
                return self.models.execute_kw(
                    self.config['ODOO_DB'], self.uid, self.config['ODOO_API_KEY'],
                    model, method, list(args)
                )
        except Exception as e:
            error_msg = f"Errore esecuzione {model}.{method}: {e}"
            self.logger.error(error_msg)
            raise OdooException(error_msg, 'EXECUTION_ERROR')
    
    def create_invoice(self, invoice_data: InvoiceData) -> Optional[int]:
        """Crea fattura singola"""
        try:
            # Prepara dati fattura
            invoice_vals = self._prepare_invoice_data(invoice_data)
            
            # Crea fattura
            invoice_id = self.execute('account.move', 'create', [invoice_vals])
            
            self.logger.info(f"Fattura creata con ID: {invoice_id}")
            return invoice_id
            
        except Exception as e:
            self.logger.error(f"Errore creazione fattura: {e}")
            raise OdooException(f"Errore creazione fattura: {e}", 'INVOICE_CREATE_ERROR')
    
    def create_and_confirm_invoice(self, invoice_data: InvoiceData) -> Optional[int]:
        """Crea e conferma fattura in un unico passaggio"""
        try:
            # Crea fattura
            invoice_id = self.create_invoice(invoice_data)
            
            if not invoice_id:
                return None
            
            # Conferma fattura
            if self.confirm_invoice(invoice_id):
                self.logger.info(f"Fattura {invoice_id} creata e confermata")
                return invoice_id
            else:
                self.logger.warning(f"Fattura {invoice_id} creata ma non confermata")
                return invoice_id
                
        except Exception as e:
            self.logger.error(f"Errore creazione e conferma fattura: {e}")
            raise
    
    def confirm_invoice(self, invoice_id: int) -> bool:
        """Conferma una fattura"""
        try:
            # Verifica stato fattura
            invoice_data = self.execute('account.move', 'read', invoice_id, 
                                      fields=['state', 'name'])
            
            invoice = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
            current_state = invoice.get('state', 'draft')
            
            if current_state == 'posted':
                self.logger.info('Fattura già confermata')
                return True
            elif current_state == 'draft':
                # Conferma fattura
                self.execute('account.move', 'action_post', invoice_id)
                self.logger.info('Fattura confermata')
                return True
            else:
                self.logger.warning(f'Stato fattura non gestito: {current_state}')
                return False
                
        except Exception as e:
            self.logger.error(f'Errore conferma fattura: {e}')
            raise OdooException(f'Errore conferma fattura: {e}', 'INVOICE_CONFIRM_ERROR')
    
    def _prepare_invoice_data(self, invoice_data: InvoiceData) -> Dict[str, Any]:
        """Prepara dati per creazione fattura"""
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
            if item.description:
                line_vals['description'] = item.description
                
            invoice_lines.append((0, 0, line_vals))
        
        invoice_vals = {
            'partner_id': invoice_data.partner_id,
            'move_type': 'out_invoice',
            'invoice_date': invoice_date,
            'invoice_date_due': due_date,
            'invoice_line_ids': invoice_lines,
        }
        
        if invoice_data.reference:
            invoice_vals['ref'] = invoice_data.reference
        
        return invoice_vals
    
    def _calculate_due_date(self, invoice_date: str, invoice_data: InvoiceData) -> str:
        """Calcola data scadenza fattura"""
        invoice_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
        
        if invoice_data.manual_due_date:
            return invoice_data.manual_due_date
        elif invoice_data.due_days:
            due_dt = invoice_dt + timedelta(days=invoice_data.due_days)
            return due_dt.strftime('%Y-%m-%d')
        else:
            # Default 30 giorni
            due_dt = invoice_dt + timedelta(days=30)
            return due_dt.strftime('%Y-%m-%d')
    
    def get_invoice_details(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Ottieni dettagli di una fattura"""
        try:
            invoice_data = self.execute('account.move', 'read', invoice_id,
                                      fields=['name', 'partner_id', 'invoice_date', 
                                             'invoice_date_due', 'amount_total', 'state'])
            
            if invoice_data:
                inv = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
                return {
                    'name': inv.get('name'),
                    'partner_name': inv['partner_id'][1] if inv.get('partner_id') else None,
                    'invoice_date': inv.get('invoice_date'),
                    'due_date': inv.get('invoice_date_due'),
                    'amount_total': inv.get('amount_total'),
                    'state': inv.get('state')
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Errore recupero dettagli fattura: {e}")
            raise OdooException(f"Errore recupero dettagli fattura: {e}", 'INVOICE_READ_ERROR')

def create_odoo_client(config: Dict[str, Any]) -> OdooClient:
    """Factory function per creare client Odoo"""
    return OdooClient(config)

# Esempi di utilizzo
def example_create_invoice():
    """Esempio creazione fattura"""
    # Configurazione (normalmente da SecureConfig)
    config = {
        'ODOO_URL': 'https://mysite.odoo.com/',
        'ODOO_DB': 'mydb',
        'ODOO_USERNAME': 'user@domain.com',
        'ODOO_API_KEY': 'api_key_here'
    }
    
    # Crea client
    client = create_odoo_client(config)
    
    # Dati fattura
    items = [
        InvoiceItem(
            product_id=41,
            quantity=2,
            price_unit=100.0,
            name='Prodotto 1',
            description='Descrizione prodotto 1'
        ),
        InvoiceItem(
            product_id=41,
            quantity=1,
            price_unit=200.0,
            name='Prodotto 2'
        )
    ]
    
    invoice_data = InvoiceData(
        partner_id=8378,
        items=items,
        due_days=30,
        reference='Fattura da sistema automatico'
    )
    
    # Crea e conferma fattura
    try:
        invoice_id = client.create_and_confirm_invoice(invoice_data)
        if invoice_id:
            print(f"✅ Fattura creata: {invoice_id}")
            
            # Ottieni dettagli
            details = client.get_invoice_details(invoice_id)
            if details:
                print(f"📄 Fattura: {details['name']}")
                print(f"💰 Totale: €{details['amount_total']}")
        else:
            print("❌ Errore creazione fattura")
            
    except OdooException as e:
        print(f"❌ Errore Odoo: {e}")
    except Exception as e:
        print(f"❌ Errore generico: {e}")

if __name__ == '__main__':
    example_create_invoice()
