"""
Categories Routes - Route Flask per gestione categorie CDR con markup personalizzabili
Aggiornato per utilizzare il sistema unificato cdr_categories_enhanced.py
"""

import json
import logging
from datetime import datetime
import os
from pathlib import Path
from flask import request, jsonify, render_template, Response
import csv
import io

# from contratti import CDRContractsService
from odoo_integration import OdooAPI


logger = logging.getLogger(__name__)

def fatture_routes(app, secure_config):
    @app.route('/gestione_fatture')
    def gestione_fatture():
        from routes.menu_routes import render_with_menu_context
        return render_with_menu_context('gestione_fatture.html', {'config': secure_config})
    
    @app.route('/gestione_ordini')
    def gestione_ordini():
        """Pagina per gestire gli ordini clienti con traffico extra"""
        from routes.menu_routes import render_with_menu_context
        return render_with_menu_context('gestione_abbonamenti.html', {'config': secure_config})

    @app.route('/api/fatturazione/genera_fattura', methods=['POST'])
    def genera_fattura():
        """Route originale per generare fatture tradizionali"""
        if not request.is_json:
            return jsonify({"error": "Dati non in formato JSON"}), 400
    
        try:
            logger.info("Avvio della generazione di fattura")
            data = request.get_json() or {}
            return_data = OdooAPI.gen_fattura(data)
            return return_data
            
        except Exception as e:
            logger.error(f"❌ Errore nella generazione della fattura: {e}")
            return jsonify({
                'success': False,
                'message': f'Errore durante generazione fattura: {str(e)}',
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/api/fatturazione/lista_clienti', methods=['GET'])
    def lista_clienti():
        """Route per ottenere la lista dei clienti disponibili"""
        try:
            odoo = OdooAPI(
                url=os.getenv('ODOO_URL'),
                db=os.getenv('ODOO_DB'),
                username=os.getenv('ODOO_USERNAME'),
                api_key=os.getenv('ODOO_API_KEY')
            )
            
            if not odoo.connect():
                return jsonify({
                    'success': False,
                    'message': 'Impossibile connettersi a Odoo'
                }), 500
            
            # Cerca clienti (non fornitori)
            partners = odoo.execute('res.partner', 'search_read',
                [('is_company', '=', True), ('customer_rank', '>', 0)],
                fields=['id', 'name', 'email', 'phone'],
                limit=50)
            
            return jsonify({
                'success': True,
                'clients': partners,
                'count': len(partners),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Errore nel recupero clienti: {e}")
            return jsonify({
                'success': False,
                'message': f'Errore durante recupero clienti: {str(e)}',
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/api/fatturazione/ordini_cliente/<int:partner_id>', methods=['GET'])
    def ordini_cliente(partner_id):
        """Route per ottenere gli ordini di un cliente specifico"""
        try:
            odoo = OdooAPI(
                url=os.getenv('ODOO_URL'),
                db=os.getenv('ODOO_DB'),
                username=os.getenv('ODOO_USERNAME'),
                api_key=os.getenv('ODOO_API_KEY')
            )
            
            if not odoo.connect():
                return jsonify({
                    'success': False,
                    'message': 'Impossibile connettersi a Odoo'
                }), 500
            
            # Cerca ordini del cliente
            orders = odoo.execute('sale.order', 'search_read',
                [('partner_id', '=', partner_id)],
                fields=['id', 'name', 'state', 'amount_total', 'date_order', 'order_line'],
                order='date_order desc',
                limit=20)
            
            # Per ogni ordine, controlla se ha traffico extra
            for order in orders:
                if order.get('order_line'):
                    lines = odoo.execute('sale.order.line', 'search_read',
                        [
                            ('order_id', '=', order['id']),
                            ('name', 'like', 'EXTRA_TRAFFIC_')
                        ],
                        fields=['name', 'price_unit'])
                    
                    order['extra_traffic_lines'] = len(lines)
                    order['extra_traffic_amount'] = sum(line['price_unit'] for line in lines)
                else:
                    order['extra_traffic_lines'] = 0
                    order['extra_traffic_amount'] = 0
            
            return jsonify({
                'success': True,
                'orders': orders,
                'count': len(orders),
                'partner_id': partner_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Errore nel recupero ordini cliente {partner_id}: {e}")
            return jsonify({
                'success': False,
                'message': f'Errore durante recupero ordini: {str(e)}',
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }), 500

    # Restituisce le informazioni sulle route aggiunte
    return {
        'routes_added': [
            '/gestione_fatture',
            '/gestione_ordini',
            '/api/fatturazione/lista_clienti',
            '/api/fatturazione/ordini_cliente/<int:partner_id>'
        ],
        'routes_count': 9
    }