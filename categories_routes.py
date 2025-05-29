#!/usr/bin/env python3
"""
Categories Routes - Route Flask per gestione categorie CDR
Aggiunge endpoint per CRUD delle macro categorie nell'interfaccia web
"""

import json
import logging
from datetime import datetime
import os  # ✅ IMPORT MANCANTE AGGIUNTO
from flask import request, jsonify, render_template, Response
import csv
import io

logger = logging.getLogger(__name__)

def add_categories_routes(app, cdr_analytics_enhanced, secure_config):
    """
    Aggiunge le route per la gestione delle categorie CDR
    
    Args:
        app: Istanza Flask
        cdr_analytics_enhanced: Istanza CDRAnalyticsEnhanced con categories_manager
    """
    categories_manager = cdr_analytics_enhanced.get_categories_manager()
    
    @app.route('/categories')
    def categories_page():
        """Pagina principale gestione categorie con info configurazione"""
        try:
            categories = categories_manager.get_all_categories()
            stats = categories_manager.get_statistics()
            conflicts = categories_manager.validate_patterns_conflicts()
            
            # ✅ INFO CONFIGURAZIONE DA .env
            config_info = {
                'config_directory': secure_config.get_config()['config_directory'],
                'config_file_name': secure_config.get_config()['categories_config_file'],
                'config_file_path': str(categories_manager.config_file),
                'config_exists': categories_manager.config_file.exists(),
                'config_size_bytes': categories_manager.config_file.stat().st_size if categories_manager.config_file.exists() else 0,
                'config_readable': os.access(categories_manager.config_file, os.R_OK) if categories_manager.config_file.exists() else False,
                'config_writable': os.access(categories_manager.config_file, os.W_OK) if categories_manager.config_file.exists() else False
            }
            
            return render_template('categories.html', 
                                 categories=categories,
                                 stats=stats,
                                 conflicts=conflicts,
                                 config_info=config_info)
        except Exception as e:
            logger.error(f"Errore caricamento pagina categorie: {e}")
            return render_template('error.html', 
                                 error_message=f"Errore caricamento categorie: {e}")
        
    @app.route('/api/config/info')
    def get_config_info():
        """API per ottenere informazioni sulla configurazione"""
        try:
            config = secure_config.get_config()
            
            info = {
                'success': True,
                'directories': {
                    'config_directory': config['config_directory'],
                    'output_directory': config['output_directory'],
                    'categories_file': config['categories_config_file']
                },
                'paths': {
                    'config_full_path': str(categories_manager.config_file),
                    'config_exists': categories_manager.config_file.exists(),
                    'config_absolute': str(categories_manager.config_file.resolve())
                },
                'permissions': {
                    'config_readable': os.access(categories_manager.config_file, os.R_OK) if categories_manager.config_file.exists() else None,
                    'config_writable': os.access(categories_manager.config_file, os.W_OK) if categories_manager.config_file.exists() else None
                }
            }
            
            return jsonify(info)
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500        
    
    @app.route('/api/categories', methods=['GET'])
    def get_categories():
        """API per ottenere tutte le categorie"""
        try:
            categories_data = {}
            for name, category in categories_manager.get_all_categories().items():
                categories_data[name] = {
                    'name': category.name,
                    'display_name': category.display_name,
                    'price_per_minute': category.price_per_minute,
                    'currency': category.currency,
                    'patterns': category.patterns,
                    'description': category.description,
                    'is_active': category.is_active,
                    'created_at': category.created_at,
                    'updated_at': category.updated_at
                }
            
            return jsonify({
                'success': True,
                'categories': categories_data,
                'stats': categories_manager.get_statistics()
            })
            
        except Exception as e:
            logger.error(f"Errore API get categories: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/<category_name>', methods=['GET'])
    def get_category(category_name):
        """API per ottenere una categoria specifica"""
        try:
            category = categories_manager.get_category(category_name)
            
            if not category:
                return jsonify({'success': False, 'message': 'Categoria non trovata'}), 404
            
            return jsonify({
                'success': True,
                'category': {
                    'name': category.name,
                    'display_name': category.display_name,
                    'price_per_minute': category.price_per_minute,
                    'currency': category.currency,
                    'patterns': category.patterns,
                    'description': category.description,
                    'is_active': category.is_active,
                    'created_at': category.created_at,
                    'updated_at': category.updated_at
                }
            })
            
        except Exception as e:
            logger.error(f"Errore API get category {category_name}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories', methods=['POST'])
    def create_category():
        """API per creare una nuova categoria"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            # Validazione dati richiesti
            required_fields = ['name', 'display_name', 'price_per_minute', 'patterns']
            for field in required_fields:
                if field not in data or not data[field]:
                    return jsonify({'success': False, 'message': f'Campo {field} obbligatorio'}), 400
            
            # Estrai dati
            name = data['name'].strip().upper()
            display_name = data['display_name'].strip()
            price_per_minute = float(data['price_per_minute'])
            patterns = [p.strip() for p in data['patterns'] if p.strip()]
            currency = data.get('currency', 'EUR')
            description = data.get('description', '').strip()
            
            # Validazioni aggiuntive
            if price_per_minute < 0:
                return jsonify({'success': False, 'message': 'Il prezzo deve essere positivo'}), 400
            
            if not patterns:
                return jsonify({'success': False, 'message': 'Almeno un pattern è obbligatorio'}), 400
            
            # Crea categoria
            success = categories_manager.add_category(
                name=name,
                display_name=display_name,
                price_per_minute=price_per_minute,
                patterns=patterns,
                currency=currency,
                description=description
            )
            
            if success:
                logger.info(f"Categoria {name} creata con successo")
                return jsonify({
                    'success': True,
                    'message': f'Categoria {name} creata con successo',
                    'category_name': name
                })
            else:
                return jsonify({'success': False, 'message': 'Errore nella creazione della categoria'}), 500
                
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)}), 400
        except Exception as e:
            logger.error(f"Errore API create category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/<category_name>', methods=['PUT'])
    def update_category(category_name):
        """API per aggiornare una categoria esistente"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            # Verifica esistenza categoria
            if not categories_manager.get_category(category_name):
                return jsonify({'success': False, 'message': 'Categoria non trovata'}), 404
            
            # Prepara aggiornamenti
            updates = {}
            
            if 'display_name' in data:
                updates['display_name'] = data['display_name'].strip()
            
            if 'price_per_minute' in data:
                price = float(data['price_per_minute'])
                if price < 0:
                    return jsonify({'success': False, 'message': 'Il prezzo deve essere positivo'}), 400
                updates['price_per_minute'] = price
            
            if 'patterns' in data:
                patterns = [p.strip() for p in data['patterns'] if p.strip()]
                if not patterns:
                    return jsonify({'success': False, 'message': 'Almeno un pattern è obbligatorio'}), 400
                updates['patterns'] = patterns
            
            if 'currency' in data:
                updates['currency'] = data['currency']
            
            if 'description' in data:
                updates['description'] = data['description'].strip()
            
            if 'is_active' in data:
                updates['is_active'] = bool(data['is_active'])
            
            # Aggiorna categoria
            success = categories_manager.update_category(category_name, **updates)
            
            if success:
                logger.info(f"Categoria {category_name} aggiornata con successo")
                return jsonify({
                    'success': True,
                    'message': f'Categoria {category_name} aggiornata con successo'
                })
            else:
                return jsonify({'success': False, 'message': 'Errore nell\'aggiornamento della categoria'}), 500
                
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)}), 400
        except Exception as e:
            logger.error(f"Errore API update category {category_name}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/<category_name>', methods=['DELETE'])
    def delete_category(category_name):
        """API per eliminare una categoria"""
        try:
            # Verifica esistenza categoria
            if not categories_manager.get_category(category_name):
                return jsonify({'success': False, 'message': 'Categoria non trovata'}), 404
            
            # Elimina categoria
            success = categories_manager.delete_category(category_name)
            
            if success:
                logger.info(f"Categoria {category_name} eliminata con successo")
                return jsonify({
                    'success': True,
                    'message': f'Categoria {category_name} eliminata con successo'
                })
            else:
                return jsonify({'success': False, 'message': 'Errore nell\'eliminazione della categoria'}), 500
                
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)}), 400
        except Exception as e:
            logger.error(f"Errore API delete category {category_name}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/test-classification', methods=['POST'])
    def test_classification():
        """API per testare la classificazione di tipi di chiamata"""
        try:
            data = request.get_json()
            if not data or 'call_types' not in data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            call_types = data['call_types']
            duration_seconds = int(data.get('duration_seconds', 300))  # Default 5 minuti
            
            results = []
            
            for call_type in call_types:
                classification = categories_manager.calculate_call_cost(call_type, duration_seconds)
                results.append({
                    'call_type': call_type,
                    'category_name': classification['category_name'],
                    'category_display': classification['category_display_name'],
                    'matched': classification['matched'],
                    'price_per_minute': classification['price_per_minute'],
                    'cost_calculated': classification['cost_calculated'],
                    'currency': classification['currency']
                })
            
            return jsonify({
                'success': True,
                'test_duration_seconds': duration_seconds,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Errore API test classification: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/conflicts', methods=['GET'])
    def get_pattern_conflicts():
        """API per ottenere conflitti tra pattern delle categorie"""
        try:
            conflicts = categories_manager.validate_patterns_conflicts()
            
            return jsonify({
                'success': True,
                'conflicts': conflicts,
                'has_conflicts': len(conflicts) > 0
            })
            
        except Exception as e:
            logger.error(f"Errore API conflicts: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/statistics', methods=['GET'])
    def get_categories_statistics():
        """API per ottenere statistiche delle categorie"""
        try:
            stats = categories_manager.get_statistics()
            
            return jsonify({
                'success': True,
                'statistics': stats
            })
            
        except Exception as e:
            logger.error(f"Errore API statistics: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/export', methods=['GET'])
    def export_categories():
        """API per esportare le categorie"""
        try:
            format_type = request.args.get('format', 'json').lower()
            
            if format_type not in ['json', 'csv']:
                return jsonify({'success': False, 'message': 'Formato non supportato'}), 400
            
            exported_data = categories_manager.export_categories(format_type)
            
            if format_type == 'json':
                response = jsonify({
                    'success': True,
                    'format': format_type,
                    'data': json.loads(exported_data)
                })
            else:  # CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                response = Response(
                    exported_data,
                    mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=categories_{timestamp}.csv'}
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Errore API export: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/import', methods=['POST'])
    def import_categories():
        """API per importare categorie"""
        try:
            data = request.get_json()
            if not data or 'categories_data' not in data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            categories_data = data['categories_data']
            merge_mode = data.get('merge', True)
            
            if isinstance(categories_data, str):
                # JSON string
                success = categories_manager.import_categories(categories_data, 'json', merge_mode)
            elif isinstance(categories_data, dict):
                # JSON object
                success = categories_manager.import_categories(json.dumps(categories_data), 'json', merge_mode)
            else:
                return jsonify({'success': False, 'message': 'Formato dati non valido'}), 400
            
            if success:
                logger.info(f"Categorie importate con successo (merge: {merge_mode})")
                return jsonify({
                    'success': True,
                    'message': 'Categorie importate con successo',
                    'merge_mode': merge_mode
                })
            else:
                return jsonify({'success': False, 'message': 'Errore nell\'importazione'}), 500
                
        except Exception as e:
            logger.error(f"Errore API import: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/reset-defaults', methods=['POST'])
    def reset_to_defaults():
        """API per ripristinare categorie di default"""
        try:
            success = categories_manager.reset_to_defaults()
            
            if success:
                logger.info("Categorie ripristinate ai valori di default")
                return jsonify({
                    'success': True,
                    'message': 'Categorie ripristinate ai valori di default'
                })
            else:
                return jsonify({'success': False, 'message': 'Errore nel ripristino'}), 500
                
        except Exception as e:
            logger.error(f"Errore API reset defaults: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/bulk-update', methods=['POST'])
    def bulk_update_categories():
        """API per aggiornamento massivo delle categorie"""
        try:
            data = request.get_json()
            if not data or 'updates' not in data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            updates = data['updates']  # Lista di {category_name, updates}
            results = []
            
            for update_item in updates:
                category_name = update_item.get('category_name')
                category_updates = update_item.get('updates', {})
                
                if category_name and category_updates:
                    success = categories_manager.update_category(category_name, **category_updates)
                    results.append({
                        'category_name': category_name,
                        'success': success
                    })
            
            successful_updates = sum(1 for r in results if r['success'])
            
            return jsonify({
                'success': True,
                'message': f'{successful_updates}/{len(results)} categorie aggiornate con successo',
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Errore API bulk update: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/validate', methods=['POST'])
    def validate_category_data():
        """API per validare dati categoria prima del salvataggio"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            validation_errors = []
            warnings = []
            
            # Validazione nome
            name = data.get('name', '').strip().upper()
            if not name:
                validation_errors.append('Nome categoria obbligatorio')
            elif categories_manager.get_category(name):
                validation_errors.append(f'Categoria {name} già esistente')
            
            # Validazione display name
            if not data.get('display_name', '').strip():
                validation_errors.append('Nome visualizzato obbligatorio')
            
            # Validazione prezzo
            try:
                price = float(data.get('price_per_minute', 0))
                if price < 0:
                    validation_errors.append('Il prezzo deve essere positivo')
                elif price > 10:
                    warnings.append(f'Prezzo molto alto: {price} EUR/min')
            except (ValueError, TypeError):
                validation_errors.append('Prezzo non valido')
            
            # Validazione pattern
            patterns = data.get('patterns', [])
            if not patterns or not any(p.strip() for p in patterns):
                validation_errors.append('Almeno un pattern è obbligatorio')
            else:
                # Verifica conflitti pattern
                clean_patterns = [p.strip().upper() for p in patterns if p.strip()]
                for pattern in clean_patterns:
                    for cat_name, category in categories_manager.get_active_categories().items():
                        if any(pattern in existing_pattern.upper() for existing_pattern in category.patterns):
                            warnings.append(f'Pattern "{pattern}" potrebbe confliggere con categoria {cat_name}')
            
            return jsonify({
                'success': True,
                'valid': len(validation_errors) == 0,
                'errors': validation_errors,
                'warnings': warnings
            })
            
        except Exception as e:
            logger.error(f"Errore API validate: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/health', methods=['GET'])
    def check_system_health():
        """API per verificare lo stato di salute del sistema categorie"""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'checks': {},
                'warnings': [],
                'errors': []
            }
            
            # Check 1: Caricamento categorie
            categories = categories_manager.get_all_categories()
            health_status['checks']['categories_loaded'] = len(categories) > 0
            
            if len(categories) == 0:
                health_status['warnings'].append('Nessuna categoria configurata')
            
            # Check 2: Categorie attive
            active_categories = categories_manager.get_active_categories()
            health_status['checks']['active_categories'] = len(active_categories) > 0
            
            if len(active_categories) == 0:
                health_status['errors'].append('Nessuna categoria attiva')
                health_status['status'] = 'degraded'
            
            # Check 3: Pattern configurati
            total_patterns = sum(len(cat.patterns) for cat in categories.values())
            health_status['checks']['patterns_configured'] = total_patterns > 0
            
            if total_patterns < 5:
                health_status['warnings'].append('Pochi pattern configurati (< 5)')
            
            # Check 4: Conflitti pattern
            conflicts = categories_manager.validate_patterns_conflicts()
            health_status['checks']['no_pattern_conflicts'] = len(conflicts) == 0
            
            if len(conflicts) > 0:
                health_status['warnings'].append(f'{len(conflicts)} conflitti pattern rilevati')
            
            # Check 5: File di configurazione
            config_file_exists = categories_manager.config_file.exists()
            health_status['checks']['config_file_exists'] = config_file_exists
            
            if not config_file_exists:
                health_status['errors'].append('File di configurazione mancante')
                health_status['status'] = 'unhealthy'
            
            # Determina status finale
            if health_status['errors']:
                health_status['status'] = 'unhealthy'
            elif health_status['warnings']:
                health_status['status'] = 'degraded'
            
            # Statistiche aggiuntive
            stats = categories_manager.get_statistics()
            health_status['statistics'] = stats
            
            status_code = 200
            if health_status['status'] == 'unhealthy':
                status_code = 503  # Service unavailable
            
            return jsonify(health_status), status_code
            
        except Exception as e:
            logger.error(f"Errore API health check: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/api/categories/export-csv', methods=['GET'])
    def export_categories_csv():
        """API per esportare categorie in formato CSV"""
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                'Nome', 'Nome Visualizzato', 'Prezzo per Minuto', 'Valuta',
                'Pattern (separati da ;)', 'Descrizione', 'Attiva',
                'Data Creazione', 'Ultima Modifica'
            ])
            
            # Dati
            for category in categories_manager.get_all_categories().values():
                writer.writerow([
                    category.name,
                    category.display_name,
                    category.price_per_minute,
                    category.currency,
                    ';'.join(category.patterns),
                    category.description,
                    'Sì' if category.is_active else 'No',
                    category.created_at,
                    category.updated_at
                ])
            
            csv_content = output.getvalue()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            response = Response(
                csv_content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=categorie_cdr_{timestamp}.csv'
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Errore API export CSV: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/import-csv', methods=['POST'])
    def import_categories_csv():
        """API per importare categorie da file CSV"""
        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'message': 'Nessun file fornito'}), 400
            
            file = request.files['file']
            if file.filename == '' or not file.filename.endswith('.csv'):
                return jsonify({'success': False, 'message': 'File CSV richiesto'}), 400
            
            merge_mode = request.form.get('merge', 'true').lower() == 'true'
            
            # Leggi contenuto CSV
            csv_content = file.read().decode('utf-8')
            
            # Processa CSV
            reader = csv.DictReader(io.StringIO(csv_content))
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Validazione e pulizia dati
                    name = row.get('Nome', '').strip().upper()
                    display_name = row.get('Nome Visualizzato', '').strip()
                    price_str = row.get('Prezzo per Minuto', '0').replace(',', '.')
                    currency = row.get('Valuta', 'EUR').strip()
                    patterns_str = row.get('Pattern (separati da ;)', '').strip()
                    description = row.get('Descrizione', '').strip()
                    active_str = row.get('Attiva', 'Sì').strip().lower()
                    
                    # Conversioni
                    price = float(price_str)
                    patterns = [p.strip() for p in patterns_str.split(';') if p.strip()]
                    is_active = active_str in ['sì', 'si', 'yes', '1', 'true', 'attiva']
                    
                    # Validazioni
                    if not name or not display_name or not patterns:
                        errors.append(f"Riga {row_num}: dati obbligatori mancanti")
                        continue
                    
                    if price < 0:
                        errors.append(f"Riga {row_num}: prezzo non valido")
                        continue
                    
                    # Aggiungi o aggiorna categoria
                    if categories_manager.get_category(name) and not merge_mode:
                        errors.append(f"Riga {row_num}: categoria {name} già esistente")
                        continue
                    
                    if categories_manager.get_category(name):
                        # Aggiorna categoria esistente
                        success = categories_manager.update_category(
                            name,
                            display_name=display_name,
                            price_per_minute=price,
                            patterns=patterns,
                            currency=currency,
                            description=description,
                            is_active=is_active
                        )
                    else:
                        # Crea nuova categoria
                        success = categories_manager.add_category(
                            name=name,
                            display_name=display_name,
                            price_per_minute=price,
                            patterns=patterns,
                            currency=currency,
                            description=description
                        )
                        if success and not is_active:
                            # Imposta stato inattivo se necessario
                            categories_manager.update_category(name, is_active=False)
                    
                    if success:
                        imported_count += 1
                    else:
                        errors.append(f"Riga {row_num}: errore nel salvataggio categoria {name}")
                        
                except Exception as e:
                    errors.append(f"Riga {row_num}: errore elaborazione - {str(e)}")
            
            if imported_count > 0:
                message = f"Importate {imported_count} categorie"
                if errors:
                    message += f" con {len(errors)} errori"
                
                return jsonify({
                    'success': True,
                    'message': message,
                    'imported_count': imported_count,
                    'errors': errors
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Nessuna categoria importata',
                    'errors': errors
                }), 400
                
        except Exception as e:
            logger.error(f"Errore API import CSV: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    logger.info("🔗 Route categorie CDR registrate con successo")
    
    # Restituisce le informazioni sulle route aggiunte
    return {
        'routes_added': [
            '/categories',
            '/api/categories',
            '/api/categories/<category_name>',
            '/api/categories/test-classification',
            '/api/categories/conflicts',
            '/api/categories/statistics',
            '/api/categories/export',
            '/api/categories/import',
            '/api/categories/reset-defaults',
            '/api/categories/bulk-update',
            '/api/categories/validate',
            '/api/categories/health',
            '/api/categories/export-csv',
            '/api/categories/import-csv'
        ],
        'routes_count': 14
    }