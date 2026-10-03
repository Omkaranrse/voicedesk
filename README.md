# VoiceDesk

VoiceDesk is an ultra-low latency real-time voice AI receptionist for clinic appointment booking, powered by LiveKit, Silero VAD, Speaches (faster-whisper), Ollama (llama3.2:3b), and Kokoro TTS.

## Architecture

VoiceDesk supports two audio ingress paths:
1. **WebRTC Browser Audio**: Direct WebRTC connection via Next.js web application.
2. **SIP Telephony (Stage 8)**: Inbound SIP telephone calls via LiveKit SIP service.

```
Phone (Linphone) -> SIP UDP/TCP 5060 -> LiveKit SIP -> LiveKit Room -> VoiceDesk Agent -> STT -> LLM -> TTS -> LiveKit SIP -> Phone
```

## Quick Start (Standard Web Stack)

1. Setup environment configuration:
   ```bash
   cp .env.example .env
   ```
2. Start the core services:
   ```bash
   make up
   # Or: docker compose up -d --build
   ```
3. Run test suite:
   ```bash
   make test
   ```

## SIP Telephony (Stage 8)

SIP telephony is optional and managed via the `sip` Compose profile.

### 1. Start Stack with SIP Profile
```bash
make sip-up
# Or: docker compose --profile sip up -d --build
```

### 2. Configure Inbound Trunk and Dispatch Rule
Ensure LiveKit CLI (`lk`) is installed (`brew install livekit-cli`):
```bash
# Load credentials from .env
set -a && source .env && set +a

# Create Inbound Trunk
lk sip inbound create infra/sip/inbound-trunk.json

# Create Dispatch Rule (routes to 'voicedesk' agent)
lk sip dispatch create infra/sip/dispatch-rule.json
```

Verify status:
```bash
lk sip inbound list
lk sip dispatch list
```

### 3. Connect Linphone on a Mobile Device
1. Install **Linphone** on your phone (iOS / Android).
2. Connect your phone to the same Wi-Fi network as your laptop.
3. Open Linphone and dial the SIP URI:
   ```text
   sip:anything@<LAPTOP-LAN-IP>:5060
   ```
   *(To find your laptop LAN IP on macOS, run `ipconfig getifaddr en0`)*.
4. Transport setting: Use **UDP** or **TCP**.
5. Once dialed, LiveKit SIP creates a room (`sip-call-_...`) and automatically assigns the `voicedesk` agent. The agent greets the caller and processes appointment inquiries and bookings in real-time.
