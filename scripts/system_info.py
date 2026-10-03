#!/usr/bin/env python3
"""System information detector for VoiceDesk benchmarking.
Detects CPU, RAM, architecture, OS, Docker, Python, and local AI model versions.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


def _run_cmd(cmd: str) -> str:
    """Run a shell command and return clean stdout string."""
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def get_cpu_info() -> str:
    """Detect human-readable CPU brand/model."""
    if sys.platform == "darwin":
        brand = _run_cmd("sysctl -n machdep.cpu.brand_string")
        if brand and brand != "unknown":
            return brand
    elif sys.platform == "linux":
        model = _run_cmd("lscpu | grep 'Model name' | cut -d':' -f2")
        if model and model != "unknown":
            return model.strip()
    return platform.processor() or platform.machine()


def get_ram_info() -> str:
    """Detect total system RAM."""
    if sys.platform == "darwin":
        mem_bytes = _run_cmd("sysctl -n hw.memsize")
        if mem_bytes.isdigit():
            gb = int(mem_bytes) / (1024**3)
            return f"{gb:.1f} GB"
    elif sys.platform == "linux":
        mem_kb = _run_cmd("grep MemTotal /proc/meminfo | awk '{print $2}'")
        if mem_kb.isdigit():
            gb = int(mem_kb) / (1024**2)
            return f"{gb:.1f} GB"
    return "unknown"


def get_docker_version() -> str:
    """Detect Docker daemon/CLI version."""
    v = _run_cmd("docker --version")
    return v if v else "Docker not found"


def get_ollama_models() -> list[dict[str, Any]]:
    """Fetch locally installed Ollama models via API."""
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", headers={"User-Agent": "VoiceDesk-Bench"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return [
                {
                    "name": m.get("name"),
                    "parameter_size": m.get("details", {}).get("parameter_size", "unknown"),
                    "quantization": m.get("details", {}).get("quantization_level", "unknown"),
                    "size_gb": round(m.get("size", 0) / (1024**3), 2),
                }
                for m in data.get("models", [])
            ]
    except Exception:
        return []


def get_speaches_models() -> list[str]:
    """Fetch loaded Speaches STT models via API."""
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:8000/v1/models", headers={"User-Agent": "VoiceDesk-Bench"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return [m.get("id") for m in data.get("data", []) if m.get("id")]
    except Exception:
        return []


def collect_system_info() -> Dict[str, Any]:
    """Return dictionary with complete system and runtime specifications."""
    return {
        "os": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "python_version": platform.python_version(),
        "docker_version": get_docker_version(),
        "ollama_models": get_ollama_models(),
        "speaches_models": get_speaches_models(),
    }


def main():
    info = collect_system_info()
    print("==================================================")
    print("VoiceDesk System Hardware & Software Info")
    print("==================================================")
    print(f"OS:            {info['os']}")
    print(f"Architecture:  {info['architecture']}")
    print(f"CPU:           {info['cpu']}")
    print(f"Total RAM:     {info['ram']}")
    print(f"Python:        {info['python_version']}")
    print(f"Docker:        {info['docker_version']}")
    print("--------------------------------------------------")
    print("Ollama Models Installed:")
    if info["ollama_models"]:
        for m in info["ollama_models"]:
            print(f"  - {m['name']} ({m['parameter_size']}, {m['size_gb']} GB, {m['quantization']})")
    else:
        print("  (None or Ollama unreachable)")
    print("--------------------------------------------------")
    print("Speaches STT Models Loaded:")
    if info["speaches_models"]:
        for m in info["speaches_models"]:
            print(f"  - {m}")
    else:
        print("  (None or Speaches unreachable)")
    print("==================================================")


if __name__ == "__main__":
    main()
