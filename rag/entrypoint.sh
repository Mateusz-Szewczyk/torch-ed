#!/bin/bash

# Start the Ollama service in the background
ollama serve &

# Wait for the Ollama service to be ready
echo "Waiting for Ollama service to start..."
until ollama list > /dev/null 2>&1; do
  echo "Ollama service is starting up..."
  sleep 2
done
echo "Ollama service is up and running!"

# Check if the required model is available, and pull it if not
MODEL_NAME="llama3.2:3b-instruct-fp16"
if ! ollama list | grep -q "$MODEL_NAME"; then
  echo "Pulling the required model: $MODEL_NAME"
  ollama pull "$MODEL_NAME"
else
  echo "Model $MODEL_NAME is already available."
fi

# Run the FastAPI application using Uvicorn
# Adjust host and port as needed for your environment
echo "Starting FastAPI app with Uvicorn..."
uvicorn main_api:app --host 0.0.0.0 --port 8042
