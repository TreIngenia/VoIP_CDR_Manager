#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Route per la gestione del listino prezzi
Integrazione con il sistema FTP Scheduler esistente
"""

import os
import json
import pandas as pd
from flask import Blueprint, request, jsonify, send_file, send_from_directory, render_template
from werkzeug.utils import secure_filename
import logging
from datetime import datetime
import tempfile
from pathlib import Path

# logger = logging.getLogger(__name__)
# Import dei logger esistenti se disponibili
try:
    from logger_config import get_logger, log_success, log_error, log_warning, log_info
    logger = get_logger(__name__)
except ImportError:
    # Fallback al logging standard se i logger personalizzati non sono disponibili
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def log_success(msg): logger.info(f"✅ {msg}")
    def log_error(msg): logger.error(f"❌ {msg}")
    def log_warning(msg): logger.warning(f"⚠️ {msg}")
    def log_info(msg): logger.info(f"ℹ️ {msg}")

def create_listino_routes(app, secure_config):
    # Crea blueprint per le route del listino
    # listino_bp = Blueprint('listino', __name__, url_prefix='/listino')
    
    # Ottieni configurazione
    config = secure_config.get_config()
    
    # Directory per i file di upload del listino
    LISTINO_UPLOAD_FOLDER = os.path.join(config.get('output_directory', 'output'), 'listino_uploads')
    os.makedirs(LISTINO_UPLOAD_FOLDER, exist_ok=True)
    
    # Configurazioni
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    ALLOWED_EXTENSIONS = {'csv'}
    
    def allowed_file(filename):
        """Verifica se il file ha un'estensione consentita"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def detect_csv_separator(content):
        """Rileva il separatore CSV analizzando il contenuto del file"""
        semicolon_count = content.count(';')
        comma_count = content.count(',')
        
        if semicolon_count > comma_count:
            return ';'
        else:
            return ','
    
    def parse_csv_file(file_path):
        """Analizza un file CSV con gestione robusta di encoding e separatori"""
        try:
            # Prova prima con encoding utf-8
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Se fallisce, prova con latin-1
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Rileva il separatore
        separator = detect_csv_separator(content)
        
        # Leggi il CSV con pandas
        df = pd.read_csv(
            file_path,
            sep=separator,
            encoding='utf-8' if ';' in content else 'latin-1',
            skipinitialspace=True
        )
        
        # Pulisci le intestazioni
        df.columns = df.columns.str.strip()
        
        # Converti i dati in formato JSON compatibile
        data = []
        for _, row in df.iterrows():
            row_dict = {}
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    row_dict[col] = None
                elif isinstance(value, (int, float)):
                    # Mantieni i numeri come numeri
                    row_dict[col] = float(value) if value != int(value) else int(value)
                else:
                    # Converti tutto il resto in stringa e prova a convertire in numero
                    str_value = str(value).strip()
                    try:
                        # Prova a convertire in float
                        if ',' in str_value and '.' not in str_value:
                            # Sostituisci virgola con punto per numeri europei
                            str_value = str_value.replace(',', '.')
                        
                        float_value = float(str_value)
                        row_dict[col] = float_value if float_value != int(float_value) else int(float_value)
                    except ValueError:
                        # Se non è un numero, mantieni come stringa
                        row_dict[col] = str_value
            
            data.append(row_dict)
        
        return data
    
    # ===== ROUTE PRINCIPALI =====
    
    @app.route('/listino')
    def listino():
        from routes.menu_routes import render_with_menu_context
        return render_with_menu_context('listino.html', {'config':secure_config})   
    
    
        # """Dashboard principale per la gestione del listino"""
        # try:
        #     from routes.menu_routes import render_with_menu_context
        #     return render_with_menu_context('listino.html', {'config':secure_config.get_config()})    
        #     # return send_from_directory('static/listino', 'listino.html')
        # except Exception as e:
        #     log_error(f"Errore serving dashboard listino: {e}")
        #     # Fallback: rendering di un template semplice
        #     return render_template('listino.html') if os.path.exists('templates/listino/dashboard.html') else \
        #            f"<h1>Gestione Listino Prezzi</h1><p>Dashboard non disponibile. Errore: {e}</p>"
    
    @app.route('/listino/static/<path:filename>')
    def listino_static_files(filename):
        """Serve i file statici del listino"""
        static_listino_path = os.path.join('static', 'listino')
        if os.path.exists(static_listino_path):
            return send_from_directory(static_listino_path, filename)
        else:
            return "File non trovato", 404
    
    # ===== API ROUTES =====
    
    @app.route('/listino/api/upload', methods=['POST'])
    def upload_file():
        """API per caricare un file CSV"""
        try:
            # Verifica che ci sia un file nella richiesta
            if 'file' not in request.files:
                return jsonify({
                    'status': False,
                    'message': 'Nessun file caricato'
                }), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({
                    'status': False,
                    'message': 'Nessun file selezionato'
                }), 400
            
            if file and allowed_file(file.filename):
                # Sicurezza: usa secure_filename
                filename = secure_filename(file.filename)
                upload_path = os.path.join(LISTINO_UPLOAD_FOLDER, filename)
                
                # Verifica dimensione file
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    return jsonify({
                        'status': False,
                        'message': f'File troppo grande. Massimo {MAX_FILE_SIZE // (1024*1024)}MB'
                    }), 400
                
                # Salva il file
                file.save(upload_path)
                
                # Analizza il file CSV
                data = parse_csv_file(upload_path)
                
                log_success(f"File listino {filename} caricato con successo. Righe: {len(data)}")
                
                return jsonify({
                    'status': True,
                    'message': 'File caricato con successo',
                    'data': data,
                    'filename': filename
                })
            else:
                return jsonify({
                    'status': False,
                    'message': 'Tipo di file non supportato. Solo file CSV sono ammessi.'
                }), 400
        
        except Exception as error:
            log_error(f"Errore durante il caricamento listino: {str(error)}")
            return jsonify({
                'status': False,
                'message': f'Errore durante il caricamento: {str(error)}'
            }), 500
    
    @app.route('/listino/api/apply-markup', methods=['POST'])
    def apply_markup():
        """API per applicare un ricarico a tutti i prezzi"""
        try:
            data = request.get_json()
            
            if not data or 'data' not in data or 'markup' not in data or 'priceColumns' not in data:
                return jsonify({
                    'status': False,
                    'message': 'Parametri mancanti'
                }), 400
            
            table_data = data['data']
            markup = float(data['markup'])
            price_columns = data['priceColumns']
            
            log_info(f"Applicazione ricarico {markup}% su {len(price_columns)} colonne")
            
            markup_factor = 1 + (markup / 100)
            
            updated_data = []
            for item in table_data:
                new_item = item.copy()
                
                for column in price_columns:
                    if column in new_item and new_item[column] is not None:
                        # Gestisce sia stringhe che numeri
                        value = new_item[column]
                        
                        if isinstance(value, str):
                            # Sostituisci virgola con punto
                            value = float(value.replace(',', '.'))
                        elif isinstance(value, (int, float)):
                            value = float(value)
                        else:
                            continue
                        
                        if not pd.isna(value):
                            new_item[column] = round(value * markup_factor, 2)
                
                updated_data.append(new_item)
            
            log_success(f"Ricarico {markup}% applicato con successo")
            
            return jsonify({
                'status': True,
                'message': f'Ricarico del {markup}% applicato con successo a {len(price_columns)} colonne',
                'data': updated_data
            })
        
        except Exception as error:
            log_error(f"Errore durante l'applicazione del ricarico: {str(error)}")
            return jsonify({
                'status': False,
                'message': f'Errore durante l\'applicazione del ricarico: {str(error)}'
            }), 500
    
    @app.route('/listino/api/save', methods=['POST'])
    def save_data():
        """API per salvare i dati modificati"""
        try:
            request_data = request.get_json()
            
            # Gestisci diversi formati di dati
            if 'current' in request_data and 'original' in request_data:
                # Nuovo formato
                data = request_data
                filename = request_data.get('filename')
            elif 'data' in request_data and 'filename' in request_data:
                # Formato adattato o originale
                data = request_data['data']
                filename = request_data['filename']
            else:
                # Formato originale
                data = request_data.get('data')
                filename = request_data.get('filename')
            
            if not data or not filename:
                return jsonify({
                    'status': False,
                    'message': 'Dati o filename mancanti'
                }), 400
            
            # Salva come JSON per mantenere il tipo di dati
            file_stem = Path(filename).stem
            json_path = os.path.join(LISTINO_UPLOAD_FOLDER, f"{file_stem}.json")
            
            # Aggiungi timestamp e metadati
            save_data_with_metadata = {
                'data': data,
                'metadata': {
                    'saved_at': datetime.now().isoformat(),
                    'original_filename': filename,
                    'file_size': len(str(data)),
                    'app_version': 'listino_integration_v1.0'
                }
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(save_data_with_metadata, f, indent=2, ensure_ascii=False)
            
            # Prepara i dati per il CSV
            if isinstance(data, dict) and 'current' in data and isinstance(data['current'], list):
                # Nuovo formato: usa i dati correnti
                csv_data = data['current']
            else:
                # Vecchio formato: usa i dati così come sono
                csv_data = data if isinstance(data, list) else [data]
            
            # Salva anche come CSV
            csv_path = os.path.join(LISTINO_UPLOAD_FOLDER, f"{file_stem}_modificato.csv")
            
            if csv_data:
                df = pd.DataFrame(csv_data)
                df.to_csv(csv_path, sep=';', index=False, encoding='utf-8')
            
            log_success(f"Listino salvato: JSON={json_path}, CSV={csv_path}")
            
            return jsonify({
                'status': True,
                'message': 'Dati salvati con successo nei formati JSON e CSV',
                'jsonPath': json_path,
                'csvPath': csv_path
            })
        
        except Exception as error:
            log_error(f"Errore durante il salvataggio listino: {str(error)}")
            return jsonify({
                'status': False,
                'message': f'Errore durante il salvataggio: {str(error)}'
            }), 500
    
    @app.route('/listino/api/last-file', methods=['GET'])
    def get_last_file():
        """API per ottenere l'ultimo file salvato"""
        try:
            uploads_dir = Path(LISTINO_UPLOAD_FOLDER)
            log_info(f"Ricerca ultimo file listino in: {uploads_dir.absolute()}")
            
            # Verifica che la directory esista
            if not uploads_dir.exists():
                uploads_dir.mkdir(parents=True, exist_ok=True)
                log_info("Cartella upload listino creata")
                
                return jsonify({
                    'status': False,
                    'message': 'Nessun file trovato. La cartella è stata creata. Carica un file per iniziare.'
                }), 404
            
            # Leggi tutti i file nella directory uploads
            try:
                files = list(uploads_dir.iterdir())
                file_names = [f.name for f in files if f.is_file()]
                log_info(f"File listino trovati: {file_names}")
            except Exception as e:
                log_error(f"Errore durante la lettura della directory listino: {e}")
                return jsonify({
                    'status': False,
                    'message': f'Errore durante la lettura della directory: {str(e)}'
                }), 500
            
            # Se la directory è vuota
            if not file_names:
                return jsonify({
                    'status': False,
                    'message': 'Nessun file listino presente. Carica un file per iniziare.'
                }), 404
            
            # Filtra i file JSON e CSV
            json_files = [f for f in file_names if f.endswith('.json')]
            csv_files = [f for f in file_names if f.endswith('.csv')]
            
            # Priorità assoluta ai file JSON
            if json_files:
                # Ordina per data di modifica (più recente prima)
                json_files_with_time = []
                for filename in json_files:
                    file_path = uploads_dir / filename
                    mtime = file_path.stat().st_mtime
                    json_files_with_time.append((filename, mtime))
                
                json_files_with_time.sort(key=lambda x: x[1], reverse=True)
                latest_json_file = json_files_with_time[0][0]
                
                log_info(f"Caricamento ultimo file listino JSON: {latest_json_file}")
                
                # Leggi il contenuto del file JSON
                json_path = uploads_dir / latest_json_file
                
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                    
                    # Estrai i dati dal formato con metadata
                    if 'data' in saved_data and 'metadata' in saved_data:
                        data = saved_data['data']
                        metadata = saved_data['metadata']
                        log_info(f"File listino con metadata: salvato il {metadata.get('saved_at', 'N/A')}")
                    else:
                        # Formato vecchio senza metadata
                        data = saved_data
                        metadata = {}
                    
                except json.JSONDecodeError as e:
                    return jsonify({
                        'status': False,
                        'message': f'Errore durante il parsing del file JSON listino: {str(e)}'
                    }), 500
                
                # Trova il nome originale del file CSV
                original_filename = metadata.get('original_filename', latest_json_file.replace('.json', '.csv'))
                
                # Verifica se i dati hanno il formato con current e original
                if isinstance(data, dict) and 'current' in data and 'original' in data:
                    return jsonify({
                        'status': True,
                        'message': 'File listino JSON caricato con successo (formato strutturato)',
                        'data': data,
                        'filename': data.get('filename', original_filename),
                        'type': 'json',
                        'metadata': metadata
                    })
                else:
                    return jsonify({
                        'status': True,
                        'message': 'File listino JSON caricato con successo (formato standard)',
                        'data': data,
                        'filename': original_filename,
                        'type': 'json',
                        'metadata': metadata
                    })
            
            elif csv_files:
                # Non ci sono file JSON, usa i CSV
                csv_files_with_time = []
                for filename in csv_files:
                    file_path = uploads_dir / filename
                    mtime = file_path.stat().st_mtime
                    csv_files_with_time.append((filename, mtime))
                
                csv_files_with_time.sort(key=lambda x: x[1], reverse=True)
                latest_csv_file = csv_files_with_time[0][0]
                
                log_info(f"Caricamento ultimo file listino CSV: {latest_csv_file}")
                
                # Analizza il CSV
                csv_path = uploads_dir / latest_csv_file
                data = parse_csv_file(str(csv_path))
                
                return jsonify({
                    'status': True,
                    'message': 'File listino CSV caricato con successo',
                    'data': data,
                    'filename': latest_csv_file,
                    'type': 'csv'
                })
            
            else:
                # Non ci sono file
                return jsonify({
                    'status': False,
                    'message': 'Nessun file listino salvato trovato'
                }), 404
        
        except Exception as error:
            log_error(f"Errore durante il recupero dell'ultimo file listino: {str(error)}")
            return jsonify({
                'status': False,
                'message': f'Errore durante il recupero dell\'ultimo file: {str(error)}'
            }), 500
    
    @app.route('/listino/logger/export-csv', methods=['POST'])
    def export_csv():
        """API per esportare i dati in CSV"""
        try:
            request_data = request.get_json()
            data = request_data.get('data')
            filename = request_data.get('filename')
            
            if not data or not filename:
                return jsonify({
                    'status': False,
                    'message': 'Dati o filename mancanti'
                }), 400
            
            # Prepara i dati per l'esportazione
            csv_data = data
            
            # Se i dati hanno il nuovo formato con current e original
            if isinstance(data, dict) and 'current' in data and 'original' in data and isinstance(data['current'], list):
                # Crea un dataset arricchito che include i valori originali
                enhanced_data = []
                
                for i, row in enumerate(data['current']):
                    enhanced_row = row.copy()
                    
                    # Aggiungi i valori originali disponibili
                    if i < len(data['original']) and data['original'][i]:
                        original_row = data['original'][i]
                        
                        for key, value in row.items():
                            # Per ogni colonna che sembra essere un prezzo
                            if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace(',', '.').replace('.', '').isdigit()):
                                # Aggiungi il valore originale con suffisso
                                if key in original_row:
                                    enhanced_row[f"{key}_originale"] = original_row[key]
                    
                    enhanced_data.append(enhanced_row)
                
                csv_data = enhanced_data
            
            # Crea il file CSV temporaneo
            file_stem = Path(filename).stem
            export_filename = f"{file_stem}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            export_path = os.path.join(LISTINO_UPLOAD_FOLDER, export_filename)
            
            # Salva il CSV
            if csv_data:
                df = pd.DataFrame(csv_data)
                df.to_csv(export_path, sep=';', index=False, encoding='utf-8')
            
            log_success(f"Export listino CSV creato: {export_filename}")
            
            # Invia il file al client
            return send_file(
                export_path,
                as_attachment=True,
                download_name=export_filename,
                mimetype='text/csv'
            )
        
        except Exception as error:
            log_error(f"Errore durante l'esportazione listino CSV: {str(error)}")
            return jsonify({
                'status': False,
                'message': f'Errore durante l\'esportazione: {str(error)}'
            }), 500
    
    # ===== ROUTE DI GESTIONE =====
    
    @app.route('/listino/api/files/list', methods=['GET'])
    def list_files():
        """Lista tutti i file del listino"""
        try:
            uploads_dir = Path(LISTINO_UPLOAD_FOLDER)
            
            if not uploads_dir.exists():
                return jsonify({
                    'status': True,
                    'files': [],
                    'message': 'Nessun file presente'
                })
            
            files_info = []
            for file_path in uploads_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    files_info.append({
                        'name': file_path.name,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'type': 'JSON' if file_path.suffix == '.json' else 'CSV'
                    })
            
            # Ordina per data di modifica (più recente prima)
            files_info.sort(key=lambda x: x['modified'], reverse=True)
            
            return jsonify({
                'status': True,
                'files': files_info,
                'count': len(files_info)
            })
        
        except Exception as error:
            log_error(f"Errore durante il listing file listino: {str(error)}")
            return jsonify({
                'status': False,
                'message': f'Errore durante il listing: {str(error)}'
            }), 500
    
    @app.route('/listino/api/files/delete/<filename>', methods=['DELETE'])
    def delete_file(filename):
        """Elimina un file del listino"""
        try:
            # Sicurezza: usa secure_filename
            safe_filename = secure_filename(filename)
            file_path = Path(LISTINO_UPLOAD_FOLDER) / safe_filename
            
            if not file_path.exists():
                return jsonify({
                    'status': False,
                    'message': 'File non trovato'
                }), 404
            
            # Verifica che il file sia nella directory corretta
            if not str(file_path.resolve()).startswith(str(Path(LISTINO_UPLOAD_FOLDER).resolve())):
                return jsonify({
                    'status': False,
                    'message': 'Accesso negato'
                }), 403
            
            file_path.unlink()
            log_success(f"File listino eliminato: {safe_filename}")
            
            return jsonify({
                'status': True,
                'message': f'File {safe_filename} eliminato con successo'
            })
        
        except Exception as error:
            log_error(f"Errore durante l'eliminazione file listino: {str(error)}")
            return jsonify({
                'status': False,
                'message': f'Errore durante l\'eliminazione: {str(error)}'
            }), 500
    
    # Conta manualmente le route del blueprint
    route_count = 0
    route_names = []
    
    # Lista delle route definite nel blueprint
    blueprint_routes = [
        '/', '/static/<path:filename>', '/api/upload', '/api/apply-markup', 
        '/api/save', '/api/last-file', '/api/export-csv', '/api/files/list', 
        '/api/files/delete/<filename>'
    ]
    
    route_count = len(blueprint_routes)
    route_names = [f"/listino{route}" for route in blueprint_routes]
    
    log_success(f"Route listino prezzi create: {route_count} endpoint")
    log_info(f"Route disponibili: {', '.join(route_names[:3])}...")  # Mostra solo le prime 3
    
    return {
        'routes_added': [
            '/listino', 
            '/listino/static/<path:filename>', 
            '/listino/api/upload', 
            '/listino/api/apply-markup', 
            '/listino/api/save', 
            '/listino/api/last-file', 
            '/listino/api/export-csv', 
            '/listino/api/files/list', 
            '/listino/api/files/delete/<filename>'
        ],
        'routes_count': route_count,
        'upload_folder': LISTINO_UPLOAD_FOLDER,
        'route_names': route_names,
        'features': [
            'Upload CSV',
            'Applicazione ricarichi',
            'Salvataggio JSON/CSV',
            'Export avanzato',
            'Gestione file',
            'Dashboard integrata'
        ]
    }
    return {
        # 'blueprint': listino_bp,
        'routes_count': route_count,
        'upload_folder': LISTINO_UPLOAD_FOLDER,
        'route_names': route_names,
        'features': [
            'Upload CSV',
            'Applicazione ricarichi',
            'Salvataggio JSON/CSV',
            'Export avanzato',
            'Gestione file',
            'Dashboard integrata'
        ]
    }

def add_listino_routes(app, secure_config):
    """
    Aggiunge le route del listino prezzi all'app Flask esistente
    
    Args:
        app: Istanza Flask dell'applicazione
        secure_config: Configurazione sicura dell'applicazione
    
    Returns:
        dict: Informazioni sull'integrazione
    """
    try:
        log_info("Inizializzazione sistema gestione listino prezzi...")
        
        # Crea le route del listino
        listino_info = create_listino_routes(secure_config)
        
        # Verifica che il blueprint sia stato creato correttamente
        if 'blueprint' not in listino_info:
            raise Exception("Errore nella creazione del blueprint listino")
        
        # Registra il blueprint nell'app
        app.register_blueprint(listino_info['blueprint'])
        
        log_success(f"Sistema listino prezzi integrato: {listino_info['routes_count']} route")
        log_info(f"Directory upload listino: {listino_info['upload_folder']}")
        log_info(f"Funzionalità: {', '.join(listino_info['features'])}")
        
        # Struttura di ritorno completa e sicura
        return {
            'status': 'success',
            'routes_count': listino_info.get('routes_count', 0),
            'upload_folder': listino_info.get('upload_folder', ''),
            'features': listino_info.get('features', []),
            'route_names': listino_info.get('route_names', []),
            'endpoints': {
                'dashboard': '/listino/',
                'upload': '/listino/api/upload',
                'save': '/listino/api/save',
                'export': '/listino/api/export-csv',
                'files': '/listino/api/files/list'
            },
            'message': f'Sistema listino integrato con successo: {listino_info.get("routes_count", 0)} route disponibili'
        }
        
    except Exception as e:
        log_error(f"Errore durante l'integrazione sistema listino: {e}")
        
        # Ritorna una struttura di errore sicura
        return {
            'status': 'error',
            'message': str(e),
            'routes_count': 0,
            'upload_folder': '',
            'features': [],
            'route_names': [],
            'endpoints': {}
        }