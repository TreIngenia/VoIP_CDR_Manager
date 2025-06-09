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