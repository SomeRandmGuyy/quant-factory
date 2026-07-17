"""Settings load data paths from env."""
import os
from quant_lab_api.config import Settings


def test_settings_reads_csv_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CSV_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FUNDAMENTALS_FILE", str(tmp_path / "f.csv"))
    s = Settings()
    assert s.csv_data_dir == str(tmp_path)
