import os
import re
from flask import Blueprint, render_template_string, request, jsonify, url_for
from menu import MENU_ITEMS

menu_bp = Blueprint('menu', __name__)

def process_partials_recursive(content, base_dir='templates_new'):
    """Process partials recursively in the content."""
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

# ✅ CLASSE BREADCRUMB BUILDER (DEVE ESSERE PRIMA DELLA FUNZIONE CHE LA USA)
class BreadcrumbBuilder:
    """Classe per costruire breadcrumb dai menu items"""
    
    def __init__(self, menu_items):
        self.menu_items = menu_items
    
    def find_menu_path(self, endpoint, items=None, path=None):
        """Trova il percorso di un endpoint nella struttura menu"""
        if items is None:
            items = self.menu_items
        if path is None:
            path = []
        
        for item in items:
            current_path = path + [item]
            
            if item.get('endpoint') == endpoint:
                return current_path
            
            if 'children' in item:
                result = self.find_menu_path(endpoint, item['children'], current_path)
                if result:
                    return result
        
        return None
    
    def build_breadcrumb(self, endpoint, include_home=True):
        """Costruisce il breadcrumb per un endpoint"""
        breadcrumb = []

        if self._endpoint_to_title(endpoint) == 'Index': 
            return breadcrumb    
        
        # Aggiungi Home se richiesto
       
        if include_home:
            if self._endpoint_to_title(endpoint) != 'Index': 
                breadcrumb.append({
                    'title': 'Dashboard',
                    'url': self._safe_url_for('index'),
                    'is_active': endpoint == 'index',
                    'icon': 'ki-outline ki-home fs-3'
                })
        
        # Trova il percorso nel menu
        menu_path = self.find_menu_path(endpoint)
        
        if menu_path:
            for i, item in enumerate(menu_path):
                is_last = (i == len(menu_path) - 1)
                
                # Salta sezioni senza endpoint
                if item.get('type') == 'section' and 'endpoint' not in item:
                    continue
                
                breadcrumb_item = {
                    'title': item.get('title', 'Senza titolo'),
                    'url': self._safe_url_for(item.get('endpoint')) if item.get('endpoint') and not is_last else None,
                    'is_active': is_last,
                    'icon': item.get('icon', '')
                }
                
                breadcrumb.append(breadcrumb_item)
        else:
            # Fallback per endpoint non in menu
            breadcrumb.append({
                'title': self._endpoint_to_title(endpoint),
                'url': None,
                'is_active': True,
                'icon': ''
            })
        
        return breadcrumb
    
    def _safe_url_for(self, endpoint):
        """Genera URL in modo sicuro"""
        if not endpoint:
            return '#'
        try:
            return url_for(endpoint)
        except:
            return '#'
    
    def _endpoint_to_title(self, endpoint):
        """Converte endpoint in titolo"""
        if not endpoint:
            return 'Pagina'
        
        if '.' in endpoint:
            endpoint = endpoint.split('.')[-1]
        
        title = endpoint.replace('_', ' ').title()
        
        replacements = {
            'Config': 'Configurazione',
            'Cdr': 'CDR',
            'Api': 'API',
            'Ftp': 'FTP',
            'Gestione Utenti': 'Gestione Contratti'
        }
        
        for old, new in replacements.items():
            title = title.replace(old, new)
        
        return title

# ✅ ISTANZA GLOBALE (DOPO LA CLASSE)
_breadcrumb_builder = BreadcrumbBuilder(MENU_ITEMS)

# ✅ FUNZIONE RENDER (DOPO L'ISTANZA GLOBALE)
def render_with_menu_context(template_path, additional_context=None):
    """Render template con menu + breadcrumb integrato"""
    try:
        if template_path.startswith(os.getenv("TEMPLATE_FOLDER", "templates_new")+'/'):
            file_path = template_path
        else:
            file_path = os.getenv("TEMPLATE_FOLDER", "templates_new")+f'/{template_path}'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        processed_html = process_partials_recursive(content)

        # ✅ CALCOLO BREADCRUMB INTEGRATO
        endpoint = request.endpoint
        breadcrumb = _breadcrumb_builder.build_breadcrumb(endpoint)

        context = {
            'menu_items': MENU_ITEMS,
            'current_endpoint': endpoint,
            'breadcrumb': breadcrumb,  # ✅ BREADCRUMB AUTOMATICO
        }

        if additional_context:
            context.update(additional_context)
        
        return render_template_string(processed_html, **context)

    except Exception as e:
        from flask import render_template
        context = {
            'menu_items': MENU_ITEMS,
            'error_message': str(e),
            'breadcrumb': []  # ✅ BREADCRUMB VUOTO IN CASO ERRORE
        }
        if additional_context:
            context.update(additional_context)
        return render_template('error.html', **context)

# ✅ ROUTE API BREADCRUMB
@menu_bp.route('/api/breadcrumb')
def get_breadcrumb_api():
    """API per ottenere breadcrumb dell'endpoint corrente"""
    try:
        include_home = request.args.get('include_home', 'true').lower() == 'true'
        endpoint = request.args.get('endpoint', request.endpoint)
        
        breadcrumb = _breadcrumb_builder.build_breadcrumb(endpoint, include_home)
        
        return jsonify({
            'success': True,
            'breadcrumb': breadcrumb,
            'current_endpoint': endpoint,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'breadcrumb': []
        }), 500

@menu_bp.route('/api/breadcrumb/<endpoint>')
def get_breadcrumb_for_endpoint(endpoint):
    """API per breadcrumb di un endpoint specifico"""
    try:
        include_home = request.args.get('include_home', 'true').lower() == 'true'
        breadcrumb = _breadcrumb_builder.build_breadcrumb(endpoint, include_home)
        
        return jsonify({
            'success': True,
            'breadcrumb': breadcrumb,
            'target_endpoint': endpoint
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'breadcrumb': []
        }), 500

# ✅ ROUTE MENU ESISTENTI
@menu_bp.route('/api/menu/items')
def get_menu_items():
    """API per ottenere elementi menu con URL processati"""
    try:
        processed_menu = []
        
        for item in MENU_ITEMS:
            menu_item = item.copy()
            
            if 'endpoint' in item:
                menu_item['is_active'] = request.endpoint == item['endpoint']
                try:
                    menu_item['url'] = url_for(item['endpoint'])
                except:
                    menu_item['url'] = '#'
            
            elif 'children' in item:
                processed_children = []
                for child in item['children']:
                    child_item = child.copy()
                    if 'endpoint' in child:
                        child_item['is_active'] = request.endpoint == child['endpoint']
                        try:
                            child_item['url'] = url_for(child['endpoint'])
                        except:
                            child_item['url'] = '#'
                    processed_children.append(child_item)
                menu_item['children'] = processed_children
            
            processed_menu.append(menu_item)
        
        return jsonify({
            'success': True,
            'menu_items': processed_menu,
            'current_endpoint': request.endpoint
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Errore menu: {str(e)}'
        }), 500

# ✅ FUNZIONI TEMPLATE GLOBALI
def register_breadcrumb_globals(app):
    """Registra funzioni template globali per breadcrumb"""
    
    @app.template_global()
    def get_breadcrumb(endpoint=None, include_home=True):
        """Template global per ottenere breadcrumb"""
        if endpoint is None:
            endpoint = request.endpoint
        return _breadcrumb_builder.build_breadcrumb(endpoint, include_home)
    
    @app.template_global()
    def breadcrumb_html(endpoint=None, include_home=True, css_classes="breadcrumb"):
        """Template global per HTML breadcrumb"""
        breadcrumb = get_breadcrumb(endpoint, include_home)
        
        html_parts = [f'<ol class="{css_classes}">']
        
        for item in breadcrumb:
            li_class = "breadcrumb-item"
            if item['is_active']:
                li_class += " active"
            
            html_parts.append(f'<li class="{li_class}">')
            
            if item['url'] and not item['is_active']:
                icon_html = f'<i class="{item["icon"]} me-1"></i>' if item['icon'] else ''
                html_parts.append(f'<a href="{item["url"]}" class="text-decoration-none">{icon_html}{item["title"]}</a>')
            else:
                icon_html = f'<i class="{item["icon"]} me-1"></i>' if item['icon'] else ''
                html_parts.append(f'{icon_html}{item["title"]}')
            
            html_parts.append('</li>')
        
        html_parts.append('</ol>')
        return ''.join(html_parts)
    
    @app.template_global()
    def breadcrumb_json(endpoint=None, include_home=True):
        """Template global per breadcrumb JSON"""
        import json
        breadcrumb = get_breadcrumb(endpoint, include_home)
        return json.dumps(breadcrumb)

def register_menu_globals(app):
    """Registra funzioni globali per menu nei template"""
    
    @app.template_global()
    def is_menu_active(endpoint):
        return request.endpoint == endpoint
    
    @app.template_global()
    def get_menu_icon(item):
        return item.get('icon', 'ki-outline ki-element-11 fs-2')
    
    @app.template_global()
    def get_menu_url(item):
        if 'endpoint' in item:
            try:
                return url_for(item['endpoint'])
            except:
                return '#'
        return '#'
    
    @app.template_global()
    def has_menu_children(item):
        return 'children' in item and len(item['children']) > 0
    
    @app.context_processor
    def inject_menu_context():
        return {
            'menu_items': MENU_ITEMS,
            'current_endpoint': request.endpoint
        }