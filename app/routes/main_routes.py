from flask import Blueprint, render_template, render_template_string, request, jsonify
import os
import re
from menu import MENU_ITEMS

main = Blueprint('main', __name__)

def process_partials_recursive(content, base_dir='templates'):
    """
    Process partials recursively in the content.
    This function looks for comments in the format <!--layout-partial:filename.html-->
    and replaces them with the content of the specified file.
    It supports nested partials by calling itself recursively.
    """
    pattern = r'<!--layout-partial:(.*?)-->'
    
    def replacer(match):
        partial_path = match.group(1).strip()
        full_path = os.path.join(base_dir, partial_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                nested = f.read()
                return process_partials_recursive(nested, base_dir)
        except FileNotFoundError:
            return f"<!-- Partial {partial_path} not found -->"
    
    return re.sub(pattern, replacer, content)

def render_with_template(path, title, additional_context=None):
    """
    Render a template with the processed content, menu items and additional context.
    This function reads the content of the specified template file,
    processes it to replace partials, and then renders it with the menu items.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            processed_html = process_partials_recursive(content)
        
        # Context base con menu items e title
        context = {
            'menu_items': MENU_ITEMS,
            'page_title': title,
            'current_endpoint': request.endpoint
        }
        
        # Aggiungi context aggiuntivo se fornito
        if additional_context:
            context.update(additional_context)
            
        return render_template_string(processed_html, **context)
    except Exception as e:
        # Log dell'errore e fallback
        print(f"Errore nel rendering template {path}: {e}")
        return render_template_string(
            "<div class='alert alert-danger'>Errore nel caricamento della pagina</div>",
            menu_items=MENU_ITEMS,
            page_title=title,
            error_message=str(e)
        )

# ============ ROUTE PRINCIPALI ============

@main.route('/')
def index():
    """Dashboard principale"""
    # Puoi aggiungere dati specifici per la dashboard
    dashboard_data = {
        'stats': {
            'total_reports': 0,
            'active_jobs': 0,
            'last_execution': None
        }
    }
    return render_with_template('templates/index.html', 'Dashboard', dashboard_data)

@main.route('/report/mensile')
def report_mensile():
    """Report mensili"""
    # Dati specifici per i report mensili
    report_data = {
        'report_type': 'mensile',
        'available_months': ['2024-01', '2024-02', '2024-03'],
        'current_month': '2024-03'
    }
    return render_with_template('templates/report_mensile.html', 'Report Mensili', report_data)

@main.route('/report/annuale')
def report_annuale():
    """Report annuali"""
    # Dati specifici per i report annuali
    report_data = {
        'report_type': 'annuale',
        'available_years': ['2022', '2023', '2024'],
        'current_year': '2024'
    }
    return render_with_template('templates/report_annuale.html', 'Report Annuali', report_data)

@main.route('/settings')
def settings():
    """Pagina impostazioni"""
    # Configurazioni attuali
    settings_data = {
        'ftp_configured': True,  # Esempio
        'scheduler_active': False,
        'last_backup': '2024-03-15'
    }
    return render_with_template('templates/config.html', 'Impostazioni', settings_data)

# ============ API ENDPOINTS ============

@main.route('/api/menu/items')
def get_menu_items():
    """API per ottenere gli elementi del menu"""
    try:
        # Processa gli elementi del menu per aggiungere informazioni di stato
        processed_menu = []
        
        for item in MENU_ITEMS:
            menu_item = item.copy()
            
            # Aggiungi informazioni aggiuntive per ogni tipo di menu
            if 'endpoint' in item:
                # Per elementi con endpoint, verifica se sono attivi
                menu_item['is_active'] = request.endpoint == item['endpoint']
                menu_item['url'] = url_for(item['endpoint']) if item['endpoint'] else '#'
            
            elif 'children' in item:
                # Per elementi con sottomenu, processa i figli
                processed_children = []
                for child in item['children']:
                    child_item = child.copy()
                    if 'endpoint' in child:
                        child_item['is_active'] = request.endpoint == child['endpoint']
                        child_item['url'] = url_for(child['endpoint']) if child['endpoint'] else '#'
                    processed_children.append(child_item)
                menu_item['children'] = processed_children
            
            # Aggiungi badge di stato se necessario
            if item.get('title') == 'Dashboard':
                menu_item['badge'] = {'text': 'Home', 'class': 'bg-primary'}
            elif 'Report' in item.get('title', ''):
                menu_item['badge'] = {'text': 'New', 'class': 'bg-success'}
            
            processed_menu.append(menu_item)
        
        return jsonify({
            'success': True,
            'menu_items': processed_menu,
            'current_endpoint': request.endpoint
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Errore nel caricamento menu: {str(e)}'
        }), 500

@main.route('/api/menu/breadcrumb')
def get_breadcrumb():
    """API per ottenere il breadcrumb della pagina corrente"""
    try:
        current_endpoint = request.endpoint
        breadcrumb = []
        
        # Sempre includi Home
        breadcrumb.append({
            'title': 'Home',
            'url': url_for('main.index'),
            'is_active': current_endpoint == 'main.index'
        })
        
        # Trova l'elemento corrente nel menu per costruire il breadcrumb
        def find_in_menu(items, endpoint, path=[]):
            for item in items:
                current_path = path + [item]
                
                if item.get('endpoint') == endpoint:
                    return current_path
                
                if 'children' in item:
                    result = find_in_menu(item['children'], endpoint, current_path)
                    if result:
                        return result
            return None
        
        menu_path = find_in_menu(MENU_ITEMS, current_endpoint)
        
        if menu_path:
            for i, item in enumerate(menu_path):
                is_last = (i == len(menu_path) - 1)
                breadcrumb.append({
                    'title': item['title'],
                    'url': url_for(item['endpoint']) if item.get('endpoint') and not is_last else None,
                    'is_active': is_last
                })
        
        return jsonify({
            'success': True,
            'breadcrumb': breadcrumb
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Errore nel breadcrumb: {str(e)}'
        }), 500

# ============ UTILITY FUNCTIONS ============

def get_menu_context():
    """Ottieni il context del menu per i template"""
    return {
        'menu_items': MENU_ITEMS,
        'current_endpoint': request.endpoint,
        'menu_helper': {
            'is_active': lambda endpoint: request.endpoint == endpoint,
            'has_children': lambda item: 'children' in item and len(item['children']) > 0,
            'get_icon_class': lambda item: item.get('icon', 'ki-outline ki-element-11'),
            'get_url': lambda item: url_for(item['endpoint']) if item.get('endpoint') else '#'
        }
    }

def register_menu_globals(app):
    """Registra funzioni globiali per i template"""
    
    @app.template_global()
    def is_menu_active(endpoint):
        """Verifica se un endpoint del menu è attivo"""
        return request.endpoint == endpoint
    
    @app.template_global()
    def get_menu_icon(item):
        """Ottieni l'icona per un elemento del menu"""
        return item.get('icon', 'ki-outline ki-element-11 fs-2')
    
    @app.template_global()
    def get_menu_url(item):
        """Ottieni l'URL per un elemento del menu"""
        if 'endpoint' in item:
            try:
                return url_for(item['endpoint'])
            except:
                return '#'
        return '#'
    
    @app.template_global()
    def has_menu_children(item):
        """Verifica se un elemento del menu ha figli"""
        return 'children' in item and len(item['children']) > 0
    
    @app.template_global()
    def get_active_menu_section():
        """Ottieni la sezione attiva del menu"""
        current_endpoint = request.endpoint
        
        for item in MENU_ITEMS:
            if item.get('endpoint') == current_endpoint:
                return item.get('title', '')
            
            if 'children' in item:
                for child in item['children']:
                    if child.get('endpoint') == current_endpoint:
                        return item.get('title', '')
        
        return ''

# ============ ERROR HANDLERS ============

@main.errorhandler(404)
def not_found_error(error):
    """Handler per errori 404"""
    return render_with_template(
        'templates/error.html', 
        'Pagina Non Trovata',
        {'error_code': 404, 'error_message': 'La pagina richiesta non è stata trovata'}
    ), 404

@main.errorhandler(500)
def internal_error(error):
    """Handler per errori 500"""
    return render_with_template(
        'templates/error.html',
        'Errore Interno',
        {'error_code': 500, 'error_message': 'Si è verificato un errore interno del server'}
    ), 500

# ============ CONTEXT PROCESSORS ============

@main.context_processor
def inject_menu_context():
    """Inietta il context del menu in tutti i template"""
    return get_menu_context()

# Per compatibilità con url_for nei template
from flask import url_for