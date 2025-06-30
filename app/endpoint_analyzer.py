#!/usr/bin/env python3
"""
Endpoint Analyzer per FTP Scheduler App
Script per analizzare e listare tutti gli endpoint disponibili nell'applicazione Flask
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import importlib.util
import inspect
import re

# Aggiungi la directory corrente al path per importare l'app
sys.path.insert(0, os.getcwd())

class EndpointAnalyzer:
    """Analizzatore di endpoint Flask"""
    
    def __init__(self):
        self.endpoints = []
        self.app = None
        
    def analyze_app(self):
        """Analizza l'applicazione Flask per estrarre gli endpoint"""
        try:
            # Importa l'app principale
            from app import create_app
            from config import SecureConfig
            from ftp_processor import FTPProcessor  
            from scheduler import SchedulerManager
            from app.routes.default_routes import create_routes
            
            print("🔍 Inizializzazione componenti app...")
            
            # Crea componenti necessari
            secure_config = SecureConfig()
            processor = FTPProcessor(secure_config)
            scheduler_manager = SchedulerManager()
            
            # Crea app Flask
            app = create_app()
            app = create_routes(app, secure_config, processor, scheduler_manager)
            self.app = app
            
            print("✅ App inizializzata correttamente")
            
            # Analizza gli endpoint
            self._extract_endpoints()
            
        except Exception as e:
            print(f"❌ Errore nell'analisi dell'app: {e}")
            print("🔄 Tentativo di analisi alternativa...")
            self._analyze_routes_file()
    
    def _extract_endpoints(self):
        """Estrae gli endpoint dall'app Flask"""
        if not self.app:
            return
            
        print("🔍 Estrazione endpoint da Flask app...")
        
        for rule in self.app.url_map.iter_rules():
            # Ottieni informazioni sul metodo HTTP
            methods = list(rule.methods)
            # Rimuovi metodi automatici Flask
            methods = [m for m in methods if m not in ['HEAD', 'OPTIONS']]
            
            # Ottieni la funzione associata alla route
            view_function = self.app.view_functions.get(rule.endpoint)
            
            # Estrai documentazione
            description = self._extract_docstring(view_function)
            
            # Determina parametri URL
            url_params = self._extract_url_parameters(rule.rule)
            
            # Analizza il codice della funzione per dettagli extra
            function_details = self._analyze_function(view_function)
            
            endpoint_info = {
                'url': rule.rule,
                'methods': methods,
                'endpoint_name': rule.endpoint,
                'description': description,
                'url_parameters': url_params,
                'function_name': view_function.__name__ if view_function else 'Unknown',
                'module': view_function.__module__ if view_function else 'Unknown',
                'request_data': function_details.get('request_data', []),
                'response_format': function_details.get('response_format', 'Unknown'),
                'status_codes': function_details.get('status_codes', [200]),
                'auth_required': function_details.get('auth_required', False)
            }
            
            self.endpoints.append(endpoint_info)
        
        print(f"✅ Trovati {len(self.endpoints)} endpoint")
    
    def _analyze_routes_file(self):
        """Analizza il file routes.py direttamente se l'import dell'app fallisce"""
        print("🔍 Analisi diretta del file routes.py...")
        
        try:
            routes_file = Path('routes/default_routes.py')
            if not routes_file.exists():
                print("❌ File routes.py non trovato")
                return
            
            with open(routes_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Pattern per trovare le route Flask
            route_pattern = r'@app\.route\([\'\"](.*?)[\'\"]\s*(?:,\s*methods\s*=\s*\[(.*?)\])?\)'
            function_pattern = r'def\s+(\w+)\s*\([^)]*\):\s*(?:\n\s*[\'\"]{3}([^\'\"]*)[\'\"]{3})?'
            
            routes_matches = re.finditer(route_pattern, content)
            
            for match in routes_matches:
                url = match.group(1)
                methods_str = match.group(2)
                
                # Estrai metodi HTTP
                if methods_str:
                    methods = [m.strip().strip('\'"') for m in methods_str.split(',')]
                else:
                    methods = ['GET']
                
                # Trova la funzione associata
                pos = match.end()
                remaining_content = content[pos:]
                func_match = re.search(function_pattern, remaining_content)
                
                if func_match:
                    func_name = func_match.group(1)
                    docstring = func_match.group(2) or "Nessuna descrizione disponibile"
                else:
                    func_name = "Unknown"
                    docstring = "Nessuna descrizione disponibile"
                
                endpoint_info = {
                    'url': url,
                    'methods': methods,
                    'endpoint_name': func_name,
                    'description': docstring.strip(),
                    'url_parameters': self._extract_url_parameters(url),
                    'function_name': func_name,
                    'module': 'routes',
                    'request_data': [],
                    'response_format': 'Unknown',
                    'status_codes': [200],
                    'auth_required': False
                }
                
                self.endpoints.append(endpoint_info)
            
            print(f"✅ Trovati {len(self.endpoints)} endpoint tramite analisi file")
            
        except Exception as e:
            print(f"❌ Errore nell'analisi del file routes.py: {e}")
    
    def _extract_docstring(self, function):
        """Estrae la docstring da una funzione"""
        if not function:
            return "Nessuna descrizione disponibile"
        
        docstring = inspect.getdoc(function)
        return docstring if docstring else "Nessuna descrizione disponibile"
    
    def _extract_url_parameters(self, url_rule):
        """Estrae i parametri URL da una regola Flask"""
        import re
        params = re.findall(r'<([^>]+)>', url_rule)
        
        parsed_params = []
        for param in params:
            if ':' in param:
                param_type, param_name = param.split(':', 1)
                parsed_params.append({
                    'name': param_name,
                    'type': param_type,
                    'required': True
                })
            else:
                parsed_params.append({
                    'name': param,
                    'type': 'string',
                    'required': True
                })
        
        return parsed_params
    
    def _analyze_function(self, function):
        """Analizza il codice di una funzione per estrarre dettagli"""
        details = {
            'request_data': [],
            'response_format': 'Unknown',
            'status_codes': [200],
            'auth_required': False
        }
        
        if not function:
            return details
        
        try:
            # Ottieni il codice sorgente
            source = inspect.getsource(function)
            
            # Cerca indicazioni sui dati di richiesta
            if 'request.get_json()' in source:
                details['request_data'].append('JSON payload')
            if 'request.form' in source:
                details['request_data'].append('Form data')
            if 'request.args' in source:
                details['request_data'].append('Query parameters')
            
            # Cerca formato di risposta
            if 'jsonify(' in source:
                details['response_format'] = 'JSON'
            elif 'render_template(' in source:
                details['response_format'] = 'HTML'
            elif 'return' in source and 'str(' in source:
                details['response_format'] = 'Text/String'
            
            # Cerca codici di stato HTTP
            status_codes = re.findall(r'return.*?,\s*(\d{3})', source)
            if status_codes:
                details['status_codes'] = [int(code) for code in status_codes]
            
            # Controlla se richiede autenticazione (semplice)
            if 'auth' in source.lower() or 'login' in source.lower():
                details['auth_required'] = True
                
        except Exception as e:
            print(f"⚠️ Errore nell'analisi della funzione {function.__name__}: {e}")
        
        return details
    
    def generate_report(self):
        """Genera un report completo degli endpoint"""
        if not self.endpoints:
            print("❌ Nessun endpoint trovato da analizzare")
            return
        
        # Ordina endpoint per URL
        self.endpoints.sort(key=lambda x: x['url'])
        
        # Genera report console
        self._print_console_report()
        
        # Genera report JSON
        self._generate_json_report()
        
        # Genera report Markdown
        self._generate_markdown_report()
        
        # Genera report HTML
        self._generate_html_report()
    
    def _print_console_report(self):
        """Stampa report sulla console"""
        print("\n" + "="*80)
        print("📋 ENDPOINT ANALYSIS REPORT")
        print("="*80)
        print(f"🕒 Generato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Totale endpoint: {len(self.endpoints)}")
        print("="*80)
        
        # Raggruppa per metodo HTTP
        methods_count = {}
        for endpoint in self.endpoints:
            for method in endpoint['methods']:
                methods_count[method] = methods_count.get(method, 0) + 1
        
        print(f"📈 Distribuzione metodi HTTP:")
        for method, count in sorted(methods_count.items()):
            print(f"   {method}: {count} endpoint")
        
        print("\n" + "-"*80)
        print("📋 ELENCO DETTAGLIATO ENDPOINT:")
        print("-"*80)
        
        for i, endpoint in enumerate(self.endpoints, 1):
            methods_str = " | ".join(endpoint['methods'])
            
            print(f"\n{i:2d}. {endpoint['url']}")
            print(f"    🔗 Metodi: {methods_str}")
            print(f"    📝 Funzione: {endpoint['function_name']}")
            print(f"    📄 Descrizione: {endpoint['description']}")
            
            if endpoint['url_parameters']:
                print(f"    📋 Parametri URL:")
                for param in endpoint['url_parameters']:
                    print(f"       - {param['name']} ({param['type']}) {'- Richiesto' if param['required'] else ''}")
            
            if endpoint['request_data']:
                print(f"    📥 Dati richiesta: {', '.join(endpoint['request_data'])}")
            
            print(f"    📤 Formato risposta: {endpoint['response_format']}")
            
            if len(endpoint['status_codes']) > 1 or endpoint['status_codes'][0] != 200:
                print(f"    📊 Codici stato: {', '.join(map(str, endpoint['status_codes']))}")
    
    def _generate_json_report(self):
        """Genera report in formato JSON"""
        filename = f"endpoints_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            'generation_timestamp': datetime.now().isoformat(),
            'total_endpoints': len(self.endpoints),
            'endpoints': self.endpoints,
            'methods_summary': self._get_methods_summary(),
            'categories': self._categorize_endpoints()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report JSON salvato: {filename}")
    
    def _generate_markdown_report(self):
        """Genera report in formato Markdown"""
        filename = f"endpoints_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        md_content = f"""# 📋 FTP Scheduler App - Endpoint Report

**Generato il:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Totale endpoint:** {len(self.endpoints)}

## 📊 Distribuzione Metodi HTTP

| Metodo | Conteggio |
|--------|-----------|
"""
        
        methods_summary = self._get_methods_summary()
        for method, count in sorted(methods_summary.items()):
            md_content += f"| {method} | {count} |\n"
        
        md_content += "\n## 📋 Endpoint Dettagliati\n\n"
        
        for i, endpoint in enumerate(self.endpoints, 1):
            methods_badges = " ".join([f"`{m}`" for m in endpoint['methods']])
            
            md_content += f"""### {i}. `{endpoint['url']}`

**Metodi:** {methods_badges}  
**Funzione:** `{endpoint['function_name']}`  
**Descrizione:** {endpoint['description']}

"""
            
            if endpoint['url_parameters']:
                md_content += "**Parametri URL:**\n"
                for param in endpoint['url_parameters']:
                    required = "✅ Richiesto" if param['required'] else "❌ Opzionale"
                    md_content += f"- `{param['name']}` ({param['type']}) - {required}\n"
                md_content += "\n"
            
            if endpoint['request_data']:
                md_content += f"**Dati Richiesta:** {', '.join(endpoint['request_data'])}  \n"
            
            md_content += f"**Formato Risposta:** {endpoint['response_format']}  \n"
            
            if len(endpoint['status_codes']) > 1 or endpoint['status_codes'][0] != 200:
                codes = ", ".join(map(str, endpoint['status_codes']))
                md_content += f"**Codici Stato:** {codes}  \n"
            
            md_content += "\n---\n\n"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"📝 Report Markdown salvato: {filename}")
    
    def _generate_html_report(self):
        """Genera report in formato HTML"""
        filename = f"endpoints_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FTP Scheduler - Endpoint Report</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .method-badge {{ font-size: 0.75em; margin: 2px; }}
        .endpoint-card {{ margin-bottom: 1rem; }}
        .status-code {{ background: #e9ecef; padding: 2px 6px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <h1>📋 FTP Scheduler App - Endpoint Report</h1>
                <p class="text-muted">Generato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="alert alert-info">
                    <strong>Totale endpoint:</strong> {len(self.endpoints)}
                </div>
                
                <h2>📊 Distribuzione Metodi HTTP</h2>
                <div class="row mb-4">
"""
        
        methods_summary = self._get_methods_summary()
        for method, count in sorted(methods_summary.items()):
            color = {
                'GET': 'success', 'POST': 'primary', 'PUT': 'warning',
                'DELETE': 'danger', 'PATCH': 'info'
            }.get(method, 'secondary')
            
            html_content += f"""
                    <div class="col-md-2 col-sm-4 mb-2">
                        <div class="card text-center">
                            <div class="card-body">
                                <span class="badge bg-{color} fs-6">{method}</span>
                                <h5 class="card-title mt-2">{count}</h5>
                            </div>
                        </div>
                    </div>
"""
        
        html_content += """
                </div>
                
                <h2>📋 Endpoint Dettagliati</h2>
"""
        
        for i, endpoint in enumerate(self.endpoints, 1):
            methods_badges = ""
            for method in endpoint['methods']:
                color = {
                    'GET': 'success', 'POST': 'primary', 'PUT': 'warning',
                    'DELETE': 'danger', 'PATCH': 'info'
                }.get(method, 'secondary')
                methods_badges += f'<span class="badge bg-{color} method-badge">{method}</span>'
            
            html_content += f"""
                <div class="card endpoint-card">
                    <div class="card-header">
                        <h5 class="mb-0">
                            {i}. <code>{endpoint['url']}</code>
                            {methods_badges}
                        </h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Funzione:</strong> <code>{endpoint['function_name']}</code></p>
                        <p><strong>Descrizione:</strong> {endpoint['description']}</p>
"""
            
            if endpoint['url_parameters']:
                html_content += "<p><strong>Parametri URL:</strong></p><ul>"
                for param in endpoint['url_parameters']:
                    required_badge = '<span class="badge bg-success">Richiesto</span>' if param['required'] else '<span class="badge bg-secondary">Opzionale</span>'
                    html_content += f"<li><code>{param['name']}</code> ({param['type']}) {required_badge}</li>"
                html_content += "</ul>"
            
            if endpoint['request_data']:
                html_content += f"<p><strong>Dati Richiesta:</strong> {', '.join(endpoint['request_data'])}</p>"
            
            html_content += f"<p><strong>Formato Risposta:</strong> {endpoint['response_format']}</p>"
            
            if len(endpoint['status_codes']) > 1 or endpoint['status_codes'][0] != 200:
                codes_html = " ".join([f'<span class="status-code">{code}</span>' for code in endpoint['status_codes']])
                html_content += f"<p><strong>Codici Stato:</strong> {codes_html}</p>"
            
            html_content += """
                    </div>
                </div>
"""
        
        html_content += """
            </div>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"🌐 Report HTML salvato: {filename}")
    
    def _get_methods_summary(self):
        """Ottieni il riepilogo dei metodi HTTP"""
        methods_count = {}
        for endpoint in self.endpoints:
            for method in endpoint['methods']:
                methods_count[method] = methods_count.get(method, 0) + 1
        return methods_count
    
    def _categorize_endpoints(self):
        """Categorizza gli endpoint per funzionalità"""
        categories = {
            'UI': [],          # Pagine web
            'API': [],         # Endpoint API
            'Admin': [],       # Funzioni amministrative
            'Health': [],      # Monitoraggio
            'CDR': []          # CDR Analytics
        }
        
        for endpoint in self.endpoints:
            url = endpoint['url']
            
            if '/api/' in url:
                categories['API'].append(endpoint)
            elif '/health' in url or '/status' in url or '/logs' in url:
                categories['Health'].append(endpoint)
            elif '/cdr' in url:
                categories['CDR'].append(endpoint)
            elif endpoint['response_format'] == 'HTML':
                categories['UI'].append(endpoint)
            else:
                categories['Admin'].append(endpoint)
        
        return categories

def main():
    """Funzione principale"""
    print("🚀 FTP Scheduler App - Endpoint Analyzer")
    print("="*50)
    
    analyzer = EndpointAnalyzer()
    
    # Analizza l'applicazione
    analyzer.analyze_app()
    
    if not analyzer.endpoints:
        print("❌ Nessun endpoint trovato. Verifica che l'app sia configurata correttamente.")
        return
    
    # Genera i report
    analyzer.generate_report()
    
    print("\n✅ Analisi completata!")
    print(f"📊 Totale endpoint analizzati: {len(analyzer.endpoints)}")
    print("\n📁 File generati:")
    print("   - Report console (visualizzato sopra)")
    print("   - endpoints_report_*.json (formato JSON)")
    print("   - endpoints_report_*.md (formato Markdown)")  
    print("   - endpoints_report_*.html (formato HTML)")

if __name__ == "__main__":
    main()