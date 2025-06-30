"""
Odoo Routes v18.2+ - VERSIONE RIORGANIZZATA E SEMPLIFICATA
Route Flask ottimizzate con manager modulari
"""
from flask import request, jsonify, render_template
from datetime import datetime
import logging

# Import dei manager riorganizzati
from odoo_manager import get_odoo_manager
from odoo_utils import (
    build_api_response, build_select2_response, 
    validate_pagination_params, calculate_pagination_info,
    PerformanceTimer
)
from odoo_exceptions import OdooException

logger = logging.getLogger(__name__)

def add_odoo_routes(app, secure_config):
    """Registra tutte le route Odoo mantenendo i nomi originali"""
    
    # Inizializza manager principale
    odoo_manager = get_odoo_manager(secure_config)
    
    # ==================== PAGINE WEB ====================
    
    @app.route('/odoo_partners')
    def odoo_partners_page():
        """Pagina principale gestione clienti Odoo 18.2+"""
        try:
            from routes.menu_routes import render_with_menu_context
            return render_with_menu_context('odoo_partners.html')
        except Exception as e:
            logger.error(f"Errore pagina partner Odoo: {e}")
            return render_template('error.html', error_message=f"Errore: {e}")
    
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
    
    @app.route('/api/odoo/partners', methods=['GET'])
    def api_get_partners():
        """API per ottenere lista clienti con paginazione"""
        try:
            with PerformanceTimer("api_get_partners"):
                # Validazione parametri
                page = int(request.args.get('page', 1))
                per_page = int(request.args.get('per_page', 20))
                search = request.args.get('search', '').strip()
                partner_type = request.args.get('type', '')
                
                # Valida paginazione
                pagination = validate_pagination_params(page, per_page)
                if not pagination['valid']:
                    return build_api_response(False, message=pagination['error'], status_code=400)
                
                # Costruisci filtri
                filters = []
                if partner_type == 'company':
                    filters.append(('is_company', '=', True))
                elif partner_type == 'person':
                    filters.append(('is_company', '=', False))
                
                # Ricerca o lista normale
                if search:
                    partners = odoo_manager.partners.search_partners(search, limit=pagination['per_page'])
                    total_count = min(len(partners) * 2, 1000)  # Stima
                else:
                    partners = odoo_manager.partners.get_partners_list(
                        limit=pagination['per_page'], 
                        offset=pagination['offset'], 
                        filters=filters
                    )
                    total_count = odoo_manager.partners.get_partners_count(filters=filters)
                
                # Calcola info paginazione
                pagination_info = calculate_pagination_info(
                    pagination['page'], pagination['per_page'], total_count
                )
                
                return build_api_response(True, {
                    'partners': partners,
                    'pagination': pagination_info,
                    'search_term': search,
                    'partner_type': partner_type
                })
                
        except OdooException as e:
            logger.error(f"Errore Odoo API get partners: {e}")
            return build_api_response(False, message=str(e), error_code=e.error_code, status_code=500)
        except Exception as e:
            logger.error(f"Errore generico API get partners: {e}")
            return build_api_response(False, message=str(e), error_code='INTERNAL_ERROR', status_code=500)
    
    @app.route('/api/odoo/partners/<int:partner_id>', methods=['GET'])
    def api_get_partner_details(partner_id):
        """API per dettagli specifici partner"""
        try:
            with PerformanceTimer(f"api_get_partner_details_{partner_id}"):
                partner = odoo_manager.partners.get_partner_by_id(partner_id)
                
                if not partner:
                    return build_api_response(False, message=f'Partner {partner_id} non trovato', status_code=404)
                
                return build_api_response(True, {'partner': partner})
                
        except OdooException as e:
            logger.error(f"Errore Odoo get partner {partner_id}: {e}")
            return build_api_response(False, message=str(e), error_code=e.error_code, status_code=500)
        except Exception as e:
            logger.error(f"Errore generico get partner {partner_id}: {e}")
            return build_api_response(False, message=str(e), error_code='INTERNAL_ERROR', status_code=500)
    
    @app.route('/api/odoo/partners/summary', methods=['GET'])
    def api_partners_summary():
        """API per statistiche riassuntive clienti"""
        try:
            with PerformanceTimer("api_partners_summary"):
                summary = odoo_manager.partners.get_partners_summary()
                return build_api_response(True, {'summary': summary})
                
        except OdooException as e:
            logger.error(f"Errore Odoo partners summary: {e}")
            return build_api_response(False, message=str(e), error_code=e.error_code, status_code=500)
        except Exception as e:
            logger.error(f"Errore generico partners summary: {e}")
            return build_api_response(False, message=str(e), error_code='INTERNAL_ERROR', status_code=500)
    
    @app.route('/api/odoo/partners/search', methods=['POST'])
    def api_search_partners():
        """API per ricerca avanzata clienti"""
        try:
            with PerformanceTimer("api_search_partners"):
                data = request.get_json()
                if not data:
                    return build_api_response(False, message='Dati non validi', status_code=400)
                
                search_term = data.get('search_term', '').strip()
                limit = min(int(data.get('limit', 20)), 100)
                
                if not search_term:
                    return build_api_response(False, message='Termine di ricerca obbligatorio', status_code=400)
                
                partners = odoo_manager.partners.search_partners(search_term, limit=limit)
                
                return build_api_response(True, {
                    'partners': partners,
                    'search_term': search_term,
                    'results_count': len(partners)
                })
                
        except OdooException as e:
            logger.error(f"Errore Odoo search partners: {e}")
            return build_api_response(False, message=str(e), error_code=e.error_code, status_code=500)
        except Exception as e:
            logger.error(f"Errore generico search partners: {e}")
            return build_api_response(False, message=str(e), error_code='INTERNAL_ERROR', status_code=500)
    
    @app.route('/api/odoo/partners/select', methods=['GET'])
    def api_partners_for_select2():
        """API per recuperare partner per Select2"""
        try:
            with PerformanceTimer("api_partners_for_select2"):
                partners = odoo_manager.partners.get_all_partners_for_select()
                
                select2_data = []
                for partner in partners:
                    if isinstance(partner, dict):
                        select2_data.append({
                            'id': partner.get('commercial_partner_id'),
                            'text': partner.get('display_name', 'Nome non disponibile')
                        })
                
                return build_api_response(True, {
                    'results': select2_data,
                    'total': len(select2_data)
                })
                
        except OdooException as e:
            logger.error(f"Errore Odoo partners Select2: {e}")
            return build_api_response(False, message=str(e), error_code=e.error_code, status_code=500)
        except Exception as e:
            logger.error(f"Errore generico partners Select2: {e}")
            return build_api_response(False, message=str(e), error_code='INTERNAL_ERROR', status_code=500)

    # ==================== API PRODOTTI ====================
    
    @app.route('/api/odoo/products/select', methods=['GET'])
    def get_all_products_for_select():
        """API per recuperare prodotti per Select2"""
        try:
            with PerformanceTimer("get_all_products_for_select"):
                products = odoo_manager.products.get_all_products_for_select()
                
                select2_data = []
                for product in products:
                    if isinstance(product, dict):
                        select2_data.append({
                            'id': product.get('id'),
                            'text': product.get('display_name', 'Nome non disponibile')
                        })
                
                return build_api_response(True, {
                    'results': select2_data,
                    'total': len(select2_data)
                })
                
        except OdooException as e:
            logger.error(f"Errore Odoo products Select2: {e}")
            return build_api_response(False, message=str(e), error_code=e.error_code, status_code=500)
        except Exception as e:
            logger.error(f"Errore generico products Select2: {e}")
            return build_api_response(False, message=str(e), error_code='INTERNAL_ERROR', status_code=500)

    # ==================== API FATTURE ====================
    
    @app.route('/api/odoo/payment_terms', methods=['GET'])
    def api_get_payment_terms():
        """API per ottenere modalità di pagamento disponibili"""
        try:
            with PerformanceTimer("api_get_payment_terms"):
                payment_terms = odoo_manager.products.get_payment_terms()
                
                return build_api_response(True, {
                    'payment_terms': payment_terms,
                    'count': len(payment_terms)
                })
                
        except OdooException as e:
            logger.error(f"Errore Odoo payment terms: {e}")
            return build_api_response(False, message=str(e), error_code=e.error_code, status_code=500)
        except Exception as e:
            logger.error(f"Errore generico payment terms: {e}")
            return build_api_response(False, message=str(e), error_code='INTERNAL_ERROR', status_code=500)
    
    @app.route('/api/odoo/payment_terms/select', methods=['GET'])
    def get_all_payment_terms_for_select():
        """API per recuperare payment terms per Select2"""
        try:
            with PerformanceTimer("get_all_payment_terms_for_select"):
                payment_terms = odoo_manager.products.get_all_payment_terms_for_select()
                
                select2_data = []
                for payment_term in payment_terms:
                    if isinstance(payment_term, dict):
                        select2_data.append({
                            'id': payment_term.get('id'),
                            'text': payment_term.get('display_name', 'Nome non disponibile')
                        })
                
                return build_api_response(True, {
                    'results': select2_data,
                    'total': len(select2_data)
                })
                
        except OdooException as e:
            logger.error(f"Errore Odoo payment terms Select2: {e}")
            return build_api_response(False, message=str(e), error_code=e.error_code, status_code=500)
        except Exception as e:
            logger.error(f"Errore generico payment terms Select2: {e}")
            return build_api_response(False, message=str(e), error_code='INTERNAL_ERROR', status_code=500)

    # ==================== API ABBONAMENTI ====================
    
    @app.route('/api/subscriptions', methods=['GET'])
    @app.route('/api/subscriptions/select', methods=['GET'])
    @app.route('/api/subscriptions/partner/<int:partner_id>', methods=['GET'])
    @app.route('/api/subscriptions/select/partner/<int:partner_id>', methods=['GET'])
    @app.route('/api/subscriptions/limit/<int:limit>', methods=['GET'])
    @app.route('/api/subscriptions/select/limit/<int:limit>', methods=['GET'])
    @app.route('/api/subscriptions/partner/<int:partner_id>/limit/<int:limit>', methods=['GET'])
    @app.route('/api/subscriptions/select/partner/<int:partner_id>/limit/<int:limit>', methods=['GET'])
    def get_subscriptions(partner_id=None, limit=100):
        """API per recuperare abbonamenti (mantiene tutti i path originali)"""
        try:
            with PerformanceTimer(f"get_subscriptions_p{partner_id}_l{limit}"):
                # Determina il formato dal path
                format_type = 'select' if '/select' in request.path else 'full'
                
                # Validazione parametri
                if limit < 1 or limit > 1000:
                    return build_api_response(
                        False, 
                        message="Limite deve essere tra 1 e 1000", 
                        error_code="INVALID_LIMIT", 
                        status_code=400
                    )
                
                # Recupera dati
                json_data = odoo_manager.subscriptions.get_subscriptions_json(
                    partner_id=partner_id,
                    limit=limit
                )
                
                if json_data is None:
                    return build_api_response(
                        False, 
                        message="Errore nel recupero dei dati da Odoo", 
                        error_code="ODOO_CONNECTION_ERROR", 
                        status_code=500
                    )
                
                # Formato select
                if format_type == 'select':
                    select_data = {"results": []}
                    
                    for subscription in json_data.get('subscriptions', []):
                        subscription_id = subscription['id']
                        subscription_name = subscription.get('name', 'N/A')
                        
                        # Informazioni partner
                        partner_info = subscription.get('partner', {})
                        partner_id_info = partner_info.get('id', 'N/A')
                        partner_name = partner_info.get('name', 'N/A')
                        
                        # Prende il primo prodotto dell'abbonamento come rappresentativo
                        if subscription.get('subscription_products') and len(subscription['subscription_products']) > 0:
                            first_product = subscription['subscription_products'][0]
                            product_name = first_product['name']
                            product_id = first_product.get('product', {}).get('id', 'N/A')
                            text = f"id: {product_id} | {product_name} ({subscription_name} | id: {subscription_id})"
                        else:
                            text = f"{subscription_name} (N/A)"
                        
                        select_data["results"].append({
                            "id": subscription_id,
                            "text": text,
                            "name": subscription_name,
                            "partner": {
                                "id": partner_id_info,
                                "name": partner_name
                            }
                        })
                    
                    return jsonify(select_data)
                
                # Formato completo (default)
                return jsonify(json_data)
                
        except Exception as e:
            logger.error(f"Errore get_subscriptions: {e}")
            return build_api_response(
                False, 
                message=f"Errore interno del server: {str(e)}", 
                error_code="INTERNAL_ERROR", 
                status_code=500
            )

    @app.route('/api/subscriptions/<int:subscription_id>', methods=['GET'])
    @app.route('/api/subscriptions/select/<int:subscription_id>', methods=['GET'])
    def get_subscription_detail(subscription_id):
        """API per dettaglio singolo abbonamento"""
        try:
            with PerformanceTimer(f"get_subscription_detail_{subscription_id}"):
                # Determina il formato dal path
                format_type = 'select' if '/select/' in request.path else 'full'
                
                # Recupera tutti gli abbonamenti (potremmo ottimizzare recuperando solo quello specifico)
                json_data = odoo_manager.subscriptions.get_subscriptions_json(limit=1000)
                
                if json_data is None:
                    return build_api_response(
                        False, 
                        message="Errore nel recupero dei dati da Odoo", 
                        error_code="ODOO_CONNECTION_ERROR", 
                        status_code=500
                    )
                
                # Cerca l'abbonamento specifico
                subscription = None
                for sub in json_data.get('subscriptions', []):
                    if sub['id'] == subscription_id:
                        subscription = sub
                        break
                
                if subscription is None:
                    return build_api_response(
                        False, 
                        message=f"Abbonamento con ID {subscription_id} non trovato", 
                        error_code="SUBSCRIPTION_NOT_FOUND", 
                        status_code=404
                    )
                
                # Formato select
                if format_type == 'select':
                    # Prende il primo prodotto dell'abbonamento come rappresentativo
                    if subscription.get('subscription_products') and len(subscription['subscription_products']) > 0:
                        first_product = subscription['subscription_products'][0]
                        product_name = first_product['name']
                        product_id = first_product.get('product', {}).get('id', 'N/A')
                        text = f"{product_name} ({product_id})"
                    else:
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
            logger.error(f"Errore get_subscription_detail: {e}")
            return build_api_response(
                False, 
                message=f"Errore interno del server: {str(e)}", 
                error_code="INTERNAL_ERROR", 
                status_code=500
            )

    @app.route('/api/subscriptions/summary', methods=['GET'])
    def get_subscriptions_summary():
        """API per summary degli abbonamenti"""
        try:
            with PerformanceTimer("get_subscriptions_summary"):
                partner_id = request.args.get('partner_id', type=int)
                
                # Recupera dati completi
                json_data = odoo_manager.subscriptions.get_subscriptions_json(partner_id=partner_id)
                
                if json_data is None:
                    return build_api_response(
                        False, 
                        message="Errore nel recupero dei dati da Odoo", 
                        error_code="ODOO_CONNECTION_ERROR", 
                        status_code=500
                    )
                
                # Restituisce solo export_info e summary
                summary_data = {
                    "export_info": json_data.get('export_info', {}),
                    "summary": json_data.get('summary', {})
                }
                
                return jsonify(summary_data)
                
        except Exception as e:
            logger.error(f"Errore get_subscriptions_summary: {e}")
            return build_api_response(
                False, 
                message=f"Errore interno del server: {str(e)}", 
                error_code="INTERNAL_ERROR", 
                status_code=500
            )

    @app.route('/api/docs', methods=['GET'])
    def api_docs():
        """Documentazione API"""
        docs = {
            "title": "Odoo Integration API v18.2+",
            "version": "2.0.0",
            "description": "API riorganizzata per l'integrazione con Odoo SaaS 18.2+",
            "components": {
                "partners": "Gestione clienti e fornitori",
                "products": "Gestione prodotti e termini di pagamento", 
                "invoices": "Sistema di fatturazione",
                "subscriptions": "Gestione abbonamenti e ordini ricorrenti"
            },
            "endpoints": [
                {
                    "group": "Partners",
                    "endpoints": [
                        "GET /api/odoo/partners",
                        "GET /api/odoo/partners/{id}",
                        "GET /api/odoo/partners/summary",
                        "POST /api/odoo/partners/search",
                        "GET /api/odoo/partners/select"
                    ]
                },
                {
                    "group": "Products",
                    "endpoints": [
                        "GET /api/odoo/products/select",
                        "GET /api/odoo/payment_terms",
                        "GET /api/odoo/payment_terms/select"
                    ]
                },
                {
                    "group": "Subscriptions",
                    "endpoints": [
                        "GET /api/subscriptions",
                        "GET /api/subscriptions/{id}",
                        "GET /api/subscriptions/summary",
                        "GET /api/subscriptions/partner/{partner_id}"
                    ]
                }
            ],
            "architecture": {
                "client": "OdooClient - Connessione e operazioni base",
                "managers": [
                    "OdooPartnerManager - Gestione partner",
                    "OdooProductManager - Gestione prodotti",
                    "OdooInvoiceManager - Sistema fatturazione",
                    "OdooSubscriptionManager - Gestione abbonamenti"
                ],
                "utils": "Helper functions e utilità comuni",
                "performance": "Timer e logging delle performance"
            }
        }
        
        return jsonify(docs)

    # ==================== FUNZIONE DI FATTURAZIONE LEGACY ====================
    
    def gen_fattura(fact_data):
        """Funzione di fatturazione consolidata (compatibilità legacy)"""
        try:
            with PerformanceTimer("gen_fattura"):
                partner_id = fact_data['partner_id']
                due_days = fact_data.get('due_days', None)
                if due_days == "":
                    due_days = None
                manual_due_date = fact_data.get('manual_due_date', None)
                items = fact_data['items']
                da_confermare = fact_data.get('da_confermare', '')
                
                logger.info("🚀 Sistema Fatturazione Odoo con Manager")
                
                result = False
                
                if da_confermare not in ["SI", ""]:
                    # Crea e conferma fattura
                    invoice_id = odoo_manager.invoices.create_and_confirm_invoice(
                        partner_id=partner_id, 
                        items=items, 
                        due_days=due_days,
                        manual_due_date=manual_due_date
                    )
                    
                    if invoice_id:
                        # Visualizza dettagli
                        details = odoo_manager.invoices.get_invoice_details(invoice_id)
                        # Invia email
                        result = odoo_manager.invoices.send_invoice_email(invoice_id)
                else:
                    # Crea solo bozza
                    invoice_id = odoo_manager.invoices.create_invoice(
                        partner_id=partner_id, 
                        items=items, 
                        due_days=due_days,
                        manual_due_date=manual_due_date
                    )
                
                if not invoice_id:
                    logger.error("❌ Impossibile creare la fattura")
                    return None
                
                # Risultato JSON
                json_result = {
                    "invoice_id": invoice_id,
                    "send_email": result,
                    "partner_id": partner_id,
                    "due_days": due_days,
                    "manual_due_date": manual_due_date,
                    "items": items,
                    "da_confermare": da_confermare
                }
                
                logger.info("\n🎉 Processo fatturazione completato!")
                return jsonify(json_result)
                
        except Exception as e:
            logger.error(f"Errore gen_fattura: {e}")
            return jsonify({
                "error": str(e),
                "invoice_id": None,
                "send_email": False
            })

    logger.info("🚀 Route Odoo 18.2+ riorganizzate registrate con successo")
    
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
            # API Abbonamenti
            '/api/subscriptions',
            '/api/subscriptions/<int:subscription_id>',
            '/api/subscriptions/summary',
            # Documentazione
            '/api/docs'
        ],
        'routes_count': 15,
        'odoo_version': '18.2+',
        'architecture': 'modular_managers',
        'features': {
            'modular_design': True,
            'performance_monitoring': True,
            'standardized_responses': True,
            'comprehensive_error_handling': True,
            'legacy_compatibility': True
        }
    }