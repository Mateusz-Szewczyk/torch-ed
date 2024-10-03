# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama (Update this based on Ollama's installation instructions)
# Assuming there is a Linux binary or installation script
RUN curl -O https://ollama.ai/install.sh && \
    bash install.sh && \
    rm install.sh

# Install additional dependencies required by Ollama
# e.g., if it requires libcudart or other libraries

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Make sure main.py is executable
RUN chmod +x main.py

# Set the entry point
CMD ["python", "main.py"]
