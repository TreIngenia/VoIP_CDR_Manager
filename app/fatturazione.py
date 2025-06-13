import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urljoin

# Carica le variabili dal file .env
# Carica variabili dal file .env (opzionale)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Carica variabili dal file .env
    print("📁 File .env caricato")
    base_host = os.getenv('BASE_HOST')
except ImportError:
    print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")


def processa_json_results():
    """
    Funzione principale che processa il JSON e chiama la funzione per ogni elemento
    """
    # Se json_data è una stringa, la converte in dizionario
    print(f"Recupero i dati tramite api")
    endpoint  = "/api/contracts/process"
    url = urljoin(base_host, endpoint)

    try:
        response = requests.get(url)
        response.raise_for_status()  # Solleva eccezioni per errori HTTP

        json_data = response.json()  # Se la risposta è JSON
        # print(json_data)

    except requests.exceptions.RequestException as e:
        print(f"Errore nella richiesta: {e}")
        
    oggi = datetime.now()
    periodi_corrente = [{'anno': str(oggi.year), 'mese': str(oggi.month).zfill(2)}]

    # print(json_data)
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data
    
    # Verifica che il JSON abbia la struttura attesa
    if not data.get('success', False):
        print("Operazione non riuscita")
        return False
    
    # Processa ogni elemento in results
    results = data.get('results', [])
    for item in results:
        contract_code = item.get('contract_code')
        status = item.get('status')
        contract_type = item.get('contract_type')
        odoo_id = item.get('odoo_id')
        # Esegue la funzione per ogni elemento
        processa_json_reports(contract_code, periodi_corrente, contract_type, odoo_id)
    
    print(f"Processati {len(results)} contratti")
    return True

#RECUPERO LE INFORMAZIONI PER LA FATTURAZIONE
def leggi_json_report(nome_file, anno=None, mese=None):
    """
    Legge un file JSON dalla struttura cartella_principale/anno/mese/
    
    Args:
        nome_file (str): Nome del file senza estensione (es: "1", "30")
        anno (str): Anno specifico, se None usa anno corrente
        mese (str): Mese specifico, se None usa mese corrente
    
    Returns:
        dict: Contenuto del file JSON o None se non trovato
    """
    
    # Prende la cartella principale dal file .env
    cartella_principale = os.getenv('ANALYTICS_OUTPUT_FOLDER')
    
    if not cartella_principale:
        print("Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env")
        return None
    
    # Normalizza il percorso per essere cross-platform
    cartella_principale = os.path.normpath(os.path.expanduser(cartella_principale))
    
    # Usa anno e mese correnti se non specificati
    if anno is None or mese is None:
        oggi = datetime.now()
        anno = anno or str(oggi.year)
        mese = mese or str(oggi.month).zfill(2)
    
    # Assicura formato corretto per il mese
    if len(mese) == 1:
        mese = mese.zfill(2)
    
    # Costruisce il percorso completo
    percorso_file = os.path.join(
        cartella_principale,
        str(anno),
        mese,
        f"{nome_file}_report.json"
    )
    
    print(f"Cercando file: {percorso_file}")
    
    # Verifica se il file esiste
    if not os.path.exists(percorso_file):
        print(f"Errore: File non trovato: {percorso_file}")
        return None
    
    # Legge il file JSON
    try:
        with open(percorso_file, 'r', encoding='utf-8') as file:
            dati = json.load(file)
        print(f"File caricato con successo: {percorso_file}")
        return dati
    
    except json.JSONDecodeError as e:
        print(f"Errore nel parsing JSON: {e}")
        return None
    except Exception as e:
        print(f"Errore nella lettura del file: {e}")
        return None

def ottieni_cartelle_mesi(cartella_anno):
    """
    Ottiene tutte le cartelle mesi presenti in una cartella anno
    
    Args:
        cartella_anno (str): Percorso della cartella anno
        
    Returns:
        list: Lista delle cartelle mesi trovate
    """
    if not os.path.exists(cartella_anno):
        return []
    
    try:
        cartelle = [
            nome for nome in os.listdir(cartella_anno)
            if os.path.isdir(os.path.join(cartella_anno, nome)) and nome.isdigit()
        ]
        # Ordina le cartelle numericamente
        cartelle.sort(key=int)
        return [str(mese).zfill(2) for mese in sorted([int(m) for m in cartelle])]
    except Exception as e:
        print(f"Errore nel leggere le cartelle mesi: {e}")
        return []

def processa_json_reports(nome_file, periodi, contract_type, odoo_id):
    """
    Processa file JSON per più periodi
    
    Args:
        nome_file (str): Nome del file senza estensione
        periodi (list): Lista di dizionari con 'anno' e opzionalmente 'mese'
                       Es: [{'anno': '2024'}, {'anno': '2025', 'mese': '01'}]
    """
    load_dotenv()
    cartella_principale = os.getenv('ANALYTICS_OUTPUT_FOLDER')
    print(os.getenv('ANALYTICS_OUTPUT_FOLDER'))
    if not cartella_principale:
        print("Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env")
        return
    
    # Normalizza il percorso per essere cross-platform
    cartella_principale = os.path.normpath(os.path.expanduser(cartella_principale))
    
    risultati = []
    fatturaData = []
    for periodo in periodi:
        anno = str(periodo['anno'])
        mese_specifico = periodo.get('mese')
        
        if mese_specifico:
            # Processa solo il mese specificato
            mesi_da_processare = [mese_specifico]
        else:
            # Processa tutti i mesi presenti nell'anno
            cartella_anno = os.path.join(cartella_principale, anno)
            mesi_da_processare = ottieni_cartelle_mesi(cartella_anno)
            
            if not mesi_da_processare:
                print(f"Nessuna cartella mese trovata per l'anno {anno}")
                continue
        
        print(f"\n--- Processando anno {anno} ---")
        
        for mese in mesi_da_processare:
            print(f"\nProcessando mese {mese}/{anno}")
            
            dati = leggi_json_report(nome_file, anno, mese)

            if dati is not None:
                # Processa i dati
                if dati:
                    summary = dati.get('summary', [])
                    print(f"Trovati {len(dati)} risultati per {mese}/{anno}")
                    
                    # for item in summary:
                    totale_chiamate = summary.get('totale_chiamate')
                    durata_totale_minuti = summary.get('durata_totale_minuti')
                    costo_cliente_totale_euro = summary.get('costo_cliente_totale_euro')
                    costo_cliente_totale_euro_by_category = summary.get('costo_cliente_totale_euro_by_category')
                    categoria_breakdown_dettagliato = summary.get('status')
                    # contract_code = item.get('contract_code')
                    # status = item.get('status')
                    # print(f"  Contratto: {contract_code}, Stato: {status}")

                    risultati.append({
                        'nome_file':nome_file,
                        'totale_chiamate': totale_chiamate,
                        'durata_totale_minuti': durata_totale_minuti,
                        'costo_cliente_totale_euro': costo_cliente_totale_euro,
                        'costo_cliente_totale_euro_by_category': costo_cliente_totale_euro_by_category,
                        'contract_type': contract_type,
                        'odoo_id': odoo_id,
                        'totale': len(summary)
                    })

                    fatturaData.append({
                        'partner_id': odoo_id,
                        'nome_file':nome_file,
                        'due_days': "",
                        'manual_due_date': "",
                        'da_confermare': "SI",
                        'totale_chiamate': totale_chiamate,
                        'durata_totale_minuti': durata_totale_minuti,
                        'costo_cliente_totale_euro': costo_cliente_totale_euro,
                        'costo_cliente_totale_euro_by_category': costo_cliente_totale_euro_by_category,
                        'contract_type': contract_type,
                        'odoo_id': odoo_id,
                        'totale': len(summary)
                    })

                    items = []
                    for dato in fatturaData:
                        items.append({
                            "product_id": 15,
                            "quantity": 1,  # o un altro campo
                            "price_unit": dato['costo_cliente_totale_euro'],  # o altro campo
                            "name": f"Tipo cotnratto: {dato['contract_type']} dettaglio: {dato['costo_cliente_totale_euro_by_category']}"
                        })

                    # COSTRUISCI JSON FINALE
                    json_fattura = {
                        "partner_id": odoo_id,
                        "due_days": 1,
                        "manual_due_date": "",
                        "da_confermare": "SI",
                        "items": items
                    }

                    # Dati da inviare (fatturaData deve essere un dizionario Python, NON una stringa JSON)
                    
                    endpoint  = "/api/fatturazione/genera_fattura"
                    url = urljoin(base_host, endpoint)
                    # url = "http://127.0.0.1:5001/api/fatturazione/genera_fattura"

                    headers = {
                        "Content-Type": "application/json"
                    }

                    try:
                        response = requests.post(url, headers=headers, json=json_fattura)
                        response.raise_for_status()  # Lancia eccezione se HTTP != 200

                        # Ottieni risposta JSON
                        data = response.json()

                        # Stampa formattata (come nel .textContent JS)
                        print(json.dumps(data, indent=2, ensure_ascii=False))

                    except requests.exceptions.RequestException as e:
                        print(f"❌ Errore nella richiesta: {e}")
                    print(json_fattura)
                else:
                    print(f"Operazione non riuscita nel JSON per {mese}/{anno}")
        
    # Riepilogo finale
    print(f"\n--- RIEPILOGO ---")
    print(f"Periodi processati: {len(risultati)}")
    totale_contratti = sum(r['totale'] for r in risultati)
    print(f"Totale contratti trovati: {totale_contratti}")
    # print(f"Ecco i risultati: {json_fattura}")
    
    return risultati

# Esempio di utilizzo
if __name__ == "__main__":
    processa_json_results()
    # processa_json_reports(96, [{'anno': '2025'}])

      # const fatturaData = {
    #         partner_id: 1951,
    #         due_days: "",
    #         manual_due_date: "2025-09-01",
    #         da_confermare: "NO",
    #         items: [
    #             {
    #             product_id: 15,
    #             quantity: 2,
    #             price_unit: 100,
    #             name: "Prodotto 1"
    #             }
    #         ]
    #     };