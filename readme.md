# FTP Scheduler App

Un'applicazione web Python per il download automatico e schedulato di file da server FTP con conversione in formato JSON.

## 🚀 Caratteristiche Principali

- **Download FTP Automatizzato**: Connessione e download da server FTP
- **Schedulazione Flessibile**: Supporto per schedulazioni mensili, settimanali, giornaliere, a intervalli o con espressioni cron
- **Generazione Nomi File Intelligente**: Pattern automatici basati su data/mese corrente
- **Conversione Multi-formato**: Supporto per CSV, Excel, TXT → JSON
- **Interfaccia Web Intuitiva**: Dashboard e configurazione tramite browser
- **Logging Completo**: Monitoraggio di tutte le operazioni
- **Esecuzione Manuale**: Possibilità di eseguire download immediati per test

## 📋 Requisiti

- Python 3.8+
- Accesso a server FTP
- Spazio disco per file scaricati

## 🛠️ Installazione

### Installazione Standard

1. **Clona o scarica il progetto**
```bash
git clone <repository-url>
cd ftp-scheduler-app
```

2. **Crea ambiente virtuale (raccomandato)**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate     # Windows
```

3. **Installa dipendenze**
```bash
pip install -r requirements.txt
```

4. **Esegui setup iniziale**
```bash
python setup.py
```

5. **Avvia l'applicazione**
```bash
python app.py
```

6. **Apri il browser**
```
http://localhost:5000
```

### Installazione con Docker

1. **Clona il progetto**
```bash
git clone <repository-url>
cd ftp-scheduler-app
```

2. **Avvia con Docker Compose**
```bash
docker-compose up -d
```

3. **Accedi all'applicazione**
```
http://localhost:5000
```

## 🔧 Configurazione

### Configurazione FTP

| Campo | Descrizione | Esempio |
|-------|-------------|---------|
| Host FTP | Indirizzo del server FTP | `ftp.example.com` |
| Username | Nome utente FTP | `myuser` |
| Password | Password FTP | `mypassword` |
| Directory | Directory sul server (opzionale) | `/data` o `/` |

### Configurazione Download

#### Modalità Download
- **Tutti i file**: Scarica tutti i file presenti nella directory FTP
- **File specifico**: Scarica un singolo file basato su nome o pattern

#### Pattern Nomi File

| Pattern | Esempio Output | Descrizione |
|---------|---------------|-------------|
| Mensile | `report_2025_01.csv` | Anno_Mese |
| Settimanale | `report_2025_W03.csv` | Anno_Settimana |
| Giornaliero | `report_2025_01_15.csv` | Anno_Mese_Giorno |
| Trimestrale | `report_2025_Q1.csv` | Anno_Trimestre |
| Annuale | `report_2025.csv` | Anno |
| Personalizzato | Definito dall'utente | Usa codici strftime |

#### Codici Pattern Personalizzati
```
%Y = Anno (2025)
%m = Mese (01-12)
%d = Giorno (01-31)
%H = Ora (00-23)
%M = Minuto (00-59)
%U = Settimana dell'anno (00-53)
```

### Configurazione Schedulazione

#### Tipi di Schedulazione

1. **Mensile**
   - Esecuzione il giorno X di ogni mese
   - Esempio: Giorno 1 di ogni mese alle 09:00

2. **Settimanale**
   - Esecuzione un giorno specifico della settimana
   - Esempio: Ogni lunedì alle 09:00

3. **Giornaliera**
   - Esecuzione ogni giorno a un orario specifico
   - Esempio: Ogni giorno alle 09:00

4. **Intervallo**
   - Esecuzione ogni X giorni
   - Esempio: Ogni 30 giorni

5. **Cron Personalizzato**
   - Espressione cron completa
   - Formato: `minuto ora giorno mese giorno_settimana`
   - Esempio: `0 9 1 * *` (alle 9:00 del primo giorno di ogni mese)

## 📁 Struttura Progetto

```
ftp-scheduler-app/
├── app.py                 # Applicazione principale
├── requirements.txt       # Dipendenze Python
├── setup.py              # Script di setup
├── test_conversion.py    # Script di test
├── templates/            # Template HTML
│   ├── base.html
│   ├── index.html
│   └── config.html
├── output/               # File scaricati e convertiti
├── logs/                 # File di log
├── Dockerfile           # Configurazione Docker
├── docker-compose.yml   # Docker Compose
├── ftp-scheduler.service # Servizio systemd
└── test_ftp_server.py   # Server FTP di test
```

## 🎯 Utilizzo

### Dashboard Principale

1. **Visualizza Stato**: Mostra configurazione corrente e stato delle schedulazioni
2. **Esecuzione Manuale**: Pulsante per test immediato
3. **Test FTP**: Verifica connessione e lista file sul server
4. **Risultati**: Storico delle operazioni eseguite

### Configurazione

1. Vai alla pagina **Configurazione**
2. Compila i dati del server FTP
3. Scegli la modalità di download
4. Configura la schedulazione
5. Salva la configurazione

### Monitoraggio

- **Log**: Visualizza il file di log completo
- **Stato JSON**: Informazioni dettagliate su schedulazioni e ultima esecuzione
- **Risultati Dashboard**: Cronologia operazioni con dettagli

## 🔄 Conversioni Supportate

### Formati Input
- **CSV**: File separati da virgola
- **Excel**: File .xlsx e .xls
- **TXT**: File di testo (assume formato CSV con tab)
- **JSON**: File già in formato JSON (copia)

### Formato Output
Tutti i file vengono convertiti in JSON con struttura:
```json
[
  {
    "campo1": "valore1",
    "campo2": "valore2"
  }
]
```

Per file di testo semplice:
```json
{
  "content": "contenuto del file",
  "source_file": "nome_file_originale.txt"
}
```

## 🧪 Testing

### Test Conversioni File
```bash
python test_conversion.py conversion
```

### Test Generazione Nomi File
```bash
python test_conversion.py filename
```

### Server FTP di Test Locale
```bash
pip install pyftpdlib
python test_ftp_server.py
```

Credenziali server di test:
- Host: `localhost` o `127.0.0.1`
- Username: `testuser`
- Password: `testpass`
- Porta: `21`

## 🚀 Deployment

### Servizio Systemd (Linux)

1. **Modifica il percorso nel file di servizio**
```bash
nano ftp-scheduler.service
```

2. **Installa il servizio**
```bash
sudo cp ftp-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ftp-scheduler
sudo systemctl start ftp-scheduler
```

3. **Verifica stato**
```bash
sudo systemctl status ftp-scheduler
```

### Docker Production

1. **Build e avvio**
```bash
docker-compose up -d --build
```

2. **Verifica container**
```bash
docker-compose ps
docker-compose logs ftp-scheduler
```

### Reverse Proxy (Nginx)

Configurazione Nginx per produzione:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🔒 Sicurezza

### Raccomandazioni

1. **Password FTP**: Usa password complesse
2. **HTTPS**: Configura SSL/TLS per produzione
3. **Firewall**: Limita accesso alla porta 5000
4. **Backup**: Fai backup regolari della configurazione
5. **Logging**: Monitora i log per attività sospette

### Variabili d'Ambiente

Per maggiore sicurezza, usa variabili d'ambiente:
```bash
export FTP_HOST=your-ftp-server.com
export FTP_USER=your-username
export FTP_PASS=your-password
```

Modifica `app.py` per leggere da variabili d'ambiente:
```python
import os
CONFIG['ftp_host'] = os.getenv('FTP_HOST', '')
CONFIG['ftp_user'] = os.getenv('FTP_USER', '')
CONFIG['ftp_password'] = os.getenv('FTP_PASS', '')
```

## 📊 API Endpoints

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/` | GET | Dashboard principale |
| `/config` | GET/POST | Pagina configurazione |
| `/manual_run` | GET | Esecuzione manuale |
| `/test_ftp` | GET | Test connessione FTP |
| `/status` | GET | Stato JSON dell'applicazione |
| `/logs` | GET | Visualizzazione log |

## 🐛 Troubleshooting

### Problemi Comuni

#### Errore Connessione FTP
```
Errore connessione FTP: [Errno 111] Connection refused
```
**Soluzioni**:
- Verifica host, porta e credenziali
- Controlla firewall e porte aperte
- Testa connessione manuale con client FTP

#### File Non Trovato
```
Errore nel download di filename.csv: 550 File not found
```
**Soluzioni**:
- Verifica il nome del file sul server
- Controlla il pattern di generazione nome
- Usa "Lista file FTP" per vedere file disponibili

#### Errore Conversione
```
Errore nella conversione di file.csv: 'utf-8' codec can't decode
```
**Soluzioni**:
- Il file potrebbe avere encoding diverso
- Prova ad aprire il file manualmente per verificare formato
- Controlla che il file non sia corrotto

#### Scheduler Non Funziona
```
Job non viene eseguito all'orario previsto
```
**Soluzioni**:
- Verifica configurazione orario
- Controlla log per errori
- Riavvia applicazione
- Verifica fuso orario del server

### Log Debug

Per debug dettagliato, modifica il livello di logging in `app.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Controllo Salute Sistema

Script per verificare stato:
```bash
#!/bin/bash
echo "=== FTP Scheduler Health Check ==="
echo "Processo: $(ps aux | grep app.py | grep -v grep)"
echo "Porta 5000: $(netstat -tlnp | grep :5000)"
echo "Log recenti:"
tail -n 10 app.log
```

## 📈 Monitoraggio e Metriche

### File di Log

I log includono:
- Connessioni FTP riuscite/fallite
- File scaricati con timestamp
- Errori di conversione
- Esecuzioni scheduler

### Metriche Utili

Monitora questi aspetti:
- Frequenza errori FTP
- Tempo di esecuzione download
- Dimensione file scaricati
- Successo conversioni JSON

## 🤝 Contributi

Per contribuire al progetto:

1. Fork del repository
2. Crea branch per feature (`git checkout -b feature/nome-feature`)
3. Commit modifiche (`git commit -am 'Aggiunge nuova feature'`)
4. Push branch (`git push origin feature/nome-feature`)
5. Crea Pull Request

## 📝 Changelog

### v1.0.0
- Implementazione core FTP download
- Interfaccia web con Flask
- Schedulazione con APScheduler
- Conversione multi-formato in JSON
- Sistema di logging
- Configurazione tramite web interface

## 📄 Licenza

Questo progetto è rilasciato sotto licenza MIT. Vedi file LICENSE per dettagli.

## 🆘 Supporto

Per supporto:
1. Controlla la sezione Troubleshooting
2. Verifica i log dell'applicazione
3. Crea issue su GitHub con dettagli dell'errore

---

**Versione**: 1.0.0  
**Autore**: Sistema di Automazione FTP  
**Ultima modifica**: 2025