#!/usr/bin/env bash
set -e

echo "=== VoiceDesk Smoke Test ==="

echo ""
echo "1. Testing TTS (Kokoro)..."

curl -sS -f http://localhost:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "Hello, this is VoiceDesk.",
    "voice": "af_alloy",
    "response_format": "mp3"
  }' \
  --output /tmp/voicedesk-test.mp3

test -s /tmp/voicedesk-test.mp3
echo "TTS: OK"

echo ""
echo "2. Testing STT (Speaches)..."

say "Hello, this is VoiceDesk." -o /tmp/voicedesk-test.aiff
afconvert -f WAVE -d LEI16@16000 \
  /tmp/voicedesk-test.aiff \
  /tmp/voicedesk-test.wav

STT_RESULT=$(curl -sS -f \
  http://localhost:8000/v1/audio/transcriptions \
  -F "file=@/tmp/voicedesk-test.wav" \
  -F "model=Systran/faster-whisper-small")

echo "STT response: $STT_RESULT"
echo "STT: OK"

echo ""
echo "3. Testing LLM (Ollama)..."

LLM_RESULT=$(curl -sS -f \
  http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [
      {
        "role": "user",
        "content": "Say hello in exactly five words."
      }
    ]
  }')

echo "LLM response: $LLM_RESULT"
echo "LLM: OK"

echo ""
echo "=== ALL SMOKE TESTS PASSED ==="
