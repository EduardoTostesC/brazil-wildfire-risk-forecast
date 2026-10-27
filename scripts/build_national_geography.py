"""Archive or benchmark IBGE2024 geography without modifying historical MT.

Derivation tool: pyshp2.3.1 (isolated optional installation), Shapely2.0.7.
The normal application loader does not need pyshp. Output paths must be new.
"""
import argparse
import gzip
import hashlib
import json
import resource
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.geo.boundaries import IBGE_SOURCE_URL, load_boundaries
from src.geo.national_grid import build_national_grid, geodesic_area_km2

EXPECTED_ZIP_SHA256 = "be61a1e11bf86b265098b5a0b02eb836237421ad73354b1f0892fb6be4598866"
PYSHP_WHEEL_SHA256 = "67024c0ccdc352ba5db777c4e968483782dfa78f8e200672a90d2d30fd8b7b49"


def derive(archive, output):
    """Reproduce unchanged geometries from the immutable official shapefile ZIP."""
    import shapefile
    from pyproj import CRS
    from shapely.geometry import mapping, shape

    if shapefile.__version__ != "2.3.1":
        raise ValueError("Use the documented isolated pyshp2.3.1 tool")
    if output.exists():
        raise FileExistsError("Use a new output directory; archives are immutable")
    raw = archive.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_ZIP_SHA256:
        raise ValueError("IBGE2024 source ZIP hash mismatch: preserve changed sources as a new version")
    output.mkdir(parents=True)
    with ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP CRC failed")
        members = z.namelist()
        for name in members:
            if Path(name).name != name:
                raise ValueError("Unsafe archive member")
            (output / name).write_bytes(z.read(name))
    if CRS.from_wkt((output / "BR_UF_2024.prj").read_text()).to_epsg() != 4674:
        raise ValueError("Source CRS must be SIRGAS2000 geographic")
    reader = shapefile.Reader(str(output / "BR_UF_2024.shp"),
                             encoding=(output / "BR_UF_2024.cpg").read_text().strip())
    features = [{"type": "Feature", "properties": row.record.as_dict(),
                 "geometry": mapping(shape(row.shape.__geo_interface__))}
                for row in reader.iterShapeRecords()]
    plaintext = (json.dumps({"type": "FeatureCollection", "features": features},
                           ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    compressed = gzip.compress(plaintext, compresslevel=9, mtime=0)
    (output / "BR_UF_2024.zip").write_bytes(raw)
    (output / "BR_UF_2024.geojson.gz").write_bytes(compressed)
    receipt = {"schema_version": 1, "sha256": hashlib.sha256(compressed).hexdigest(),
               "derived_plaintext_sha256": hashlib.sha256(plaintext).hexdigest(),
               "raw_zip_sha256": EXPECTED_ZIP_SHA256, "raw_zip_size_bytes": len(raw),
               "geojson_gzip_size_bytes": len(compressed), "geojson_size_bytes": len(plaintext),
               "source_url": IBGE_SOURCE_URL,
               "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
               "attribution": "Fonte: IBGE, Malha Municipal Digital 2024, agregação UF. Instituto Brasileiro de Geografia e Estatística.",
               "crs": "EPSG:4674", "geometry_version": "ibge-2024", "territorial_year": 2024,
               "source_archive_members": members,
               "derivation": {"tool": "pyshp", "version": "2.3.1", "wheel_sha256": PYSHP_WHEEL_SHA256,
                              "shapely_version": "2.0.7", "script": "scripts/build_national_geography.py",
                              "steps": "iterShapeRecords/__geo_interface__, shape/mapping; no simplification, repair or coordinate transform; canonical compact JSON; gzip9 mtime0"}}
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    load_boundaries(output / "BR_UF_2024.geojson.gz", output / "receipt.json")
    print(f"Archived 27 official geometries; derived gzip SHA256 {receipt['sha256']}")


def benchmark(source, output):
    """Measure both resolutions against the complete archived 27-UF geometry."""
    if output.exists():
        raise FileExistsError("Select a new evidence output file")
    boundaries = load_boundaries(source / "BR_UF_2024.geojson.gz", source / "receipt.json")
    results = []
    for resolution in (.5, .25):
        start = time.perf_counter()
        units = build_national_grid(boundaries, "ibge-2024", resolution)
        elapsed = time.perf_counter() - start
        counts = Counter(row["uf_code"] for row in units)
        areas = defaultdict(float)
        for row in units:
            areas[row["uf_code"]] += row["uf_area_km2"]
        if set(counts) != set(boundaries):
            raise ValueError("Grid does not cover all 27 UFs")
        per_uf = {code: {"spatial_units": counts[code],
                         "polygon_area_km2": geodesic_area_km2(boundaries[code]),
                         "clipped_area_km2": areas[code],
                         "polygon_components": len(boundaries[code].geoms) if hasattr(boundaries[code], "geoms") else 1,
                         "small_intersections_lt_1pct": sum(row["uf_code"] == code and row["uf_fraction_geodesic"] < .01 for row in units)}
                  for code in sorted(boundaries)}
        results.append({"resolution_deg": resolution, "spatial_units": len(units),
                        "national_cells": len({row["national_cell_id"] for row in units}),
                        "wall_seconds": elapsed,
                        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        "per_uf": per_uf, "spatial_config_sha256": units[0]["spatial_config_sha256"]})
        print(f"{resolution}deg: {len(units)} units, {elapsed:.2f}s", flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"source_receipt": str(source / "receipt.json"),
                                  "geometry_gzip_sha256": hashlib.sha256((source / "BR_UF_2024.geojson.gz").read_bytes()).hexdigest(),
                                  "receipt_sha256": hashlib.sha256((source / "receipt.json").read_bytes()).hexdigest(),
                                  "measurement": "complete official IBGE2024 geometry; no fire/climate/model metrics",
                                  "results": results}, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    archive = sub.add_parser("derive")
    archive.add_argument("--archive", type=Path, required=True)
    archive.add_argument("--output", type=Path, required=True)
    measured = sub.add_parser("benchmark")
    measured.add_argument("--source", type=Path, default=Path("data/geo/national/ibge-2024"))
    measured.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "derive":
        derive(args.archive, args.output)
    else:
        benchmark(args.source, args.output)
