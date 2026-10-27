import json
from pathlib import Path

import pandas as pd
import pytest

from src.data.manifest import collect_manifest, verify_data_manifest
from src.data.quality import climate_quality


def test_climate_cache_rejects_incomplete_duplicates_and_fill():
    frame = pd.DataFrame({"date": pd.date_range("2024-02-28", periods=3), "grid_id": "000_000",
                          "T2M_MAX": 30, "T2M_MIN": 20, "RH2M": 60, "WS10M": 3, "PRECTOTCORR": 0})
    assert climate_quality(frame, "2024-02-28", "2024-03-01")["valid"]
    assert not climate_quality(frame.iloc[:2], "2024-02-28", "2024-03-01")["valid"]
    assert not climate_quality(pd.concat([frame, frame.iloc[:1]]), "2024-02-28", "2024-03-01")["valid"]
    frame.loc[0, "PRECTOTCORR"] = -999
    assert not climate_quality(frame, "2024-02-28", "2024-03-01")["valid"]


def test_manifest_verify_does_not_rewrite_and_detects_mutation(tmp_path, monkeypatch):
    import src.data.manifest as module
    cfg = {"region": {"state_code": "MT"}, "data": {"start_year": 2024, "end_year": 2024,
           "satellite": "AQUA_M-T", "fire_base_url": "test", "power_base_url": "test"}}
    monkeypatch.setattr(module, "build_grid", lambda cfg: pd.DataFrame({"grid_id": []}))
    monkeypatch.setattr(module, "_load_ibge_polygon", lambda root: None)
    (tmp_path / "data/sample").mkdir(parents=True)
    (tmp_path / "data/raw/fire").mkdir(parents=True)
    annual = pd.DataFrame({"lat": [-12.], "lon": [-55.], "data_hora_gmt": ["2024-08-15 18:00:00"],
                           "satelite": ["AQUA_M-T"], "estado": ["MATO GROSSO"]})
    annual.to_csv(tmp_path / "data/raw/fire/focos_MT_2024.csv", index=False)
    sample = tmp_path / "data/sample/example.csv"
    sample.write_text("x\n1\n", encoding="utf-8")
    path = tmp_path / "data/data_manifest.json"
    path.write_text(json.dumps(collect_manifest(tmp_path, cfg)), encoding="utf-8")
    original = path.read_bytes()
    assert verify_data_manifest(cfg, tmp_path) == []
    sample.write_text("x\n2\n", encoding="utf-8")
    assert any("changed" in error for error in verify_data_manifest(cfg, tmp_path))
    assert path.read_bytes() == original


def test_missing_boundary_does_not_create_unmasked_grid(tmp_path):
    from src.data.build_grid import _load_ibge_polygon
    with pytest.raises(FileNotFoundError):
        _load_ibge_polygon(Path(tmp_path))


def test_invalid_boundary_fails_explicitly(tmp_path):
    from src.data.build_grid import _load_ibge_polygon
    folder = tmp_path / "data/geo"
    folder.mkdir(parents=True)
    (folder / "mato_grosso_ibge.geojson").write_text('{"features": []}')
    with pytest.raises(ValueError, match="GeoJSON"):
        _load_ibge_polygon(tmp_path)
