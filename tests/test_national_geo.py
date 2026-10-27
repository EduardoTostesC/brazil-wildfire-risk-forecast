"""Synthetic engineering fixtures are never evidence of real UF coverage."""
import hashlib
import json

import pytest
from shapely.geometry import MultiPolygon, Polygon, box, mapping

from src.geo.boundaries import load_boundaries, validate_boundaries
from src.geo.national_grid import assign_point, build_national_grid, cell_id, geodesic_area_km2
from src.geo.uf_registry import UF_BY_ABBREVIATION, UF_BY_CODE, UF_REGISTRY


@pytest.fixture
def neighboring_ufs():
    # State border falls within a global cell; DF is a tiny disconnected polygon.
    return {"51": box(-56, -13, -55.75, -12.5),
            "52": box(-55.75, -13, -55.5, -12.5),
            "53": box(-54.99, -12.99, -54.98, -12.98)}


def test_registry_exact_codes_and_regions():
    expected = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
                "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}
    assert len(UF_REGISTRY) == len(UF_BY_CODE) == 27
    assert set(UF_BY_ABBREVIATION) == expected
    assert UF_BY_CODE["53"].name == "Distrito Federal"
    assert {uf.region_code for uf in UF_REGISTRY} == set("12345")
    assert all(uf.geometry_id == f"IBGE:UF:{uf.uf_code}" for uf in UF_REGISTRY)


@pytest.mark.parametrize("resolution", [0.5, 0.25])
def test_grid_identity_order_invariance_and_df(neighboring_ufs, resolution):
    a = build_national_grid(neighboring_ufs, "fixture-not-IBGE", resolution)
    b = build_national_grid(dict(reversed(list(neighboring_ufs.items()))), "fixture-not-IBGE", resolution)
    assert [r["spatial_unit_id"] for r in a] == [r["spatial_unit_id"] for r in b]
    assert [r["spatial_config_sha256"] for r in a] == [r["spatial_config_sha256"] for r in b]
    assert len({r["spatial_unit_id"] for r in a}) == len(a)
    assert {r["uf_code"] for r in a} == {"51", "52", "53"}
    assert all(r["uf_area_km2"] > 0 and 0 < r["uf_fraction_geodesic"] <= 1.0001 for r in a)
    assert any(r["uf_code"] == "53" and r["uf_fraction_geodesic"] < 0.01 for r in a)
    for code, polygon in neighboring_ufs.items():
        from shapely.ops import unary_union
        union = unary_union([r["geometry"] for r in a if r["uf_code"] == code])
        assert union.symmetric_difference(polygon).area < 1e-12


def test_border_event_assigned_once_with_all_candidates(neighboring_ufs):
    result = assign_point(-12.75, -55.75, neighboring_ufs)
    assert result["uf_code"] == "51"
    assert result["boundary"]
    assert result["candidate_uf_codes"] == ["51", "52"]
    ids = {r["spatial_unit_id"] for r in build_national_grid(neighboring_ufs, "fixture")}
    assert result["spatial_unit_id"] in ids
    assert assign_point(-12.75, -55.6, neighboring_ufs)["uf_code"] == "52"
    assert assign_point(0, 0, neighboring_ufs) is None


def test_coincident_grid_and_uf_border_has_valid_unit():
    boundaries = {"51": box(-56, -13, -55.5, -12.5), "52": box(-55.5, -13, -55, -12.5)}
    result = assign_point(-12.75, -55.5, boundaries)
    assert result["uf_code"] == "52"  # east owns the grid line; western contact has zero area.
    assert result["candidate_uf_codes"] == ["51", "52"]
    assert result["spatial_unit_id"] in {r["spatial_unit_id"] for r in build_national_grid(boundaries, "fixture")}
    assert assign_point(-12.5, -55.75, boundaries) is None  # exterior north edge quarantined.


def test_grid_floor_and_resolution_namespaces():
    assert cell_id(-12.5, -55.5) != cell_id(-12.5000001, -55.5000001)
    assert cell_id(-12.5, -55.5) != cell_id(-12.5, -55.5, 0.25)
    assert cell_id(-90, -180).endswith("r0000:c0000")


@pytest.mark.parametrize("lat,lon,resolution", [(float("nan"), 0, .5), (90, 0, .5), (0, 180, .5), (0, 0, .1)])
def test_invalid_coordinates_or_resolution_rejected(lat, lon, resolution):
    with pytest.raises(ValueError):
        cell_id(lat, lon, resolution)


def test_holes_islands_and_orientation_are_preserved():
    outer = [(-56, -13), (-55, -13), (-55, -12), (-56, -12)]
    hole = [(-55.8, -12.8), (-55.2, -12.8), (-55.2, -12.2), (-55.8, -12.2)]
    polygon = Polygon(outer, [hole])
    island = box(-54.9, -12.9, -54.89, -12.89)
    multipolygon = MultiPolygon([polygon, island])
    assert geodesic_area_km2(polygon) < geodesic_area_km2(Polygon(outer))
    assert geodesic_area_km2(Polygon(outer[::-1], [hole[::-1]])) == pytest.approx(geodesic_area_km2(polygon))
    assert geodesic_area_km2(multipolygon) == pytest.approx(geodesic_area_km2(polygon) + geodesic_area_km2(island))
    units = build_national_grid({"16": multipolygon}, "fixture")
    from shapely.ops import unary_union
    assert unary_union([r["geometry"] for r in units]).symmetric_difference(multipolygon).area < 1e-12
    assert assign_point(-12.5, -55.5, {"16": multipolygon}) is None  # polygon hole


def test_unknown_overlap_and_invalid_polygon_rejected():
    with pytest.raises(ValueError, match="Unknown"):
        validate_boundaries({"99": box(0, 0, 1, 1)}, require_all=False)
    with pytest.raises(ValueError, match="Overlapping"):
        validate_boundaries({"51": box(0, 0, 1, 1), "52": box(0.5, 0.5, 2, 2)}, require_all=False)
    with pytest.raises(ValueError, match="Invalid polygon"):
        validate_boundaries({"51": Polygon([(0, 0), (1, 1), (0, 1), (1, 0)])}, require_all=False)


@pytest.fixture
def archived_fixture(tmp_path):
    # Artificial rectangles are used ONLY to exercise loader integrity contracts.
    features = [{"type": "Feature", "properties": {"codarea": code},
                 "geometry": mapping(box(-70 + i, -30, -69.5 + i, -29.5))}
                for i, code in enumerate(UF_BY_CODE)]
    path = tmp_path / "synthetic.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    receipt = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "source_url": "https://servicodados.ibge.gov.br/fixture-not-an-acquisition",
               "retrieved_at_utc": "2026-10-27T00:00:00Z", "attribution": "synthetic fixture only",
               "crs": "EPSG:4674", "geometry_version": "ibge-2024", "territorial_year": 2024}
    manifest = tmp_path / "receipt.json"
    manifest.write_text(json.dumps(receipt))
    return path, manifest, receipt


def test_loader_requires_all_27_and_hash_provenance(archived_fixture):
    path, manifest, _ = archived_fixture
    assert set(load_boundaries(path, manifest)) == set(UF_BY_CODE)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="SHA-256"):
        load_boundaries(path, manifest)


@pytest.mark.parametrize("field,value", [("territorial_year", 2023), ("crs", "EPSG:3857"),
                                         ("source_url", "https://example.com/geo"), ("attribution", "")])
def test_loader_rejects_wrong_provenance(archived_fixture, field, value):
    path, manifest, receipt = archived_fixture
    receipt[field] = value
    manifest.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        load_boundaries(path, manifest)


def test_missing_or_duplicate_geometries_fail(archived_fixture):
    path, manifest, receipt = archived_fixture
    document = json.loads(path.read_text())
    document["features"][-1] = document["features"][0]
    path.write_text(json.dumps(document))
    receipt["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="Duplicate"):
        load_boundaries(path, manifest)
    with pytest.raises(ValueError, match="27"):
        validate_boundaries({"51": box(0, 0, 1, 1)})


def test_gzip_loader_checks_both_archived_and_plaintext_hashes(archived_fixture):
    import gzip
    path, manifest, receipt = archived_fixture
    plain = path.read_bytes()
    zipped = path.with_suffix('.geojson.gz')
    zipped.write_bytes(gzip.compress(plain, mtime=0))
    receipt['sha256'] = hashlib.sha256(zipped.read_bytes()).hexdigest()
    receipt['derived_plaintext_sha256'] = hashlib.sha256(plain).hexdigest()
    manifest.write_text(json.dumps(receipt))
    assert len(load_boundaries(zipped, manifest)) == 27
    receipt['derived_plaintext_sha256'] = '0' * 64
    manifest.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='plaintext SHA-256'):
        load_boundaries(zipped, manifest)


@pytest.fixture(scope='module')
def real_ibge_boundaries():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'data/geo/national/ibge-2024'
    return load_boundaries(root / 'BR_UF_2024.geojson.gz', root / 'receipt.json')


def test_real_ibge_2024_archive_integrity():
    from pathlib import Path
    from zipfile import ZipFile
    root = Path(__file__).resolve().parents[1] / 'data/geo/national/ibge-2024'
    receipt = json.loads((root / 'receipt.json').read_text())
    archive = root / 'BR_UF_2024.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['raw_zip_sha256']
    with ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        from pyproj import CRS
        assert CRS.from_wkt(bundle.read('BR_UF_2024.prj').decode()).to_epsg() == 4674


def test_real_27_ufs_representative_points_and_df_grid(real_ibge_boundaries):
    assert set(real_ibge_boundaries) == set(UF_BY_CODE)
    for code, geometry in real_ibge_boundaries.items():
        point = geometry.representative_point()
        assigned = assign_point(point.y, point.x, real_ibge_boundaries)
        assert assigned['uf_code'] == code
        assert geodesic_area_km2(geometry) > 0
    df = build_national_grid({'53': real_ibge_boundaries['53']}, 'ibge-2024')
    assert df and all(row['uf_area_km2'] > 0 for row in df)
    assert any(row['uf_fraction_geodesic'] < 1 for row in df)
