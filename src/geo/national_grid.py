"""Global lattice and clipped cell×UF units; no historical pilot dependencies."""
import hashlib
import json
import math

from pyproj import Geod
from shapely.geometry import Point, box
from shapely.geometry.polygon import orient

from src.geo.boundaries import validate_boundaries

_GEOD = Geod(ellps="GRS80")


def _resolution(resolution):
    if resolution not in (0.5, 0.25):
        raise ValueError("Supported national resolutions: 0.5 and 0.25 degrees")
    return float(resolution)


def grid_version(resolution=0.5):
    return f"global-grs80-{_resolution(resolution):g}deg-v1"


def cell_id(latitude, longitude, resolution=0.5):
    """Half-open global cells; exact grid lines belong to north/east cell."""
    resolution = _resolution(resolution)
    if not (math.isfinite(latitude) and math.isfinite(longitude)
            and -90 <= latitude < 90 and -180 <= longitude < 180):
        raise ValueError("Finite coordinates in [-90,90) × [-180,180) required")
    row = math.floor((latitude + 90) / resolution)
    col = math.floor((longitude + 180) / resolution)
    return f"{grid_version(resolution)}:r{row:04d}:c{col:04d}"


def geodesic_area_km2(geometry):
    """Sum oriented polygon areas, preserving holes and multipolygon islands."""
    if geometry.is_empty:
        return 0.0
    if geometry.geom_type == "Polygon":
        return abs(_GEOD.geometry_area_perimeter(orient(geometry, sign=1.0))[0]) / 1e6
    if hasattr(geometry, "geoms"):
        return sum(geodesic_area_km2(part) for part in geometry.geoms)
    return 0.0


def build_national_grid(boundaries, geometry_version, resolution=0.5):
    """Return deterministic records for every positive-area cell×UF intersection.

    Partial fixture boundary sets are accepted for engineering tests; production
    callers must use load_boundaries, which enforces all 27 real official UFs.
    Geometry-content fingerprints participate in spatial_config_sha256.
    """
    validate_boundaries(boundaries, require_all=False)
    resolution = _resolution(resolution)
    config = {"origin": [-180, -90], "resolution_deg": resolution,
              "grid_version": grid_version(resolution), "geometry_version": geometry_version,
              "geometry_sha256": {code: hashlib.sha256(boundaries[code].wkb).hexdigest()
                                  for code in sorted(boundaries)}}
    digest = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    rows = []
    for code in sorted(boundaries):
        geom = boundaries[code]
        west, south, east, north = geom.bounds
        for row in range(math.floor((south + 90) / resolution), math.ceil((north + 90) / resolution)):
            lat_min = row * resolution - 90
            for col in range(math.floor((west + 180) / resolution), math.ceil((east + 180) / resolution)):
                lon_min = col * resolution - 180
                cell = box(lon_min, lat_min, lon_min + resolution, lat_min + resolution)
                if not geom.intersects(cell):
                    continue
                clipped = geom.intersection(cell)
                area = geodesic_area_km2(clipped)
                if area <= 0:
                    continue
                # Drop zero-area line/point members of GeometryCollections.
                if clipped.geom_type == "GeometryCollection":
                    from shapely.ops import unary_union
                    clipped = unary_union([p for p in clipped.geoms if p.geom_type in {"Polygon", "MultiPolygon"}])
                cell_area = geodesic_area_km2(cell)
                identity = cell_id(lat_min + resolution / 2, lon_min + resolution / 2, resolution)
                rows.append({"national_cell_id": identity, "spatial_unit_id": f"{identity}:uf{code}",
                             "uf_code": code, "geometry": clipped, "cell_area_km2": cell_area,
                             "uf_area_km2": area, "uf_fraction_geodesic": area / cell_area,
                             "lat_min": lat_min, "lat_max": lat_min + resolution,
                             "lon_min": lon_min, "lon_max": lon_min + resolution,
                             "lat_center": lat_min + resolution / 2, "lon_center": lon_min + resolution / 2,
                             "geometry_version": geometry_version, "grid_version": grid_version(resolution),
                             "spatial_config_sha256": digest})
    return rows


def assign_point(latitude, longitude, boundaries, resolution=0.5):
    """One event→one UF; report all boundary candidates and choose lowest code.

    Grid boundary ownership uses the same global floor rule as cell_id. If a
    point touches only the exterior north/east edge of the entire territory,
    the half-open cell has no positive-area unit: return None for quarantine.
    """
    identity = cell_id(latitude, longitude, resolution)
    point = Point(longitude, latitude)
    candidates = sorted(code for code, geom in boundaries.items() if geom.covers(point))
    if not candidates:
        return None
    resolution = _resolution(resolution)
    lon = math.floor((longitude + 180) / resolution) * resolution - 180
    lat = math.floor((latitude + 90) / resolution) * resolution - 90
    cell = box(lon, lat, lon + resolution, lat + resolution)
    eligible = [code for code in candidates if geodesic_area_km2(boundaries[code].intersection(cell)) > 0]
    if not eligible:
        return None
    code = eligible[0]
    return {"national_cell_id": identity, "spatial_unit_id": f"{identity}:uf{code}", "uf_code": code,
            "boundary": any(boundaries[c].boundary.covers(point) for c in candidates),
            "candidate_uf_codes": candidates}
