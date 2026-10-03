# VoiceDesk Production Hardening Baseline (Phase 0)

**Date**: October 2026  
**Auditor/Engineer**: Principal Reliability & Security Engineering  
**Scope**: Repository State Prior to Phase 1 Implementation

---

## 1. System Inventory & Environment

### Runtime & Toolchain
- **Host OS**: macOS 27.0 (Apple Darwin, aarch64 / Apple Silicon M1 Pro)
- **Host Python Version**: Python 3.14.5
- **Docker Base Python Version**: Python 3.12-slim (`agent/Dockerfile`)
- **Package Manager**: Astral `uv` 0.11.16
- **Core Agent Framework**: `livekit-agents` v1.8.3
- **LiveKit Client Protocol**: `livekit` v1.1.18, `livekit-api` v1.2.1, `livekit-protocol` v1.1.27
- **Inference Plugins**: `livekit-plugins-openai` v1.8.3, `livekit-plugins-silero` v1.8.3
- **Validation & Settings**: `pydantic` v2.13.5, `pydantic-settings` v2.15.0
- **HTTP Client**: `httpx` v0.28.1
- **Testing**: `pytest` v9.1.1, `ruff` v0.16.9

### Existing Test Suite Baseline
- **Command Executed**: `cd agent && uv run pytest`
- **Total Test Count**: 27 tests across 8 test suites
- **Results**:
  - `tests/test_benchmark_infra.py`: 5 passed
  - `tests/test_call_timeout.py`: 3 passed
  - `tests/test_db.py`: 2 passed
  - `tests/test_guardrails.py`: 3 passed
  - `tests/test_kokoro_tts.py`: 4 passed
  - `tests/test_privacy.py`: 2 passed
  - `tests/test_resilient_llm.py`: 4 passed
  - `tests/test_tools.py`: 4 passed
- **Status**: 27 passed, 0 failed, 10 deprecation warnings (`asyncio.iscoroutinefunction` in `livekit.rtc.event_emitter` under Python 3.14) in 11.79s.

---

## 2. Current Architecture Summary

The existing architecture operates as a single-node, multi-container real-time pipeline:

```
[WebRTC Client / SIP Linphone]
       │
       ▼
[LiveKit Server 1.13.7 (livekit:7880, UDP 50000-50020)]
  ▲                ▲
  │ (WebRTC)       │ (Signaling & Dispatch)
[LiveKit SIP]    [Redis 7 (Unauthenticated)]
       │
       ▼ (WebSocket ws://livekit:7880)
[VoiceDesk Agent (livekit.agents 1.8.3)]
   ├─ Silero VAD (Endpointing: min_delay=0.45s, max_delay=1.6s)
   ├─ Speaches STT (faster-whisper-small via OpenAI batch HTTP endpoint)
   ├─ Resilient LLM Layer (Ollama llama3.2:3b + FallbackAdapter + ResilientLLM)
   ├─ Clinic Tools (check_slots, book_slot, cancel_slot, reschedule_slot)
   │     └─ SQLite Database (voicedesk.db, WAL mode, synchronous I/O)
   ├─ Kokoro TTS (FastAPI direct PCM streaming, af_alloy voice)
   └─ Metrics Logger (Synchronous CSV appends)
```

---

## 3. Current Security Posture & Vulnerability Baseline

1. **Frontend Token Generation (`frontend/app/api/token/route.ts`)**:
   - Room names and participant identities generated with `Math.floor(Math.random() * 10_000)`. Max integer space is 10,000, creating high collision probability (>50% at 118 active sessions) where callers could join the same room and overhear patient details.
   - Throws an unhandled runtime error if `process.env.NODE_ENV !== 'development'`, blocking production deployments.
   - Zero authentication, session verification, or rate limiting; any client can request unlimited LiveKit tokens.
2. **Appointment Operations (`agent/src/voicedesk/tools.py`)**:
   - `cancel_slot` and `reschedule_slot` accept raw unvalidated strings and delete or modify appointments based solely on caller name (`booked_by`).
   - No phone number or confirmation code verification exists.
   - Any caller can cancel or reschedule another patient's appointment by knowing or guessing their name.
3. **Telephony Ingress (`infra/sip/inbound-trunk.json`)**:
   - Configures `"allowed_addresses": ["0.0.0.0/0"]` without SIP digest authentication. Allows arbitrary internet traffic to send SIP INVITE requests to port 5060.
4. **State Store Authentication (`docker-compose.yml`)**:
   - Redis 7 container runs without a password (`requirepass` is unset).
5. **Container Privilege**:
   - `agent/Dockerfile` runs as the `root` superuser with no non-root user defined.

---

## 4. Concurrency & Async Execution Assumptions

1. **Event-Loop Blocking Disk I/O**:
   - `agent/src/voicedesk/tools.py` directly executes synchronous `sqlite3` methods (`db.free_slots`, `db.book`, `db.cancel`, `db.reschedule`) inside async coroutines.
   - `agent/src/voicedesk/metrics.py` synchronously opens and appends to `metrics.csv` inside an event handler on the main asyncio thread.
   - These calls block the event loop during database lock contention and disk I/O, risking audio stutter and jitter.
2. **Worker Process Concurrency**:
   - `AgentServer(num_idle_processes=1)` in `main.py` maintains only one pre-warmed idle worker. Second incoming callers encounter process initialization latency.
3. **Network Port Capacity**:
   - WebRTC UDP port range in `infra/livekit/livekit.yaml` is `50000-50020` (21 ports), limiting theoretical concurrency to ~10 simultaneous WebRTC sessions.
   - SIP RTP port range in `infra/sip/config.yaml` is `20000-20050` (51 ports), limiting theoretical concurrency to ~25 SIP calls.

---

## 5. Latency & Performance Measurements

- **Live End-to-End Latency Under Load**: **Not measured** (requires live Docker stack and automated telephony harness).
- **Batch STT Turn-around Time**: **Not measured** (Speaches model inference depends on active audio duration).
- **Isolated Component Benchmarks (from historical runs in `benchmarks/results/`)**:
  - Direct Kokoro TTS First-Byte Latency: ~0.15s – 0.35s on short sentences.
  - LLM TTFT (Ollama `llama3.2:3b` on Apple Silicon M1 Pro): ~0.35s – 0.65s.
- **Concurrent Load Degradation**: **Not measured** (no multi-caller stress test exists yet).

---

## 6. Known Limitations Identified in Audit

1. **Database Multi-Process Scaling**: SQLite in WAL mode handles single-instance concurrency well, but multi-node agent clustering will require PostgreSQL or distributed locking.
2. **Batch STT vs. Streaming STT**: Speaches HTTP API operates in batch mode (VAD endpointing must finalize before audio upload), introducing a minimum ~450ms serialization latency.
3. **Context Window Accumulation**: Conversation history is not truncated or summarized, leading to token growth over extended phone calls.
4. **Docker Health Checks Missing**: `docker-compose.yml` does not define health checks for Redis, LiveKit, Speaches, Kokoro, or the Agent.
