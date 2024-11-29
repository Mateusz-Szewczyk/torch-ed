FROM ubuntu:22.04

# Ustaw zmienną środowiskową, aby uniknąć interaktywnych promptów
ENV DEBIAN_FRONTEND=noninteractive

# Zainstaluj zależności systemowe
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Stwórz użytkownika aplikacji
RUN useradd -ms /bin/bash appuser

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj kod aplikacji
COPY . /app

# Zainstaluj zależności Pythona
RUN pip3 install --no-cache-dir -r requirements.txt

CMD bash -c "
  until nc -z db 5432; do
    echo 'Czekam na połączenie z bazą danych...';
    sleep 5;
  done;
  python init_db.py;
"

# Zmień użytkownika na "appuser"
USER appuser

# Eksponuj port aplikacji
EXPOSE 8042

# Uruchom aplikację
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8042"]
