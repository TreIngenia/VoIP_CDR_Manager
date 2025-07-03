#!/usr/bin/env python3
"""
Script per aggiungere addebiti agli abbonamenti Odoo
Accetta i dati dei contratti tramite parametri diretti
"""
import os
import xmlrpc.client
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Abbonamenti:
    def __init__(self):
        # Carica solo variabili ambiente per Odoo
        self.odoo_url = os.getenv('ODOO_URL', 'http://localhost:8069')
        self.odoo_db = os.getenv('ODOO_DB')
        self.odoo_user = os.getenv('ODOO_USERNAME')
        self.odoo_password = os.getenv('ODOO_API_KEY')
        
        # Validazione parametri obbligatori
        missing_params = []
        if not self.odoo_db:
            missing_params.append('ODOO_DB')
        if not self.odoo_user:
            missing_params.append('ODOO_USERNAME')
        if not self.odoo_password:
            missing_params.append('ODOO_API_KEY')
        
        if missing_params:
            raise ValueError(f"❌ Parametri mancanti nel file .env: {', '.join(missing_params)}")
        
        print(f"🔧 Configurazione Odoo:")
        print(f"   URL: {self.odoo_url}")
        print(f"   Database: {self.odoo_db}")

    def test_connessione_odoo(self):
        """
        Testa la connessione a Odoo
        
        Returns:
            dict: Risultato test
        """
        try:
            print("🧪 Test connessione Odoo...")
            
            common = xmlrpc.client.ServerProxy(f'{self.odoo_url}/xmlrpc/2/common')
            version_info = common.version()
            print(f"✅ Odoo raggiungibile - Versione: {version_info.get('server_version', 'N/A')}")
            
            uid = common.authenticate(self.odoo_db, self.odoo_user, self.odoo_password, {})
            
            if not uid:
                return {
                    'success': False,
                    'error': 'Autenticazione fallita'
                }
            
            print(f"✅ Autenticazione riuscita - User ID: {uid}")
            return {
                'success': True,
                'version': version_info.get('server_version'),
                'user_id': uid
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def aggiungi_addebito_a_partner(self, odoo_id, contract_code, importo, descrizione):
        """
        Aggiunge un addebito alla prossima fattura di un partner
        
        Args:
            odoo_id (str/int): ID del partner in Odoo
            contract_code (str): Codice del contratto
            importo (float): Importo addebito
            descrizione (str): Descrizione addebito
            
        Returns:
            dict: Risultato operazione
        """
        try:
            print(f"🔄 Aggiunta addebito: partner {odoo_id}, contratto {contract_code}, €{importo}")
            
            # Connessione Odoo
            common = xmlrpc.client.ServerProxy(f'{self.odoo_url}/xmlrpc/2/common')
            uid = common.authenticate(self.odoo_db, self.odoo_user, self.odoo_password, {})
            
            if not uid:
                return {
                    'success': False,
                    'error': 'Autenticazione Odoo fallita'
                }
            
            models = xmlrpc.client.ServerProxy(f'{self.odoo_url}/xmlrpc/2/object')
            
            # Trova abbonamento del partner
            subscription_ids = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'sale.order', 'search',
                [[
                    ('partner_id', '=', int(odoo_id)),
                    ('state', 'in', ['sale', 'done'])
                ]]
            )
            
            if not subscription_ids:
                return {
                    'success': False,
                    'error': f'Nessun abbonamento attivo trovato per partner {odoo_id}'
                }
            
            subscription_id = subscription_ids[0]
            
            # Leggi info abbonamento
            subscription = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'sale.order', 'read',
                [subscription_id], 
                {'fields': ['name', 'partner_id']}
            )[0]
            
            # Trova o crea prodotto addebiti
            product_ids = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'product.product', 'search',
                [[('default_code', '=', 'VoIP_EXTRA')]]
            )
            
            if not product_ids:
                product_id = models.execute_kw(
                    self.odoo_db, uid, self.odoo_password,
                    'product.product', 'create',
                    [{
                        'name': 'Traffico VoIP extra soglia.',
                        'default_code': 'VoIP_EXTRA',
                        'type': 'service',
                        'list_price': 0.0,
                        'invoice_policy': 'order',
                    }]
                )
            else:
                product_id = product_ids[0]
            
            # Aggiungi riga addebito
            order_line_id = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'sale.order.line', 'create',
                [{
                    'order_id': subscription_id,
                    'product_id': product_id,
                    'name': f"Dettaglio: \n {descrizione}", # - Contratto {contract_code}
                    'product_uom_qty': 1.0,
                    'price_unit': float(importo),
                }]
            )
            
            return {
                'success': True,
                'message': f'Addebito di €{importo} aggiunto al contratto {contract_code}',
                'subscription_id': subscription_id,
                'subscription_name': subscription['name'],
                'partner_name': subscription['partner_id'][1] if subscription['partner_id'] else 'N/A',
                'order_line_id': order_line_id,
                'importo': float(importo)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def processa_addebiti_da_lista(self, contracts_list, target_contract_types=['41'], importo_default=25.50):
        """
        Processo principale: riceve lista contratti e applica addebiti ai tipi specificati
        FUNZIONE PRINCIPALE - RICEVE I DATI TRAMITE PARAMETRI
        
        Args:
            contracts_list (list): Lista contratti nel formato:
                [
                    {
                        'contract_code': '1',
                        'contract_type': '41', 
                        'odoo_id': '1953',
                        'contract_name': 'Nome Cliente' (opzionale)
                    },
                    ...
                ]
            target_contract_types (list): Lista dei contract_type che devono ricevere addebiti
            importo_default (float): Importo di default per l'addebito
            
        Returns:
            dict: Risultati completi del processo
        """
        try:
            print("🚀 AVVIO PROCESSO ADDEBITI DA LISTA CONTRATTI")
            print("="*60)
            
            # Validazione input
            if not contracts_list:
                return {
                    'success': False,
                    'error': 'Lista contratti vuota',
                    'step': 'input_validation'
                }
            
            if not isinstance(contracts_list, list):
                return {
                    'success': False,
                    'error': 'contracts_list deve essere una lista',
                    'step': 'input_validation'
                }
            
            print(f"📊 Ricevuti {len(contracts_list)} contratti da processare")
            print(f"🎯 Target contract_types: {target_contract_types}")
            print(f"💰 Importo addebito: €{importo_default}")
            
            # Step 1: Test connessione Odoo
            conn_result = self.test_connessione_odoo()
            if not conn_result['success']:
                return {
                    'success': False,
                    'error': f'Connessione Odoo fallita: {conn_result["error"]}',
                    'step': 'connection_test'
                }
            
            # Step 2: Filtra contratti target
            contratti_target = []
            contratti_saltati = []
            
            for contratto in contracts_list:
                # Validazione singolo contratto
                required_fields = ['contract_code', 'contract_type', 'odoo_id']
                missing_fields = [field for field in required_fields if not contratto.get(field)]
                
                if missing_fields:
                    print(f"⚠️ Contratto saltato per campi mancanti: {missing_fields}")
                    continue
                
                if contratto['contract_type'] in target_contract_types:
                    contratti_target.append(contratto)
                else:
                    contratti_saltati.append(contratto)
            
            print(f"\n🎯 Contratti target ({len(contratti_target)}):")
            for c in contratti_target:
                print(f"   - Contratto {c['contract_code']}: tipo {c['contract_type']}, partner {c['odoo_id']}")
            
            print(f"\n⏭️ Contratti saltati ({len(contratti_saltati)}):")
            for c in contratti_saltati:
                print(f"   - Contratto {c['contract_code']}: tipo {c['contract_type']} (saltato)")
            
            # Step 3: Applica addebiti
            risultati = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'target_contract_types': target_contract_types,
                'importo_default': importo_default,
                'totale_contratti': len(contracts_list),
                'contratti_target': len(contratti_target),
                'contratti_saltati': len(contratti_saltati),
                'addebiti_applicati': 0,
                'addebiti_falliti': 0,
                'dettagli': [],
                'errori': []
            }
            
            if not contratti_target:
                risultati['message'] = f'Nessun contratto trovato con tipo {target_contract_types}'
                return risultati
            
            print(f"\n🔄 Applicazione addebiti a {len(contratti_target)} contratti...")
            
            for contratto in contratti_target:
                print(f"\n   📌 Processando contratto {contratto['contract_code']}...")
                
                addebito_result = self.aggiungi_addebito_a_partner(
                    odoo_id=contratto['odoo_id'],
                    contract_code=contratto['contract_code'],
                    importo=importo_default,
                    descrizione=f"Addebito automatico tipo {contratto['contract_type']}"
                )
                
                if addebito_result['success']:
                    risultati['addebiti_applicati'] += 1
                    risultati['dettagli'].append({
                        'contract_code': contratto['contract_code'],
                        'contract_type': contratto['contract_type'],
                        'odoo_id': contratto['odoo_id'],
                        'importo': importo_default,
                        'status': 'success',
                        'subscription_name': addebito_result['subscription_name'],
                        'partner_name': addebito_result['partner_name']
                    })
                    print(f"      ✅ Addebito aggiunto: {addebito_result['message']}")
                else:
                    risultati['addebiti_falliti'] += 1
                    risultati['errori'].append({
                        'contract_code': contratto['contract_code'],
                        'contract_type': contratto['contract_type'],
                        'odoo_id': contratto['odoo_id'],
                        'error': addebito_result['error']
                    })
                    print(f"      ❌ Errore: {addebito_result['error']}")
            
            # Step 4: Riassunto finale
            print(f"\n📊 RIASSUNTO FINALE:")
            print(f"   Contratti totali: {risultati['totale_contratti']}")
            print(f"   Contratti target (tipo {target_contract_types}): {risultati['contratti_target']}")
            print(f"   Addebiti applicati: {risultati['addebiti_applicati']}")
            print(f"   Addebiti falliti: {risultati['addebiti_falliti']}")
            print(f"   Importo totale: €{risultati['addebiti_applicati'] * importo_default}")
            
            if risultati['errori']:
                print(f"\n❌ Errori:")
                for errore in risultati['errori']:
                    print(f"   - Contratto {errore['contract_code']}: {errore['error']}")
            
            return risultati
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Errore processo: {str(e)}',
                'step': 'processing'
            }

    def aggiungi_addebito_singolo(self, contract_code, contract_type, odoo_id, importo, descrizione):
        """
        Aggiunge un addebito a un singolo contratto
        FUNZIONE SEMPLICE PER UN SOLO CONTRATTO
        
        Args:
            contract_code (str): Codice del contratto
            contract_type (str): Tipo del contratto
            odoo_id (str/int): ID del partner in Odoo
            importo (float): Importo addebito
            descrizione (str): Descrizione addebito
            
        Returns:
            dict: Risultato operazione
        """
        try:
            print(f"🔄 Addebito singolo: contratto {contract_code} (tipo {contract_type})")
            
            # Test connessione
            conn_result = self.test_connessione_odoo()
            if not conn_result['success']:
                return {
                    'success': False,
                    'error': f'Connessione Odoo fallita: {conn_result["error"]}'
                }
            
            # Applica addebito
            result = self.aggiungi_addebito_a_partner(
                odoo_id=odoo_id,
                contract_code=contract_code,
                importo=importo,
                descrizione=descrizione
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# ============================================================================
# ESEMPI DI UTILIZZO CON PARAMETRI DIRETTI
# ============================================================================

def esempio_utilizzo():
    """
    Esempi di come usare la classe con parametri diretti
    """
    print("🧪 ESEMPI DI UTILIZZO")
    print("="*50)
    
    # Inizializza classe
    abbonamenti = Abbonamenti()
    
    # # Esempio 1: Lista contratti (come dal tuo sistema)
    # contracts_list = [
    #     {
    #         'contract_code': '1',
    #         'contract_type': '42',      # ← Questo riceverà addebito
    #         'odoo_id': '1953',
    #         'contract_name': 'Cliente Test 1'
    #     }
    # ]
    
    # print("\n📋 Test con lista contratti...")
    # result = abbonamenti.processa_addebiti_da_lista(
    #     contracts_list=contracts_list,
    #     target_contract_types=['42'],  # Solo tipo 41
    #     importo_default=25.50
    # )
    
    # print(f"Risultato: {'✅ Successo' if result['success'] else '❌ Errore'}")
    
    # Esempio 2: Singolo contratto
    print("\n📋 Test addebito singolo...")
    result_singolo = abbonamenti.aggiungi_addebito_singolo(
        contract_code='1',
        contract_type='50',
        odoo_id='1953',
        importo=10.00,
        descrizione='Test addebito singolo'
    )
    
    print(f"Risultato singolo: {'✅ Successo' if result_singolo['success'] else '❌ Errore'}")


if __name__ == '__main__':
    """
    Test dello script
    """
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            # Solo test connessione
            abbonamenti = Abbonamenti()
            conn_result = abbonamenti.test_connessione_odoo()
            print(f"Test connessione: {'✅ OK' if conn_result['success'] else '❌ FALLITO'}")
            if not conn_result['success']:
                print(f"Errore: {conn_result['error']}")
        elif sys.argv[1] == '--esempio':
            # Esegui esempi
            esempio_utilizzo()
        else:
            print("Usage: python abbonamenti.py [--test|--esempio]")
    else:
        print("📋 VARIABILI RICHIESTE PER L'USO:")
        print("="*50)
        print("Per usare questo script, devi passare una lista di contratti nel formato:")
        print("""
contracts_list = [
    {
        'contract_code': '1',      # Codice del contratto
        'contract_type': '41',     # Tipo del contratto 
        'odoo_id': '1953',         # ID del partner in Odoo
        'contract_name': 'Nome'    # Nome cliente (opzionale)
    },
    # ... altri contratti
]

# Poi chiama:
abbonamenti = Abbonamenti()
result = abbonamenti.processa_addebiti_da_lista(
    contracts_list=contracts_list,
    target_contract_types=['41'],  # Tipi che ricevono addebiti
    importo_default=25.50          # Importo addebito
)
        """)
        print("\nOppure per un singolo contratto:")
        print("""
result = abbonamenti.aggiungi_addebito_singolo(
    contract_code='1',
    contract_type='41', 
    odoo_id='1953',
    importo=25.50,
    descrizione='Descrizione addebito'
)
        """)