import os
import xmlrpc.client
from dotenv import load_dotenv

# Carica configurazione
load_dotenv()

url = os.getenv('ODOO_URL')
db = os.getenv('ODOO_DB')
username = os.getenv('ODOO_USERNAME')
api_key = os.getenv('ODOO_API_KEY')

class OdooDiscovery:
    def __init__(self, url, db, username, api_key):
        self.url = url
        self.db = db
        self.username = username
        self.api_key = api_key
        self.uid = None
        self.models = None
        
    def connect(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.api_key, {})
            
            if not self.uid:
                raise Exception("Autenticazione fallita")
                
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"✅ Connesso con UID: {self.uid}")
            return True
            
        except Exception as e:
            print(f"❌ Errore connessione: {e}")
            return False
    
    def execute(self, model, method, *args, **kwargs):
        if not self.uid or not self.models:
            raise Exception("Non ancora connesso")
        
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
    
    def discover_subscription_modules(self):
        """
        Scopre quali moduli di abbonamento sono installati
        """
        print("🔍 SCOPERTA MODULI ABBONAMENTO")
        print("=" * 50)
        
        # Lista dei moduli da verificare
        modules_to_check = [
            'sale_subscription',
            'subscription',
            'sale_subscription_dashboard',
            'website_sale_subscription',
            'sale_subscription_asset',
            'payment_stripe',
            'sale_payment',
            'subscription_stripe',
            'sale_subscription_stripe'
        ]
        
        try:
            # Verifica moduli installati
            for module_name in modules_to_check:
                try:
                    module_info = self.execute('ir.module.module', 'search_read',
                        [('name', '=', module_name)],
                        fields=['name', 'state', 'summary', 'description'])
                    
                    if module_info:
                        module = module_info[0]
                        status = "✅ INSTALLATO" if module['state'] == 'installed' else f"❌ {module['state'].upper()}"
                        print(f"{module_name}: {status}")
                        if module['state'] == 'installed' and module.get('summary'):
                            print(f"  └─ {module['summary']}")
                    
                except Exception as e:
                    print(f"{module_name}: ❓ Non verificabile ({str(e)[:50]}...)")
                    
        except Exception as e:
            print(f"❌ Errore nella verifica moduli: {e}")
    
    def discover_subscription_models(self):
        """
        Scopre quali modelli di abbonamento sono disponibili
        """
        print("\n🔍 SCOPERTA MODELLI ABBONAMENTO")
        print("=" * 50)
        
        models_to_check = [
            'sale.subscription',
            'sale.subscription.line',
            'subscription.subscription',
            'subscription.line',
            'sale.order',
            'sale.order.line',
            'subscription.package',
            'subscription.template'
        ]
        
        available_models = []
        
        for model_name in models_to_check:
            try:
                # Testa se il modello esiste cercando i campi
                fields = self.execute(model_name, 'fields_get', [])
                count = self.execute(model_name, 'search_count', [])
                
                print(f"✅ {model_name}: {count} record, {len(fields)} campi")
                available_models.append({
                    'model': model_name,
                    'count': count,
                    'fields_count': len(fields)
                })
                
                # Se è un modello di abbonamento, mostra alcuni campi chiave
                if 'subscription' in model_name.lower():
                    key_fields = []
                    subscription_fields = ['recurring_total', 'recurring_rule_type', 'stage_id', 'partner_id', 'template_id']
                    for field in subscription_fields:
                        if field in fields:
                            key_fields.append(field)
                    
                    if key_fields:
                        print(f"  └─ Campi chiave: {', '.join(key_fields)}")
                        
            except Exception as e:
                print(f"❌ {model_name}: Non disponibile")
        
        return available_models
    
    def discover_stripe_configuration(self):
        """
        Scopre la configurazione Stripe
        """
        print("\n🔍 SCOPERTA CONFIGURAZIONE STRIPE")
        print("=" * 50)
        
        try:
            # Verifica provider di pagamento
            payment_providers = self.execute('payment.provider', 'search_read',
                [('code', '=', 'stripe')],
                fields=['name', 'state', 'code', 'stripe_publishable_key'])
            
            if payment_providers:
                for provider in payment_providers:
                    status = "✅ ABILITATO" if provider['state'] == 'enabled' else f"❌ {provider['state'].upper()}"
                    print(f"Stripe Provider: {status}")
                    print(f"  └─ Nome: {provider['name']}")
                    print(f"  └─ Publishable Key: {'Configurata' if provider.get('stripe_publishable_key') else 'Non configurata'}")
            else:
                print("❌ Nessun provider Stripe trovato")
                
            # Verifica metodi di pagamento Stripe
            payment_methods = self.execute('payment.method', 'search_read',
                [('code', '=', 'stripe')],
                fields=['name', 'active'])
                
            if payment_methods:
                for method in payment_methods:
                    status = "✅ ATTIVO" if method['active'] else "❌ INATTIVO"
                    print(f"Metodo Stripe: {status} - {method['name']}")
            
            # Verifica acquirer (versioni precedenti)
            try:
                acquirers = self.execute('payment.acquirer', 'search_read',
                    [('provider', '=', 'stripe')],
                    fields=['name', 'state'])
                    
                if acquirers:
                    for acquirer in acquirers:
                        print(f"Acquirer Stripe: {acquirer['state']} - {acquirer['name']}")
            except:
                pass  # payment.acquirer potrebbe non esistere in versioni più recenti
                
        except Exception as e:
            print(f"❌ Errore nella verifica Stripe: {e}")
    
    def discover_sample_subscriptions(self):
        """
        Mostra alcuni abbonamenti di esempio
        """
        print("\n🔍 ABBONAMENTI DI ESEMPIO")
        print("=" * 50)
        
        # Prova prima con sale.subscription
        try:
            subscriptions = self.execute('sale.subscription', 'search_read',
                [], fields=['name', 'partner_id', 'recurring_total', 'stage_id'], limit=5)
            
            if subscriptions:
                print("📋 Abbonamenti trovati (sale.subscription):")
                for sub in subscriptions:
                    partner_name = sub['partner_id'][1] if sub.get('partner_id') else 'N/A'
                    stage_name = sub['stage_id'][1] if sub.get('stage_id') else 'N/A'
                    print(f"  • ID: {sub['id']} | {sub['name']} | Cliente: {partner_name} | €{sub.get('recurring_total', 0)} | Stage: {stage_name}")
                return 'sale.subscription'
            else:
                print("ℹ️ Nessun abbonamento trovato in sale.subscription")
                
        except Exception as e:
            print(f"❌ sale.subscription non disponibile: {str(e)[:100]}...")
        
        # Se sale.subscription non funziona, prova con sale.order
        try:
            orders = self.execute('sale.order', 'search_read',
                [('state', 'in', ['sale', 'done'])],
                fields=['name', 'partner_id', 'amount_total', 'state'], limit=5)
            
            if orders:
                print("📋 Ordini di vendita trovati:")
                for order in orders:
                    partner_name = order['partner_id'][1] if order.get('partner_id') else 'N/A'
                    print(f"  • ID: {order['id']} | {order['name']} | Cliente: {partner_name} | €{order.get('amount_total', 0)} | Stato: {order['state']}")
                return 'sale.order'
                
        except Exception as e:
            print(f"❌ Errore nella verifica ordini: {e}")
        
        return None
    
    def full_discovery(self):
        """
        Esegue la scoperta completa
        """
        print("🚀 ANALISI COMPLETA CONFIGURAZIONE ODOO")
        print("=" * 60)
        
        if not self.connect():
            return False
        
        # Scopri moduli
        self.discover_subscription_modules()
        
        # Scopri modelli
        available_models = self.discover_subscription_models()
        
        # Scopri configurazione Stripe
        self.discover_stripe_configuration()
        
        # Mostra abbonamenti di esempio
        primary_model = self.discover_sample_subscriptions()
        
        # Riepilogo finale
        print("\n" + "=" * 60)
        print("📊 RIEPILOGO CONFIGURAZIONE")
        print("=" * 60)
        
        if primary_model:
            print(f"✅ Modello principale abbonamenti: {primary_model}")
        else:
            print("❌ Nessun modello di abbonamento identificato")
        
        print(f"📈 Modelli disponibili: {len(available_models)}")
        
        return {
            'primary_model': primary_model,
            'available_models': available_models,
            'connected': True
        }

# Funzione principale per eseguire la scoperta
def run_discovery():
    """
    Esegue la scoperta della configurazione Odoo
    """
    discovery = OdooDiscovery(url, db, username, api_key)
    return discovery.full_discovery()

if __name__ == "__main__":
    result = run_discovery()
    
    if result:
        print(f"\n🎉 Scoperta completata!")
        print(f"Modello principale: {result.get('primary_model', 'Non identificato')}")
    else:
        print("\n❌ Scoperta fallita - verifica le credenziali")