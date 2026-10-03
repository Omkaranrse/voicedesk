# VoiceDesk 🎙️🏥
### Autonomous Real-Time Clinical AI Voice Receptionist

[![Live Demo](https://img.shields.io/badge/Live_Demo-Vercel-black?style=for-the-badge&logo=vercel)](https://voicedesk-omkar.vercel.app)
[![LiveKit Agents](https://img.shields.io/badge/LiveKit_Agents-2.0-cyan?style=for-the-badge&logo=livekit)](https://livekit.io)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js)](https://nextjs.org)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![Creator](https://img.shields.io/badge/Produced_By-Omkar_Anarse-00f0ff?style=for-the-badge)](https://omkar-anarse.vercel.app)

VoiceDesk is an enterprise-grade, ultra-low latency real-time AI voice receptionist designed for clinic and medical practice appointment booking. Built on **LiveKit WebRTC**, **Silero VAD**, **Faster-Whisper (Speaches)**, **LLaMA 3.2 / 3.3 (Groq/Ollama)**, and **Kokoro TTS (24kHz Direct PCM)**, it achieves sub-second conversational turn latencies with end-to-end appointment verification and security.

---

## 🌟 Key Features

- **Sub-Second Voice Conversational Loop**: End-to-end audio roundtrip (Speech → STT → LLM Stream → TTS Chunking → WebRTC) with typical TTFB under 400ms.
- **Dual Audio Ingress**:
  - **WebRTC Browser Audio**: Interactive web application with real-time waveform visualizers, natural interruption detection, and live session stats.
  - **SIP Telephony**: Inbound phone call ingress via LiveKit SIP for standard mobile or landline telephony (Linphone, Twilio, Telnyx).
- **Interactive Appointments Dashboard (`/appointments`)**:
  - Live calendar and schedule grid tracking all weekly clinic slots.
  - Real-time booking status, patient names, and 4-digit security PIN verification.
  - Direct search and day-filtering (Monday – Wednesday).
- **Hardened Scheduling Engine**:
  - **Input Validation**: Strict Pydantic models for all agent tool parameters (`check_slots`, `book_slot`, `cancel_slot`, `reschedule_slot`).
  - **4-Digit Confirmation Code**: Generates and enforces unique numeric PINs to prevent unauthorized appointment modifications or cancellations.
  - **Atomic Transactions & Lock Resilience**: Bounded retry with exponential backoff on SQLite WAL mode locks with zero-leak transactional rollbacks.
- **Natural Turn-Taking & Anti-Hallucination**:
  - Tuned Silero VAD endpointing (`min_delay: 0.6s`, `max_delay: 1.4s`) preventing awkward turn cutting.
  - Sliding context window truncation preserving system prompts while capping token bloat on extended calls.
  - Strict clinical system prompt disallowing medical diagnosis while enforcing slot confirmation.

---

## 🏗️ Architecture

```mermaid
graph TD
    UserPhone[Telephone Caller] -->|SIP UDP 5060| SIP[LiveKit SIP Service]
    UserWeb[Browser Client] -->|WebRTC Media| LK[LiveKit Media SFU]
    SIP --> LK

    subgraph VoiceDesk Agent Worker
        VAD[Silero VAD] -->|Audio Chunks| STT[Faster-Whisper / Speaches / Groq]
        STT -->|Transcript| LLM[LLaMA 3.2 / Groq / OpenAI]
        LLM -->|Preemptive Stream| TTS[Kokoro TTS / 24kHz PCM]
        LLM -.->|Tool Calls| DB[(SQLite WAL / voicedesk.db)]
    end

    LK <-->|Agent Protocol| VoiceDesk Agent Worker
    TTS -->|Audio Packets| LK
```

---

## 🚀 Live Demo & Deployment

| Service | Link / Target | Purpose |
| :--- | :--- | :--- |
| **Live Receptionist** | [voicedesk-omkar.vercel.app](https://voicedesk-omkar.vercel.app) | Public voice calling interface |
| **Appointments Dashboard**| [voicedesk-omkar.vercel.app/appointments](https://voicedesk-omkar.vercel.app/appointments) | Live visual clinic schedule |
| **Creator Portfolio** | [omkar-anarse.vercel.app](https://omkar-anarse.vercel.app) | Portfolio of Omkar Anarse |

---

## 🛠️ Quick Start (Local Development)

### Prerequisites
- Python 3.12+ (or [uv](https://docs.astral.sh/uv/))
- Node.js 20+ & pnpm
- Docker & Docker Compose (optional for local STT/TTS containers)

### 1. Clone & Configure Environment
```bash
git clone https://github.com/Omkaranrse/voicedesk.git
cd voicedesk
cp .env.example .env
```

Fill in your `.env` with your LiveKit credentials (or [LiveKit Cloud](https://cloud.livekit.io)):
```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
```

### 2. Run the Full Stack via Docker
```bash
make up
# Or: docker compose up -d --build
```

### 3. Run the Voice Agent Worker
```bash
cd agent
uv sync
uv run python -m voicedesk.main dev
```

### 4. Run the Next.js Frontend
```bash
cd frontend
pnpm install
pnpm dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📊 Management & Verification CLI

VoiceDesk includes built-in commands for monitoring and inspection:

```bash
# View live appointment bookings & PINs in the terminal
make slots

# Run comprehensive test suite (Unit, Security, Guardrails, E2E)
make test

# Run latency and speech synthesis benchmarks
uv run --directory agent python ../benchmarks/run_benchmarks.py
```

Example output of `make slots`:
```text
=================================================================
         VOICEDESK CLINICAL APPOINTMENT SCHEDULE (LIVE)
=================================================================
DAY          | TIME     | STATUS      | PATIENT          | PIN
-----------------------------------------------------------------
Monday       | 10:00    | 📅 Booked    | Omkar Anarse     | 4819
Monday       | 11:00    | ✅ Available | -                | -
Monday       | 14:00    | ✅ Available | -                | -
Tuesday      | 10:00    | ✅ Available | -                | -
Tuesday      | 11:00    | ✅ Available | -                | -
Tuesday      | 14:00    | ✅ Available | -                | -
Wednesday    | 10:00    | ✅ Available | -                | -
Wednesday    | 11:00    | ✅ Available | -                | -
Wednesday    | 14:00    | ✅ Available | -                | -
=================================================================
```

---

## 📞 SIP Telephony Setup (Linphone / Inbound Calling)

LiveKit SIP allows regular phone calls to connect directly to the voice receptionist.

1. **Start with SIP Profile**:
   ```bash
   make sip-up
   ```
2. **Create Inbound Trunk & Dispatch Rule**:
   ```bash
   lk sip inbound create infra/sip/inbound-trunk.json
   lk sip dispatch create infra/sip/dispatch-rule.json
   ```
3. **Dial with Linphone**:
   - Open Linphone (iOS / Android / Desktop) on your local Wi-Fi.
   - Dial `sip:call@<YOUR-IP>:5060`.
   - The AI agent will answer the call, detect caller ID, and converse naturally over audio.

---

## 🛡️ Security & Reliability Posture

- **Rate Limiting**: Sliding window IP rate limiter on token generation preventing room exhaustion.
- **Cryptographic Identifiers**: UUIDv4 tokens and participant IDs mitigating collision and enumeration attacks.
- **Container Hardening**: Agent Docker container runs as unprivileged `appuser` (UID 10001).
- **Network Boundaries**: Inbound SIP trunk restricted to local subnet / loopback ranges.
- **Failover Safe**: Resilient fallback LLM orchestration and automated call duration supervisor (max 300s timeout).

---

## 👨‍💻 Author & Creator

**Omkar Anarse**  
*AI Full Stack Engineer*  
🌐 **Portfolio**: [https://omkar-anarse.vercel.app](https://omkar-anarse.vercel.app)  
🐙 **GitHub**: [@Omkaranrse](https://github.com/Omkaranrse)

---

## 📄 License
This project is licensed under the MIT License.
