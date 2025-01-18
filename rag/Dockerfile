# Wybieramy bazowy obraz Pythona
FROM python:3.12-slim

# Ustawiamy zmienne środowiskowe
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8043

# Ustawiamy katalog roboczy w kontenerze
WORKDIR /app

# Kopiujemy plik z zależnościami
COPY requirements.txt .

# Instalacja zależności systemowych i Pythonowych
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    ca-certificates \
    pandoc \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && . $HOME/.cargo/env \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    # Instalacja zależności Pythona
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    # Czyszczenie
    && apt-get purge -y --auto-remove build-essential curl git \
    && rm -rf /root/.cache/pip/* \
    && rm -rf /root/.cargo/registry

# Kopiujemy kod aplikacji
COPY . .

# Eksponujemy port aplikacji
EXPOSE 8043

# Uruchamiamy aplikację
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8043", "--proxy-headers"]
