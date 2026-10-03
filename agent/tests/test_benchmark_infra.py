import csv
import statistics
import sys
from pathlib import Path

# Ensure scripts dir is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from run_benchmark import check_models_available, reset_metrics_csv
from summarize import compute_quantiles, parse_metrics_csv
from system_info import collect_system_info


def test_compute_quantiles():
    """Verify p50 and p95 calculation matches formula."""
    xs = [float(i) for i in range(1, 21)]  # 1 to 20
    p50, p95 = compute_quantiles(xs)
    assert p50 == statistics.median(xs)
    assert p95 == statistics.quantiles(xs, n=20)[18]


def test_parse_metrics_csv_multi_format(tmp_path):
    """Verify parser handles 4-column legacy rows and 10-column current rows, ignoring bad rows."""
    test_csv = tmp_path / "test_metrics.csv"
    with open(test_csv, "w", newline="") as f:
        writer = csv.writer(f)
        # Legacy row
        writer.writerow([100.0, "room1", "llm_ttft", "0.55"])
        # Current format row
        writer.writerow(
            [
                101.0,
                "room1",
                "tts",
                "0.95",
                "1.20",
                "2.50",
                "0.001",
                "True",
                "False",
                "50",
            ]
        )
        # Cancelled turn (-1.0)
        writer.writerow(
            [102.0, "room1", "tts", "-1.0", "0.50", "0.0", "0.0", "False", "True", "20"]
        )
        # STT and EOU rows
        writer.writerow([103.0, "room1", "stt", "0.32"])
        writer.writerow([104.0, "room1", "eou", "0.15"])
        # Malformed row (too few fields)
        writer.writerow(["bad", "row"])
        # Non-numeric value
        writer.writerow([105.0, "room1", "llm", "not-a-number"])

    primary, detailed, warnings = parse_metrics_csv(str(test_csv))

    assert "llm" in primary
    assert primary["llm"] == [0.55]

    assert "tts" in primary
    assert primary["tts"] == [0.95]  # -1.0 must be excluded

    assert "stt" in primary
    assert primary["stt"] == [0.32]

    assert "eou" in primary
    assert primary["eou"] == [0.15]

    # Detailed metrics extracted
    assert "tts_duration" in detailed
    assert detailed["tts_duration"] == [1.20]

    # Warnings recorded for the 2 bad rows
    assert len(warnings) == 2


def test_system_info_collector():
    """Verify system info collection captures essential hardware details."""
    info = collect_system_info()
    assert "os" in info
    assert "cpu" in info
    assert "ram" in info
    assert "architecture" in info
    assert "python_version" in info


def test_benchmark_metrics_reset(tmp_path):
    """Verify metrics CSV reset archives existing data and creates empty clean file."""
    metrics_file = tmp_path / "metrics.csv"
    metrics_file.write_text("100.0,room,llm,0.5\n")

    archive = reset_metrics_csv(metrics_file)
    assert archive is not None
    assert archive.exists()
    assert "100.0,room,llm,0.5" in archive.read_text()
    assert metrics_file.read_text() == ""


def test_model_availability_checker():
    """Verify model availability checker accurately reflects system state."""
    mock_sys_info = {
        "ollama_models": [{"name": "llama3.2:3b"}],
        "speaches_models": ["Systran/faster-whisper-small"],
    }

    avail = check_models_available(
        "Systran/faster-whisper-small", "llama3.2:3b", mock_sys_info
    )
    assert avail["ready"] is True
    assert avail["stt_available"] is True
    assert avail["llm_available"] is True

    unavail = check_models_available(
        "Systran/faster-whisper-base", "qwen2.5:7b", mock_sys_info
    )
    assert unavail["ready"] is False
    assert unavail["stt_available"] is False
    assert unavail["llm_available"] is False
