# setup.py - Script di setup e inizializzazione
import os
import json
from pathlib import Path

def create_directory_structure():
    """Crea la struttura delle directory necessarie"""
    directories = [
        'templates',
        'static/css',
        'static/js',
        'output',
        'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Directory creata: {directory}")

def create_sample_config():
    """Crea un file di configurazione di esempio"""
    sample_config = {
        "ftp_host": "ftp.example.com",
        "ftp_user": "username",
        "ftp_password": "password",
        "ftp_directory": "/data",
        "download_all_files": False,
        "specific_filename": "",
        "output_directory": "output",
        "file_naming_pattern": "monthly",
        "custom_pattern": "",
        "schedule_type": "monthly",
        "schedule_day": 1,
        "schedule_hour": 9,
        "schedule_minute": 0,
        "interval_days": 30,
        "cron_expression": "0 9 1 * *"
    }
    
    with open('config_sample.json', 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print("File di configurazione di esempio creato: config_sample.json")

def create_sample_data():
    """Crea file di dati di esempio per test"""
    import csv
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Crea un CSV di esempio
    sample_data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(100):
        sample_data.append({
            'id': i + 1,
            'nome': f'Prodotto_{i+1}',
            'categoria': ['Elettronica', 'Abbigliamento', 'Casa', 'Sport'][i % 4],
            'prezzo': round(10.99 + (i * 2.5), 2),
            'quantita': (i % 50) + 1,
            'data_vendita': (base_date + timedelta(days=i % 30)).strftime('%Y-%m-%d'),
            'venditore': f'Venditore_{(i % 5) + 1}'
        })
    
    # Salva come CSV
    df = pd.DataFrame(sample_data)
    csv_path = Path('output/sample_data.csv')
    df.to_csv(csv_path, index=False)
    print(f"File CSV di esempio creato: {csv_path}")
    
    # Salva come Excel
    excel_path = Path('output/sample_data.xlsx')
    df.to_excel(excel_path, index=False)
    print(f"File Excel di esempio creato: {excel_path}")
    
    # Crea un file di testo delimitato
    txt_path = Path('output/sample_data.txt')
    df.to_csv(txt_path, index=False, sep='\t')
    print(f"File TXT di esempio creato: {txt_path}")

def create_test_ftp_server():
    """Crea uno script per testare un server FTP locale (opzionale)"""
    ftp_test_script = '''#!/usr/bin/env python3
"""
Script per avviare un server FTP di test locale
Richiede: pip install pyftpdlib
"""

import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

def main():
    # Crea directory per il server FTP
    ftp_dir = os.path.join(os.getcwd(), 'ftp_test_data')
    os.makedirs(ftp_dir, exist_ok=True)
    
    # Crea alcuni file di test
    test_files = [
        'report_2025_01.csv',
        'report_2025_02.csv',
        'data_export.xlsx',
        'monthly_stats.txt'
    ]
    
    for filename in test_files:
        filepath = os.path.join(ftp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f'Test data for {filename}\\nGenerated for testing purposes\\n')
    
    # Configura autorizzatore
    authorizer = DummyAuthorizer()
    authorizer.add_user("testuser", "testpass", ftp_dir, perm="elradfmw")
    authorizer.add_anonymous(ftp_dir)
    
    # Configura handler
    handler = FTPHandler
    handler.authorizer = authorizer
    
    # Avvia server
    server = FTPServer(("127.0.0.1", 21), handler)
    
    print("Server FTP di test avviato su localhost:21")
    print("Username: testuser")
    print("Password: testpass")
    print(f"Directory: {ftp_dir}")
    print("Premi Ctrl+C per fermare il server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nServer FTP fermato")

if __name__ == "__main__":
    main()
'''
    
    with open('test_ftp_server.py', 'w') as f:
        f.write(ftp_test_script)
    
    print("Script server FTP di test creato: test_ftp_server.py")
    print("Per usarlo: pip install pyftpdlib && python test_ftp_server.py")

def create_systemd_service():
    """Crea un file di servizio systemd per Linux"""
    service_content = '''[Unit]
Description=FTP Scheduler App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/your/app
Environment=PATH=/path/to/your/venv/bin
ExecStart=/path/to/your/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
'''
    
    with open('ftp-scheduler.service', 'w') as f:
        f.write(service_content)
    
    print("File servizio systemd creato: ftp-scheduler.service")
    print("Per installarlo:")
    print("1. Modifica i percorsi nel file")
    print("2. sudo cp ftp-scheduler.service /etc/systemd/system/")
    print("3. sudo systemctl daemon-reload")
    print("4. sudo systemctl enable ftp-scheduler")
    print("5. sudo systemctl start ftp-scheduler")

def create_docker_files():
    """Crea Dockerfile e docker-compose.yml"""
    dockerfile_content = '''FROM python:3.11-slim

WORKDIR /app

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY . .

# Crea directory necessarie
RUN mkdir -p output logs templates

# Espone la porta 5000
EXPOSE 5000

# Avvia l'applicazione
CMD ["python", "app.py"]
'''
    
    docker_compose_content = '''version: '3.8'

services:
  ftp-scheduler:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./output:/app/output
      - ./logs:/app/logs
      - ./app.log:/app/app.log
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
    
  # Opzionale: server FTP di test
  ftp-server:
    image: stilliard/pure-ftpd
    ports:
      - "21:21"
      - "30000-30009:30000-30009"
    volumes:
      - ./ftp_test_data:/home/ftpusers/testuser
    environment:
      - PUBLICHOST=localhost
      - FTP_USER_NAME=testuser
      - FTP_USER_PASS=testpass
      - FTP_USER_HOME=/home/ftpusers/testuser
    restart: unless-stopped
'''
    
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile_content)
    
    with open('docker-compose.yml', 'w') as f:
        f.write(docker_compose_content)
    
    print("File Docker creati: Dockerfile, docker-compose.yml")
    print("Per avviare con Docker:")
    print("docker-compose up -d")

def main():
    """Esegue il setup completo"""
    print("=== Setup FTP Scheduler App ===")
    
    print("\n1. Creazione struttura directory...")
    create_directory_structure()
    
    print("\n2. Creazione configurazione di esempio...")
    create_sample_config()
    
    print("\n3. Creazione dati di esempio...")
    create_sample_data()
    
    print("\n4. Creazione script server FTP di test...")
    create_test_ftp_server()
    
    print("\n5. Creazione file servizio systemd...")
    create_systemd_service()
    
    print("\n6. Creazione file Docker...")
    create_docker_files()
    
    print("\n=== Setup completato! ===")
    print("\nProssimi passi:")
    print("1. pip install -r requirements.txt")
    print("2. Modifica la configurazione in app.py o tramite interfaccia web")
    print("3. python app.py")
    print("4. Apri http://localhost:5000 nel browser")
    print("\nPer test con server FTP locale:")
    print("pip install pyftpdlib && python test_ftp_server.py")

if __name__ == "__main__":
    main()


# test_conversion.py - Script per testare le conversioni di file
import sys
import json
from pathlib import Path
from app_new import FTPProcessor, CONFIG

def test_file_conversion():
    """Testa la conversione di diversi tipi di file"""
    print("=== Test Conversione File ===")
    
    # Crea processore
    processor = FTPProcessor(CONFIG)
    
    # File di test da convertire
    test_files = [
        'output/sample_data.csv',
        'output/sample_data.xlsx', 
        'output/sample_data.txt'
    ]
    
    for file_path in test_files:
        if Path(file_path).exists():
            print(f"\nConversione di: {file_path}")
            json_path = processor.convert_to_json(file_path)
            
            if json_path:
                print(f"Convertito in: {json_path}")
                
                # Mostra preview del JSON
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list) and len(data) > 0:
                    print(f"Numero di record: {len(data)}")
                    print("Preview primo record:")
                    print(json.dumps(data[0], indent=2))
                elif isinstance(data, dict):
                    print("Contenuto JSON:")
                    if len(str(data)) > 500:
                        print(str(data)[:500] + "...")
                    else:
                        print(json.dumps(data, indent=2))
            else:
                print("Errore nella conversione!")
        else:
            print(f"File non trovato: {file_path}")

def test_filename_generation():
    """Testa la generazione dei nomi file"""
    print("\n=== Test Generazione Nomi File ===")
    
    processor = FTPProcessor(CONFIG)
    
    patterns = ['monthly', 'weekly', 'daily', 'quarterly', 'yearly']
    
    for pattern in patterns:
        filename = processor.generate_filename(pattern)
        print(f"{pattern:10}: {filename}")
    
    # Test pattern personalizzato
    custom_patterns = [
        '%Y_%m_report.csv',
        'data_%d_%m_%Y.xlsx',
        'export_%Y_Q%q.json'  # Questo darà errore
    ]
    
    print("\nPattern personalizzati:")
    for pattern in custom_patterns:
        try:
            filename = processor.generate_filename('custom', pattern)
            print(f"{pattern:20}: {filename}")
        except Exception as e:
            print(f"{pattern:20}: ERRORE - {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "conversion":
            test_file_conversion()
        elif sys.argv[1] == "filename":
            test_filename_generation()
        else:
            print("Uso: python test_conversion.py [conversion|filename]")
    else:
        test_file_conversion()
        test_filename_generation()