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
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Kopiujemy cały kod aplikacji do kontenera
COPY . .

# Eksponujemy port, na którym działa aplikacja FastAPI
EXPOSE 8043

# Definiujemy zmienną środowiskową dla Uvicorn (opcjonalne)
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8043

# Polecenie uruchamiające aplikację FastAPI za pomocą Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8043", "--proxy-headers"]
