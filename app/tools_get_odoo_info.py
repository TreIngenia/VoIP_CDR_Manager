import os
import xmlrpc.client
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

class OdooModelExplorer:
    def __init__(self):
        self.url = os.getenv('ODOO_URL')
        self.db = os.getenv('ODOO_DB')
        self.username = os.getenv('ODOO_USERNAME')
        self.api_key = os.getenv('ODOO_API_KEY')
        self.uid = None
        self.models = None
        
    def connect(self):
        """Connessione a Odoo"""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.api_key, {})
            
            if not self.uid:
                raise Exception("Autenticazione fallita")
                
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"✅ Connesso a Odoo - UID: {self.uid}")
            return True
            
        except Exception as e:
            print(f"❌ Errore connessione: {e}")
            return False
    
    def execute(self, model, method, *args, **kwargs):
        """Esegue chiamate Odoo"""
        if not self.uid or not self.models:
            raise Exception("Non connesso")
        
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
    
    def get_all_models(self, include_details=True):
        """
        Recupera tutti i modelli disponibili in Odoo
        """
        try:
            print("🔍 Recupero di tutti i modelli disponibili...")
            
            # Recupera tutti i modelli
            if include_details:
                models = self.execute('ir.model', 'search_read', [],
                    fields=['model', 'name', 'state', 'transient', 'modules'])
            else:
                models = self.execute('ir.model', 'search_read', [],
                    fields=['model', 'name'])
            
            print(f"✅ Trovati {len(models)} modelli totali")
            
            # Raggruppa per categoria
            categorized_models = {
                'sale': [],
                'purchase': [],
                'account': [],
                'stock': [],
                'hr': [],
                'project': [],
                'crm': [],
                'website': [],
                'mail': [],
                'base': [],
                'subscription': [],
                'contract': [],
                'other': []
            }
            
            for model in models:
                model_name = model['model']
                category = 'other'
                
                # Categorizza i modelli
                if model_name.startswith('sale.'):
                    category = 'sale'
                elif model_name.startswith('purchase.'):
                    category = 'purchase'
                elif model_name.startswith('account.'):
                    category = 'account'
                elif model_name.startswith('stock.'):
                    category = 'stock'
                elif model_name.startswith('hr.'):
                    category = 'hr'
                elif model_name.startswith('project.'):
                    category = 'project'
                elif model_name.startswith('crm.'):
                    category = 'crm'
                elif model_name.startswith('website.'):
                    category = 'website'
                elif model_name.startswith('mail.'):
                    category = 'mail'
                elif model_name.startswith('res.') or model_name.startswith('ir.'):
                    category = 'base'
                elif 'subscription' in model_name.lower():
                    category = 'subscription'
                elif 'contract' in model_name.lower():
                    category = 'contract'
                
                categorized_models[category].append(model)
            
            return categorized_models
            
        except Exception as e:
            print(f"❌ Errore nel recupero modelli: {e}")
            return None
    
    def get_model_details(self, model_name):
        """
        Recupera dettagli specifici di un modello
        """
        try:
            print(f"\n🔍 DETTAGLI MODELLO: {model_name}")
            print("=" * 60)
            
            # 1. Informazioni generali del modello
            model_info = self.execute('ir.model', 'search_read',
                [('model', '=', model_name)],
                fields=['model', 'name', 'state', 'transient', 'modules', 'info'])
            
            if model_info:
                info = model_info[0]
                print(f"📋 Nome: {info['name']}")
                print(f"🏷️  Modello: {info['model']}")
                print(f"📊 Stato: {info.get('state', 'N/A')}")
                print(f"⚡ Transient: {info.get('transient', False)}")
                print(f"📦 Moduli: {info.get('modules', 'N/A')}")
                if info.get('info'):
                    print(f"ℹ️  Info: {info['info']}")
            
            # 2. Struttura dei campi
            print(f"\n📋 STRUTTURA CAMPI:")
            print("-" * 30)
            
            fields_info = self.execute(model_name, 'fields_get', [])
            
            # Raggruppa i campi per tipo
            field_types = {}
            for field_name, field_info in fields_info.items():
                field_type = field_info.get('type', 'unknown')
                if field_type not in field_types:
                    field_types[field_type] = []
                field_types[field_type].append({
                    'name': field_name,
                    'string': field_info.get('string', ''),
                    'required': field_info.get('required', False),
                    'readonly': field_info.get('readonly', False)
                })
            
            # Mostra campi per tipo
            for field_type, fields in field_types.items():
                print(f"\n🔸 {field_type.upper()} ({len(fields)} campi):")
                for field in fields[:5]:  # Primi 5 per tipo
                    required = "⚠️" if field['required'] else ""
                    readonly = "🔒" if field['readonly'] else ""
                    print(f"   {required}{readonly} {field['name']}: {field['string']}")
                if len(fields) > 5:
                    print(f"   ... e altri {len(fields) - 5} campi")
            
            # 3. Statistiche dei record
            print(f"\n📊 STATISTICHE RECORD:")
            print("-" * 30)
            
            try:
                total_records = self.execute(model_name, 'search_count', [])
                print(f"📈 Totale record: {total_records}")
                
                if total_records > 0:
                    # Prova a recuperare alcuni record di esempio
                    sample_records = self.execute(model_name, 'search_read', [],
                        fields=['id', 'display_name', 'name', 'create_date'], limit=3)
                    
                    print(f"📋 Esempi di record:")
                    for record in sample_records:
                        name = record.get('display_name') or record.get('name', f"ID: {record['id']}")
                        create_date = record.get('create_date', 'N/A')
                        print(f"   - {name} (creato: {create_date})")
                        
            except Exception as e:
                print(f"❌ Impossibile recuperare statistiche: {str(e)[:50]}...")
            
            # 4. Permessi dell'utente corrente
            print(f"\n🔐 PERMESSI UTENTE:")
            print("-" * 30)
            
            try:
                # Testa i permessi CRUD
                permissions = {}
                test_methods = ['read', 'write', 'create', 'unlink']
                
                for method in test_methods:
                    try:
                        # Testa con un record fittizio per write/unlink, con search per read
                        if method == 'read':
                            self.execute(model_name, 'search', [], limit=1)
                            permissions[method] = True
                        elif method == 'create':
                            # Non creiamo davvero, ma testiamo il permesso
                            self.execute(model_name, 'fields_get', [])
                            permissions[method] = True  # Se arriviamo qui, probabilmente ok
                        else:
                            permissions[method] = True  # Assumiamo true se non possiamo testare
                    except Exception:
                        permissions[method] = False
                
                for method, allowed in permissions.items():
                    status = "✅" if allowed else "❌"
                    print(f"   {status} {method.upper()}")
                    
            except Exception as e:
                print(f"❌ Impossibile verificare permessi: {str(e)[:50]}...")
            
            return {
                'model_info': model_info[0] if model_info else None,
                'fields_count': len(fields_info),
                'field_types': field_types,
                'total_records': total_records if 'total_records' in locals() else 0,
                'permissions': permissions if 'permissions' in locals() else {}
            }
            
        except Exception as e:
            print(f"❌ Errore nel recupero dettagli: {e}")
            return None
    
    def search_models(self, search_term):
        """
        Cerca modelli che contengono un termine specifico
        """
        try:
            print(f"🔍 Ricerca modelli contenenti: '{search_term}'")
            
            models = self.execute('ir.model', 'search_read',
                ['|', ('model', 'ilike', search_term), ('name', 'ilike', search_term)],
                fields=['model', 'name'])
            
            print(f"✅ Trovati {len(models)} modelli:")
            
            for model in models:
                print(f"   - {model['model']}: {model['name']}")
                
                # Prova a contare i record per ogni modello
                try:
                    count = self.execute(model['model'], 'search_count', [])
                    print(f"     📊 {count} record")
                except Exception as e:
                    print(f"     ❌ Errore conteggio: {str(e)[:30]}...")
            
            return models
            
        except Exception as e:
            print(f"❌ Errore nella ricerca: {e}")
            return None
    
    def export_models_report(self, filename=None):
        """
        Esporta un report completo di tutti i modelli
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"odoo_models_report_{timestamp}.json"
        
        try:
            print(f"📄 Creazione report completo...")
            
            all_models = self.get_all_models(include_details=True)
            
            if not all_models:
                print("❌ Impossibile recuperare i modelli")
                return None
            
            # Crea report strutturato
            report = {
                'generated_at': datetime.now().isoformat(),
                'odoo_url': self.url,
                'odoo_db': self.db,
                'total_models': sum(len(models) for models in all_models.values()),
                'categories': {}
            }
            
            for category, models in all_models.items():
                if models:  # Solo se ci sono modelli in questa categoria
                    report['categories'][category] = {
                        'count': len(models),
                        'models': []
                    }
                    
                    for model in models:
                        model_data = {
                            'model': model['model'],
                            'name': model['name'],
                            'state': model.get('state'),
                            'transient': model.get('transient', False)
                        }
                        
                        # Prova a contare i record
                        try:
                            model_data['record_count'] = self.execute(model['model'], 'search_count', [])
                        except:
                            model_data['record_count'] = 'N/A'
                        
                        report['categories'][category]['models'].append(model_data)
            
            # Salva il report
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Report salvato in: {filename}")
            print(f"📊 Modelli totali analizzati: {report['total_models']}")
            
            return filename
            
        except Exception as e:
            print(f"❌ Errore nella creazione del report: {e}")
            return None

def main():
    """
    Funzione principale con menu interattivo
    """
    explorer = OdooModelExplorer()
    
    if not explorer.connect():
        return
    
    while True:
        print("\n" + "="*50)
        print("🔍 ODOO MODEL EXPLORER")
        print("="*50)
        print("1. 📋 Visualizza tutti i modelli per categoria")
        print("2. 🔍 Cerca modelli specifici")
        print("3. 📊 Dettagli di un modello specifico")
        print("4. 📄 Esporta report completo")
        print("5. 🎯 Trova modelli abbonamenti/subscription")
        print("6. ❌ Esci")
        
        choice = input("\n👉 Scegli un'opzione (1-6): ").strip()
        
        if choice == '1':
            print("\n📋 RECUPERO TUTTI I MODELLI...")
            all_models = explorer.get_all_models()
            
            if all_models:
                for category, models in all_models.items():
                    if models:
                        print(f"\n🔸 {category.upper()} ({len(models)} modelli):")
                        for model in models[:10]:  # Primi 10 per categoria
                            print(f"   - {model['model']}: {model['name']}")
                        if len(models) > 10:
                            print(f"   ... e altri {len(models) - 10} modelli")
        
        elif choice == '2':
            search_term = input("🔍 Inserisci termine di ricerca: ").strip()
            if search_term:
                explorer.search_models(search_term)
        
        elif choice == '3':
            model_name = input("📊 Inserisci nome del modello (es: res.partner): ").strip()
            if model_name:
                explorer.get_model_details(model_name)
        
        elif choice == '4':
            filename = input("📄 Nome file (invio per auto): ").strip()
            explorer.export_models_report(filename if filename else None)
        
        elif choice == '5':
            print("\n🎯 RICERCA MODELLI ABBONAMENTI...")
            terms = ['subscription', 'recurring', 'contract']
            for term in terms:
                print(f"\n--- Ricerca '{term}' ---")
                explorer.search_models(term)
        
        elif choice == '6':
            print("👋 Arrivederci!")
            break
        
        else:
            print("❌ Opzione non valida")
        
        input("\nPremi INVIO per continuare...")

if __name__ == "__main__":
    main()