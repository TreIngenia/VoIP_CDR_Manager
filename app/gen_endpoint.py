#!/usr/bin/env python3
import os
import re
from pathlib import Path
from collections import defaultdict

def extract_routes_from_file(file_path):
    """
    Estrae i route da un singolo file.
    Supporta diversi pattern comuni per definire route.
    """
    routes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Pattern per diversi framework/librerie
        patterns = [
            # Express.js: app.get('/api/users', ...), router.post('/login', ...)
            r'(?:app|router)\.(?:get|post|put|delete|patch|use)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
            
            # Flask: @app.route('/api/users', methods=['GET'])
            r'@(?:app|bp|blueprint)\.route\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
            
            # FastAPI: @app.get("/api/users"), @router.post("/login")
            r'@(?:app|router)\.(?:get|post|put|delete|patch)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
            
            # Django URLs: path('api/users/', ...)
            r'path\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
            
            # Altre varianti comuni
            r'route\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
            r'url\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Pulisci il route e aggiungi il prefisso se necessario
                route = match.strip()
                if route and not route.startswith('/'):
                    route = '/' + route
                if route and route not in routes:
                    routes.append(route)
                    
    except Exception as e:
        print(f"Errore nel leggere il file {file_path}: {e}")
    
    return sorted(routes)

def scan_routes_directory(directory_path):
    """
    Scansiona la directory dei route e estrae tutti i route organizzati per file.
    """
    route_dir = Path(directory_path)
    
    if not route_dir.exists():
        print(f"Errore: La directory '{directory_path}' non esiste.")
        return {}
    
    if not route_dir.is_dir():
        print(f"Errore: '{directory_path}' non è una directory.")
        return {}
    
    routes_by_file = {}
    
    # Estensioni file da considerare
    valid_extensions = {'.js', '.py', '.ts', '.jsx', '.tsx', '.php', '.rb', '.go', '.java'}
    
    # Scansiona tutti i file nella directory
    for file_path in route_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
            routes = extract_routes_from_file(file_path)
            if routes:
                # Usa il path relativo alla directory dei route
                relative_path = file_path.relative_to(route_dir)
                routes_by_file[str(relative_path)] = routes
    
    return routes_by_file

def print_routes_summary(routes_by_file):
    """
    Stampa un riepilogo di tutti i route trovati.
    """
    if not routes_by_file:
        print("Nessun route trovato nella directory specificata.")
        return
    
    total_routes = sum(len(routes) for routes in routes_by_file.values())
    print(f"\n📊 RIEPILOGO ROUTE TROVATI")
    print("=" * 50)
    print(f"File analizzati: {len(routes_by_file)}")
    print(f"Route totali: {total_routes}")
    print()
    
    # Ordina i file per nome
    for filename in sorted(routes_by_file.keys()):
        routes = routes_by_file[filename]
        print(f"📁 {filename} ({len(routes)} route{'s' if len(routes) != 1 else ''})")
        print("-" * (len(filename) + 20))
        
        for route in routes:
            print(f"   {route}")
        print()
    
    # Lista completa ordinata di tutti i route
    all_routes = []
    for routes in routes_by_file.values():
        all_routes.extend(routes)
    
    unique_routes = sorted(set(all_routes))
    
    print(f"🗂️  TUTTI I ROUTE ORDINATI ({len(unique_routes)} unici)")
    print("=" * 50)
    for route in unique_routes:
        print(f"   {route}")

def save_routes_to_file(routes_by_file, output_file='routes_output.md'):
    """
    Salva i route in un file Markdown.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header del documento
            f.write("# 📋 Elenco Route Estratti\n\n")
            
            total_routes = sum(len(routes) for routes in routes_by_file.values())
            f.write("## 📊 Riepilogo\n\n")
            f.write(f"- **File analizzati**: {len(routes_by_file)}\n")
            f.write(f"- **Route totali**: {total_routes}\n")
            f.write(f"- **Data estrazione**: {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            # Indice dei file
            f.write("## 📑 Indice dei File\n\n")
            for filename in sorted(routes_by_file.keys()):
                routes = routes_by_file[filename]
                anchor = filename.replace('/', '-').replace('.', '-').lower()
                f.write(f"- [{filename}](#{anchor}) ({len(routes)} route)\n")
            f.write("\n")
            
            # Route per file
            f.write("## 📁 Route per File\n\n")
            for filename in sorted(routes_by_file.keys()):
                routes = routes_by_file[filename]
                anchor = filename.replace('/', '-').replace('.', '-').lower()
                f.write(f"### {filename}\n\n")
                f.write(f"**Numero di route**: {len(routes)}\n\n")
                
                if routes:
                    f.write("| Route |\n")
                    f.write("|-------|\n")
                    for route in routes:
                        f.write(f"| `{route}` |\n")
                else:
                    f.write("*Nessun route trovato in questo file.*\n")
                f.write("\n")
            
            # Lista completa
            all_routes = []
            for routes in routes_by_file.values():
                all_routes.extend(routes)
            
            unique_routes = sorted(set(all_routes))
            f.write(f"## 🗂️ Tutti i Route Ordinati\n\n")
            f.write(f"**Totale route unici**: {len(unique_routes)}\n\n")
            
            if unique_routes:
                f.write("| Route | Metodo Tipico |\n")
                f.write("|-------|---------------|\n")
                for route in unique_routes:
                    # Prova a indovinare il metodo HTTP dal nome del route
                    method = "GET"
                    route_lower = route.lower()
                    if any(word in route_lower for word in ['create', 'add', 'new', 'post']):
                        method = "POST"
                    elif any(word in route_lower for word in ['update', 'edit', 'modify', 'put']):
                        method = "PUT"
                    elif any(word in route_lower for word in ['delete', 'remove', 'del']):
                        method = "DELETE"
                    
                    f.write(f"| `{route}` | {method} |\n")
            else:
                f.write("*Nessun route trovato.*\n")
            
            f.write("\n")
            
            # Statistiche aggiuntive
            f.write("## 📈 Statistiche\n\n")
            
            # Raggruppamento per prefisso API
            api_prefixes = {}
            for route in unique_routes:
                parts = route.strip('/').split('/')
                if len(parts) >= 2:
                    prefix = f"/{parts[0]}/{parts[1]}"
                    api_prefixes[prefix] = api_prefixes.get(prefix, 0) + 1
            
            if api_prefixes:
                f.write("### Route per Prefisso API\n\n")
                f.write("| Prefisso | Numero Route |\n")
                f.write("|----------|-------------|\n")
                for prefix, count in sorted(api_prefixes.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"| `{prefix}` | {count} |\n")
                f.write("\n")
            
            # Footer
            f.write("---\n")
            f.write("*Documento generato automaticamente dallo script di estrazione route*\n")
        
        print(f"\n💾 Route salvati nel file Markdown: {output_file}")
        
    except Exception as e:
        print(f"Errore nel salvare il file: {e}")

def main():
    """
    Funzione principale dello script.
    """
    print("🔍 ESTRATTORE DI ROUTE")
    print("=" * 30)
    
    # Puoi modificare questo path o passarlo come argomento
    routes_directory = "route"  # Cambia questo path se necessario
    
    # Controlla se l'utente ha passato un argomento
    import sys
    if len(sys.argv) > 1:
        routes_directory = sys.argv[1]
    
    print(f"Scansionando la directory: {routes_directory}")
    
    # Estrai i route
    routes_by_file = scan_routes_directory(routes_directory)
    
    # Mostra i risultati
    print_routes_summary(routes_by_file)
    
    # Salva su file (opzionale)
    if routes_by_file:
        save_choice = input("\nVuoi salvare i risultati in un file? (s/n): ").lower().strip()
        if save_choice in ['s', 'si', 'sì', 'y', 'yes']:
            output_filename = input("Nome del file di output (default: routes_output.md): ").strip()
            if not output_filename:
                output_filename = "routes_output.md"
            save_routes_to_file(routes_by_file, output_filename)

if __name__ == "__main__":
    main()