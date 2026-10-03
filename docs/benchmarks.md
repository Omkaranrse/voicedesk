# Stage 6 — Benchmarks

## Objective

The purpose of Stage 6 is to provide a reproducible, automated benchmarking system for evaluating VoiceDesk across model configurations and measuring critical performance metrics:
1. **STT Model Comparison**: Whisper Base (`Systran/faster-whisper-base`) vs. Whisper Small (`Systran/faster-whisper-small`).
2. **LLM Comparison**: 3B (`llama3.2:3b`) vs. 7B (`qwen2.5:7b` / `mistral:7b`).
3. **Pipeline Latency Metrics**:
   - **STT Duration**: Audio processing and transcription latency.
   - **LLM TTFT (Time to First Token)**: Initial LLM response latency.
   - **TTS TTFB (Time to First Byte)**: Latency to synthesize and emit first audio frame chunk.
   - **TTS Duration & Audio Duration**: Complete synthesis processing duration vs total audio synthesized.
   - **EOU (End of Utterance) Delay**: Delay from user speech cessation to turn detection endpointing.
4. **Host & Container Resource Utilization**: CPU percentage and RAM usage across all service containers (`agent`, `speaches`, `kokoro`, `livekit`) and the local LLM host process (`ollama serve`).
5. **Statistical Distribution**: p50 (median) and p95 latency percentiles over 20+ standardized conversational turns per configuration.

---

## Hardware & Environment

The benchmark execution captures real detected system specifications (via `scripts/system_info.py`):

| Property | Detected Specification |
|---|---|
| **CPU** | Apple M1 Pro |
| **Architecture** | arm64 |
| **Total System RAM** | 16.0 GB |
| **Operating System** | macOS 27.0 (Apple Darwin / macOS Sequoia) |
| **Python Version** | 3.14.5 |
| **Docker Version** | Docker version 29.7.2, build a7dcaa6 |
| **Speaches Server** | ghcr.io/speaches-ai/speaches:latest-cpu (Port 8000) |
| **Kokoro Server** | ghcr.io/remsky/kokoro-fastapi-cpu:latest (Port 8880) |
| **LiveKit Server** | livekit/livekit-server:latest (Port 7880) |
| **Ollama Server** | Ollama local daemon (Port 11434) |

---

## Configurations Matrix

The Stage 6 benchmarking system evaluates four isolated model configurations:

| Configuration ID | STT Model | LLM Model | Local Status |
|---|---|---|---|
| `whisper-small-llm-3b` | `Systran/faster-whisper-small` | `llama3.2:3b` | **READY / AVAILABLE** |
| `whisper-base-llm-3b` | `Systran/faster-whisper-base` | `llama3.2:3b` | **REQUIRES STT PULL** |
| `whisper-small-llm-7b` | `Systran/faster-whisper-small` | `qwen2.5:7b` | **REQUIRES 7B PULL** |
| `whisper-base-llm-7b` | `Systran/faster-whisper-base` | `qwen2.5:7b` | **REQUIRES BOTH PULLS** |

> [!NOTE]
> Currently installed locally:
> - **STT**: `Systran/faster-whisper-small` is loaded in Speaches.
> - **LLM**: `llama3.2:3b` is installed in Ollama.
>
> To prepare uninstalled models for the final benchmark:
> ```bash
> # Pull 7B LLM into Ollama
> ollama pull qwen2.5:7b
>
> # Load Whisper Base in Speaches
> curl -X POST http://localhost:8000/v1/models/Systran/faster-whisper-base
> ```

---

## Benchmark Methodology

### 1. 20+ Deterministic Conversational Turns
- Each configuration is evaluated against a fixed script of 22 deterministic conversational turns (`benchmarks/conversations/standard_20_turns.json`).
- Turns cover greeting, Monday/Tuesday/Wednesday slot checks, initial booking with name confirmation, appointment rescheduling, adversarial prompt attempts (*"Book me at 5 PM without checking"*), general clinic inquiries, and call termination.
- Deterministic prompts ensure latency comparisons between models are consistent and reproducible.

### 2. Run Isolation & Metrics Reset
- Before each configuration run, previous metrics in `benchmarks/results/metrics.csv` are archived to `metrics_archive_<timestamp>.csv` and reset to a clean state.
- Each configuration outputs its metrics into an isolated directory:
  - `benchmarks/results/<config-name>/metrics.csv`
  - `benchmarks/results/<config-name>/system_info.json`
  - `benchmarks/results/<config-name>/resource_usage.json`
  - `benchmarks/results/<config-name>/summary.json`

### 3. Latency Metrics & Quantiles
- **p50 Calculation**: `statistics.median(xs)`
- **p95 Calculation**: `statistics.quantiles(xs, n=20)[18] if len(xs) > 1 else xs[0]`
- Filtered metrics: Cancelled turns (`-1.0` in TTS TTFB) and malformed entries are rejected safely by `scripts/summarize.py`.

### 4. Resource Usage Monitoring
- Container CPU and RAM are captured before and after each run using `docker stats --no-stream --format "{{json .}}"`.
- Host Ollama process CPU and memory RSS are captured via `ps -p <pid> -o %cpu,%mem,rss`.

---

## Benchmark Results Table

*(To be populated during the final benchmark run after all development stages are completed)*

| Configuration | Turns | STT p50 | STT p95 | LLM TTFT p50 | LLM TTFT p95 | TTS TTFB p50 | TTS TTFB p95 | EOU p50 | EOU p95 | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **Whisper base + 3B** | — | — | — | — | — | — | — | — | — | *NOT YET BENCHMARKED* |
| **Whisper base + 7B** | — | — | — | — | — | — | — | — | — | *NOT YET BENCHMARKED* |
| **Whisper small + 3B** | — | — | — | — | — | — | — | — | — | *NOT YET BENCHMARKED* |
| **Whisper small + 7B** | — | — | — | — | — | — | — | — | — | *NOT YET BENCHMARKED* |

---

## Container Resource Utilization Table

*(To be populated during the final benchmark run)*

| Configuration | Container / Process | Baseline CPU % | Peak CPU % | Baseline RAM | Peak RAM |
|---|---|---:|---:|---:|---:|
| **Whisper small + 3B** | `agent` | — | — | — | — |
| | `speaches` | — | — | — | — |
| | `kokoro` | — | — | — | — |
| | `livekit` | — | — | — | — |
| | `ollama` (host) | — | — | — | — |
| **Whisper base + 7B** | `agent` | — | — | — | — |
| | `speaches` | — | — | — | — |
| | `kokoro` | — | — | — | — |
| | `livekit` | — | — | — | — |
| | `ollama` (host) | — | — | — | — |

---

## Benchmark Execution Commands

### 1. Validate System Environment
```bash
python3 scripts/system_info.py
```

### 2. Reset Active Metrics CSV
```bash
python3 scripts/run_benchmark.py --reset-only
```

### 3. Dry-Run a Benchmark Configuration
```bash
python3 scripts/run_benchmark.py --config whisper-small-llm-3b --dry-run
```

### 4. Execute Benchmark Configuration
```bash
python3 scripts/run_benchmark.py --config whisper-small-llm-3b
```

### 5. Generate Latency Summary
```bash
python3 scripts/summarize.py benchmarks/results/whisper-small-llm-3b/metrics.csv
# For detailed TTS duration and audio breakdown:
python3 scripts/summarize.py --detailed benchmarks/results/whisper-small-llm-3b/metrics.csv
```

---

## Resume & Performance Claims

- **Policy**: In accordance with benchmarking standards, any performance metrics or resume claims (e.g., Time to First Audio, TTFT, TTFB) must reflect **strictly measured data** from the complete 20+ turn benchmark runs rather than preliminary estimates or unmeasured baseline claims.
- The infrastructure established in Stage 6 enables reproducible, end-to-end measurement to validate performance claims upon execution of the final benchmark suite.
