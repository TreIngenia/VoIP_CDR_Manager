import os
import xmlrpc.client
from datetime import datetime, timedelta
from flask import jsonify

# Carica variabili dal file .env (opzionale)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Carica variabili dal file .env
    print("📁 File .env caricato")
except ImportError:
    print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")

# Configurazione tramite variabili d'ambiente (più sicuro)
url = os.getenv('ODOO_URL', 'https://mysite.odoo.com/')
db = os.getenv('ODOO_DB', 'mydb_test')
username = os.getenv('ODOO_USERNAME', 'nome.cognome@dominio.ext')  # Valore di default aggiunto
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
        due_days = fact_data['due_days']
        manual_due_date = fact_data['manual_due_date']
        items = fact_data['items']
        da_confermare = fact_data['da_confermare']
        # return
        print("🚀 Sistema Fatturazione Odoo con API Key")
        
        # Inizializza connessione Odoo
        odoo = OdooAPI(url, db, username, api_key)
        
        if not odoo.connect():
            return
        
        if da_confermare not in ["SI",""]:
            if due_days:
                invoice_id = odoo.create_and_confirm_invoice(partner_id=partner_id, items=items, due_days=due_days)
            else:
                invoice_id = odoo.create_and_confirm_invoice(partner_id=partner_id, items=items, manual_due_date=manual_due_date)
        else:
            if due_days:
                invoice_id = odoo.create_invoice(partner_id=partner_id, items=items, due_days=due_days)
            else:
                invoice_id = odoo.create_invoice(partner_id=partner_id, items=items, manual_due_date=manual_due_date)
            
        if not invoice_id:
            print("❌ Impossibile creare la fattura")
            return

        # Visualizza dettagli fattura creata
        print("\n📋 DETTAGLI FATTURA FINALE:")
        odoo.get_invoice_details(invoice_id)
        
        # Invia email
        result = odoo.send_invoice_email(invoice_id)
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