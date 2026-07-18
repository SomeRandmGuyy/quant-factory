import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sample_prices"


def test_cli_backtest_exits_zero():
    cmd = [
        sys.executable, "-m", "quant_lab.cli", "backtest",
        "--strategy", "multi_factor",
        "--tickers", "AAPL,MSFT",
        "--start", "2024-01-02",
        "--end", "2024-02-29",
        "--provider", "csv",
        "--data-dir", str(FIXTURES),
    ]
    env = {**dict(**__import__("os").environ), "PYTHONPATH": str(Path(__file__).resolve().parents[2])}
    # parents[2] is packages/core
    proc = subprocess.run(cmd, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])})
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "metrics" in proc.stdout or "final_value" in proc.stdout
