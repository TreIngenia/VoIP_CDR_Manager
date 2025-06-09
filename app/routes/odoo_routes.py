#!/usr/bin/env python3
"""
Odoo Routes - VERSIONE CORRETTA per integrazione con odoo_integration.py
Route Flask ottimizzate per Odoo 18 con correzioni di compatibilità
"""

from flask import request, jsonify, render_template
from datetime import datetime
import logging
from odoo_integration import create_odoo_client, InvoiceItem, InvoiceData, OdooException

logger = logging.getLogger(__name__)

def add_odoo_routes(app, secure_config):
    """
    Aggiunge tutte le route per l'integrazione Odoo
    
    Args:
        app: Istanza Flask
        secure_config: Configurazione sicura con credenziali Odoo
    """
    
    def get_odoo_client():
        """Helper per creare client Odoo con configurazione"""
        try:
            config = secure_config.get_config()
            odoo_config = {
                'ODOO_URL': config.get('ODOO_URL', ''),
                'ODOO_DB': config.get('ODOO_DB', ''),
                'ODOO_USERNAME': config.get('ODOO_USERNAME', ''),
                'ODOO_API_KEY': config.get('ODOO_API_KEY', '')
            }
            
            # Verifica configurazione
            missing = [k for k, v in odoo_config.items() if not v]
            if missing:
                raise Exception(f"Configurazione Odoo incompleta: {missing}")
            
            return create_odoo_client(odoo_config)
            
        except Exception as e:
            logger.error(f"Errore creazione client Odoo: {e}")
            raise

    # ==================== PAGINE WEB ====================
    
    @app.route('/odoo_partners')
    def odoo_partners_page():
        """Pagina principale gestione clienti Odoo"""
        try:
            from routes.menu_routes import render_with_menu_context
            
            # Verifica configurazione
            config = secure_config.get_config()
            odoo_configured = all([
                config.get('ODOO_URL'),
                config.get('ODOO_DB'), 
                config.get('ODOO_USERNAME'),
                config.get('ODOO_API_KEY')
            ])
            
            if not odoo_configured:
                return render_with_menu_context('odoo_partners.html', {
                    'odoo_configured': False,
                    'error_message': 'Configurazione Odoo incompleta. Verificare file .env'
                })
            
            # Test connessione rapida usando il nuovo metodo
            try:
                client = get_odoo_client()
                # 🔧 CORREZIONE: Usa test_connection invece di get_partners_summary per il test iniziale
                test_result = client.test_connection()
                if test_result['success']:
                    connection_ok = True
                    # Dopo aver verificato la connessione, ottieni il summary
                    summary = client.get_partners_summary()
                else:
                    connection_ok = False
                    summary = {'error': test_result.get('error', 'Connessione fallita')}
            except Exception as e:
                connection_ok = False
                summary = {'error': str(e)}
            
            return render_with_menu_context('odoo_partners.html', {
                'odoo_configured': odoo_configured,
                'connection_ok': connection_ok,
                'summary': summary
            })
            
        except Exception as e:
            logger.error(f"Errore pagina clienti Odoo: {e}")
            return render_template('error.html', error_message=f"Errore: {e}")
    
    @app.route('/odoo_invoices')
    def odoo_invoices_page():
        """Pagina gestione fatture Odoo"""
        try:
            from routes.menu_routes import render_with_menu_context
            
            return render_with_menu_context('odoo_invoices.html', {
                'page_title': 'Gestione Fatture Odoo'
            })
            
        except Exception as e:
            logger.error(f"Errore pagina fatture Odoo: {e}")
            return render_template('error.html', error_message=f"Errore: {e}")

    # ==================== API PARTNERS ====================
    
    @app.route('/api/odoo/partners', methods=['GET'])
    def api_get_partners():
        """API per ottenere lista clienti con paginazione"""
        try:
            # Parametri query
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            search = request.args.get('search', '').strip()
            partner_type = request.args.get('type', '')  # 'company', 'person', 'all'
            
            # Calcola offset
            offset = (page - 1) * per_page
            
            client = get_odoo_client()
            
            # 🔧 CORREZIONE: Costruisci filtri usando il formato corretto di Odoo domain
            filters = []
            
            # Filtro per tipo
            if partner_type == 'company':
                filters.append(('is_company', '=', True))
            elif partner_type == 'person':
                filters.append(('is_company', '=', False))
            
            # Ricerca o lista normale
            if search:
                partners = client.search_partners(search, limit=per_page)
                total_count = len(partners)  # Approssimazione per ricerca
            else:
                partners = client.get_partners_list(limit=per_page, offset=offset, filters=filters)
                total_count = client.get_partners_count(filters=filters)
            
            # Calcola info paginazione
            total_pages = (total_count + per_page - 1) // per_page
            has_next = page < total_pages
            has_prev = page > 1
            
            return jsonify({
                'success': True,
                'partners': partners,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_prev': has_prev
                },
                'search_term': search,
                'partner_type': partner_type
            })
            
        except Exception as e:
            logger.error(f"Errore API get partners: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'error_type': 'PARTNERS_API_ERROR'
            }), 500
    
    @app.route('/api/odoo/partners/<int:partner_id>', methods=['GET'])
    def api_get_partner_details(partner_id):
        """API per dettagli specifici partner"""
        try:
            client = get_odoo_client()
            partner = client.get_partner_by_id(partner_id)
            
            if not partner:
                return jsonify({
                    'success': False,
                    'message': f'Partner {partner_id} non trovato'
                }), 404
            
            return jsonify({
                'success': True,
                'partner': partner
            })
            
        except Exception as e:
            logger.error(f"Errore API get partner {partner_id}: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    @app.route('/api/odoo/partners/summary', methods=['GET'])
    def api_partners_summary():
        """API per statistiche riassuntive clienti"""
        try:
            client = get_odoo_client()
            summary = client.get_partners_summary()
            
            return jsonify({
                'success': True,
                'summary': summary
            })
            
        except Exception as e:
            logger.error(f"Errore API partners summary: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    @app.route('/api/odoo/partners/search', methods=['POST'])
    def api_search_partners():
        """API per ricerca avanzata clienti"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            search_term = data.get('search_term', '').strip()
            limit = int(data.get('limit', 20))
            
            if not search_term:
                return jsonify({'success': False, 'message': 'Termine di ricerca obbligatorio'}), 400
            
            client = get_odoo_client()
            partners = client.search_partners(search_term, limit=limit)
            
            return jsonify({
                'success': True,
                'partners': partners,
                'search_term': search_term,
                'results_count': len(partners)
            })
            
        except Exception as e:
            logger.error(f"Errore API search partners: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # ==================== API PRODOTTI ====================
    
    @app.route('/api/odoo/products', methods=['GET'])
    def api_get_products():
        """🆕 API per ottenere lista prodotti"""
        try:
            limit = int(request.args.get('limit', 50))
            search = request.args.get('search', '').strip()
            
            client = get_odoo_client()
            
            # Costruisci filtri se c'è ricerca
            filters = []
            if search:
                filters.append(('name', 'ilike', search))
            
            products = client.get_products_list(limit=limit, filters=filters)
            
            return jsonify({
                'success': True,
                'products': products,
                'search_term': search,
                'results_count': len(products)
            })
            
        except Exception as e:
            logger.error(f"Errore API get products: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # ==================== API FATTURE ====================
    
    @app.route('/api/odoo/invoices/create', methods=['POST'])
    def api_create_invoice():
        """API per creare fattura con supporto campi Odoo 18"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            # Validazione dati richiesti
            required_fields = ['partner_id', 'items']
            for field in required_fields:
                if field not in data:
                    return jsonify({'success': False, 'message': f'Campo {field} obbligatorio'}), 400
            
            # 🔧 CORREZIONE: Costruisci oggetti fattura con supporto campi Odoo 18
            items = []
            for item_data in data['items']:
                # Campi base obbligatori
                item = InvoiceItem(
                    product_id=int(item_data['product_id']),
                    quantity=float(item_data['quantity']),
                    price_unit=float(item_data['price_unit']),
                    name=item_data['name'],
                    description=item_data.get('description', '')
                )
                
                # 🆕 Campi aggiuntivi per Odoo 18
                if 'account_id' in item_data and item_data['account_id']:
                    item.account_id = int(item_data['account_id'])
                
                if 'analytic_account_id' in item_data and item_data['analytic_account_id']:
                    item.analytic_account_id = int(item_data['analytic_account_id'])
                
                if 'tax_ids' in item_data and item_data['tax_ids']:
                    item.tax_ids = [int(tax_id) for tax_id in item_data['tax_ids']]
                
                items.append(item)
            
            # 🔧 CORREZIONE: InvoiceData con campi Odoo 18
            invoice_data = InvoiceData(
                partner_id=int(data['partner_id']),
                items=items,
                due_days=data.get('due_days'),
                manual_due_date=data.get('manual_due_date'),
                reference=data.get('reference', '')
            )
            
            # 🆕 Campi aggiuntivi Odoo 18
            if 'journal_id' in data and data['journal_id']:
                invoice_data.journal_id = int(data['journal_id'])
            
            if 'payment_term_id' in data and data['payment_term_id']:
                invoice_data.payment_term_id = int(data['payment_term_id'])
            
            if 'currency_id' in data and data['currency_id']:
                invoice_data.currency_id = int(data['currency_id'])
            
            if 'company_id' in data and data['company_id']:
                invoice_data.company_id = int(data['company_id'])
            
            # Crea fattura
            client = get_odoo_client()
            auto_confirm = data.get('auto_confirm', True)
            
            if auto_confirm:
                invoice_id = client.create_and_confirm_invoice(invoice_data)
            else:
                invoice_id = client.create_invoice(invoice_data)
            
            if invoice_id:
                # Ottieni dettagli fattura creata
                details = client.get_invoice_details(invoice_id)
                
                return jsonify({
                    'success': True,
                    'message': f'Fattura creata con successo',
                    'invoice_id': invoice_id,
                    'invoice_details': details
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Errore nella creazione fattura'
                }), 500
                
        except Exception as e:
            logger.error(f"Errore API create invoice: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    @app.route('/api/odoo/invoices/<int:invoice_id>', methods=['GET'])
    def api_get_invoice_details(invoice_id):
        """API per dettagli fattura"""
        try:
            client = get_odoo_client()
            details = client.get_invoice_details(invoice_id)
            
            if not details:
                return jsonify({
                    'success': False,
                    'message': f'Fattura {invoice_id} non trovata'
                }), 404
            
            return jsonify({
                'success': True,
                'invoice': details
            })
            
        except Exception as e:
            logger.error(f"Errore API get invoice {invoice_id}: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    @app.route('/api/odoo/invoices/<int:invoice_id>/confirm', methods=['POST'])
    def api_confirm_invoice(invoice_id):
        """API per confermare fattura"""
        try:
            client = get_odoo_client()
            success = client.confirm_invoice(invoice_id)
            
            if success:
                details = client.get_invoice_details(invoice_id)
                return jsonify({
                    'success': True,
                    'message': f'Fattura {invoice_id} confermata',
                    'invoice_details': details
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Errore conferma fattura {invoice_id}'
                }), 500
                
        except Exception as e:
            logger.error(f"Errore API confirm invoice {invoice_id}: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # ==================== API UTILITARIE ====================
    
    @app.route('/api/odoo/test_connection', methods=['GET'])
    def api_test_odoo_connection():
        """🔧 API corretta per testare connessione Odoo"""
        try:
            client = get_odoo_client()
            
            # 🔧 CORREZIONE: Usa il metodo test_connection specifico
            test_result = client.test_connection()
            
            if test_result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Connessione Odoo funzionante',
                    'connection_info': test_result['connection_info'],
                    'stats': test_result['stats']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Errore connessione: {test_result["error"]}',
                    'error_type': 'CONNECTION_ERROR'
                }), 500
            
        except Exception as e:
            logger.error(f"Errore test connessione Odoo: {e}")
            return jsonify({
                'success': False,
                'message': f'Errore connessione: {str(e)}',
                'error_type': 'CONNECTION_ERROR'
            }), 500
    
    @app.route('/api/odoo/company_info', methods=['GET'])
    def api_get_company_info():
        """🆕 API per ottenere informazioni azienda"""
        try:
            client = get_odoo_client()
            company_info = client.get_company_info()
            
            return jsonify({
                'success': True,
                'company_info': company_info
            })
            
        except Exception as e:
            logger.error(f"Errore API company info: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    @app.route('/api/odoo/quick_invoice', methods=['POST'])
    def api_quick_invoice():
        """API per fattura rapida da partner search"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            # Parametri richiesti
            partner_search = data.get('partner_search', '').strip()
            service_name = data.get('service_name', 'Servizio generico')
            quantity = float(data.get('quantity', 1))
            price_unit = float(data.get('price_unit', 0))
            product_id = int(data.get('product_id', 1))  # ID prodotto generico
            
            if not partner_search:
                return jsonify({'success': False, 'message': 'Partner search obbligatorio'}), 400
            
            if price_unit <= 0:
                return jsonify({'success': False, 'message': 'Prezzo deve essere maggiore di 0'}), 400
            
            client = get_odoo_client()
            
            # Cerca partner
            partners = client.search_partners(partner_search, limit=1)
            if not partners:
                return jsonify({
                    'success': False,
                    'message': f'Nessun partner trovato per: {partner_search}'
                }), 404
            
            partner = partners[0]
            
            # 🔧 CORREZIONE: Crea fattura con campi corretti
            items = [
                InvoiceItem(
                    product_id=product_id,
                    quantity=quantity,
                    price_unit=price_unit,
                    name=service_name,
                    description=f'Fatturazione per {partner["display_name"]}'
                )
            ]
            
            invoice_data = InvoiceData(
                partner_id=partner['id'],
                items=items,
                due_days=30,
                reference=f'Fattura rapida - {datetime.now().strftime("%Y-%m-%d")}'
            )
            
            invoice_id = client.create_and_confirm_invoice(invoice_data)
            
            if invoice_id:
                details = client.get_invoice_details(invoice_id)
                
                return jsonify({
                    'success': True,
                    'message': f'Fattura creata per {partner["display_name"]}',
                    'partner': partner,
                    'invoice_id': invoice_id,
                    'invoice_details': details
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Errore creazione fattura'
                }), 500
                
        except Exception as e:
            logger.error(f"Errore API quick invoice: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # 🆕 API per gestione avanzata fatture bulk
    @app.route('/api/odoo/invoices/bulk_create', methods=['POST'])
    def api_bulk_create_invoices():
        """API per creazione fatture multiple"""
        try:
            data = request.get_json()
            if not data or 'invoices' not in data:
                return jsonify({'success': False, 'message': 'Dati fatture non validi'}), 400
            
            invoices_data = data['invoices']
            auto_confirm = data.get('auto_confirm', True)
            
            client = get_odoo_client()
            results = []
            
            for i, invoice_data in enumerate(invoices_data):
                try:
                    # Costruisci oggetti per ogni fattura
                    items = []
                    for item_data in invoice_data['items']:
                        item = InvoiceItem(
                            product_id=int(item_data['product_id']),
                            quantity=float(item_data['quantity']),
                            price_unit=float(item_data['price_unit']),
                            name=item_data['name'],
                            description=item_data.get('description', '')
                        )
                        items.append(item)
                    
                    invoice_obj = InvoiceData(
                        partner_id=int(invoice_data['partner_id']),
                        items=items,
                        due_days=invoice_data.get('due_days', 30),
                        reference=invoice_data.get('reference', f'Fattura bulk #{i+1}')
                    )
                    
                    # Crea fattura
                    if auto_confirm:
                        invoice_id = client.create_and_confirm_invoice(invoice_obj)
                    else:
                        invoice_id = client.create_invoice(invoice_obj)
                    
                    if invoice_id:
                        details = client.get_invoice_details(invoice_id)
                        results.append({
                            'success': True,
                            'invoice_id': invoice_id,
                            'partner_id': invoice_data['partner_id'],
                            'details': details
                        })
                    else:
                        results.append({
                            'success': False,
                            'partner_id': invoice_data['partner_id'],
                            'error': 'Errore creazione fattura'
                        })
                        
                except Exception as e:
                    results.append({
                        'success': False,
                        'partner_id': invoice_data.get('partner_id', 'unknown'),
                        'error': str(e)
                    })
            
            successful = sum(1 for r in results if r['success'])
            
            return jsonify({
                'success': True,
                'message': f'{successful}/{len(results)} fatture create con successo',
                'results': results,
                'total_processed': len(results),
                'successful_count': successful
            })
            
        except Exception as e:
            logger.error(f"Errore API bulk create invoices: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @app.route('/api/odoo/partners/select', methods=['GET'])
    def get_partners_for_select2():
        """API per recuperare tutti i partner per Select2"""
        try:
            
            # Recupera partner per Select2
            odoo_client  = get_odoo_client()
            partners = odoo_client.get_all_partners_for_select()

            # Formato per Select2
            select2_data = []
            for partner in partners:
                # Verifica che partner sia un dict
                if isinstance(partner, dict):
                    select2_data.append({
                        'id': partner.get('commercial_partner_id'),
                        'text': partner.get('display_name', 'Nome non disponibile')
                    })
                else:
                    logger.warning(f"Partner non è un dict: {type(partner)}")
            
            return jsonify({
                'success': True,
                'results': select2_data,
                'total': len(select2_data)
            })
        except Exception as e:
            logger.error(f"Errore API partners Select2: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'results': []
            }), 500
        
    logger.info("🔗 Route Odoo corrette registrate con successo")
    
    return {
        'routes_added': [
            # Pagine
            '/odoo_partners',
            '/odoo_invoices',
            # API Partners
            '/api/odoo/partners',
            '/api/odoo/partners/<int:partner_id>',
            '/api/odoo/partners/summary',
            '/api/odoo/partners/search',
            '/api/odoo/partners/select',
            # API Prodotti (nuovo)
            '/api/odoo/products',
            # API Fatture
            '/api/odoo/invoices/create',
            '/api/odoo/invoices/<int:invoice_id>',
            '/api/odoo/invoices/<int:invoice_id>/confirm',
            '/api/odoo/invoices/bulk_create',
            # API Utilitarie
            '/api/odoo/test_connection',
            '/api/odoo/company_info',
            '/api/odoo/quick_invoice'
        ],
        'routes_count': 16
    }