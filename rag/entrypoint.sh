#!/bin/bash

# Start the Ollama service in the background
ollama serve &

# Wait for the Ollama service to be ready
until ollama list > /dev/null 2>&1; do
  echo "Waiting for Ollama service to start..."
  sleep 2
done

# Pull the required model (if not already available)
if ! ollama list | grep -q 'llama3.2:3b-instruct-fp16'; then
  echo "Pulling model llama3.2:3b-instruct-fp16..."
  ollama pull llama3.2:3b-instruct-fp16
fi

# Run your application
python main.py
