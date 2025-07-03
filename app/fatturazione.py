import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urljoin
from odoo.odoo_subscriptions import OdooSubscriptionManager
from config import SecureConfig
from message_tools import return_message
from pathlib import Path
# Carica le variabili dal file .env
# Carica variabili dal file .env (opzionale)
# try:
#     from dotenv import load_dotenv
#     load_dotenv()  # Carica variabili dal file .env
#     print("📁 File .env caricato")
#     base_host = os.getenv('BASE_HOST')
# except ImportError:
#     print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")


def processa_contratti_attivi():
    load_dotenv()
    from ftp_downloader import FTPDownloader
    secure_config = SecureConfig()
    """
    Funzione principale che processa il JSON e chiama la funzione per ogni elemento
    Restituisce un JSON unificato con tutte le risposte
    """
    message_return = str(f'Recupero i dati tramite API')
    # print("Recupero i dati tramite API")
    
    # # SCARICO I FILE E GENERO I REPORT PER OGNI CONTRATTO
    #  # ✅ Istanzia il downloader
    downloader = FTPDownloader(secure_config)
    
    message = ''
    # ✅ Chiama il metodo sull'istanza
    result = downloader.process_files()
    # if(result['success'] == True):
    #     from cdr_manager import complete_cdr_conversion
    #     files = result['files']
    #     conversion_result = complete_cdr_conversion(files, 'latin-1')
    if(result['success'] == True):
        files = result['files']
        for file in files:
            # Genera il nome del file JSON
            
            input_path = Path(file)
            json_filename = input_path.stem + '.json'
            output_path = 'output/json_from_cdr'
            output_file = output_path +'/'+ json_filename
            output_file = Path(output_file)
            if not output_file.exists():
                from cdr_manager import complete_cdr_conversion
                files = result['files']
                conversion_result = complete_cdr_conversion(files, 'latin-1')
            else:
                continue

        
    else:
        message = result
        message_return = return_message(False, message, str(message))
        return message_return
          
    
    # Struttura per raccogliere tutti i risultati
    risultati_unificati = []
    

    
    from contratti import ElaborazioneContrattiStandalone
    elaboratore_instance = ElaborazioneContrattiStandalone()
    elaboratore_instance.load_contracts_from_file("config/cdr_contracts.json")
    result = elaboratore_instance.elabora_tutti_contratti_standalone()
    result = [c for c in result['results'] if c.get('status') == 'processed']
    # return
    json_data = result
    
    # Periodo corrente
    oggi = datetime.now()
    periodi_corrente = [{'anno': str(oggi.year), 'mese': str(oggi.month).zfill(2)}]
    
    # Converte stringa JSON se necessario
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data
    
    # Verifica successo operazione
    if not data:
        message_return = return_message(False, data, str('Nessun dato caricato'))
        return message_return
    
    # Processa ogni contratto
    # results = data.get('results', [])
    results = data
    for item in results:
        # print(item.get('contract_type'))
        # return
        response = OdooSubscriptionManager.verifica_abbonamento(secure_config, int(item.get('contract_type')), '')
        response = json.dumps(response[0])
        if isinstance(response, str):
            response_data = json.loads(response)
        else:
            response_data = response
        
        # print(response_data)
        if response_data.get('success') is True:
            message_return = str(f'Success TRUE')
            # print("Success TRUE")
            
            contract_code = item.get('contract_code')
            status = item.get('status')
            contract_type = item.get('contract_type')
            odoo_id = int(item.get('odoo_id'))
              
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
            
        elif response_data.get('success') is False:
            message_return = return_message(False, response_data, str(response_data))
            return message_return
        else:
            message_return = str(f'Campo \'success\' non trovato')
            # print("Campo 'success' non trovato")
            return            
    
    # JSON finale unificato
    json_finale = {
        "success":True,
        "timestamp": datetime.now().isoformat(),
        "contratti_processati": len(results),
        "risultati": risultati_unificati
    }
    
    message_return = str(f'Processati {len(results)} contratti')
    # print(f"Processati {len(results)} contratti")
    # print (json_finale)
    return json_finale

def processa_contratti_attivi_TEST():
    load_dotenv()
    from ftp_downloader import FTPDownloader
    secure_config = SecureConfig()
    """
    Funzione principale che processa il JSON e chiama la funzione per ogni elemento
    Restituisce un JSON unificato con tutte le risposte
    """
    message_return = str(f'Recupero i dati tramite API')
    # print("Recupero i dati tramite API")
    
    # SCARICO I FILE E GENERO I REPORT PER OGNI CONTRATTO
     # ✅ Istanzia il downloader
    downloader = FTPDownloader(secure_config)
    
    message = ''
    # ✅ Chiama il metodo sull'istanza
    result = downloader.process_files()
    if(result['success'] == True):
        from cdr_manager import complete_cdr_conversion
        files = result['files']
        conversion_result = complete_cdr_conversion(files, 'latin-1')
    else:
        message = result
        message_return = return_message(False, message, str(message))
        return message_return
          
    
    # Struttura per raccogliere tutti i risultati
    risultati_unificati = []
    

    from contratti import ElaborazioneContratti
    elaboratore_instance = ElaborazioneContratti()
    result = elaboratore_instance.elabora_tutti_contratti_get(30)
    json_data = result
    # def mia_elaborazione(contract_data):
    #     contract_code = contract_data['contract_code']
    #     odoo_id_1 = contract_data['odoo_id']
    #     contract_type = contract_data['contract_type']
    #     status = 'ok' if contract_data['contract_code'] == 'processed' else 'ko'

    #     # LA TUA LOGICA QUI:
    #     # generate_report(contract_code)
    #     # send_email(contract_code)
    #     # update_database(contract_code)
        
    #     return {
    #         'success': True,
    #         'result': {            
    #             'total': len(contract_code),
    #             'contract_code': contract_code,
    #             # 'odoo_id': odoo_id,
    #             'contract_type': contract_type,
    #             'status': status
    #         }
    #     }
    # from contratti import ElaborazioneContrattiStandalone
    # elaboratore_instance = ElaborazioneContrattiStandalone()
    # elaboratore_instance.load_contracts_from_file("config/cdr_contracts.json")
    # result = elaboratore_instance.elabora_tutti_contratti_standalone()
    # result = [c for c in result['results'] if c.get('status') == 'processed']
    return
    if result['success']:
        print(f"TEST----------------------------------->{json.dumps(result, indent=4, ensure_ascii=False)}")
    return
    json_data = result
    
    # Periodo corrente
    oggi = datetime.now()
    periodi_corrente = [{'anno': str(oggi.year), 'mese': str(oggi.month).zfill(2)}]
    
    # Converte stringa JSON se necessario
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data
    
    # Verifica successo operazione
    if data.get('success') is False:
        message_return = return_message(False, data, str(data))
        return message_return
    
    # Processa ogni contratto
    results = data.get('results', [])
    for item in results:
        print(item)
        
        response = OdooSubscriptionManager.verifica_abbonamento(secure_config, int(item.get('contract_type')), '')
        response = json.dumps(response[0])
        if isinstance(response, str):
            response_data = json.loads(response)
        else:
            response_data = response
        
        # print(response_data)
        if response_data.get('success') is True:
            print("Success TRUE")
            
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
            
        elif response_data.get('success') is False:
            message_return = return_message(False, response_data, str(response_data))
            return message_return
        else:
            print("Campo 'success' non trovato")
            return            
    
    # JSON finale unificato
    json_finale = {
        "success":True,
        "timestamp": datetime.now().isoformat(),
        "contratti_processati": len(results),
        "risultati": risultati_unificati
    }
    
    print(f"Processati {len(results)} contratti")
    # print (json_finale)
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
    cartella_principale = os.getenv('analytics_output_folder')
    
    if not cartella_principale:
        message_return = str(f'Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env')
        # print("Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env")
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
        message_return = str(f'Errore: File non trovato: {percorso_file}')
        # print(f"Errore: File non trovato: {percorso_file}")
        return None
    
    # Legge il file JSON
    try:
        with open(percorso_file, 'r', encoding='utf-8') as file:
            dati = json.load(file)
            message_return = str(f'File caricato con successo: {percorso_file}"')
        # print(f"File caricato con successo: {percorso_file}")
        return [dati,percorso_file]
    
    except json.JSONDecodeError as e:
        message_return = str(f'Errore nel parsing JSON: {e}')
        # print(f"Errore nel parsing JSON: {e}")
        return None
    except Exception as e:
        message_return = str(f'Errore nella lettura del file: {e}')
        # print(f"Errore nella lettura del file: {e}")
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
        message_return = str(f'Errore nel leggere le cartelle mesi: {e}')
        # print(f"Errore nel leggere le cartelle mesi: {e}")
        return []



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
    cartella_principale = os.getenv('analytics_output_folder')
    # print(os.getenv('analytics_output_folder'))
    
    if not cartella_principale:
        message_return = str(f'Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env')
        # print("Errore: ANALYTICS_OUTPUT_FOLDER non trovata nel file .env")
        return message_return
    
    # Normalizza il percorso per essere cross-platform
    cartella_principale = os.path.normpath(os.path.expanduser(cartella_principale))
    
    # Gestione valori di default
    if periodi is None:
        # Se non specificato, usa l'anno corrente
        anno_corrente = str(datetime.now().year)
        periodi = [{'anno': anno_corrente}]
        message_return = str(f'Parametro \'periodi\' non specificato, uso anno corrente: {anno_corrente}')
        # print(f"Parametro 'periodi' non specificato, uso anno corrente: {anno_corrente}")
    
    if contract_type is None:
        contract_type = "default"  # o un altro valore di default appropriato
        message_return = str(f'Parametro \'contract_type\' non specificato, uso valore di default: {contract_type}')
        # print(f"Parametro 'contract_type' non specificato, uso valore di default: {contract_type}")
    
    if odoo_id is None:
        message_return = str(f'Parametro \'odoo_id\' non specificato, le operazioni di fatturazione saranno saltate')
        # print("Parametro 'odoo_id' non specificato, le operazioni di fatturazione saranno saltate")
    
    risultati = []
    fatturaData = []
    api_responses = []  
    errori = []         
    success = True
    message_return = ''
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
                success = False
                message_return = str(f'Nessun mese trovata per l\'anno {anno}')
                continue
        

        
        for mese in mesi_da_processare:
            
            dati = leggi_json_report(nome_file, anno, mese)
           
            if dati is not None: 
                json_file = dati[1]
                dati = dati[0]
                json_dati = json.dumps(dati, indent=4, ensure_ascii=False)
                # print(json_dati)
                
                # Processa i dati
                if dati:
                    # Verifica se il JSON non è stato elaborato
                    metadata = dati.get('metadata', {})
                    contract_id = metadata.get('contract_id')
                    if metadata.get('elaborato') is None or metadata.get('elaborato') is False:

                        contract_data = dati.get('contract_data', [])
                        aggregated_metrics =  contract_data.get('aggregated_metrics', [])

                        totale_chiamate = aggregated_metrics.get('total_calls')
                        durata_totale_minuti = aggregated_metrics.get('total_duration_minutes')
                        costo_cliente_totale_euro = aggregated_metrics.get('total_cost_euro_final_user')
                        call_types_analysis = contract_data.get('call_types_analysis')
                        detailed_analysis = call_types_analysis.get('detailed_analysis')
                        
                        if float(costo_cliente_totale_euro) > 0:
                            # costo_cliente_totale_euro_by_category = " | ".join([f"{k}: {v['total_cost_final_user']}" for k, v in detailed_analysis.items()])
                            costo_cliente_totale_euro_by_category = " \n ".join([
                                f"{k}: {int(v['total_duration_minutes'])} min. e {int(round((v['total_duration_minutes'] - int(v['total_duration_minutes']))*60))} sec. | Tot: {v['total_cost_final_user']} €"
                                for k, v in detailed_analysis.items()
                            ])


                            json_dati = json.dumps(detailed_analysis, indent=4, ensure_ascii=False)
                            # print(costo_cliente_totale_euro_by_category, len(detailed_analysis))
                            
                            # summary = dati.get('summary', [])
                            
                            # print(f"Trovati {len(dati)} risultati per {mese}/{anno}")

                            # totale_chiamate = summary.get('totale_chiamate')
                            # durata_totale_minuti = summary.get('durata_totale_minuti')
                            # costo_cliente_totale_euro = summary.get('costo_cliente_totale_euro')
                            # costo_cliente_totale_euro_by_category = summary.get('costo_cliente_totale_euro_by_category')
                            # categoria_breakdown_dettagliato = summary.get('status')


                            
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
                                'totale': len(detailed_analysis)
                            })
                            
                            # Salta le operazioni di fatturazione se odoo_id non è fornito
                            if odoo_id is None:
                                success = False
                                message_return = str(f'Saltando operazioni di fatturazione per {mese}/{anno} (odoo_id non fornito)')
                                continue
                            
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
                                success = True
                                message_return = str(f'Fattura generata con successo per {mese}/{anno}')

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
                                success = False
                                message_return = str(f'Errore nella richiesta per {mese}/{anno}: {e}')
                               
                        else:
                            return
                            

                    else:
                        success = False
                        message_return = str(f'Il contratto n. {contract_id} del mese {mese}/{anno} è già stato elaborato')
                        # return message_return
                        
                else:
                    success = False
                    message_return = str(f'Operazione non riuscita per il contratto n. {contract_id} del mese {mese}/{anno}')
    
    # Costruisci il JSON finale con tutte le informazioni
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
        "error_message": message_return,
        "errori": errori,
        "success": success
    }
    
    # # Stampa riepilogo
    # print(f"\n--- RIEPILOGO ---")
    # print(f"Periodi processati: {risultato_finale['riepilogo']['periodi_processati']}")
    # print(f"Totale contratti trovati: {risultato_finale['riepilogo']['totale_contratti']}")
    # print(f"Chiamate API riuscite: {risultato_finale['riepilogo']['chiamate_api_riuscite']}")
    # print(f"Chiamate API fallite: {risultato_finale['riepilogo']['chiamate_api_fallite']}")
    
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
    
    message_return = str(f'Campo \'elaborato\' aggiunto con successo al metadata. File salvato in: {output_file_path}')
    # print(f"Campo 'elaborato' aggiunto con successo al metadata")
    # print(f"File salvato in: {output_file_path}")
    
    return data


# Esempio di utilizzo
if __name__ == "__main__":
    result = processa_contratti_attivi()
    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=4, ensure_ascii=False))
    else:
        print(result)
    
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