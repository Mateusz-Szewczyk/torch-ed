# Use a base image with CUDA support
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    sqlite3 \
    libsqlite3-dev \
    ca-certificates \
    # Dependencies for Ollama
    libunwind-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Verify sqlite3 version (should be >= 3.35.0)
RUN sqlite3 --version

# Install Python
RUN apt-get update && apt-get install -y python3.10 python3-pip

# Install Ollama
RUN curl -sSfL https://ollama.ai/install.sh | bash

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Copy and set permissions for entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Ensure your Python scripts are executable
RUN chmod +x main.py

# Set the entry point
ENTRYPOINT ["./entrypoint.sh"]
