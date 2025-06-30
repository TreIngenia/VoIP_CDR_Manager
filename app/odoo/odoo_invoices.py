"""
Odoo Invoice Manager v18.2+
Sistema di fatturazione consolidato e semplificato
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from .odoo_client import OdooClient
from .odoo_exceptions import OdooDataError, OdooValidationError

try:
    from logger_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

@dataclass
class InvoiceItem:
    """Item fattura per Odoo 18.2+"""
    product_id: int
    quantity: float
    price_unit: float
    name: str
    account_id: Optional[int] = None
    analytic_distribution: Optional[Dict[str, float]] = None
    tax_ids: Optional[List[int]] = None

@dataclass
class InvoiceData:
    """Dati fattura completi per Odoo 18.2+"""
    partner_id: int
    items: List[InvoiceItem]
    due_days: Optional[int] = None
    manual_due_date: Optional[str] = None
    reference: str = ""
    journal_id: Optional[int] = None
    payment_term_id: Optional[int] = None
    currency_id: Optional[int] = None
    company_id: Optional[int] = None

class OdooInvoiceManager:
    """Manager consolidato per la gestione delle fatture"""
    
    def __init__(self, client: OdooClient):
        self.client = client
        self.logger = get_logger(__name__)
    
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
    
    def get_partner_payment_terms(self, partner_id: int) -> tuple[Optional[int], Optional[str]]:
        """Ottieni i termini di pagamento del cliente"""
        try:
            partner_data = self.client.execute(
                'res.partner', 'read', partner_id,
                fields=['property_payment_term_id', 'name']
            )
            
            partner = partner_data[0] if isinstance(partner_data, list) else partner_data
            
            if partner and partner['property_payment_term_id']:
                payment_term_id = partner['property_payment_term_id'][0]
                payment_term_name = partner['property_payment_term_id'][1]
                
                self.logger.info(f"Cliente: {partner['name']} - Termini: {payment_term_name}")
                return payment_term_id, payment_term_name
            else:
                self.logger.info(f"Cliente: {partner['name'] if partner else 'Sconosciuto'} - Nessun termine impostato")
                return None, None
                
        except Exception as e:
            self.logger.error(f"Errore recupero termini pagamento: {e}")
            return None, None
    
    def calculate_due_date_from_terms(self, invoice_date_str: str, payment_term_id: int) -> Optional[str]:
        """Calcola la data di scadenza basata sui termini di pagamento"""
        try:
            # Mapping semplificato per termini comuni
            common_terms = {
                1: 0,   # Immediate Payment
                2: 15,  # 15 Days
                3: 30,  # 30 Days  
                4: 60,  # 60 Days
                5: 45,  # 45 Days
                6: 90,  # 90 Days
            }
            
            days = common_terms.get(payment_term_id, 30)
            
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d')
            due_date = invoice_date + timedelta(days=days)
            
            self.logger.info(f"Calcolato: {days} giorni → scadenza {due_date.strftime('%Y-%m-%d')}")
            return due_date.strftime('%Y-%m-%d')
            
        except Exception as e:
            self.logger.error(f"Errore calcolo data scadenza: {e}")
            return None
    
    def calculate_due_date_manual(self, invoice_date_str: str, days_offset: int) -> str:
        """Calcola la data di scadenza aggiungendo giorni alla data fattura"""
        invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d')
        due_date = invoice_date + timedelta(days=days_offset)
        return due_date.strftime('%Y-%m-%d')
    
    def create_invoice(self, partner_id: int, items: List[dict], due_days: Optional[int] = None, 
                      manual_due_date: Optional[str] = None, reference: str = "") -> int:
        """Crea una fattura con gestione intelligente della data di scadenza"""
        
        invoice_date = datetime.now().strftime('%Y-%m-%d')
        due_date = None
        force_due_date = False
        
        self.logger.info("=" * 50)
        self.logger.info("🧾 CREAZIONE FATTURA")
        self.logger.info("=" * 50)
        
        # Logica priorità data scadenza
        if manual_due_date is not None and manual_due_date != '':
            # Priorità 1: Data manuale
            due_date = manual_due_date
            force_due_date = True
            self.logger.info(f"📅 ✅ Usando data manuale: {due_date}")
            
        elif due_days is not None:
            # Priorità 2: Giorni manuali
            due_date = self.calculate_due_date_manual(invoice_date, due_days)
            force_due_date = True
            self.logger.info(f"📅 ✅ Usando giorni manuali: {due_days} → {due_date}")
            
        else:
            # Priorità 3: Termini cliente
            self.logger.info("🔍 Controllo termini pagamento cliente...")
            payment_term_id, payment_term_name = self.get_partner_payment_terms(partner_id)
            
            if payment_term_id:
                due_date = self.calculate_due_date_from_terms(invoice_date, payment_term_id)
                
            if not due_date:
                # Fallback: 30 giorni
                due_date = self.calculate_due_date_manual(invoice_date, 30)
                self.logger.info(f"📅 Usando fallback: 30 giorni → {due_date}")
        
        # Prepara dati fattura
        invoice_data = {
            'partner_id': partner_id,
            'move_type': 'out_invoice',
            'invoice_date': invoice_date,
            'invoice_date_due': due_date,
            'ref': reference,
            'invoice_line_ids': [(0, 0, item) for item in items],
        }
        
        # Se forziamo la data, non usiamo termini di pagamento
        if force_due_date:
            invoice_data['invoice_payment_term_id'] = False
        
        try:
            invoice_id = self.client.execute('account.move', 'create', [invoice_data])
            
            self.logger.info(f'✅ Fattura (bozza) creata con ID: {invoice_id}')
            self.logger.info(f'📅 Data fattura: {invoice_date}')
            self.logger.info(f'📅 Data scadenza: {due_date}')
            
            # Verifica fattura creata
            try:
                created_invoice = self.client.execute(
                    'account.move', 'read', invoice_id,
                    fields=['invoice_date', 'invoice_date_due', 'name']
                )
                created = created_invoice[0] if isinstance(created_invoice, list) else created_invoice
                self.logger.info(f"✅ Fattura verificata: {created.get('name', 'Bozza')}")
                self.logger.info(f"  - Data fattura: {created.get('invoice_date', 'N/A')}")
                self.logger.info(f"  - Data scadenza: {created.get('invoice_date_due', 'N/A')}")
            except:
                self.logger.info("✅ Fattura creata con successo")
            
            self.logger.info("=" * 50)
            return invoice_id
            
        except Exception as e:
            self.logger.error(f"Errore creazione fattura: {e}")
            raise OdooDataError(f"Errore creazione fattura: {e}")
    
    def confirm_invoice(self, invoice_id: int, expected_due_date: Optional[str] = None) -> bool:
        """Conferma una fattura (da bozza a confermata)"""
        try:
            # Verifica stato fattura
            invoice_data = self.client.execute(
                'account.move', 'read', invoice_id,
                fields=['state', 'name', 'invoice_date_due']
            )
            
            invoice = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
            current_state = invoice.get('state', 'draft')
            invoice_name = invoice.get('name', 'N/A')
            
            self.logger.info(f"📄 Fattura {invoice_name} - Stato: {current_state}")
            
            if current_state == 'posted':
                self.logger.info('✅ La fattura è già confermata.')
                return True
            elif current_state == 'draft':
                self.logger.info('🔄 Confermando la fattura...')
                self.client.execute('account.move', 'action_post', invoice_id)
                self.logger.info('✅ Fattura confermata e numerata.')
                return True
            else:
                self.logger.warning(f'⚠️ Stato fattura non gestito: {current_state}')
                return False
                
        except Exception as e:
            self.logger.error(f'❌ Errore conferma fattura: {e}')
            return False
    
    def check_email_configuration(self) -> bool:
        """Verifica la configurazione email di Odoo"""
        try:
            smtp_servers = self.client.execute(
                'ir.mail_server', 'search_read', [],
                fields=['name', 'smtp_host', 'smtp_port']
            )
            
            if not smtp_servers:
                self.logger.warning("⚠️ Nessun server SMTP configurato in Odoo")
                return False
            
            self.logger.info(f"📧 Server SMTP trovati: {len(smtp_servers)}")
            for server in smtp_servers:
                self.logger.info(f"  - {server['name']}: {server['smtp_host']}:{server['smtp_port']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Errore controllo configurazione email: {e}")
            return False
    
    def send_invoice_email_method1(self, invoice_id: int) -> bool:
        """Metodo 1: Invio tramite message_post"""
        try:
            # Recupera dati fattura
            invoice_data = self.client.execute(
                'account.move', 'read', invoice_id,
                fields=['partner_id', 'name', 'amount_total', 'invoice_date']
            )
            
            invoice = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
            
            if not invoice:
                self.logger.error("Fattura non trovata")
                return False
                
            partner_id = invoice['partner_id'][0] if invoice['partner_id'] else False
            if not partner_id:
                self.logger.error("Partner non trovato")
                return False
            
            # Recupera email partner
            partner_data = self.client.execute(
                'res.partner', 'read', partner_id,
                fields=['email', 'name']
            )
            
            partner = partner_data[0] if isinstance(partner_data, list) else partner_data
            
            if not partner or not partner['email']:
                self.logger.error("Email del cliente non trovata")
                return False
                
            partner_email = partner['email']
            partner_name = partner['name']
            invoice_name = invoice['name']
            
            # Invia email tramite message_post
            self.client.execute(
                'account.move', 'message_post', invoice_id,
                body=f'<p>Gentile {partner_name},</p><p>La fattura {invoice_name} è pronta per il download.</p>',
                subject=f'Fattura {invoice_name}',
                message_type='email',
                subtype_xmlid='mail.mt_comment',
                partner_ids=[partner_id]
            )
            
            self.logger.info(f'📧 Fattura {invoice_id} inviata via email a {partner_email} (Metodo 1)')
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Errore invio email (Metodo 1): {e}")
            return False
    
    def send_invoice_email_method2(self, invoice_id: int) -> bool:
        """Metodo 2: Invio tramite mail.mail diretto"""
        try:
            # Recupera dati fattura e partner
            invoice_data = self.client.execute(
                'account.move', 'read', invoice_id,
                fields=['partner_id', 'name', 'amount_total', 'invoice_date']
            )
            
            invoice = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
            
            if not invoice:
                self.logger.error("Fattura non trovata")
                return False
                
            partner_id = invoice['partner_id'][0] if invoice['partner_id'] else False
            if not partner_id:
                self.logger.error("Partner non trovato")
                return False
            
            partner_data = self.client.execute(
                'res.partner', 'read', partner_id,
                fields=['email', 'name']
            )
            
            partner = partner_data[0] if isinstance(partner_data, list) else partner_data
            
            if not partner or not partner['email']:
                self.logger.error("Email del cliente non trovata")
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
            mail_id = self.client.execute('mail.mail', 'create', [mail_data])
            self.client.execute('mail.mail', 'send', mail_id)
            
            self.logger.info(f'📧 Fattura {invoice_id} inviata via email a {partner_email} (Metodo 2)')
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Errore invio email (Metodo 2): {e}")
            return False
    
    def send_invoice_email_method3(self, invoice_id: int) -> bool:
        """Metodo 3: Invio tramite mail.template"""
        try:
            # Cerca template per fatture
            template_ids = self.client.execute(
                'mail.template', 'search',
                [['model', '=', 'account.move']]
            )
            
            if not template_ids:
                self.logger.error("Nessun template email trovato")
                return False
                
            template_id = template_ids[0]
            
            # Invia email con template
            self.client.execute(
                'mail.template', 'send_mail',
                template_id, invoice_id,
                force_send=True, raise_exception=True
            )
            
            self.logger.info(f'📧 Fattura {invoice_id} inviata via email (Metodo 3)')
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Errore invio email (Metodo 3): {e}")
            return False
    
    def send_invoice_email(self, invoice_id: int) -> bool:
        """Funzione principale per invio email fattura"""
        self.logger.info("📧 Tentativo invio email...")
        
        # Verifica configurazione email
        if not self.check_email_configuration():
            self.logger.warning("⚠️ La configurazione email potrebbe non essere visibile via API")
        
        # Prova i diversi metodi in sequenza
        for method_num, method in enumerate([
            self.send_invoice_email_method1,
            self.send_invoice_email_method2,
            self.send_invoice_email_method3
        ], 1):
            try:
                if method(invoice_id):
                    return True
            except Exception as e:
                self.logger.error(f"Metodo {method_num} fallito: {e}")
                continue
        
        self.logger.error("❌ Tutti i metodi di invio email hanno fallito")
        self.logger.info("💡 Prova a inviare manualmente dall'interfaccia web di Odoo")
        return False
    
    def get_invoice_details(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Ottieni dettagli di una fattura"""
        try:
            invoice_data = self.client.execute(
                'account.move', 'read', invoice_id,
                fields=['name', 'partner_id', 'invoice_date', 'invoice_date_due', 'amount_total', 'state']
            )
            
            if invoice_data:
                inv = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
                
                details = {
                    'id': invoice_id,
                    'name': inv['name'],
                    'partner_name': inv['partner_id'][1] if inv['partner_id'] else 'N/A',
                    'partner_id': inv['partner_id'][0] if inv['partner_id'] else None,
                    'invoice_date': inv['invoice_date'],
                    'invoice_date_due': inv['invoice_date_due'],
                    'amount_total': inv['amount_total'],
                    'state': inv['state']
                }
                
                self.logger.info(f"📄 Fattura: {details['name']}")
                self.logger.info(f"👤 Cliente: {details['partner_name']}")
                self.logger.info(f"📅 Data: {details['invoice_date']}")
                self.logger.info(f"📅 Scadenza: {details['invoice_date_due']}")
                self.logger.info(f"💰 Totale: €{details['amount_total']}")
                self.logger.info(f"📊 Stato: {details['state']}")
                
                return details
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Errore recupero dettagli fattura: {e}")
            return None
    
    def create_and_confirm_invoice(self, partner_id: int, items: List[dict], 
                                 due_days: Optional[int] = None, 
                                 manual_due_date: Optional[str] = None,
                                 reference: str = "") -> Optional[int]:
        """Crea e conferma una fattura in un unico passaggio"""
        
        self.logger.info("=" * 50)
        self.logger.info("🧾 CREAZIONE E CONFERMA FATTURA")
        self.logger.info("=" * 50)
        
        # Step 1: Crea la fattura
        invoice_id = self.create_invoice(
            partner_id=partner_id,
            items=items,
            due_days=due_days,
            manual_due_date=manual_due_date,
            reference=reference
        )
        
        if not invoice_id:
            self.logger.error("❌ Errore nella creazione della fattura")
            return None
        
        # Step 2: Conferma la fattura
        if self.confirm_invoice(invoice_id):
            self.logger.info("🎉 Fattura creata e confermata con successo!")
            return invoice_id
        else:
            self.logger.warning("⚠️ Fattura creata ma non confermata")
            return invoice_id