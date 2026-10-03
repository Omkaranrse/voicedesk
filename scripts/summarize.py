#!/usr/bin/env python3
"""Summarize VoiceDesk benchmark metrics CSV.
Calculates p50, p95, and sample counts for STT, LLM, TTS, and EOU latencies.
Robustly handles variable row widths and ignores malformed rows.
"""

import csv
import os
import statistics
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


def parse_metrics_csv(filepath: str) -> Tuple[Dict[str, List[float]], Dict[str, List[float]], List[str]]:
    """Parse metrics CSV file and return primary metrics, detailed metrics, and parsing warnings.
    
    Handles both legacy format ([time, room, metric_name, val]) and 
    current format ([time, room, 'tts', ttfb, duration, audio_dur, ...]).
    """
    if not os.path.exists(filepath):
        print(
            f"Error: metrics CSV not found: '{filepath}'.\n"
            "Run benchmarks first (e.g. 'python scripts/run_benchmark.py') or specify a valid CSV file.",
            file=sys.stderr,
        )
        sys.exit(1)

    primary_vals = defaultdict(list)
    detailed_vals = defaultdict(list)
    errors = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for line_num, row in enumerate(reader, 1):
            if not row or not any(field.strip() for field in row):
                continue  # skip empty lines

            if len(row) < 4:
                errors.append(f"Line {line_num}: malformed row (expected at least 4 fields, got {len(row)}): {row}")
                continue

            raw_metric = row[2].strip().lower()
            raw_val = row[3].strip()

            try:
                val = float(raw_val)
            except ValueError:
                errors.append(f"Line {line_num}: non-numeric latency value '{raw_val}' in row: {row}")
                continue

            # Standardize core metric keys
            if raw_metric in ("llm", "llm_ttft"):
                metric_key = "llm"
            elif raw_metric in ("tts", "tts_ttfb"):
                metric_key = "tts"
            elif raw_metric in ("stt", "stt_duration"):
                metric_key = "stt"
            elif raw_metric in ("eou", "eou_delay"):
                metric_key = "eou"
            else:
                metric_key = raw_metric

            # For TTS, negative values (like -1.0) indicate cancelled turns
            if metric_key == "tts" and val < 0:
                continue

            primary_vals[metric_key].append(val)

            # Extra columns available in full TTS rows
            if raw_metric == "tts" and len(row) >= 6:
                try:
                    duration = float(row[4].strip())
                    audio_dur = float(row[5].strip())
                    if duration >= 0:
                        detailed_vals["tts_duration"].append(duration)
                    if audio_dur >= 0:
                        detailed_vals["tts_audio_duration"].append(audio_dur)
                except (ValueError, IndexError):
                    pass

    return primary_vals, detailed_vals, errors


def compute_quantiles(xs: List[float]) -> Tuple[float, float]:
    """Compute p50 and p95 using standard 20-quantile formula."""
    if not xs:
        return 0.0, 0.0
    p50 = statistics.median(xs)
    p95 = (
        statistics.quantiles(xs, n=20)[18]
        if len(xs) > 1
        else xs[0]
    )
    return p50, p95


def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print("Usage: summarize.py [--detailed] [METRICS_CSV_PATH]")
        print("Calculates p50, p95, and count for STT, LLM, TTS, and EOU metrics.")
        return

    detailed = "--detailed" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--detailed"]

    filepath = args[0] if len(args) > 0 else "benchmarks/results/metrics.csv"

    primary, detailed_metrics, parse_errors = parse_metrics_csv(filepath)

    if not primary:
        print(f"No valid metric entries found in {filepath}.")
        if parse_errors:
            print(f"Encountered {len(parse_errors)} parsing errors (run with bad rows).", file=sys.stderr)
        return

    # Standard format output as required
    for metric, xs in sorted(primary.items()):
        p50, p95 = compute_quantiles(xs)
        print(
            f"{metric:14} "
            f"n={len(xs):3} "
            f"p50={p50:.2f}s "
            f"p95={p95:.2f}s"
        )

    # Detailed breakdown if requested
    if detailed and detailed_metrics:
        print("\n--- Detailed Breakdown ---")
        for metric, xs in sorted(detailed_metrics.items()):
            p50, p95 = compute_quantiles(xs)
            print(
                f"{metric:18} "
                f"n={len(xs):3} "
                f"p50={p50:.2f}s "
                f"p95={p95:.2f}s"
            )

    if parse_errors:
        print(f"\n[Note: Ignored {len(parse_errors)} malformed/empty row(s)]", file=sys.stderr)


if __name__ == "__main__":
    main()
