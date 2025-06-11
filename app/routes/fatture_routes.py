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
from gen_odoo_invoice_token import OdooAPI


logger = logging.getLogger(__name__)

def fatture_routes(app, secure_config):
    @app.route('/gestione_fatture')
    def gestione_fatture():
        from routes.menu_routes import render_with_menu_context
        return render_with_menu_context('gestione_fatture.html', {'config':secure_config})   


    @app.route('/api/fatturazione/genera_fattura', methods=['POST'])
    def genera_fattura():
        if not request.is_json:
            return jsonify({"error": "Dati non in formato JSON"}), 400
    
        try:
            logger.info("Avvio della generazione di fattura")
            #Ricevo i dati json
            data = request.get_json() or {}
            print(data)
            return_data = OdooAPI.gen_fattura(data)
            return return_data
            
        except Exception as e:
            logger.error(f"❌ Errore nella generazione della fattura: {e}")
                
            return jsonify({
                'success': False,
                'message': f'Errore durante estrazione: {str(e)}',
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }), 500

    # Restituisce le informazioni sulle route aggiunte
    return {
        'routes_added': [
            '/gestione_fatture'
        ],
        'routes_count': 1
    }

