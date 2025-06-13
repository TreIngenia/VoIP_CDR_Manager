#!/usr/bin/env python3
"""
Odoo Routes v18.2+ - VERSIONE COMPLETAMENTE CORRETTA E VERIFICATA
Route Flask ottimizzate per Odoo SaaS~18.2+ con gestione avanzata dei campi
"""

from flask import request, jsonify, render_template
from datetime import datetime, timedelta
import logging
from odoo_integration import create_odoo_client, InvoiceItem, InvoiceData, OdooException

logger = logging.getLogger(__name__)

def add_odoo_routes(app, secure_config):
    """
    Aggiunge tutte le route per l'integrazione Odoo 18.2+
    
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
        """Pagina principale gestione clienti Odoo 18.2+"""
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
            
            # Test connessione con info versione
            try:
                client = get_odoo_client()
                test_result = client.test_connection()
                
                if test_result['success']:
                    connection_ok = True
                    summary = client.get_partners_summary()
                    version_info = {
                        'server_version': test_result['connection_info']['server_version'],
                        'compatibility': test_result['compatibility']
                    }
                else:
                    connection_ok = False
                    summary = {'error': test_result.get('error', 'Connessione fallita')}
                    version_info = None
                    
            except Exception as e:
                connection_ok = False
                summary = {'error': str(e)}
                version_info = None
            
            return render_with_menu_context('odoo_partners.html', {
                'odoo_configured': odoo_configured,
                'connection_ok': connection_ok,
                'summary': summary,
                'version_info': version_info
            })
            
        except Exception as e:
            logger.error(f"Errore pagina clienti Odoo: {e}")
            return render_template('error.html', error_message=f"Errore: {e}")
    
    @app.route('/odoo_invoices')
    def odoo_invoices_page():
        """Pagina gestione fatture Odoo 18.2+"""
        try:
            from routes.menu_routes import render_with_menu_context
            
            return render_with_menu_context('odoo_invoices.html', {
                'page_title': 'Gestione Fatture Odoo 18.2+'
            })
            
        except Exception as e:
            logger.error(f"Errore pagina fatture Odoo: {e}")
            return render_template('error.html', error_message=f"Errore: {e}")

    # ==================== API PARTNERS ====================
    
    @app.route('/api/odoo/partners', methods=['GET'])
    def api_get_partners():
        """API per ottenere lista clienti con paginazione"""
        try:
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            search = request.args.get('search', '').strip()
            partner_type = request.args.get('type', '')
            
            offset = (page - 1) * per_page
            client = get_odoo_client()
            
            # Costruisci filtri
            filters = []
            if partner_type == 'company':
                filters.append(('is_company', '=', True))
            elif partner_type == 'person':
                filters.append(('is_company', '=', False))
            
            # Ricerca o lista normale
            if search:
                partners = client.search_partners(search, limit=per_page)
                total_count = min(len(partners) * 2, 1000)  # Stima
            else:
                partners = client.get_partners_list(limit=per_page, offset=offset, filters=filters)
                total_count = client.get_partners_count(filters=filters)
            
            # Calcola paginazione
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
            limit = min(int(data.get('limit', 20)), 100)
            
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

    @app.route('/api/odoo/partners/select', methods=['GET'])
    def api_partners_for_select2():
        """API per recuperare partner per Select2"""
        try:
            client = get_odoo_client()
            partners = client.get_all_partners_for_select()

            select2_data = []
            for partner in partners:
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
        
    @app.route('/api/odoo/products/select', methods=['GET'])
    def get_all_products_for_select():
        """API per recuperare partner per Select2"""
        try:
            client = get_odoo_client()
            products = client.get_all_products_for_select()

            select2_data = []
            for product in products:
                if isinstance(product, dict):
                    select2_data.append({
                        'id': product.get('id'),
                        'text': product.get('display_name', 'Nome non disponibile')
                    })
                else:
                    logger.warning(f"Partner non è un dict: {type(product)}")
            
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

    @app.route('/api/odoo/payment_terms/select', methods=['GET'])
    def get_all_payment_terms_for_select():
        """API per recuperare partner per Select2"""
        try:
            client = get_odoo_client()
            payment_terms = client.get_all_payment_terms_for_select()

            select2_data = []
            for payment_term in payment_terms:
                if isinstance(payment_term, dict):
                    select2_data.append({
                        'id': payment_term.get('id'),
                        'text': payment_term.get('display_name', 'Nome non disponibile')
                    })
                else:
                    logger.warning(f"Partner non è un dict: {type(payment_term)}")
            
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
    # ==================== API PRODOTTI ====================
    
    @app.route('/api/odoo/products', methods=['GET'])
    def api_get_products():
        """API per ottenere lista prodotti"""
        try:
            limit = min(int(request.args.get('limit', 50)), 200)
            search = request.args.get('search', '').strip()
            
            client = get_odoo_client()
            products = client.get_available_services(limit=limit, search_term=search)
            
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

    @app.route('/api/odoo/services/available', methods=['GET'])
    def api_get_available_services():
        """API per ottenere servizi/prodotti disponibili per fatturazione"""
        try:
            limit = min(int(request.args.get('limit', 100)), 500)
            search_term = request.args.get('search', '').strip()
            
            client = get_odoo_client()
            services = client.get_available_services(limit=limit, search_term=search_term)
            
            return jsonify({
                'success': True,
                'services': services,
                'count': len(services),
                'search_term': search_term,
                'limit': limit
            })
            
        except Exception as e:
            logger.error(f"Errore API get available services: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @app.route('/api/odoo/payment_terms', methods=['GET'])
    def api_get_payment_terms():
        """API per ottenere modalità di pagamento disponibili"""
        try:
            client = get_odoo_client()
            payment_terms = client.get_payment_terms()
            
            return jsonify({
                'success': True,
                'payment_terms': payment_terms,
                'count': len(payment_terms)
            })
            
        except Exception as e:
            logger.error(f"Errore API get payment terms: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # ==================== API FATTURE ====================
    
    @app.route('/api/odoo/invoices/create', methods=['POST'])
    def api_create_invoice():
        """API per creare fattura standard"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dati non validi'}), 400
            
            required_fields = ['partner_id', 'items']
            for field in required_fields:
                if field not in data:
                    return jsonify({'success': False, 'message': f'Campo {field} obbligatorio'}), 400
            
            # Costruisci oggetti fattura
            items = []
            for item_data in data['items']:
                item = InvoiceItem(
                    product_id=int(item_data['product_id']),
                    quantity=float(item_data['quantity']),
                    price_unit=float(item_data['price_unit']),
                    name=item_data['name']
                )
                
                # Campi aggiuntivi per 18.2+
                if 'account_id' in item_data and item_data['account_id']:
                    item.account_id = int(item_data['account_id'])
                
                if 'analytic_distribution' in item_data and item_data['analytic_distribution']:
                    item.analytic_distribution = item_data['analytic_distribution']
                
                if 'tax_ids' in item_data and item_data['tax_ids']:
                    item.tax_ids = [int(tax_id) for tax_id in item_data['tax_ids']]
                
                items.append(item)
            
            # Dati fattura
            invoice_data = InvoiceData(
                partner_id=int(data['partner_id']),
                items=items,
                due_days=data.get('due_days'),
                manual_due_date=data.get('manual_due_date'),
                reference=data.get('reference', '')
            )
            
            # Campi aggiuntivi
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
                details = client.get_invoice_details(invoice_id)
                
                return jsonify({
                    'success': True,
                    'message': 'Fattura creata con successo',
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
    
    @app.route('/api/odoo/services/invoice/create', methods=['POST'])
    def api_create_service_invoice():
        """API per creare fattura servizio"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False, 
                    'message': 'Dati JSON non validi'
                }), 400
            
            # Validazione campi obbligatori
            required_fields = ['partner_id', 'service_id', 'service_description', 'price_without_tax']
            missing_fields = [field for field in required_fields if field not in data or data[field] is None]
            
            if missing_fields:
                return jsonify({
                    'success': False,
                    'message': f'Campi obbligatori mancanti: {", ".join(missing_fields)}',
                    'required_fields': required_fields
                }), 400
            
            # Validazioni specifiche
            try:
                partner_id = int(data['partner_id'])
                service_id = int(data['service_id'])
                price_without_tax = float(data['price_without_tax'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Formati dati non validi'
                }), 400
            
            if price_without_tax <= 0:
                return jsonify({
                    'success': False,
                    'message': 'Il prezzo deve essere maggiore di 0'
                }), 400
            
            service_description = str(data['service_description']).strip()
            if not service_description:
                return jsonify({
                    'success': False,
                    'message': 'La descrizione del servizio non può essere vuota'
                }), 400
            
            # Parametri opzionali
            payment_term_id = data.get('payment_term_id')
            if payment_term_id:
                try:
                    payment_term_id = int(payment_term_id)
                except (ValueError, TypeError):
                    payment_term_id = None
            
            create_draft = bool(data.get('create_draft', False))
            
            due_days = data.get('due_days')
            if due_days:
                try:
                    due_days = int(due_days)
                    if due_days < 0:
                        due_days = None
                except (ValueError, TypeError):
                    due_days = None
            
            reference = str(data.get('reference', '')).strip()
            
            logger.info(f"Creazione fattura servizio: partner_id={partner_id}, service_id={service_id}")
            
            # Crea fattura
            client = get_odoo_client()
            
            result = client.create_service_invoice(
                partner_id=partner_id,
                service_id=service_id,
                service_description=service_description,
                price_without_tax=price_without_tax,
                payment_term_id=payment_term_id,
                create_draft=create_draft,
                due_days=due_days,
                reference=reference
            )
            
            logger.info(f"Fattura servizio creata: {result.get('invoice_id')}")
            return jsonify(result)
            
        except OdooException as e:
            logger.error(f"Errore Odoo create service invoice: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'error_code': getattr(e, 'error_code', 'ODOO_ERROR'),
                'error_type': 'ODOO_EXCEPTION'
            }), 500
            
        except Exception as e:
            logger.error(f"Errore API create service invoice: {e}")
            return jsonify({
                'success': False,
                'message': f'Errore interno: {str(e)}',
                'error_code': 'INTERNAL_ERROR',
                'error_type': 'GENERIC_EXCEPTION'
            }), 500

    @app.route('/api/odoo/services/invoice/quick', methods=['POST'])
    def api_quick_service_invoice():
        """API per fatturazione rapida con ricerca cliente"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False, 
                    'message': 'Dati JSON non validi'
                }), 400
            
            # Campi obbligatori
            partner_search = data.get('partner_search', '').strip()
            service_name = data.get('service_name', '').strip()
            service_description = data.get('service_description', '').strip()
            price_without_tax = data.get('price_without_tax')
            
            if not all([partner_search, service_name, service_description]):
                return jsonify({
                    'success': False,
                    'message': 'partner_search, service_name e service_description sono obbligatori'
                }), 400
            
            try:
                price_without_tax = float(price_without_tax)
                if price_without_tax <= 0:
                    raise ValueError("Prezzo deve essere maggiore di 0")
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'price_without_tax deve essere un numero maggiore di 0'
                }), 400
            
            create_draft = data.get('create_draft', False)
            
            client = get_odoo_client()
            
            # Cerca cliente
            partners = client.search_partners(partner_search, limit=1)
            if not partners:
                return jsonify({
                    'success': False,
                    'message': f'Nessun cliente trovato per: {partner_search}',
                    'error_code': 'PARTNER_NOT_FOUND'
                }), 404
            
            partner = partners[0]
            
            # Cerca servizio generico
            try:
                services = client.get_available_services(limit=1, search_term="servizio")
                
                if not services:
                    services = client.get_available_services(limit=1)
                
                if not services:
                    return jsonify({
                        'success': False,
                        'message': 'Nessun prodotto/servizio disponibile per la fatturazione',
                        'error_code': 'NO_SERVICE_AVAILABLE'
                    }), 500
                
                service_id = services[0]['id']
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Errore ricerca servizio: {e}',
                    'error_code': 'SERVICE_SEARCH_ERROR'
                }), 500
            
            # Crea fattura rapida
            result = client.create_service_invoice(
                partner_id=partner['id'],
                service_id=service_id,
                service_description=f"{service_name} - {service_description}",
                price_without_tax=price_without_tax,
                payment_term_id=None,
                create_draft=create_draft,
                due_days=None,
                reference=f"Fatturazione rapida - {service_name}"
            )
            
            # Aggiungi info ricerca
            result['partner_search_info'] = {
                'search_term': partner_search,
                'found_partner': partner['display_name'],
                'partner_email': partner.get('email', '')
            }
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Errore API quick service invoice: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @app.route('/api/odoo/services/invoice/validate', methods=['POST'])
    def api_validate_service_invoice_data():
        """API per validare dati prima della creazione fattura"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False, 
                    'message': 'Dati JSON non validi'
                }), 400
            
            # Validazione campi obbligatori
            required_fields = ['partner_id', 'service_id', 'service_description', 'price_without_tax']
            missing_fields = [field for field in required_fields if field not in data or data[field] is None]
            
            if missing_fields:
                return jsonify({
                    'success': False,
                    'message': f'Campi obbligatori mancanti: {", ".join(missing_fields)}',
                    'missing_fields': missing_fields
                }), 400
            
            client = get_odoo_client()
            
            # Verifica esistenza partner
            partner_id = int(data['partner_id'])
            partner_data = client.get_partner_by_id(partner_id)
            if not partner_data:
                return jsonify({
                    'success': False,
                    'message': f'Cliente {partner_id} non trovato',
                    'error_code': 'PARTNER_NOT_FOUND'
                }), 404
            
            # Verifica esistenza servizio
            service_id = int(data['service_id'])
            try:
                service_data = client.execute(
                    'product.product', 
                    'read', 
                    [service_id],
                    fields=['id', 'name', 'sale_ok', 'list_price', 'taxes_id']
                )
                
                if not service_data:
                    return jsonify({
                        'success': False,
                        'message': f'Servizio {service_id} non trovato',
                        'error_code': 'SERVICE_NOT_FOUND'
                    }), 404
                
                service = service_data[0]
                if not service.get('sale_ok', False):
                    return jsonify({
                        'success': False,
                        'message': f'Servizio {service_id} non è vendibile',
                        'error_code': 'SERVICE_NOT_SALEABLE'
                    }), 400
                    
            except Exception:
                return jsonify({
                    'success': False,
                    'message': f'Errore verifica servizio {service_id}',
                    'error_code': 'SERVICE_VALIDATION_ERROR'
                }), 500
            
            # Calcola anteprima
            price_without_tax = float(data['price_without_tax'])
            create_draft = data.get('create_draft', False)
            due_days = data.get('due_days', 30)
            
            estimated_due_date = (datetime.now() + timedelta(days=due_days)).strftime('%Y-%m-%d')
            
            # Calcola tasse
            tax_ids = service.get('taxes_id', [])
            estimated_tax_rate = 0.22 if tax_ids else 0.0
            estimated_tax = price_without_tax * estimated_tax_rate
            estimated_total = price_without_tax + estimated_tax
            
            return jsonify({
                'success': True,
                'validation': 'passed',
                'preview': {
                    'partner_info': {
                        'id': partner_data['id'],
                        'name': partner_data['display_name'],
                        'email': partner_data.get('email', ''),
                        'vat': partner_data.get('vat', '')
                    },
                    'service_info': {
                        'id': service['id'],
                        'name': service['name'],
                        'description': data['service_description'],
                        'list_price': service.get('list_price', 0.0),
                        'custom_price': price_without_tax,
                        'has_taxes': len(tax_ids) > 0
                    },
                    'amounts': {
                        'price_without_tax': price_without_tax,
                        'estimated_tax': round(estimated_tax, 2),
                        'estimated_total': round(estimated_total, 2),
                        'tax_rate': estimated_tax_rate,
                        'tax_note': 'Stima basata su configurazione servizio'
                    },
                    'invoice_type': 'Bozza' if create_draft else 'Confermata',
                    'estimated_due_date': estimated_due_date,
                    'creation_date': datetime.now().strftime('%Y-%m-%d')
                }
            })
            
        except Exception as e:
            logger.error(f"Errore API validate service invoice: {e}")
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

    @app.route('/api/odoo/invoices/bulk_create', methods=['POST'])
    def api_bulk_create_invoices():
        """API per creazione fatture multiple"""
        try:
            data = request.get_json()
            if not data or 'invoices' not in data:
                return jsonify({'success': False, 'message': 'Dati fatture non validi'}), 400
            
            invoices_data = data['invoices']
            auto_confirm = data.get('auto_confirm', True)
            
            # Limite di sicurezza
            if len(invoices_data) > 50:
                return jsonify({
                    'success': False,
                    'message': 'Limite massimo 50 fatture per operazione bulk'
                }), 400
            
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
                            name=item_data['name']
                        )
                        
                        # Gestione campi 18.2+
                        if 'analytic_distribution' in item_data:
                            item.analytic_distribution = item_data['analytic_distribution']
                        
                        if 'tax_ids' in item_data:
                            item.tax_ids = item_data['tax_ids']
                        
                        items.append(item)
                    
                    invoice_obj = InvoiceData(
                        partner_id=int(invoice_data['partner_id']),
                        items=items,
                        due_days=invoice_data.get('due_days', 30),
                        reference=invoice_data.get('reference', f'Fattura bulk #{i+1}'),
                        payment_term_id=invoice_data.get('payment_term_id')
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
                'successful_count': successful,
                'failed_count': len(results) - successful
            })
            
        except Exception as e:
            logger.error(f"Errore API bulk create invoices: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # ==================== API UTILITARIE ====================
    
    @app.route('/api/odoo/test_connection', methods=['GET'])
    def api_test_odoo_connection():
        """API per testare connessione Odoo"""
        try:
            client = get_odoo_client()
            test_result = client.test_connection()
            
            if test_result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Connessione Odoo funzionante',
                    'connection_info': test_result['connection_info'],
                    'stats': test_result['stats'],
                    'compatibility': test_result['compatibility']
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
        """API per ottenere informazioni azienda"""
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
            
            # Crea fattura con campi corretti
            items = [
                InvoiceItem(
                    product_id=product_id,
                    quantity=quantity,
                    price_unit=price_unit,
                    name=service_name
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

    # ==================== API DEBUG ====================
    
    @app.route('/api/odoo/debug/model_fields/<model_name>', methods=['GET'])
    def api_debug_model_fields(model_name):
        """API di debug per verificare campi disponibili in un modello"""
        try:
            # Modelli consentiti per sicurezza
            allowed_models = [
                'res.partner', 'account.move', 'account.move.line', 
                'product.product', 'account.payment.term'
            ]
            
            if model_name not in allowed_models:
                return jsonify({
                    'success': False,
                    'message': f'Modello {model_name} non consentito',
                    'allowed_models': allowed_models
                }), 400
            
            client = get_odoo_client()
            result = client.debug_model_fields(model_name)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @app.route('/api/odoo/debug/compatibility_check', methods=['GET'])
    def api_debug_compatibility_check():
        """Verifica completa compatibilità per Odoo 18.2+"""
        try:
            client = get_odoo_client()
            
            # Test connessione
            connection_test = client.test_connection()
            
            # Test debug modelli principali
            models_to_test = ['res.partner', 'account.move', 'account.move.line']
            model_results = {}
            
            for model in models_to_test:
                try:
                    model_results[model] = client.debug_model_fields(model)
                except Exception as e:
                    model_results[model] = {'success': False, 'error': str(e)}
            
            # Test dati di esempio
            try:
                test_partners = client.get_partners_list(limit=1)
                test_services = client.get_available_services(limit=1)
                data_test = {
                    'partners_available': len(test_partners) > 0,
                    'services_available': len(test_services) > 0
                }
            except Exception as e:
                data_test = {'error': str(e)}
            
            # Calcola punteggio compatibilità
            score = 0
            max_score = 100
            issues = []
            
            if connection_test['success']:
                score += 30
            else:
                issues.append('Connessione fallita')
            
            # Verifica campi critici
            critical_fields = {
                'res.partner': ['mobile', 'customer_rank'],
                'account.move': ['invoice_payment_term_id'],
                'account.move.line': ['analytic_distribution']
            }
            
            for model, fields in critical_fields.items():
                if model in model_results and model_results[model]['success']:
                    score += 15
                    for field in fields:
                        if field in model_results[model].get('key_fields', []):
                            score += 5
                        else:
                            issues.append(f'Campo {field} non trovato in {model}')
                else:
                    issues.append(f'Impossibile verificare modello {model}')
            
            if data_test.get('partners_available') and data_test.get('services_available'):
                score += 20
            else:
                issues.append('Dati di test non disponibili')
            
            # Livello compatibilità
            if score >= 90:
                level = 'EXCELLENT'
                message = 'Compatibilità eccellente con Odoo 18.2+'
            elif score >= 70:
                level = 'GOOD'
                message = 'Buona compatibilità con Odoo 18.2+'
            elif score >= 50:
                level = 'FAIR'
                message = 'Compatibilità sufficiente, alcuni problemi riscontrati'
            else:
                level = 'POOR'
                message = 'Compatibilità insufficiente, richiede interventi'
            
            return jsonify({
                'success': True,
                'compatibility_report': {
                    'score': score,
                    'max_score': max_score,
                    'level': level,
                    'message': message,
                    'issues': issues,
                    'odoo_version': connection_test.get('connection_info', {}).get('server_version', 'Unknown'),
                    'test_results': {
                        'connection': connection_test['success'],
                        'models': model_results,
                        'data_availability': data_test
                    }
                },
                'recommendations': [
                    'Verificare configurazione per campi mancanti',
                    'Testare creazione fattura con dati reali',
                    'Monitorare log per errori di compatibilità',
                    'Aggiornare codice per nuovi campi 18.2+'
                ],
                'generated_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Errore compatibility check: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'compatibility_report': {
                    'score': 0,
                    'level': 'ERROR',
                    'message': f'Errore durante verifica: {e}'
                }
            }), 500

    @app.route('/api/odoo/debug/test_data', methods=['GET'])
    def api_get_test_data():
        """API per ottenere primi partner e servizi disponibili per test"""
        try:
            client = get_odoo_client()
            
            # Primi 5 partner
            partners = client.get_partners_list(limit=5)
            
            # Primi 5 servizi
            services = client.get_available_services(limit=5)
            
            return jsonify({
                'success': True,
                'test_data': {
                    'partners': partners,
                    'services': services,
                    'partner_count': len(partners),
                    'service_count': len(services)
                },
                'message': 'Usa questi ID per testare la creazione fatture'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @app.route('/api/odoo/test/create_sample_invoice', methods=['POST'])
    def api_test_create_sample_invoice():
        """Crea fattura di test per verificare funzionamento"""
        try:
            data = request.get_json() or {}
            
            client = get_odoo_client()
            
            # Usa dati forniti o primi disponibili
            partner_id = data.get('partner_id')
            service_id = data.get('service_id')
            
            if not partner_id:
                partners = client.get_partners_list(limit=1)
                if not partners:
                    return jsonify({
                        'success': False,
                        'message': 'Nessun partner disponibile per test'
                    }), 400
                partner_id = partners[0]['id']
            
            if not service_id:
                services = client.get_available_services(limit=1)
                if not services:
                    return jsonify({
                        'success': False,
                        'message': 'Nessun servizio disponibile per test'
                    }), 400
                service_id = services[0]['id']
            
            # Crea fattura di test (sempre bozza)
            result = client.create_service_invoice(
                partner_id=partner_id,
                service_id=service_id,
                service_description="Fattura di test per verifica compatibilità Odoo 18.2+",
                price_without_tax=1.00,  # Importo simbolico
                payment_term_id=None,
                create_draft=True,  # Sempre bozza per test
                due_days=30,
                reference="TEST-18.2-COMPATIBILITY"
            )
            
            return jsonify({
                'success': True,
                'message': 'Fattura di test creata con successo',
                'test_result': result,
                'test_parameters': {
                    'partner_id': partner_id,
                    'service_id': service_id,
                    'auto_selected': not data.get('partner_id') or not data.get('service_id')
                },
                'note': 'Fattura creata in bozza per test - eliminare se non necessaria'
            })
            
        except Exception as e:
            logger.error(f"Errore test create sample invoice: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'error_type': 'TEST_INVOICE_ERROR'
            }), 500

    # ==================== GESTIONE ERRORI ====================
    
    @app.errorhandler(OdooException)
    def handle_odoo_exception(e):
        """Gestore errori specifici Odoo"""
        logger.error(f"Errore Odoo: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'error_code': getattr(e, 'error_code', 'ODOO_ERROR'),
            'error_type': 'ODOO_EXCEPTION'
        }), 500

    # ==================== ROUTE INFO ====================
    
    @app.route('/api/odoo/info', methods=['GET'])
    def api_odoo_info():
        """Informazioni generali sull'integrazione Odoo"""
        try:
            client = get_odoo_client()
            test_result = client.test_connection()
            
            if test_result['success']:
                info = {
                    'integration_version': '18.2+',
                    'odoo_version': test_result['connection_info']['server_version'],
                    'database': test_result['connection_info']['database'],
                    'company': test_result['connection_info']['company_name'],
                    'user': test_result['connection_info']['user_name'],
                    'statistics': test_result['stats'],
                    'compatibility': test_result['compatibility'],
                    'features': {
                        'partner_management': True,
                        'invoice_creation': True,
                        'service_invoicing': True,
                        'bulk_operations': True,
                        'mobile_field_support': test_result['compatibility'].get('mobile_field_available', False),
                        'analytic_distribution': test_result['compatibility'].get('analytic_distribution_available', False)
                    },
                    'endpoints': {
                        'partners': '/api/odoo/partners',
                        'invoices': '/api/odoo/invoices',
                        'services': '/api/odoo/services',
                        'debug': '/api/odoo/debug'
                    }
                }
            else:
                info = {
                    'integration_version': '18.2+',
                    'status': 'disconnected',
                    'error': test_result['error']
                }
            
            return jsonify({
                'success': test_result['success'],
                'info': info
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'info': {
                    'integration_version': '18.2+',
                    'status': 'error',
                    'error': str(e)
                }
            }), 500

    logger.info("🚀 Route Odoo 18.2+ registrate con successo")
    
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
            # API Prodotti/Servizi
            '/api/odoo/products',
            '/api/odoo/services/available',
            '/api/odoo/payment_terms',
            # API Fatture
            '/api/odoo/invoices/create',
            '/api/odoo/services/invoice/create',
            '/api/odoo/services/invoice/quick',
            '/api/odoo/services/invoice/validate',
            '/api/odoo/invoices/<int:invoice_id>',
            '/api/odoo/invoices/<int:invoice_id>/confirm',
            '/api/odoo/invoices/bulk_create',
            # API Utilitarie
            '/api/odoo/test_connection',
            '/api/odoo/company_info',
            '/api/odoo/quick_invoice',
            '/api/odoo/info',
            # API Debug
            '/api/odoo/debug/model_fields/<model_name>',
            '/api/odoo/debug/compatibility_check',
            '/api/odoo/debug/test_data',
            '/api/odoo/test/create_sample_invoice'
        ],
        'routes_count': 23,
        'odoo_version': '18.2+',
        'features': {
            'dynamic_field_detection': True,
            'mobile_field_support': True,
            'analytic_distribution': True,
            'bulk_operations': True,
            'advanced_debugging': True,
            'comprehensive_validation': True
        }
    }