"""
Odoo Invoice Creator Script
Script Python per creare fatture tramite API con opzione bozza/finale

Utilizzo:
    python odoo_invoice_creator.py --partner-search "mario rossi" --amount 150.50 --description "Consulenza IT"
    python odoo_invoice_creator.py --partner-id 123 --items items.json --draft
    python odoo_invoice_creator.py --config config.json --bulk invoices.json
"""

import json
import argparse
import requests
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@dataclass
class InvoiceItem:
    """Item per fattura"""
    product_id: int
    quantity: float
    price_unit: float
    name: str
    description: str = ""
    account_id: Optional[int] = None
    analytic_account_id: Optional[int] = None
    tax_ids: Optional[List[int]] = None

@dataclass
class InvoiceConfig:
    """Configurazione per creazione fattura"""
    partner_id: Optional[int] = None
    partner_search: Optional[str] = None
    items: List[InvoiceItem] = None
    due_days: int = 30
    manual_due_date: Optional[str] = None
    reference: str = ""
    journal_id: Optional[int] = None
    payment_term_id: Optional[int] = None
    currency_id: Optional[int] = None
    company_id: Optional[int] = None
    auto_confirm: bool = True  # Campo chiave per gestire bozza/finale

class OdooInvoiceCreator:
    """Classe principale per creazione fatture Odoo"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'OdooInvoiceCreator/1.0'
        })
    
    def test_connection(self) -> bool:
        """Testa la connessione all'API Odoo"""
        try:
            logger.info("🔌 Test connessione API Odoo...")
            response = self.session.get(f"{self.base_url}/api/odoo/test_connection")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    info = result.get('connection_info', {})
                    logger.info(f"✅ Connesso a Odoo {info.get('server_version')} - {info.get('company_name')}")
                    return True
                else:
                    logger.error(f"❌ Test connessione fallito: {result.get('message')}")
                    return False
            else:
                logger.error(f"❌ Errore HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Errore connessione: {e}")
            return False
    
    def search_partner(self, search_term: str, limit: int = 5) -> Optional[List[Dict]]:
        """Cerca partner per nome/email"""
        try:
            logger.info(f"🔍 Ricerca partner: '{search_term}'")
            
            response = self.session.post(
                f"{self.base_url}/api/odoo/partners/search",
                json={
                    "search_term": search_term,
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    partners = result.get('partners', [])
                    logger.info(f"✅ Trovati {len(partners)} partner")
                    return partners
                else:
                    logger.error(f"❌ Ricerca fallita: {result.get('message')}")
                    return None
            else:
                logger.error(f"❌ Errore HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Errore ricerca partner: {e}")
            return None
    
    def get_partner_details(self, partner_id: int) -> Optional[Dict]:
        """Ottiene dettagli partner per ID"""
        try:
            logger.info(f"📋 Recupero dettagli partner ID: {partner_id}")
            
            response = self.session.get(f"{self.base_url}/api/odoo/partners/{partner_id}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    partner = result.get('partner')
                    logger.info(f"✅ Partner trovato: {partner.get('display_name')}")
                    return partner
                else:
                    logger.error(f"❌ Partner non trovato: {result.get('message')}")
                    return None
            else:
                logger.error(f"❌ Errore HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Errore recupero partner: {e}")
            return None
    
    def get_products(self, search: str = "", limit: int = 10) -> List[Dict]:
        """Ottiene lista prodotti"""
        try:
            logger.info("🛒 Recupero prodotti disponibili...")
            
            params = {"limit": limit}
            if search:
                params["search"] = search
            
            response = self.session.get(
                f"{self.base_url}/api/odoo/products",
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    products = result.get('products', [])
                    logger.info(f"✅ Trovati {len(products)} prodotti")
                    return products
                else:
                    logger.error(f"❌ Errore recupero prodotti: {result.get('message')}")
                    return []
            else:
                logger.error(f"❌ Errore HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Errore recupero prodotti: {e}")
            return []
    
    def create_invoice(self, config: InvoiceConfig) -> Optional[Dict]:
        """
        Crea fattura con configurazione specificata
        
        Args:
            config: Configurazione fattura con auto_confirm per gestire bozza/finale
            
        Returns:
            Dict con risultato creazione fattura
        """
        try:
            # Risolvi partner se necessario
            partner_id = self._resolve_partner(config)
            if not partner_id:
                return None
            
            # Prepara payload per API
            invoice_data = {
                "partner_id": partner_id,
                "items": [asdict(item) for item in config.items],
                "due_days": config.due_days,
                "reference": config.reference or f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "auto_confirm": config.auto_confirm  # 🔧 CAMPO CHIAVE per bozza/finale
            }
            
            # Campi opzionali
            if config.manual_due_date:
                invoice_data["manual_due_date"] = config.manual_due_date
            if config.journal_id:
                invoice_data["journal_id"] = config.journal_id
            if config.payment_term_id:
                invoice_data["payment_term_id"] = config.payment_term_id
            if config.currency_id:
                invoice_data["currency_id"] = config.currency_id
            if config.company_id:
                invoice_data["company_id"] = config.company_id
            
            # Log del tipo di fattura che verrà creata
            if config.auto_confirm:
                logger.info("📄 Creazione fattura FINALE (confermata automaticamente)")
            else:
                logger.info("📝 Creazione fattura BOZZA (richiede conferma manuale)")
            
            # Chiamata API
            response = self.session.post(
                f"{self.base_url}/api/odoo/invoices/create",
                json=invoice_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    invoice_details = result.get('invoice_details', {})
                    logger.info(f"✅ Fattura creata: {invoice_details.get('name')} - €{invoice_details.get('amount_total')}")
                    
                    if config.auto_confirm:
                        logger.info(f"🎯 Stato: {invoice_details.get('state')} (FINALE)")
                    else:
                        logger.info(f"📝 Stato: {invoice_details.get('state')} (BOZZA)")
                    
                    return result
                else:
                    logger.error(f"❌ Errore creazione fattura: {result.get('message')}")
                    return None
            else:
                logger.error(f"❌ Errore HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Errore creazione fattura: {e}")
            return None
    
    async def _resolve_partner(self, config: InvoiceConfig) -> Optional[int]:
        """Risolve partner_id da configurazione"""
        if config.partner_id:
            # Verifica che il partner esista
            partner = self.get_partner_details(config.partner_id)
            return config.partner_id if partner else None
        
        elif config.partner_search:
            # Cerca partner per nome
            partners = self.search_partner(config.partner_search, limit=1)
            if partners and len(partners) > 0:
                partner_id = partners[0]['id']
                logger.info(f"🎯 Partner selezionato: {partners[0]['display_name']} (ID: {partner_id})")
                return partner_id
            else:
                logger.error(f"❌ Nessun partner trovato per: '{config.partner_search}'")
                return None
        
        else:
            logger.error("❌ Deve essere specificato partner_id o partner_search")
            return None
    
    def confirm_invoice(self, invoice_id: int) -> bool:
        """Conferma una fattura in bozza"""
        try:
            logger.info(f"✅ Conferma fattura ID: {invoice_id}")
            
            response = self.session.post(f"{self.base_url}/api/odoo/invoices/{invoice_id}/confirm")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"✅ Fattura {invoice_id} confermata con successo")
                    return True
                else:
                    logger.error(f"❌ Errore conferma: {result.get('message')}")
                    return False
            else:
                logger.error(f"❌ Errore HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Errore conferma fattura: {e}")
            return False
    
    def get_invoice_details(self, invoice_id: int) -> Optional[Dict]:
        """Ottiene dettagli di una fattura"""
        try:
            response = self.session.get(f"{self.base_url}/api/odoo/invoices/{invoice_id}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result.get('invoice')
                else:
                    logger.error(f"❌ Fattura non trovata: {result.get('message')}")
                    return None
            else:
                logger.error(f"❌ Errore HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Errore recupero fattura: {e}")
            return None
    
    def create_quick_invoice(self, partner_search: str, service_name: str, 
                           amount: float, quantity: float = 1, product_id: int = 1,
                           draft_mode: bool = False) -> Optional[Dict]:
        """
        Crea fattura rapida con ricerca partner
        
        Args:
            partner_search: Nome o email del cliente
            service_name: Descrizione del servizio
            amount: Importo unitario
            quantity: Quantità (default: 1)
            product_id: ID prodotto Odoo (default: 1)
            draft_mode: Se True crea bozza, se False crea e conferma
        """
        try:
            if draft_mode:
                logger.info("📝 Creazione fattura rapida in modalità BOZZA")
            else:
                logger.info("📄 Creazione fattura rapida FINALE")
            
            invoice_data = {
                "partner_search": partner_search,
                "service_name": service_name,
                "quantity": quantity,
                "price_unit": amount,
                "product_id": product_id
            }
            
            # Se in modalità bozza, usa l'endpoint standard con auto_confirm=False
            if draft_mode:
                # Prima cerca il partner
                partners = self.search_partner(partner_search, limit=1)
                if not partners:
                    logger.error(f"❌ Partner non trovato: {partner_search}")
                    return None
                
                partner_id = partners[0]['id']
                
                # Crea configurazione per fattura bozza
                items = [InvoiceItem(
                    product_id=product_id,
                    quantity=quantity,
                    price_unit=amount,
                    name=service_name,
                    description=f"Fatturazione per {partners[0]['display_name']}"
                )]
                
                config = InvoiceConfig(
                    partner_id=partner_id,
                    items=items,
                    reference=f"Quick-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    auto_confirm=False  # BOZZA
                )
                
                return self.create_invoice(config)
            
            else:
                # Usa endpoint quick_invoice (sempre finale)
                response = self.session.post(
                    f"{self.base_url}/api/odoo/quick_invoice",
                    json=invoice_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        details = result.get('invoice_details', {})
                        logger.info(f"✅ Fattura rapida creata: {details.get('name')} - €{details.get('amount_total')}")
                        return result
                    else:
                        logger.error(f"❌ Errore fattura rapida: {result.get('message')}")
                        return None
                else:
                    logger.error(f"❌ Errore HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Errore fattura rapida: {e}")
            return None


def load_config_from_file(config_file: str) -> Dict:
    """Carica configurazione da file JSON"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Errore caricamento config: {e}")
        return {}

def load_items_from_file(items_file: str) -> List[InvoiceItem]:
    """Carica items da file JSON"""
    try:
        with open(items_file, 'r', encoding='utf-8') as f:
            items_data = json.load(f)
        
        items = []
        for item_data in items_data:
            items.append(InvoiceItem(**item_data))
        
        return items
    except Exception as e:
        logger.error(f"❌ Errore caricamento items: {e}")
        return []

def print_invoice_summary(result: Dict):
    """Stampa riepilogo fattura creata"""
    if not result or not result.get('success'):
        return
    
    details = result.get('invoice_details', {})
    partner = result.get('partner', {})
    
    print("\n" + "="*60)
    print("📄 RIEPILOGO FATTURA CREATA")
    print("="*60)
    print(f"ID Fattura: {result.get('invoice_id')}")
    print(f"Numero: {details.get('name')}")
    print(f"Cliente: {partner.get('display_name') or details.get('partner_name')}")
    print(f"Importo: €{details.get('amount_total')}")
    print(f"Stato: {details.get('state')}")
    
    # Indica se è bozza o finale
    state = details.get('state', '').lower()
    if state == 'draft':
        print("📝 TIPO: BOZZA (richiede conferma manuale)")
        print(f"🔗 Per confermare: python {sys.argv[0]} --confirm-invoice {result.get('invoice_id')}")
    elif state in ['posted', 'open']:
        print("✅ TIPO: FINALE (confermata)")
    
    print("="*60)

def create_sample_files():
    """Crea file di esempio per testing"""
    
    # Config di esempio
    sample_config = {
        "partner_search": "mario rossi",
        "items": [
            {
                "product_id": 1,
                "quantity": 1,
                "price_unit": 150.0,
                "name": "Consulenza IT",
                "description": "Consulenza tecnica specialistica"
            }
        ],
        "due_days": 30,
        "reference": "CONS-001",
        "auto_confirm": False
    }
    
    with open('sample_config.json', 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    
    # Items di esempio
    sample_items = [
        {
            "product_id": 1,
            "quantity": 10,
            "price_unit": 50.0,
            "name": "Ore Consulenza",
            "description": "Ore di consulenza tecnica"
        },
        {
            "product_id": 2,
            "quantity": 1,
            "price_unit": 200.0,
            "name": "Setup Sistema",
            "description": "Configurazione iniziale sistema"
        }
    ]
    
    with open('sample_items.json', 'w', encoding='utf-8') as f:
        json.dump(sample_items, f, indent=2, ensure_ascii=False)
    
    print("✅ File di esempio creati:")
    print("   - sample_config.json")
    print("   - sample_items.json")

def main():
    parser = argparse.ArgumentParser(
        description="Crea fatture Odoo con controllo bozza/finale",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:

1. Fattura rapida FINALE:
   python odoo_invoice_creator.py --partner-search "mario rossi" --amount 150.50 --service "Consulenza IT"

2. Fattura rapida BOZZA:
   python odoo_invoice_creator.py --partner-search "mario rossi" --amount 150.50 --service "Consulenza IT" --draft

3. Fattura complessa da partner ID (FINALE):
   python odoo_invoice_creator.py --partner-id 123 --items sample_items.json

4. Fattura complessa BOZZA:
   python odoo_invoice_creator.py --partner-id 123 --items sample_items.json --draft

5. Da file configurazione:
   python odoo_invoice_creator.py --config sample_config.json

6. Conferma fattura bozza:
   python odoo_invoice_creator.py --confirm-invoice 456

7. Dettagli fattura:
   python odoo_invoice_creator.py --invoice-details 456

8. Crea file di esempio:
   python odoo_invoice_creator.py --create-samples
        """
    )
    
    # Gruppo principale
    group = parser.add_mutually_exclusive_group(required=True)
    
    # Fattura rapida
    parser.add_argument('--partner-search', help='Nome o email cliente per ricerca')
    parser.add_argument('--partner-id', type=int, help='ID specifico del cliente')
    parser.add_argument('--amount', type=float, help='Importo fattura (per modalità rapida)')
    parser.add_argument('--service', help='Descrizione servizio (per modalità rapida)')
    parser.add_argument('--quantity', type=float, default=1.0, help='Quantità (default: 1)')
    parser.add_argument('--product-id', type=int, default=1, help='ID prodotto Odoo (default: 1)')
    
    # Fattura da file
    parser.add_argument('--items', help='File JSON con items fattura')
    parser.add_argument('--config', help='File JSON con configurazione completa')
    
    # Gestione stato fattura
    parser.add_argument('--draft', action='store_true', 
                       help='Crea fattura in BOZZA (richiede conferma manuale)')
    parser.add_argument('--due-days', type=int, default=30, 
                       help='Giorni scadenza (default: 30)')
    parser.add_argument('--reference', help='Riferimento fattura')
    
    # Azioni su fatture esistenti
    group.add_argument('--confirm-invoice', type=int, 
                      help='Conferma fattura bozza per ID')
    group.add_argument('--invoice-details', type=int, 
                      help='Mostra dettagli fattura per ID')
    
    # Utilità
    group.add_argument('--test-connection', action='store_true', 
                      help='Testa connessione API')
    group.add_argument('--list-partners', help='Lista partner (ricerca opzionale)')
    group.add_argument('--list-products', help='Lista prodotti (ricerca opzionale)')
    group.add_argument('--create-samples', action='store_true', 
                      help='Crea file di esempio')
    
    # Configurazione
    parser.add_argument('--base-url', default='http://localhost:5001', 
                       help='URL base API (default: http://localhost:5001)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Output dettagliato')
    
    args = parser.parse_args()
    
    # Configura logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Azioni senza API
    if args.create_samples:
        create_sample_files()
        return
    
    # Inizializza client
    creator = OdooInvoiceCreator(args.base_url)
    
    # Test connessione
    if args.test_connection:
        if creator.test_connection():
            print("✅ Connessione API Odoo funzionante")
            sys.exit(0)
        else:
            print("❌ Connessione API Odoo fallita")
            sys.exit(1)
    
    # Verifica connessione per operazioni che la richiedono
    if not creator.test_connection():
        logger.error("❌ Impossibile connettersi all'API Odoo")
        sys.exit(1)
    
    # Azioni informative
    if args.list_partners is not None:
        partners = creator.search_partner(args.list_partners or "", limit=20)
        if partners:
            print("\n📋 Partner trovati:")
            for p in partners:
                print(f"  {p['id']:3d}: {p['display_name']} ({p.get('email', 'N/A')})")
        return
    
    if args.list_products is not None:
        products = creator.get_products(args.list_products or "", limit=20)
        if products:
            print("\n🛒 Prodotti trovati:")
            for p in products:
                print(f"  {p['id']:3d}: {p['name']} - €{p['list_price']}")
        return
    
    # Dettagli fattura
    if args.invoice_details:
        details = creator.get_invoice_details(args.invoice_details)
        if details:
            print(f"\n📄 Dettagli Fattura ID {args.invoice_details}:")
            print(f"  Numero: {details.get('name')}")
            print(f"  Cliente: {details.get('partner_name')}")
            print(f"  Data: {details.get('invoice_date')}")
            print(f"  Scadenza: {details.get('due_date')}")
            print(f"  Importo: €{details.get('amount_total')}")
            print(f"  Stato: {details.get('state')}")
        return
    
    # Conferma fattura
    if args.confirm_invoice:
        if creator.confirm_invoice(args.confirm_invoice):
            print(f"✅ Fattura {args.confirm_invoice} confermata con successo")
        else:
            print(f"❌ Errore conferma fattura {args.confirm_invoice}")
        return
    
    # Creazione fatture
    result = None
    
    if args.config:
        # Da file configurazione completo
        config_data = load_config_from_file(args.config)
        if not config_data:
            sys.exit(1)
        
        # Converti items se presenti
        if 'items' in config_data:
            items = [InvoiceItem(**item) for item in config_data['items']]
            config_data['items'] = items
        
        config = InvoiceConfig(**config_data)
        result = creator.create_invoice(config)
    
    elif args.items:
        # Da file items + parametri
        items = load_items_from_file(args.items)
        if not items:
            sys.exit(1)
        
        config = InvoiceConfig(
            partner_id=args.partner_id,
            partner_search=args.partner_search,
            items=items,
            due_days=args.due_days,
            reference=args.reference or f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            auto_confirm=not args.draft  # Se --draft è True, auto_confirm è False
        )
        result = creator.create_invoice(config)
    
    elif args.partner_search and args.amount and args.service:
        # Fattura rapida
        result = creator.create_quick_invoice(
            partner_search=args.partner_search,
            service_name=args.service,
            amount=args.amount,
            quantity=args.quantity,
            product_id=args.product_id,
            draft_mode=args.draft  # Modalità bozza se richiesta
        )
    
    else:
        parser.print_help()
        print("\n❌ Parametri insufficienti per creare fattura")
        sys.exit(1)
    
    # Mostra risultato
    if result and result.get('success'):
        print_invoice_summary(result)
        sys.exit(0)
    else:
        print("❌ Errore creazione fattura")
        sys.exit(1)

if __name__ == "__main__":
    main()