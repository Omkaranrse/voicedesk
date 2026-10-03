#!/usr/bin/env bash
set -e

echo "Pulling Ollama model..."
ollama pull llama3.2:3b

echo "Downloading Speaches Whisper model..."
curl -X POST http://localhost:8000/v1/models/Systran/faster-whisper-small

echo "All models are ready."
