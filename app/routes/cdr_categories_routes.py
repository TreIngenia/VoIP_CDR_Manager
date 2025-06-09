"""
Categories Routes - Route Flask per gestione categorie CDR con markup personalizzabili
Aggiornato per utilizzare il sistema unificato cdr_categories_enhanced.py
"""

import json
import logging
from datetime import datetime
import os
from flask import request, jsonify, render_template, Response
import csv
import io

logger = logging.getLogger(__name__)

def add_cdr_categories_routes(app, cdr_analytics_enhanced, secure_config):
    """
    Aggiunge le route per la gestione delle categorie CDR con markup
    
    Args:
        app: Istanza Flask
        cdr_analytics_enhanced: Istanza CDRAnalyticsEnhanced con categories_manager
        secure_config: Configurazione sicura per markup globale
    """
    categories_manager = cdr_analytics_enhanced.get_categories_manager()
    
    @app.route('/cdr_categories_new')
    def cdr_categories_page_new():
        """Pagina principale gestione categorie con info configurazione e markup"""
        try:
            from routes.menu_routes import render_with_menu_context
            
            categories = categories_manager.get_all_categories_with_pricing()
            stats = categories_manager.get_statistics()
            conflicts = categories_manager.validate_patterns_conflicts()
            
            # Info configurazione da .env incluso markup
            config_info = {
                'config_directory': secure_config.get_config()['config_directory'],
                'config_file_name': secure_config.get_config()['categories_config_file'],
                'config_file_path': str(categories_manager.config_file),
                'config_exists': categories_manager.config_file.exists(),
                'config_size_bytes': categories_manager.config_file.stat().st_size if categories_manager.config_file.exists() else 0,
                'config_readable': os.access(categories_manager.config_file, os.R_OK) if categories_manager.config_file.exists() else False,
                'config_writable': os.access(categories_manager.config_file, os.W_OK) if categories_manager.config_file.exists() else False,
                # Nuove info markup
                'global_markup_percent': categories_manager.global_markup_percent,
                'voip_config': {
                    'base_fixed': secure_config.get_config().get('voip_price_fixed', 0.02),
                    'base_mobile': secure_config.get_config().get('voip_price_mobile', 0.15),
                    'global_markup': secure_config.get_config().get('voip_markup_percent', 0.0),
                    'currency': secure_config.get_config().get('voip_currency', 'EUR')
                }
            }
            
            return render_with_menu_context('categoriesNEW.html', {
                'categories': categories,
                'stats': stats,
                'conflicts': conflicts,
                'config_info': config_info
            })
        except Exception as e:
            logger.error(f"Errore caricamento pagina categorie: {e}")
            return render_template('error.html', 
                                 error_message=f"Errore caricamento categorie: {e}")

    @app.route('/cdr_categories_edit')
    def cdr_categories_edit():
        """Pagina principale gestione categorie con info configurazione e markup"""
        try:
            from routes.menu_routes import render_with_menu_context
            
            categories = categories_manager.get_all_categories_with_pricing()
            stats = categories_manager.get_statistics()
            conflicts = categories_manager.validate_patterns_conflicts()
            
            # Info configurazione da .env incluso markup
            config_info = {
                'config_directory': secure_config.get_config()['config_directory'],
                'config_file_name': secure_config.get_config()['categories_config_file'],
                'config_file_path': str(categories_manager.config_file),
                'config_exists': categories_manager.config_file.exists(),
                'config_size_bytes': categories_manager.config_file.stat().st_size if categories_manager.config_file.exists() else 0,
                'config_readable': os.access(categories_manager.config_file, os.R_OK) if categories_manager.config_file.exists() else False,
                'config_writable': os.access(categories_manager.config_file, os.W_OK) if categories_manager.config_file.exists() else False,
                # Nuove info markup
                'global_markup_percent': categories_manager.global_markup_percent,
                'voip_config': {
                    'base_fixed': secure_config.get_config().get('voip_price_fixed', 0.02),
                    'base_mobile': secure_config.get_config().get('voip_price_mobile', 0.15),
                    'global_markup': secure_config.get_config().get('voip_markup_percent', 0.0),
                    'currency': secure_config.get_config().get('voip_currency', 'EUR')
                }
            }
            
            return render_with_menu_context('categories.html', {
                'categories': categories,
                'stats': stats,
                'conflicts': conflicts,
                'config_info': config_info
            })
        except Exception as e:
            logger.error(f"Errore caricamento pagina categorie: {e}")
            return render_template('error.html', 
                                 error_message=f"Errore caricamento categorie: {e}")
    
    @app.route('/api/categories', methods=['GET'])
    def get_categories():
        """API per ottenere tutte le categorie con informazioni pricing"""
        try:
            categories_data = categories_manager.get_all_categories_with_pricing()
            
            return jsonify({
                'success': True,
                'categories': categories_data,
                'stats': categories_manager.get_statistics(),
                'global_markup_percent': categories_manager.global_markup_percent
            })
            
        except Exception as e:
            logger.error(f"Errore API get categories: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/<category_name>', methods=['GET'])
    def get_category(category_name):
        """API per ottenere una categoria specifica con pricing"""
        try:
            category = categories_manager.get_category(category_name)
            
            if not category:
                return jsonify({'success': False, 'message': 'Categoria non trovata'}), 404
            
            # Costruisce dati categoria con pricing info
            from dataclasses import asdict
            category_data = asdict(category)
            category_data['pricing_info'] = category.get_pricing_info(categories_manager.global_markup_percent)
            
            return jsonify({
                'success': True,
                'category': category_data
            })
            
        except Exception as e:
            logger.error(f"Errore API get category {category_name}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories', methods=['POST'])
    def create_category():
        """API per creare una nuova categoria con markup personalizzabile"""
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
            
            # Gestione markup personalizzato
            custom_markup_percent = None
            if 'custom_markup_percent' in data and data['custom_markup_percent'] not in [None, '', 'null']:
                try:
                    custom_markup_percent = float(data['custom_markup_percent'])
                    if custom_markup_percent < -100:
                        return jsonify({'success': False, 'message': 'Markup non può essere inferiore a -100%'}), 400
                    if custom_markup_percent > 1000:
                        return jsonify({'success': False, 'message': 'Markup troppo alto (massimo 1000%)'}), 400
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'message': 'Valore markup non valido'}), 400
            
            # Validazioni aggiuntive
            if price_per_minute < 0:
                return jsonify({'success': False, 'message': 'Il prezzo deve essere positivo'}), 400
            
            if not patterns:
                return jsonify({'success': False, 'message': 'Almeno un pattern è obbligatorio'}), 400
            
            # Crea categoria con markup
            success = categories_manager.add_category(
                name=name,
                display_name=display_name,
                price_per_minute=price_per_minute,
                patterns=patterns,
                currency=currency,
                description=description,
                custom_markup_percent=custom_markup_percent
            )
            
            if success:
                logger.info(f"Categoria {name} creata con successo")
                # Restituisci info pricing complete
                new_category = categories_manager.get_category(name)
                from dataclasses import asdict
                category_data = asdict(new_category)
                category_data['pricing_info'] = new_category.get_pricing_info(categories_manager.global_markup_percent)
                
                return jsonify({
                    'success': True,
                    'message': f'Categoria {name} creata con successo',
                    'category_name': name,
                    'category_data': category_data
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
        """API per aggiornare una categoria esistente con supporto markup"""
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
            
            # Gestione aggiornamento markup personalizzato
            if 'custom_markup_percent' in data:
                markup_value = data['custom_markup_percent']
                
                if markup_value in [None, '', 'null', 'reset']:
                    # Reset a markup globale
                    updates['custom_markup_percent'] = None
                else:
                    try:
                        custom_markup = float(markup_value)
                        if custom_markup < -100:
                            return jsonify({'success': False, 'message': 'Markup non può essere inferiore a -100%'}), 400
                        if custom_markup > 1000:
                            return jsonify({'success': False, 'message': 'Markup troppo alto (massimo 1000%)'}), 400
                        updates['custom_markup_percent'] = custom_markup
                    except (ValueError, TypeError):
                        return jsonify({'success': False, 'message': 'Valore markup non valido'}), 400
            
            # Aggiorna categoria
            success = categories_manager.update_category(category_name, **updates)
            
            if success:
                logger.info(f"Categoria {category_name} aggiornata con successo")
                # Restituisci dati aggiornati con pricing
                updated_category = categories_manager.get_category(category_name)
                from dataclasses import asdict
                category_data = asdict(updated_category)
                category_data['pricing_info'] = updated_category.get_pricing_info(categories_manager.global_markup_percent)
                
                return jsonify({
                    'success': True,
                    'message': f'Categoria {category_name} aggiornata con successo',
                    'category_data': category_data
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
    
    @app.route('/api/categories/global-markup', methods=['POST'])
    def update_global_markup():
        """API per aggiornare il markup globale e ricalcolare tutti i prezzi"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            if 'global_markup_percent' not in data:
                return jsonify({'success': False, 'message': 'Campo global_markup_percent obbligatorio'}), 400
            
            try:
                new_markup = float(data['global_markup_percent'])
                if new_markup < -100:
                    return jsonify({'success': False, 'message': 'Markup globale non può essere inferiore a -100%'}), 400
                if new_markup > 1000:
                    return jsonify({'success': False, 'message': 'Markup globale troppo alto (massimo 1000%)'}), 400
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': 'Valore markup globale non valido'}), 400
            
            # Aggiorna markup globale
            success = categories_manager.update_global_markup(new_markup)
            
            if success:
                # Opzionale: aggiorna anche la configurazione .env
                update_env_config = data.get('update_env_config', False)
                if update_env_config:
                    try:
                        secure_config.update_config({'voip_markup_percent': new_markup})
                        from config import save_config_to_env
                        save_config_to_env(secure_config, app.secret_key)
                        logger.info(f"Markup globale aggiornato anche nel file .env: {new_markup}%")
                    except Exception as e:
                        logger.warning(f"Errore aggiornamento .env: {e}")
                
                # Restituisci statistiche aggiornate
                updated_stats = categories_manager.get_statistics()
                affected_categories = [
                    name for name, cat in categories_manager.get_all_categories().items() 
                    if cat.custom_markup_percent is None
                ]
                
                return jsonify({
                    'success': True,
                    'message': f'Markup globale aggiornato a {new_markup}%',
                    'global_markup_percent': new_markup,
                    'affected_categories': affected_categories,
                    'stats': updated_stats
                })
            else:
                return jsonify({'success': False, 'message': 'Errore nell\'aggiornamento del markup globale'}), 500
                
        except Exception as e:
            logger.error(f"Errore API update global markup: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/pricing-preview', methods=['POST'])
    def pricing_preview():
        """API per anteprima calcolo prezzi con markup diversi"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            base_price = float(data.get('base_price', 0))
            markup_scenarios = data.get('markup_scenarios', [0, 10, 20, 30])
            duration_minutes = int(data.get('duration_minutes', 5))
            
            if base_price < 0:
                return jsonify({'success': False, 'message': 'Prezzo base deve essere positivo'}), 400
            
            preview_results = []
            
            for markup_percent in markup_scenarios:
                try:
                    markup_multiplier = 1 + (float(markup_percent) / 100)
                    final_price = round(base_price * markup_multiplier, 4)
                    total_cost = round(final_price * duration_minutes, 4)
                    markup_amount = round(final_price - base_price, 4)
                    
                    preview_results.append({
                        'markup_percent': markup_percent,
                        'base_price': base_price,
                        'markup_amount': markup_amount,
                        'final_price': final_price,
                        'total_cost_example': total_cost,
                        'duration_minutes': duration_minutes
                    })
                except Exception as e:
                    logger.warning(f"Errore calcolo preview per markup {markup_percent}%: {e}")
            
            return jsonify({
                'success': True,
                'pricing_preview': preview_results,
                'base_price': base_price,
                'duration_minutes': duration_minutes
            })
            
        except Exception as e:
            logger.error(f"Errore API pricing preview: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/test-classification', methods=['POST'])
    def test_classification():
        """API per testare la classificazione di tipi di chiamata con markup"""
        try:
            data = request.get_json()
            if not data or 'call_types' not in data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            call_types = data['call_types']
            duration_seconds = int(data.get('duration_seconds', 300))  # Default 5 minuti
            
            results = []
            
            for call_type in call_types:
                # Testa con markup
                classification = categories_manager.calculate_call_cost(call_type, duration_seconds)
                
                results.append({
                    'call_type': call_type,
                    'category_name': classification['category_name'],
                    'category_display': classification['category_display_name'],
                    'matched': classification['matched'],
                    'price_per_minute_base': classification.get('price_per_minute_base', 0),
                    'price_per_minute_with_markup': classification.get('price_per_minute_with_markup', 0),
                    'price_per_minute_used': classification.get('price_per_minute_used', 0),
                    'markup_percent': classification.get('markup_percent_applied', 0),
                    'markup_source': classification.get('markup_source', 'none'),
                    'markup_applied': classification.get('markup_applied', False),
                    'cost_calculated': classification['cost_calculated'],
                    'currency': classification['currency']
                })
            
            return jsonify({
                'success': True,
                'test_duration_seconds': duration_seconds,
                'global_markup_percent': categories_manager.global_markup_percent,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Errore API test classification: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/bulk-update-markup', methods=['POST'])
    def bulk_update_markup():
        """API per aggiornamento massivo dei markup delle categorie"""
        try:
            data = request.get_json()
            if not data or 'updates' not in data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            updates = data['updates']  # Lista di {category_name, custom_markup_percent}
            results = []
            
            for update_item in updates:
                category_name = update_item.get('category_name')
                markup_percent = update_item.get('custom_markup_percent')
                
                if not category_name:
                    results.append({
                        'category_name': category_name,
                        'success': False,
                        'message': 'Nome categoria mancante'
                    })
                    continue
                
                try:
                    # Validazione markup
                    if markup_percent is not None and markup_percent != '':
                        markup_percent = float(markup_percent)
                        if markup_percent < -100 or markup_percent > 1000:
                            results.append({
                                'category_name': category_name,
                                'success': False,
                                'message': 'Markup fuori range (-100% - 1000%)'
                            })
                            continue
                    else:
                        markup_percent = None  # Reset a globale
                    
                    # Aggiorna categoria
                    success = categories_manager.update_category(category_name, custom_markup_percent=markup_percent)
                    
                    if success:
                        updated_category = categories_manager.get_category(category_name)
                        results.append({
                            'category_name': category_name,
                            'success': True,
                            'new_markup_percent': markup_percent,
                            'final_price': updated_category.price_with_markup if updated_category else None
                        })
                    else:
                        results.append({
                            'category_name': category_name,
                            'success': False,
                            'message': 'Errore aggiornamento categoria'
                        })
                        
                except Exception as e:
                    results.append({
                        'category_name': category_name,
                        'success': False,
                        'message': str(e)
                    })
            
            successful_updates = sum(1 for r in results if r['success'])
            
            return jsonify({
                'success': True,
                'message': f'{successful_updates}/{len(results)} categorie aggiornate con successo',
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Errore API bulk update markup: {e}")
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
        """API per ottenere statistiche delle categorie con info markup"""
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
        """API per esportare le categorie con informazioni markup"""
        try:
            format_type = request.args.get('format', 'json').lower()
            
            if format_type not in ['json', 'csv']:
                return jsonify({'success': False, 'message': 'Formato non supportato'}), 400
            
            if format_type == 'json':
                # Esporta con informazioni pricing complete
                categories_data = categories_manager.get_all_categories_with_pricing()
                response = jsonify({
                    'success': True,
                    'format': format_type,
                    'global_markup_percent': categories_manager.global_markup_percent,
                    'export_timestamp': datetime.now().isoformat(),
                    'data': categories_data
                })
            else:  # CSV
                # CSV con colonne markup
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Header esteso
                writer.writerow([
                    'Nome', 'Nome Visualizzato', 'Prezzo Base', 'Markup Personalizzato', 
                    'Prezzo Finale', 'Valuta', 'Pattern (separati da ;)', 'Descrizione', 
                    'Attiva', 'Data Creazione', 'Ultima Modifica'
                ])
                
                # Dati con pricing
                for category in categories_manager.get_all_categories().values():
                    markup_display = f"{category.custom_markup_percent}%" if category.custom_markup_percent is not None else "Globale"
                    
                    writer.writerow([
                        category.name,
                        category.display_name,
                        category.price_per_minute,
                        markup_display,
                        category.price_with_markup,
                        category.currency,
                        ';'.join(category.patterns),
                        category.description,
                        'Sì' if category.is_active else 'No',
                        category.created_at,
                        category.updated_at
                    ])
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                response = Response(
                    output.getvalue(),
                    mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=categories_markup_{timestamp}.csv'}
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Errore API export: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/import', methods=['POST'])
    def import_categories():
        """API per importare categorie JSON"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            categories_data = data.get('categories_data')
            merge_mode = data.get('merge', True)
            
            if not categories_data:
                return jsonify({'success': False, 'message': 'Dati categorie mancanti'}), 400
            
            # Usa il metodo di import del categories_manager
            success = categories_manager.import_categories(
                json.dumps(categories_data), 
                format='json', 
                merge=merge_mode
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Categorie importate con successo (merge: {merge_mode})'
                })
            else:
                return jsonify({'success': False, 'message': 'Errore durante importazione'}), 500
                
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
                    'message': 'Categorie ripristinate ai valori di default',
                    'global_markup_percent': categories_manager.global_markup_percent
                })
            else:
                return jsonify({'success': False, 'message': 'Errore nel ripristino'}), 500
                
        except Exception as e:
            logger.error(f"Errore API reset defaults: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/categories/health', methods=['GET'])
    def check_categories_health():
        """API per controllo salute sistema categorie"""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'checks': {},
                'warnings': [],
                'errors': []
            }
            
            # Check file configurazione
            try:
                if categories_manager.config_file.exists():
                    health_status['checks']['config_file_exists'] = True
                    
                    # Check permessi
                    if os.access(categories_manager.config_file, os.R_OK):
                        health_status['checks']['config_file_readable'] = True
                    else:
                        health_status['checks']['config_file_readable'] = False
                        health_status['errors'].append('File configurazione non leggibile')
                    
                    if os.access(categories_manager.config_file, os.W_OK):
                        health_status['checks']['config_file_writable'] = True
                    else:
                        health_status['checks']['config_file_writable'] = False
                        health_status['warnings'].append('File configurazione non scrivibile')
                else:
                    health_status['checks']['config_file_exists'] = False
                    health_status['warnings'].append('File configurazione non esiste')
            except Exception as e:
                health_status['checks']['config_file_check'] = False
                health_status['errors'].append(f'Errore controllo file: {str(e)}')
            
            # Check categorie caricate
            try:
                categories_count = len(categories_manager.get_all_categories())
                active_count = len(categories_manager.get_active_categories())
                
                health_status['checks']['categories_loaded'] = categories_count > 0
                health_status['checks']['active_categories'] = active_count > 0
                
                if categories_count == 0:
                    health_status['errors'].append('Nessuna categoria caricata')
                elif active_count == 0:
                    health_status['warnings'].append('Nessuna categoria attiva')
                    
            except Exception as e:
                health_status['checks']['categories_check'] = False
                health_status['errors'].append(f'Errore controllo categorie: {str(e)}')
            
            # Check conflitti pattern
            try:
                conflicts = categories_manager.validate_patterns_conflicts()
                health_status['checks']['no_pattern_conflicts'] = len(conflicts) == 0
                
                if conflicts:
                    health_status['warnings'].append(f'{len(conflicts)} conflitti pattern rilevati')
                    
            except Exception as e:
                health_status['checks']['conflicts_check'] = False
                health_status['errors'].append(f'Errore controllo conflitti: {str(e)}')
            
            # Determina stato generale
            if health_status['errors']:
                health_status['status'] = 'unhealthy'
            elif health_status['warnings']:
                health_status['status'] = 'degraded'
            
            return jsonify(health_status)
            
        except Exception as e:
            logger.error(f"Errore API health check: {e}")
            return jsonify({
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }), 500
    
    @app.route('/api/categories/validate', methods=['POST'])
    def validate_category():
        """API per validare una categoria"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Validazioni base
            if not data.get('name'):
                validation_result['errors'].append('Nome categoria mancante')
            
            if not data.get('display_name'):
                validation_result['errors'].append('Nome visualizzato mancante')
            
            try:
                price = float(data.get('price_per_minute', 0))
                if price < 0:
                    validation_result['errors'].append('Prezzo non può essere negativo')
                elif price > 100:
                    validation_result['warnings'].append('Prezzo molto alto')
            except (ValueError, TypeError):
                validation_result['errors'].append('Prezzo non valido')
            
            patterns = data.get('patterns', [])
            if not patterns:
                validation_result['errors'].append('Almeno un pattern è obbligatorio')
            elif len(patterns) > 20:
                validation_result['warnings'].append('Molti pattern potrebbero rallentare il matching')
            
            # Validazione markup
            custom_markup = data.get('custom_markup_percent')
            if custom_markup is not None:
                try:
                    markup = float(custom_markup)
                    if markup < -100:
                        validation_result['errors'].append('Markup non può essere inferiore a -100%')
                    elif markup > 1000:
                        validation_result['errors'].append('Markup troppo alto')
                    elif markup > 500:
                        validation_result['warnings'].append('Markup molto alto')
                except (ValueError, TypeError):
                    validation_result['errors'].append('Valore markup non valido')
            
            validation_result['valid'] = len(validation_result['errors']) == 0
            
            return jsonify({
                'success': True,
                'validation': validation_result
            })
            
        except Exception as e:
            logger.error(f"Errore API validate: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/cdr_categories_dashboard')
    def cdr_categories_dashboard():
        """Dashboard analytics CDR con statistiche categorie"""
        try:
            from routes.menu_routes import render_with_menu_context
            
            # Statistiche categorie
            categories = categories_manager.get_all_categories_with_pricing()
            stats = categories_manager.get_statistics()
            
            # Report generati
            reports = cdr_analytics_enhanced.list_generated_reports()
            
            # Statistiche sistema
            health_info = {
                'config_file_exists': categories_manager.config_file.exists(),
                'categories_count': len(categories),
                'active_categories_count': len(categories_manager.get_active_categories()),
                'global_markup_percent': categories_manager.global_markup_percent,
                'reports_count': len(reports),
                'latest_report': reports[0] if reports else None
            }
            
            return render_with_menu_context('cdr_dashboard.html', {
                'categories': categories,
                'stats': stats,
                'reports': reports,
                'health_info': health_info
            })
            
        except Exception as e:
            logger.error(f"Errore caricamento dashboard CDR: {e}")
            return render_template('error.html', 
                                error_message=f"Errore caricamento dashboard: {e}")
        
    logger.info("🔗 Route categorie CDR con supporto markup registrate con successo")
    
    # Restituisce le informazioni sulle route aggiunte
    return {
        'routes_added': [
            '/cdr_categories_edit',
            '/cdr_categories_new',
            '/cdr_categories_dashboard',
            '/api/categories',
            '/api/categories/<category_name>',
            '/api/categories/global-markup',
            '/api/categories/pricing-preview',
            '/api/categories/bulk-update-markup',
            '/api/categories/test-classification',
            '/api/categories/conflicts',
            '/api/categories/statistics',
            '/api/categories/export',
            '/api/categories/import',
            '/api/categories/reset-defaults',
            '/api/categories/health',
            '/api/categories/validate'
        ],
        'routes_count': 16
    }