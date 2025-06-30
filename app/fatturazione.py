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


def processa_contratti_attivi():
    """
    Funzione principale che processa il JSON e chiama la funzione per ogni elemento
    Restituisce un JSON unificato con tutte le risposte
    """
    print("Recupero i dati tramite API")
    endpoint = "/api/contracts/process"
    url = urljoin(base_host, endpoint)
    
    # Struttura per raccogliere tutti i risultati
    risultati_unificati = []
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Errore nella richiesta: {e}")
        return {"errore": str(e), "risultati": []}
    
    # Periodo corrente
    oggi = datetime.now()
    periodi_corrente = [{'anno': str(oggi.year), 'mese': str(oggi.month).zfill(2)}]
    
    # Converte stringa JSON se necessario
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data
    
    # Verifica successo operazione
    if not data.get('success', False):
        print("Operazione non riuscita")
        return {"errore": "API ha restituito success=false", "risultati": []}
    
    # Processa ogni contratto
    results = data.get('results', [])
    for item in results:
        contract_code = item.get('contract_code')
        status = item.get('status')
        contract_type = item.get('contract_type')
        odoo_id = int(item.get('odoo_id'))
        
        print(f"Processando contratto: {contract_code}")
        
        # Processa il contratto e raccoglie il risultato
        risultato_contratto = elabora_cdr(
            contract_code, 
            periodi_corrente, 
            contract_type, 
            odoo_id
        )
        
        # Aggiunge info del contratto al risultato
        risultato_contratto['contract_info'] = {
            'contract_code': contract_code,
            'status': status,
            'contract_type': contract_type,
            'odoo_id': odoo_id
        }
        
        risultati_unificati.append(risultato_contratto)
    
    # JSON finale unificato
    json_finale = {
        "timestamp": datetime.now().isoformat(),
        "contratti_processati": len(results),
        "risultati": risultati_unificati
    }
    
    print(f"Processati {len(results)} contratti")
    return json_finale

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
        return [dati,percorso_file]
    
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

# def processa_json_reports(nome_file, periodi, contract_type, odoo_id):
#     """
#     Processa file JSON per più periodi
    
#     Args:
#         nome_file (str): Nome del file senza estensione
#         periodi (list): Lista di dizionari con 'anno' e opzionalmente 'mese'
#                        Es: [{'anno': '2024'}, {'anno': '2025', 'mese': '01'}]
#     """
#     load_dotenv()
#     cartella_principale = os.getenv('ANALYTICS_OUTPUT_FOLDER')
#     print(os.getenv('ANALYTICS_OUTPUT_FOLDER'))
#     if not cartella_principale:
#         print("Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env")
#         return
    
#     # Normalizza il percorso per essere cross-platform
#     cartella_principale = os.path.normpath(os.path.expanduser(cartella_principale))
    
#     risultati = []
#     fatturaData = []
#     for periodo in periodi:
#         anno = str(periodo['anno'])
#         mese_specifico = periodo.get('mese')
        
#         if mese_specifico:
#             # Processa solo il mese specificato
#             mesi_da_processare = [mese_specifico]
#         else:
#             # Processa tutti i mesi presenti nell'anno
#             cartella_anno = os.path.join(cartella_principale, anno)
#             mesi_da_processare = ottieni_cartelle_mesi(cartella_anno)
            
#             if not mesi_da_processare:
#                 print(f"Nessuna cartella mese trovata per l'anno {anno}")
#                 continue
        
#         print(f"\n--- Processando anno {anno} ---")
        
#         for mese in mesi_da_processare:
#             print(f"\nProcessando mese {mese}/{anno}")
            
#             dati = leggi_json_report(nome_file, anno, mese)

#             if dati is not None:
#                 # Processa i dati
#                 if dati:
#                     summary = dati.get('summary', [])
#                     print(f"Trovati {len(dati)} risultati per {mese}/{anno}")
                    
#                     # for item in summary:
#                     totale_chiamate = summary.get('totale_chiamate')
#                     durata_totale_minuti = summary.get('durata_totale_minuti')
#                     costo_cliente_totale_euro = summary.get('costo_cliente_totale_euro')
#                     costo_cliente_totale_euro_by_category = summary.get('costo_cliente_totale_euro_by_category')
#                     categoria_breakdown_dettagliato = summary.get('status')
#                     # contract_code = item.get('contract_code')
#                     # status = item.get('status')
#                     # print(f"  Contratto: {contract_code}, Stato: {status}")

#                     risultati.append({
#                         'nome_file':nome_file,
#                         'totale_chiamate': totale_chiamate,
#                         'durata_totale_minuti': durata_totale_minuti,
#                         'costo_cliente_totale_euro': costo_cliente_totale_euro,
#                         'costo_cliente_totale_euro_by_category': costo_cliente_totale_euro_by_category,
#                         'contract_type': contract_type,
#                         'odoo_id': odoo_id,
#                         'totale': len(summary)
#                     })

#                     fatturaData.append({
#                         'partner_id': odoo_id,
#                         'nome_file':nome_file,
#                         'due_days': "",
#                         'manual_due_date': "",
#                         'da_confermare': "SI",
#                         'totale_chiamate': totale_chiamate,
#                         'durata_totale_minuti': durata_totale_minuti,
#                         'costo_cliente_totale_euro': costo_cliente_totale_euro,
#                         'costo_cliente_totale_euro_by_category': costo_cliente_totale_euro_by_category,
#                         'contract_type': contract_type,
#                         'odoo_id': odoo_id,
#                         'totale': len(summary)
#                     })

#                     items = []
#                     for dato in fatturaData:
#                         items.append({
#                             "product_id": 15,
#                             "quantity": 1,  # o un altro campo
#                             "price_unit": dato['costo_cliente_totale_euro'],  # o altro campo
#                             "name": f"Tipo contratto: {dato['contract_type']} dettaglio: {dato['costo_cliente_totale_euro_by_category']}"
#                         })

#                     # COSTRUISCI JSON FINALE
#                     json_fattura = {
#                         "partner_id": odoo_id,
#                         "due_days": 1,
#                         "manual_due_date": "",
#                         "da_confermare": "SI",
#                         "items": items
#                     }

#                     # Dati da inviare (fatturaData deve essere un dizionario Python, NON una stringa JSON)
                    
#                     endpoint  = "/api/fatturazione/genera_fattura"
#                     url = urljoin(base_host, endpoint)
#                     # url = "http://127.0.0.1:5001/api/fatturazione/genera_fattura"

#                     headers = {
#                         "Content-Type": "application/json"
#                     }

#                     try:
#                         response = requests.post(url, headers=headers, json=json_fattura)
#                         response.raise_for_status()  # Lancia eccezione se HTTP != 200

#                         # Ottieni risposta JSON
#                         data = response.json()

#                         # Stampa formattata (come nel .textContent JS)
#                         print(json.dumps(data, indent=2, ensure_ascii=False))

#                     except requests.exceptions.RequestException as e:
#                         print(f"❌ Errore nella richiesta: {e}")
#                     print(json_fattura)
#                 else:
#                     print(f"Operazione non riuscita nel JSON per {mese}/{anno}")
        
#     # Riepilogo finale
#     print(f"\n--- RIEPILOGO ---")
#     print(f"Periodi processati: {len(risultati)}")
#     totale_contratti = sum(r['totale'] for r in risultati)
#     print(f"Totale contratti trovati: {totale_contratti}")
#     # print(f"Ecco i risultati: {json_fattura}")
    
#     return risultati

#QUESTO E' IL FILE CORRETTO =====================================================================
# def elabora_cdr(nome_file, periodi, contract_type, odoo_id):
#     from abbonamenti import Abbonamenti
#     abbonamenti = Abbonamenti()
#     """
#     Processa file JSON per più periodi e restituisce tutte le risposte API
    
#     Args:
#         nome_file (str): Nome del file senza estensione
#         periodi (list): Lista di dizionari con 'anno' e opzionalmente 'mese'
#                        Es: [{'anno': '2024'}, {'anno': '2025', 'mese': '01'}]
    
#     Returns:
#         dict: Dizionario contenente tutti i risultati e le risposte API
#     """
#     load_dotenv()
#     cartella_principale = os.getenv('ANALYTICS_OUTPUT_FOLDER')
#     print(os.getenv('ANALYTICS_OUTPUT_FOLDER'))
#     if not cartella_principale:
#         print("Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env")
#         return {"errore": "ANALYTICS_OUTPUT_FOLDER non trovata"}
    
#     # Normalizza il percorso per essere cross-platform
#     cartella_principale = os.path.normpath(os.path.expanduser(cartella_principale))
    
#     risultati = []
#     fatturaData = []
#     api_responses = []  # ⭐ Nuovo: raccolta delle risposte API
#     errori = []         # ⭐ Nuovo: raccolta degli errori
    
#     for periodo in periodi:
#         anno = str(periodo['anno'])
#         mese_specifico = periodo.get('mese')
        
#         if mese_specifico:
#             # Processa solo il mese specificato
#             mesi_da_processare = [mese_specifico]
#         else:
#             # Processa tutti i mesi presenti nell'anno
#             cartella_anno = os.path.join(cartella_principale, anno)
#             mesi_da_processare = ottieni_cartelle_mesi(cartella_anno)
            
#             if not mesi_da_processare:
#                 print(f"Nessuna cartella mese trovata per l'anno {anno}")
#                 continue
        
#         print(f"\n--- Processando anno {anno} ---")
        
#         for mese in mesi_da_processare:
#             print(f"\nProcessando mese {mese}/{anno}")
            
#             dati = leggi_json_report(nome_file, anno, mese)

#             if dati is not None:
#                 # Processa i dati
#                 if dati:
#                     summary = dati.get('summary', [])
#                     print(f"Trovati {len(dati)} risultati per {mese}/{anno}")
                    
#                     totale_chiamate = summary.get('totale_chiamate')
#                     durata_totale_minuti = summary.get('durata_totale_minuti')
#                     costo_cliente_totale_euro = summary.get('costo_cliente_totale_euro')
#                     costo_cliente_totale_euro_by_category = summary.get('costo_cliente_totale_euro_by_category')
#                     categoria_breakdown_dettagliato = summary.get('status')

#                     risultati.append({
#                         'nome_file': nome_file,
#                         'anno': anno,
#                         'mese': mese,
#                         'totale_chiamate': totale_chiamate,
#                         'durata_totale_minuti': durata_totale_minuti,
#                         'costo_cliente_totale_euro': costo_cliente_totale_euro,
#                         'costo_cliente_totale_euro_by_category': costo_cliente_totale_euro_by_category,
#                         'contract_type': contract_type,
#                         'odoo_id': odoo_id,
#                         'totale': len(summary)
#                     })
#                     #QUI DEVO INSERIRE

                    
                    
#                     # Costruisci i dettagli per la fattura
#                     items = [{
#                         "product_id": 15,
#                         "quantity": 1,
#                         "price_unit": costo_cliente_totale_euro,
#                         "name": f"Tipo contratto: {contract_type} dettaglio: {costo_cliente_totale_euro_by_category}"
#                     }]

#                     # COSTRUISCI JSON FINALE
#                     json_fattura = {
#                         "partner_id": odoo_id,
#                         "due_days": 1,
#                         "manual_due_date": "",
#                         "da_confermare": "SI",
#                         "items": items
#                     }

#                     result_singolo = abbonamenti.aggiungi_addebito_singolo(
#                         contract_code = nome_file,
#                         contract_type = contract_type,
#                         odoo_id = odoo_id,
#                         importo = costo_cliente_totale_euro,
#                         descrizione= costo_cliente_totale_euro_by_category
#                     )

#                     # Chiamata API
#                     # endpoint = "/api/fatturazione/genera_fattura"
#                     # url = urljoin(base_host, endpoint)
#                     # headers = {"Content-Type": "application/json"}

#                     try:
#                         # return(risultati)
#                         # response = requests.post(url, headers=headers, json=json_fattura)
#                         # response.raise_for_status()
                        
#                         # # ⭐ Salva la risposta API
#                         # response_data = response.json()
                        
#                         api_response_item = {
#                             "periodo": f"{mese}/{anno}",
#                             "nome_file": nome_file,
#                             "odoo_id": odoo_id,
#                             "contract_type": contract_type,
#                             "request_payload": json_fattura,
#                             "response_data": result_singolo,
#                             # "status_code": response.status_code,
#                             "success": True
#                         }
                        
#                         api_responses.append(api_response_item)
                        
#                         print(f"✅ Fattura generata con successo per {mese}/{anno}")
#                         # print(json.dumps(response_data, indent=2, ensure_ascii=False))

#                     except requests.exceptions.RequestException as e:
#                         # ⭐ Salva l'errore
#                         error_item = {
#                             "periodo": f"{mese}/{anno}",
#                             "nome_file": nome_file,
#                             "odoo_id": odoo_id,
#                             "contract_type": contract_type,
#                             "request_payload": json_fattura,
#                             "error": str(e),
#                             "status_code": getattr(result_singolo, 'status_code', None) if 'response' in locals() else None,
#                             "success": False
#                         }
                        
#                         errori.append(error_item)
#                         print(f"❌ Errore nella richiesta per {mese}/{anno}: {e}")
                        
#                 else:
#                     print(f"Operazione non riuscita nel JSON per {mese}/{anno}")
    
#     # ⭐ Costruisci il JSON finale con tutte le informazioni
#     risultato_finale = {
#         "riepilogo": {
#             "periodi_processati": len(risultati),
#             "totale_contratti": sum(r['totale'] for r in risultati),
#             "chiamate_api_riuscite": len(api_responses),
#             "chiamate_api_fallite": len(errori),
#             "timestamp": datetime.now().isoformat()
#         },
#         "dati_processati": risultati,
#         "risposte_api": api_responses,
#         "errori": errori
#     }
    
#     # Stampa riepilogo
#     print(f"\n--- RIEPILOGO ---")
#     print(f"Periodi processati: {risultato_finale['riepilogo']['periodi_processati']}")
#     print(f"Totale contratti trovati: {risultato_finale['riepilogo']['totale_contratti']}")
#     print(f"Chiamate API riuscite: {risultato_finale['riepilogo']['chiamate_api_riuscite']}")
#     print(f"Chiamate API fallite: {risultato_finale['riepilogo']['chiamate_api_fallite']}")
    
#     return risultato_finale

def elabora_cdr(nome_file, periodi=None, contract_type=None, odoo_id=None):
    from abbonamenti import Abbonamenti
    abbonamenti = Abbonamenti()
    """
    Processa file JSON per più periodi e restituisce tutte le risposte API
    
    Args:
        nome_file (str): Nome del file senza estensione
        periodi (list, optional): Lista di dizionari con 'anno' e opzionalmente 'mese'
                                 Es: [{'anno': '2024'}, {'anno': '2025', 'mese': '01'}]
                                 Se None, elabora l'anno corrente
        contract_type (str, optional): Tipo di contratto. Se None, usa un valore di default
        odoo_id (int, optional): ID Odoo. Se None, salta le operazioni che lo richiedono
    
    Returns:
        dict: Dizionario contenente tutti i risultati e le risposte API
    """
    load_dotenv()
    cartella_principale = os.getenv('ANALYTICS_OUTPUT_FOLDER')
    print(os.getenv('ANALYTICS_OUTPUT_FOLDER'))
    
    if not cartella_principale:
        print("Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env")
        return {"errore": "ANALYTICS_OUTPUT_FOLDER non trovata"}
    
    # Normalizza il percorso per essere cross-platform
    cartella_principale = os.path.normpath(os.path.expanduser(cartella_principale))
    
    # Gestione valori di default
    if periodi is None:
        # Se non specificato, usa l'anno corrente
        anno_corrente = str(datetime.now().year)
        periodi = [{'anno': anno_corrente}]
        print(f"Parametro 'periodi' non specificato, uso anno corrente: {anno_corrente}")
    
    if contract_type is None:
        contract_type = "default"  # o un altro valore di default appropriato
        print(f"Parametro 'contract_type' non specificato, uso valore di default: {contract_type}")
    
    if odoo_id is None:
        print("Parametro 'odoo_id' non specificato, le operazioni di fatturazione saranno saltate")
    
    risultati = []
    fatturaData = []
    api_responses = []  # ⭐ Nuovo: raccolta delle risposte API
    errori = []         # ⭐ Nuovo: raccolta degli errori
    
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
            json_file = dati[1]
            dati = dati[0]
            

            if dati is not None:
                # Processa i dati
                if dati:
                    # Verifica se il JSON non è stato elaborato
                    metadata = dati.get('metadata', {})
               
                    if metadata.get('elaborato') is None or metadata.get('elaborato') is False:
                        print(f"stato: {metadata.get('elaborato')}")
                      
                        summary = dati.get('summary', [])
                        print(f"Trovati {len(dati)} risultati per {mese}/{anno}")
                        
                        totale_chiamate = summary.get('totale_chiamate')
                        durata_totale_minuti = summary.get('durata_totale_minuti')
                        costo_cliente_totale_euro = summary.get('costo_cliente_totale_euro')
                        costo_cliente_totale_euro_by_category = summary.get('costo_cliente_totale_euro_by_category')
                        categoria_breakdown_dettagliato = summary.get('status')

                        risultati.append({
                            'nome_file': nome_file,
                            'anno': anno,
                            'mese': mese,
                            'totale_chiamate': totale_chiamate,
                            'durata_totale_minuti': durata_totale_minuti,
                            'costo_cliente_totale_euro': costo_cliente_totale_euro,
                            'costo_cliente_totale_euro_by_category': costo_cliente_totale_euro_by_category,
                            'contract_type': contract_type,
                            'odoo_id': odoo_id,
                            'totale': len(summary)
                        })
                        
                        # Salta le operazioni di fatturazione se odoo_id non è fornito
                        if odoo_id is None:
                            print(f"⚠️  Saltando operazioni di fatturazione per {mese}/{anno} (odoo_id non fornito)")
                            continue
                        
                        # # Costruisci i dettagli per la fattura
                        # items = [{
                        #     "product_id": 15,
                        #     "quantity": 1,
                        #     "price_unit": costo_cliente_totale_euro,
                        #     "name": f"Tipo contratto: {contract_type} dettaglio: {costo_cliente_totale_euro_by_category}"
                        # }]

                        # # COSTRUISCI JSON FINALE
                        # json_fattura = {
                        #     "partner_id": odoo_id,
                        #     "due_days": 1,
                        #     "manual_due_date": "",
                        #     "da_confermare": "SI",
                        #     "items": items
                        # }
                        
                        result_singolo = abbonamenti.aggiungi_addebito_singolo(
                            contract_code = nome_file,
                            contract_type = contract_type,
                            odoo_id = odoo_id,
                            importo = costo_cliente_totale_euro,
                            descrizione= costo_cliente_totale_euro_by_category
                        )

                        try:
                            api_response_item = {
                                "periodo": f"{mese}/{anno}",
                                "nome_file": nome_file,
                                "odoo_id": odoo_id,
                                "contract_type": contract_type,
                                # "request_payload": json_fattura,
                                "response_data": result_singolo,
                                "success": True
                            }
                            
                            api_responses.append(api_response_item)
                            add_elaborato_to_metadata(json_file)
                            print(f"✅ Fattura generata con successo per {mese}/{anno}")

                        except requests.exceptions.RequestException as e:
                            # ⭐ Salva l'errore
                            error_item = {
                                "periodo": f"{mese}/{anno}",
                                "nome_file": nome_file,
                                "odoo_id": odoo_id,
                                "contract_type": contract_type,
                                # "request_payload": json_fattura,
                                "error": str(e),
                                "status_code": getattr(result_singolo, 'status_code', None) if 'response' in locals() else None,
                                "success": False
                            }
                            
                            errori.append(error_item)
                            print(f"❌ Errore nella richiesta per {mese}/{anno}: {e}")

                    else:
                        print(f"Il JSON per {mese}/{anno} è già stato elaborato.")
                        
                else:
                    print(f"Operazione non riuscita nel JSON per {mese}/{anno}")
    
    # ⭐ Costruisci il JSON finale con tutte le informazioni
    risultato_finale = {
        "riepilogo": {
            "periodi_processati": len(risultati),
            "totale_contratti": sum(r['totale'] for r in risultati),
            "chiamate_api_riuscite": len(api_responses),
            "chiamate_api_fallite": len(errori),
            "timestamp": datetime.now().isoformat()
        },
        "dati_processati": risultati,
        "risposte_api": api_responses,
        "errori": errori
    }
    
    # Stampa riepilogo
    print(f"\n--- RIEPILOGO ---")
    print(f"Periodi processati: {risultato_finale['riepilogo']['periodi_processati']}")
    print(f"Totale contratti trovati: {risultato_finale['riepilogo']['totale_contratti']}")
    print(f"Chiamate API riuscite: {risultato_finale['riepilogo']['chiamate_api_riuscite']}")
    print(f"Chiamate API fallite: {risultato_finale['riepilogo']['chiamate_api_fallite']}")
    
    return risultato_finale

def add_elaborato_to_metadata(json_file_path, output_file_path=None):
    """
    Aggiunge il campo 'elaborato' al metadata del JSON report
    
    Args:
        json_file_path (str): Percorso del file JSON di input
        output_file_path (str, optional): Percorso del file di output. 
                                        Se None, sovrascrive il file originale
    
    Returns:
        dict: Il JSON modificato
    """
    
    # Leggi il file JSON
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Aggiungi il campo 'elaborato' al metadata
    # Puoi impostare il valore che preferisci
    data['metadata']['elaborato'] = True
    
    # Opzionalmente, aggiungi anche un timestamp di elaborazione
    data['metadata']['elaborato_timestamp'] = datetime.now().isoformat()
    
    # Determina il percorso di output
    if output_file_path is None:
        output_file_path = json_file_path
    
    # Scrivi il file JSON modificato
    with open(output_file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    
    print(f"Campo 'elaborato' aggiunto con successo al metadata")
    print(f"File salvato in: {output_file_path}")
    
    return data

# def processa_json_reports(nome_file, periodi, contract_type, odoo_id):
#     """
#     Processa file JSON per più periodi e restituisce tutte le risposte API
    
#     Args:
#         nome_file (str): Nome del file senza estensione
#         periodi (list): Lista di dizionari con 'anno' e opzionalmente 'mese'
#                        Es: [{'anno': '2024'}, {'anno': '2025', 'mese': '01'}]
    
#     Returns:
#         dict: Dizionario contenente tutti i risultati e le risposte API
#     """
#     load_dotenv()
#     cartella_principale = os.getenv('ANALYTICS_OUTPUT_FOLDER')
#     print(os.getenv('ANALYTICS_OUTPUT_FOLDER'))
#     if not cartella_principale:
#         print("Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env")
#         return {"errore": "ANALYTICS_OUTPUT_FOLDER non trovata"}
    
#     # Normalizza il percorso per essere cross-platform
#     cartella_principale = os.path.normpath(os.path.expanduser(cartella_principale))
    
#     risultati = []
#     fatturaData = []
#     api_responses = []  # ⭐ Nuovo: raccolta delle risposte API
#     errori = []         # ⭐ Nuovo: raccolta degli errori
    
#     for periodo in periodi:
#         anno = str(periodo['anno'])
#         mese_specifico = periodo.get('mese')
        
#         if mese_specifico:
#             # Processa solo il mese specificato
#             mesi_da_processare = [mese_specifico]
#         else:
#             # Processa tutti i mesi presenti nell'anno
#             cartella_anno = os.path.join(cartella_principale, anno)
#             mesi_da_processare = ottieni_cartelle_mesi(cartella_anno)
            
#             if not mesi_da_processare:
#                 print(f"Nessuna cartella mese trovata per l'anno {anno}")
#                 continue
        
#         print(f"\n--- Processando anno {anno} ---")
        
#         for mese in mesi_da_processare:
#             print(f"\nProcessando mese {mese}/{anno}")
            
#             dati = leggi_json_report(nome_file, anno, mese)

#             if dati is not None:
#                 # Processa i dati
#                 if dati:
#                     summary = dati.get('summary', [])
#                     print(f"Trovati {len(dati)} risultati per {mese}/{anno}")
                    
#                     totale_chiamate = summary.get('totale_chiamate')
#                     durata_totale_minuti = summary.get('durata_totale_minuti')
#                     costo_cliente_totale_euro = summary.get('costo_cliente_totale_euro')
#                     costo_cliente_totale_euro_by_category = summary.get('costo_cliente_totale_euro_by_category')
#                     categoria_breakdown_dettagliato = summary.get('status')

#                     risultati.append({
#                         'nome_file': nome_file,
#                         'anno': anno,
#                         'mese': mese,
#                         'totale_chiamate': totale_chiamate,
#                         'durata_totale_minuti': durata_totale_minuti,
#                         'costo_cliente_totale_euro': costo_cliente_totale_euro,
#                         'costo_cliente_totale_euro_by_category': costo_cliente_totale_euro_by_category,
#                         'contract_type': contract_type,
#                         'odoo_id': odoo_id,
#                         'totale': len(summary)
#                     })

#                     # Costruisci i dettagli per la fattura
#                     items = [{
#                         "product_id": 15,
#                         "quantity": 1,
#                         "price_unit": costo_cliente_totale_euro,
#                         "name": f"Tipo contratto: {contract_type} dettaglio: {costo_cliente_totale_euro_by_category}"
#                     }]

#                     # COSTRUISCI JSON FINALE
#                     json_fattura = {
#                         "partner_id": odoo_id,
#                         "due_days": 1,
#                         "manual_due_date": "",
#                         "da_confermare": "SI",
#                         "items": items
#                     }

#                     # Chiamata API
#                     endpoint = "/api/fatturazione/genera_fattura"
#                     url = urljoin(base_host, endpoint)
#                     headers = {"Content-Type": "application/json"}

#                     try:
#                         response = requests.post(url, headers=headers, json=json_fattura)
#                         response.raise_for_status()
                        
#                         # ⭐ Salva la risposta API
#                         response_data = response.json()
                        
#                         api_response_item = {
#                             "periodo": f"{mese}/{anno}",
#                             "nome_file": nome_file,
#                             "odoo_id": odoo_id,
#                             "contract_type": contract_type,
#                             "request_payload": json_fattura,
#                             "response_data": response_data,
#                             "status_code": response.status_code,
#                             "success": True
#                         }
                        
#                         api_responses.append(api_response_item)
                        
#                         print(f"✅ Fattura generata con successo per {mese}/{anno}")
#                         print(json.dumps(response_data, indent=2, ensure_ascii=False))

#                     except requests.exceptions.RequestException as e:
#                         # ⭐ Salva l'errore
#                         error_item = {
#                             "periodo": f"{mese}/{anno}",
#                             "nome_file": nome_file,
#                             "odoo_id": odoo_id,
#                             "contract_type": contract_type,
#                             "request_payload": json_fattura,
#                             "error": str(e),
#                             "status_code": getattr(response, 'status_code', None) if 'response' in locals() else None,
#                             "success": False
#                         }
                        
#                         errori.append(error_item)
#                         print(f"❌ Errore nella richiesta per {mese}/{anno}: {e}")
                        
#                 else:
#                     print(f"Operazione non riuscita nel JSON per {mese}/{anno}")
    
#     # ⭐ Costruisci il JSON finale con tutte le informazioni
#     risultato_finale = {
#         "riepilogo": {
#             "periodi_processati": len(risultati),
#             "totale_contratti": sum(r['totale'] for r in risultati),
#             "chiamate_api_riuscite": len(api_responses),
#             "chiamate_api_fallite": len(errori),
#             "timestamp": datetime.now().isoformat()
#         },
#         "dati_processati": risultati,
#         "risposte_api": api_responses,
#         "errori": errori
#     }
    
#     # Stampa riepilogo
#     print(f"\n--- RIEPILOGO ---")
#     print(f"Periodi processati: {risultato_finale['riepilogo']['periodi_processati']}")
#     print(f"Totale contratti trovati: {risultato_finale['riepilogo']['totale_contratti']}")
#     print(f"Chiamate API riuscite: {risultato_finale['riepilogo']['chiamate_api_riuscite']}")
#     print(f"Chiamate API fallite: {risultato_finale['riepilogo']['chiamate_api_fallite']}")
    
#     return risultato_finale
# Esempio di utilizzo
if __name__ == "__main__":
    processa_contratti_attivi()
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