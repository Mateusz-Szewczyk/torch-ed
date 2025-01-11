# Wybieramy bazowy obraz Pythona
FROM python:3.12-slim

# Ustawiamy katalog roboczy w kontenerze
WORKDIR /app

# Kopiujemy plik z zależnościami do kontenera
COPY requirements.txt .

# Instalacja zależności systemowych i Pythonowych
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    sqlite3 \
    libsqlite3-dev \
    python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Aktualizacja pip
    pip install --upgrade pip && \
    # Instalacja zależności aplikacji
    pip install --no-cache-dir -r requirements.txt

# Kopiujemy cały kod aplikacji do kontenera
COPY . .

CMD ["python", "run.py"]
