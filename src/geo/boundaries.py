"""Strict loader for independently archived IBGE 2024 national boundaries.

No bundled synthetic geometry and no fallback to the historical MT polygon.
An acquisition receipt accompanies immutable raw GeoJSON bytes. This loader
verifies integrity and metadata, not the authenticity of an arbitrary receipt.
Acquire bytes using verified HTTPS from the declared official IBGE destination.
"""
import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from shapely.geometry import shape

from src.geo.uf_registry import UF_BY_CODE

GEOMETRY_VERSION = "ibge-2024"
# Fixed-year official archive, exercised with verified HTTPS in onboarding.
IBGE_SOURCE_URL = "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/Brasil/BR_UF_2024.zip"


def validate_boundaries(boundaries, require_all=True):
    """Validate polygon topology and reject interior overlaps between UFs."""
    if not boundaries or set(boundaries) - UF_BY_CODE.keys():
        raise ValueError("Unknown or empty UF geometry codes")
    if require_all and set(boundaries) != UF_BY_CODE.keys():
        raise ValueError("Exactly 27 official UF geometries required")
    for code, geom in boundaries.items():
        if geom.geom_type not in {"Polygon", "MultiPolygon"} or geom.is_empty or not geom.is_valid:
            raise ValueError(f"Invalid polygon geometry for UF {code}")
        west, south, east, north = geom.bounds
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError(f"Invalid geographic coordinates for UF {code}")
    codes = sorted(boundaries)
    for i, left in enumerate(codes):
        for right in codes[i + 1:]:
            if boundaries[left].intersection(boundaries[right]).area > 1e-12:
                raise ValueError(f"Overlapping UF interiors: {left}, {right}")
    return boundaries


def load_boundaries(path: Path, manifest_path: Path):
    """Load all 27 geometries from a hash-bound provenance receipt."""
    raw = Path(path).read_bytes()
    receipt = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if receipt.get("sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("Boundary SHA-256 mismatch")
    required = ("source_url", "retrieved_at_utc", "attribution", "crs", "geometry_version", "territorial_year")
    if any(not receipt.get(key) for key in required):
        raise ValueError("Incomplete boundary provenance receipt")
    source = urlparse(receipt["source_url"])
    if source.scheme != "https" or source.hostname not in {"servicodados.ibge.gov.br", "geoftp.ibge.gov.br"}:
        raise ValueError("Official HTTPS IBGE source required")
    if receipt["territorial_year"] != 2024 or receipt["geometry_version"] != GEOMETRY_VERSION:
        raise ValueError("Boundary edition must be IBGE 2024")
    if receipt["crs"] != "EPSG:4674":
        raise ValueError("Expected SIRGAS 2000 geographic coordinates (EPSG:4674)")
    if Path(path).suffix == ".gz":
        plaintext = gzip.decompress(raw)
        if receipt.get("derived_plaintext_sha256") != hashlib.sha256(plaintext).hexdigest():
            raise ValueError("Boundary derived plaintext SHA-256 mismatch")
        document = json.loads(plaintext)
    else:
        document = json.loads(raw)
    if document.get("type") != "FeatureCollection":
        raise ValueError("GeoJSON FeatureCollection required")
    boundaries = {}
    for feature in document.get("features", []):
        properties = feature.get("properties", {})
        code = str(properties.get("codarea", properties.get("CD_UF", "")))
        if code in boundaries:
            raise ValueError(f"Duplicate UF geometry: {code}")
        boundaries[code] = shape(feature["geometry"])
    return validate_boundaries(boundaries)
