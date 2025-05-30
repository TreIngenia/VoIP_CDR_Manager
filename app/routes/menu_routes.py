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

# def render_with_menu_context(template_path, page_title, additional_context=None):
#     """Render template with menu context and partials processing."""
#     try:
#         if template_path.startswith('templates_new/'):
#             file_path = template_path
#         else:
#             file_path = f'templates_new/{template_path}'
            
#         with open(file_path, 'r', encoding='utf-8') as f:
#             content = f.read()
            
#         processed_html = process_partials_recursive(content)
        
#         # Context base con menu items
#         context = {
#             'menu_items': MENU_ITEMS,
#             'page_title': page_title,
#             'current_endpoint': request.endpoint
#         }
        
#         # Aggiungi context aggiuntivo se fornito
#         if additional_context:
#             context.update(additional_context)
            
#         return render_template_string(processed_html, **context)
        
#     except Exception as e:
#         # Fallback con template Flask standard
#         from flask import render_template
#         context = {
#             'menu_items': MENU_ITEMS,
#             'page_title': page_title,
#             'error_message': str(e)
#         }
#         if additional_context:
#             context.update(additional_context)
#         return render_template('error.html', **context)
def render_with_menu_context(template_path, page_title, additional_context=None):
    """Render template con menu + breadcrumb"""
    try:
        if template_path.startswith(os.getenv("TEMPLATE_FOLDER", "templates_new")+'/'):
            file_path = template_path
        else:
            file_path = os.getenv("TEMPLATE_FOLDER", "templates_new")+f'/{template_path}'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        processed_html = process_partials_recursive(content)

        # Calcolo breadcrumb
        breadcrumb = []
        endpoint = request.endpoint

        def find_breadcrumb(items, trail=None):
            trail = trail or []
            for item in items:
                if 'endpoint' in item:
                    if item['endpoint'] == endpoint:
                        return trail + [item]
                elif 'children' in item:
                    result = find_breadcrumb(item['children'], trail + [item])
                    if result:
                        return result
            return None

        path = find_breadcrumb(MENU_ITEMS)
        for item in (path or []):
            url = '#'
            if 'endpoint' in item:
                try:
                    url = url_for(item['endpoint'])
                except:
                    url = '#'
            breadcrumb.append({
                'title': item.get('title', ''),
                'url': url
            })

        context = {
            'menu_items': MENU_ITEMS,
            'page_title': page_title,
            'current_endpoint': request.endpoint,
            'breadcrumb': breadcrumb  # 🔥 incluso automaticamente
        }

        if additional_context:
            context.update(additional_context)
        
        return render_template_string(processed_html, **context)

    except Exception as e:
        from flask import render_template
        context = {
            'menu_items': MENU_ITEMS,
            'page_title': page_title,
            'error_message': str(e)
        }
        if additional_context:
            context.update(additional_context)
        return render_template('error.html', **context)

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

from flask import request, jsonify, url_for
from menu import MENU_ITEMS

    
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