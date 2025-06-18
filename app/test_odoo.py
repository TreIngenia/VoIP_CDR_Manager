import os
import xmlrpc.client
import json
from dotenv import load_dotenv
from gen_odoo_invoice_token import OdooAPI
from datetime import datetime


load_dotenv()

def test():
    url=os.getenv('ODOO_URL')
    db=os.getenv('ODOO_DB')
    username=os.getenv('ODOO_USERNAME')
    password=os.getenv('ODOO_API_KEY')

    print (url, db, username, password)
    # === Connessione XML-RPC ===
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        raise Exception("Autenticazione fallita: controlla username, password o database")

    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    # a = models.execute_kw(db, uid, password, 'res.partner', 'fields_get', [], {'attributes': ['string', 'help', 'type']})
    # print(json.dumps(a, indent=4, sort_keys=True))
    # # === Recupero modelli ===

    # model_data = models.execute_kw(
    #     db, uid, password,
    #     'ir.model', 'search_read',
    #     [[['model','like','sales']]],  # Nessun filtro
    #     {'fields': ['name', 'model']}
    # )

    # # === Ordinamento alfabetico per nome tecnico ===


    # # === Output formattato in JSON ordinato ===
    # print(json.dumps(sorted_models, indent=4, sort_keys=True))
    # Recupera i modelli che contengono 'subscriptions'
    model_data = models.execute_kw(
        db, uid, password,
        'ir.model', 'search_read',
        [[['model', 'ilike', 'sub']]],
        {'fields': ['name', 'model']}
    )

    # Filtra e ordina solo quelli validi
    filtered = [m for m in model_data if 'model' in m]
    sorted_models = sorted(filtered, key=lambda x: x['model'])

    # Stampa
    print(json.dumps(sorted_models, indent=4, sort_keys=True))
    # try:
    #     # Connessione Odoo
        # odoo = OdooAPI(
        #     url=os.getenv('ODOO_URL'),
        #     db=os.getenv('ODOO_DB'),
        #     username=os.getenv('ODOO_USERNAME'),
        #     api_key=os.getenv('ODOO_API_KEY')
        # )
        
    #     if not odoo.connect():
    #         print("❌ Impossibile connettersi a Odoo")
    #         return [], None
        
        
    #     # Prima scopriamo quali campi sono disponibili per sale.order
    #     try:
    #         fields_info = odoo.execute('res.partner', 'fields_get', [])
    #         available_fields = list(fields_info.keys())
    #         # print(f"🔍 Campi disponibili in sale.order: {len(available_fields)}")
    #         # return len(available_fields)
    #     except:
    #         available_fields = []
        
        
    #     print('available_fields',available_fields)
    #     return available_fields
        
    # except Exception as e:
    #     print(f"❌ Errore nel recupero abbonamenti: {e}")
    #     return [], None
    
if __name__ == '__main__':
    test()
    # print(json.dumps(test, sort_keys=True, indent=4))