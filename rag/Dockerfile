# rag/Dockerfile

# ================================
# Stage 1: Builder
# ================================
FROM ubuntu:22.04 AS builder

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Download and install Ollama using the official install script
RUN curl -fsSL https://ollama.com/install.sh | sh

# ================================
# Stage 2: Runtime
# ================================
FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install runtime dependencies, including OpenGL libraries and GLib
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    supervisor \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for running the application
RUN useradd -m appuser

# Set working directory
WORKDIR /app
RUN chown -R appuser:appuser /app

# Copy Ollama from the builder stage
COPY --from=builder /usr/local/bin/ollama /usr/local/bin/ollama

# Ensure Ollama binary has execute permissions
RUN chmod +x /usr/local/bin/ollama

# Copy application code
COPY . /app

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Ensure necessary directories are created and have proper permissions
RUN mkdir -p /home/appuser/.ollama/tmp && \
    mkdir -p /var/log/supervisor /var/run /app/run && \
    chmod -R 755 /var/log/supervisor /var/run /app/run /home/appuser/.ollama && \
    chown -R appuser:appuser /home/appuser/.ollama

# Ensure Supervisor's log and run directories are writable by root
RUN mkdir -p /var/log/supervisor /var/run && \
    chmod -R 755 /var/log/supervisor /var/run

# Copy Supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose necessary ports
EXPOSE 8042 11434

# Start Supervisor as root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
