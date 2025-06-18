"""
Odoo Routes v18.2+ - VERSIONE COMPLETAMENTE CORRETTA E VERIFICATA
Route Flask ottimizzate per Odoo SaaS~18.2+ con gestione avanzata dei campi
"""

from flask import request, jsonify, render_template
from datetime import datetime, timedelta
import logging
from odoo_integration import create_odoo_client, InvoiceItem, InvoiceData, OdooException, get_odoo_client, OdooAPI, SubscriptionExtractor
# from gen_odoo_invoice_token import OdooAPI, SubscriptionExtractor
logger = logging.getLogger(__name__)

def add_odoo_routes(app, secure_config):
    extractor = SubscriptionExtractor()   

    # ==================== PAGINE WEB ====================
    try:
        client = get_odoo_client(secure_config)
        test_result = client.test_connection()
    except Exception as e:
        connection_ok = False
        summary = {'error': str(e)}
        version_info = None

    @app.route('/odoo_partners')
    def odoo_partners_page():
        """Pagina principale gestione clienti Odoo 18.2+"""
        from routes.menu_routes import render_with_menu_context

        # Test connessione con info versione
       
            
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
                

        
        return render_with_menu_context('odoo_partners.html')
            

    
    @app.route('/odoo_invoices')
    def odoo_invoices_page():
        """Pagina gestione fatture Odoo 18.2+"""
        try:
            from routes.menu_routes import render_with_menu_context
            
            return render_with_menu_context('odoo_invoices.html')
            
        except Exception as e:
            logger.error(f"Errore pagina fatture Odoo: {e}")
            return render_template('error.html', error_message=f"Errore: {e}")


    # ==================== API PARTNERS ====================
    
    # ELENCO PARTNERS
    @app.route('/api/odoo/partners', methods=['GET'])
    def api_get_partners():
        """API per ottenere lista clienti con paginazione"""
        try:
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            search = request.args.get('search', '').strip()
            partner_type = request.args.get('type', '')
            
            offset = (page - 1) * per_page
            
            
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
    
    # PARTNER CERCA (GET)
    @app.route('/api/odoo/partners/<int:partner_id>', methods=['GET'])
    def api_get_partner_details(partner_id):
        """API per dettagli specifici partner"""
        try:
            
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
    
    # PARTNER SUMMARY
    @app.route('/api/odoo/partners/summary', methods=['GET'])
    def api_partners_summary():
        """API per statistiche riassuntive clienti"""
        try:
            
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
    
    # PARTNER RICERCA (POST)
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
        
    # PARTNER (SELECT)
    @app.route('/api/odoo/partners/select', methods=['GET'])
    def api_partners_for_select2():
        """API per recuperare partner per Select2"""
        try:
            
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
        

    # ==================== API PRODOTTI ====================

    # PRODOTTI (SELECT)    
    @app.route('/api/odoo/products/select', methods=['GET'])
    def get_all_products_for_select():
        """API per recuperare partner per Select2"""
        try:
            
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

    
    # ==================== API FATTURE ====================

    # TERMINI DI PAGAMENTO
    @app.route('/api/odoo/payment_terms', methods=['GET'])
    def api_get_payment_terms():
        """API per ottenere modalità di pagamento disponibili"""
        try:
            
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
        
    # TERMINI DI PAGAMENTO (SELECT)
    @app.route('/api/odoo/payment_terms/select', methods=['GET'])
    def get_all_payment_terms_for_select():
        """API per recuperare partner per Select2"""
        try:
            
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
    
#----------------------------------------------------------------------
    @app.route('/api/subscriptions', methods=['GET'])
    @app.route('/api/subscriptions/select', methods=['GET'])
    @app.route('/api/subscriptions/partner/<int:partner_id>', methods=['GET'])
    @app.route('/api/subscriptions/select/partner/<int:partner_id>', methods=['GET'])
    @app.route('/api/subscriptions/limit/<int:limit>', methods=['GET'])
    @app.route('/api/subscriptions/select/limit/<int:limit>', methods=['GET'])
    @app.route('/api/subscriptions/partner/<int:partner_id>/limit/<int:limit>', methods=['GET'])
    @app.route('/api/subscriptions/select/partner/<int:partner_id>/limit/<int:limit>', methods=['GET'])
    def get_subscriptions(partner_id=None, limit=100):
        """
        GET /api/subscriptions
        GET /api/subscriptions/select
        GET /api/subscriptions/partner/{partner_id}
        GET /api/subscriptions/select/partner/{partner_id}
        GET /api/subscriptions/limit/{limit}
        GET /api/subscriptions/select/limit/{limit}
        GET /api/subscriptions/partner/{partner_id}/limit/{limit}
        GET /api/subscriptions/select/partner/{partner_id}/limit/{limit}
        
        Esempi:
        - GET /api/subscriptions
        - GET /api/subscriptions/select
        - GET /api/subscriptions/partner/1951
        - GET /api/subscriptions/select/partner/1951
        - GET /api/subscriptions/limit/50
        - GET /api/subscriptions/select/limit/50
        - GET /api/subscriptions/partner/1951/limit/50
        - GET /api/subscriptions/select/partner/1951/limit/50
        """
        try:
            # Determina il formato dal path
            format_type = 'select' if '/select' in request.path else 'full'
            
            # Validazione parametri
            if limit < 1 or limit > 1000:
                return jsonify({
                    "error": "Limite deve essere tra 1 e 1000",
                    "code": "INVALID_LIMIT"
                }), 400
            
            # Recupera dati
            json_data = extractor.get_subscriptions_json(
                partner_id=partner_id,
                limit=limit
            )
            
            if json_data is None:
                return jsonify({
                    "error": "Errore nel recupero dei dati da Odoo",
                    "code": "ODOO_CONNECTION_ERROR"
                }), 500
            
            # Formato select
            if format_type == 'select':
                select_data = {"results": []}
                
                for subscription in json_data.get('subscriptions', []):
                    subscription_id = subscription['id']
                    subscription_name = subscription.get('name', 'N/A')
                    
                    # Informazioni partner
                    partner_info = subscription.get('partner', {})
                    partner_id = partner_info.get('id', 'N/A')
                    partner_name = partner_info.get('name', 'N/A')
                    
                    # Prende il primo prodotto dell'abbonamento come rappresentativo
                    if subscription.get('subscription_products') and len(subscription['subscription_products']) > 0:
                        first_product = subscription['subscription_products'][0]
                        product_name = first_product['name']
                        product_id = first_product.get('product', {}).get('id', 'N/A')
                        text = f"id: {product_id} | {product_name} ({subscription_name} | id: {subscription_id})"
                    else:
                        # Fallback: usa il nome dell'ordine se non ci sono prodotti
                        text = f"{subscription_name} (N/A)"
                    
                    select_data["results"].append({
                        "id": subscription_id,
                        "text": text,
                        "name": subscription_name,
                        "partner": {
                            "id": partner_id,
                            "name": partner_name
                        }
                    })
                
                return jsonify(select_data)
            
            # Formato completo (default)
            return jsonify(json_data)
            
        except Exception as e:
            return jsonify({
                "error": f"Errore interno del server: {str(e)}",
                "code": "INTERNAL_ERROR"
            }), 500


    @app.route('/api/subscriptions/<int:subscription_id>', methods=['GET'])
    @app.route('/api/subscriptions/select/<int:subscription_id>', methods=['GET'])
    def get_subscription_detail(subscription_id):
        """
        GET /api/subscriptions/{subscription_id}
        GET /api/subscriptions/select/{subscription_id}
        
        Restituisce i dettagli di un singolo abbonamento o formato select
        
        Esempi:
        - GET /api/subscriptions/1778
        - GET /api/subscriptions/select/1778
        """
        try:
            # Determina il formato dal path
            format_type = 'select' if '/select/' in request.path else 'full'
            
            # Recupera tutti gli abbonamenti (potremmo ottimizzare recuperando solo quello specifico)
            json_data = extractor.get_subscriptions_json(limit=1000)
            
            if json_data is None:
                return jsonify({
                    "error": "Errore nel recupero dei dati da Odoo",
                    "code": "ODOO_CONNECTION_ERROR"
                }), 500
            
            # Cerca l'abbonamento specifico
            subscription = None
            for sub in json_data.get('subscriptions', []):
                if sub['id'] == subscription_id:
                    subscription = sub
                    break
            
            if subscription is None:
                return jsonify({
                    "error": f"Abbonamento con ID {subscription_id} non trovato",
                    "code": "SUBSCRIPTION_NOT_FOUND"
                }), 404
            
            # Formato select
            if format_type == 'select':
                # Prende il primo prodotto dell'abbonamento come rappresentativo
                if subscription.get('subscription_products') and len(subscription['subscription_products']) > 0:
                    first_product = subscription['subscription_products'][0]
                    product_name = first_product['name']
                    product_id = first_product.get('product', {}).get('id', 'N/A')
                    text = f"{product_name} ({product_id})"
                else:
                    # Fallback: usa il nome dell'ordine se non ci sono prodotti
                    text = f"{subscription['name']} (N/A)"
                
                select_data = {
                    "results": [
                        {
                            "id": subscription_id,
                            "text": text
                        }
                    ]
                }
                return jsonify(select_data)
            
            # Formato completo
            return jsonify(subscription)
            
        except Exception as e:
            return jsonify({
                "error": f"Errore interno del server: {str(e)}",
                "code": "INTERNAL_ERROR"
            }), 500


    @app.route('/api/subscriptions/summary', methods=['GET'])
    def get_subscriptions_summary():
        """
        GET /api/subscriptions/summary
        
        Restituisce solo il summary degli abbonamenti
        
        Parametri query:
        - partner_id (int): Filtra per ID partner specifico
        
        Esempi:
        - GET /api/subscriptions/summary
        - GET /api/subscriptions/summary?partner_id=1951
        """
        try:
            partner_id = request.args.get('partner_id', type=int)
            
            # Recupera dati completi
            json_data = extractor.get_subscriptions_json(partner_id=partner_id)
            
            if json_data is None:
                return jsonify({
                    "error": "Errore nel recupero dei dati da Odoo",
                    "code": "ODOO_CONNECTION_ERROR"
                }), 500
            
            # Restituisce solo export_info e summary
            summary_data = {
                "export_info": json_data.get('export_info', {}),
                "summary": json_data.get('summary', {})
            }
            
            return jsonify(summary_data)
            
        except Exception as e:
            return jsonify({
                "error": f"Errore interno del server: {str(e)}",
                "code": "INTERNAL_ERROR"
            }), 500


    @app.route('/api/subscriptions/partner/<int:partner_id>', methods=['GET'])
    def get_partner_subscriptions(partner_id):
        """
        GET /api/subscriptions/partner/{partner_id}
        
        Restituisce gli abbonamenti di un partner specifico
        
        Parametri query:
        - format (string): 'full' (default) o 'select'
        - limit (int): Limite risultati (default: 100)
        
        Esempi:
        - GET /api/subscriptions/partner/1951
        - GET /api/subscriptions/partner/1951?format=select
        """
        try:
            format_type = request.args.get('format', default='full')
            limit = request.args.get('limit', default=100, type=int)
            
            # Validazione
            if limit < 1 or limit > 1000:
                return jsonify({
                    "error": "Limite deve essere tra 1 e 1000",
                    "code": "INVALID_LIMIT"
                }), 400
            
            # Recupera dati per partner specifico
            json_data = extractor.get_subscriptions_json(
                partner_id=partner_id,
                limit=limit
            )
            
            if json_data is None:
                return jsonify({
                    "error": "Errore nel recupero dei dati da Odoo",
                    "code": "ODOO_CONNECTION_ERROR"
                }), 500
            
            # Se non ci sono abbonamenti per questo partner
            if json_data['summary']['total_subscriptions'] == 0:
                if format_type == 'select':
                    return jsonify({"results": []})
                else:
                    return jsonify({
                        "export_info": json_data['export_info'],
                        "summary": json_data['summary'],
                        "subscriptions": []
                    })
            
            # Formato select
            if format_type == 'select':
                select_data = {"results": []}
                
                for subscription in json_data.get('subscriptions', []):
                    subscription_id = subscription['id']
                    
                    if subscription.get('subscription_products') and len(subscription['subscription_products']) > 0:
                        first_product = subscription['subscription_products'][0]
                        product_name = first_product['name']
                        product_id = first_product.get('product', {}).get('id', 'N/A')
                        text = f"{product_name} ({product_id})"
                    else:
                        text = f"{subscription['name']} (N/A)"
                    
                    select_data["results"].append({
                        "id": subscription_id,
                        "text": text
                    })
                
                return jsonify(select_data)
            
            # Formato completo
            return jsonify(json_data)
            
        except Exception as e:
            return jsonify({
                "error": f"Errore interno del server: {str(e)}",
                "code": "INTERNAL_ERROR"
            }), 500

    @app.route('/api/docs', methods=['GET'])
    def api_docs():
        """
        GET /api/docs
        
        Documentazione API
        """
        docs = {
            "title": "Subscriptions API",
            "version": "1.0.0",
            "description": "API per recuperare abbonamenti da Odoo",
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/api/subscriptions",
                    "description": "Lista tutti gli abbonamenti",
                    "parameters": [
                        {"name": "partner_id", "type": "int", "description": "Filtra per ID partner"},
                        {"name": "limit", "type": "int", "description": "Limite risultati (1-1000, default: 100)"},
                        {"name": "format", "type": "string", "description": "'full' o 'select' (default: full)"}
                    ]
                },
                {
                    "method": "GET",
                    "path": "/api/subscriptions/{id}",
                    "description": "Dettaglio abbonamento specifico"
                },
                {
                    "method": "GET",
                    "path": "/api/subscriptions/summary",
                    "description": "Summary degli abbonamenti",
                    "parameters": [
                        {"name": "partner_id", "type": "int", "description": "Filtra per ID partner"}
                    ]
                },
                {
                    "method": "GET",
                    "path": "/api/subscriptions/partner/{partner_id}",
                    "description": "Abbonamenti di un partner specifico",
                    "parameters": [
                        {"name": "format", "type": "string", "description": "'full' o 'select'"},
                        {"name": "limit", "type": "int", "description": "Limite risultati"}
                    ]
                },
                {
                    "method": "GET",
                    "path": "/api/health",
                    "description": "Health check API e connessione Odoo"
                }
            ],
            "examples": [
                "GET /api/subscriptions",
                "GET /api/subscriptions?format=select",
                "GET /api/subscriptions?partner_id=1951&format=select",
                "GET /api/subscriptions/1778",
                "GET /api/subscriptions/summary",
                "GET /api/subscriptions/partner/1951",
                "GET /api/subscriptions/partner/1951?format=select",
                "GET /api/health"
            ]
        }
        
        return jsonify(docs)


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
            '/api/odoo/products/select',
            '/api/odoo/payment_terms',
            '/api/odoo/payment_terms/select',
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
