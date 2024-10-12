# Użyj bazowego obrazu z obsługą CUDA
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Ustaw katalog roboczy w kontenerze
WORKDIR /app

# Zainstaluj zależności systemowe
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    sqlite3 \
    libsqlite3-dev \
    ca-certificates \
    # Zależności dla Ollama
    libunwind-dev \
    libssl-dev \
    # Dodatkowe zależności dla bibliotek używanych w projekcie
    libgl1-mesa-glx \
    pandoc \
    poppler-utils \
    libpoppler-cpp-dev \
    tesseract-ocr \
    libtesseract-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Zweryfikuj wersję sqlite3 (powinna być >= 3.35.0)
RUN sqlite3 --version

# Zainstaluj Python
RUN apt-get update && apt-get install -y python3.10 python3-pip

# Zainstaluj Ollama (jeśli jest potrzebne)
RUN curl -sSfL https://ollama.ai/install.sh | bash

# Uaktualnij pip
RUN pip3 install --no-cache-dir --upgrade pip

# Skopiuj plik requirements.txt i zainstaluj zależności Pythona
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Skopiuj kod aplikacji
COPY . .

# Skopiuj i ustaw uprawnienia dla skryptu entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Upewnij się, że skrypty Pythona są wykonywalne
RUN chmod +x main.py

# Ustaw punkt wejścia
ENTRYPOINT ["./entrypoint.sh"]
