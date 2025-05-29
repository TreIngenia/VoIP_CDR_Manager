FROM python:3.13.3-slim

WORKDIR /app

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e installa dipendenze Python
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY app/ .

# Crea directory necessarie
RUN mkdir -p output logs templates

# Espone la porta 5000
EXPOSE 5001

# Avvia l'applicazione
CMD ["python", "app.py"]
