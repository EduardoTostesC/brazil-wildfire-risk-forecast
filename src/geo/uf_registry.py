"""Canonical IBGE federative unit identifiers (codes, never names, are keys).

Registry metadata is not evidence of acquired boundaries or predictive coverage.
Source: https://servicodados.ibge.gov.br/api/v1/localidades/estados
Territorial edition selected for future boundary acquisition: IBGE 2024.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class UF:
    uf_code: str
    abbreviation: str
    name: str
    region_code: str
    region_name: str
    geometry_id: str
    geometry_version: str = "ibge-2024"


_REGIONS = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}
_ROWS = (
    ("11", "RO", "Rondônia"), ("12", "AC", "Acre"), ("13", "AM", "Amazonas"),
    ("14", "RR", "Roraima"), ("15", "PA", "Pará"), ("16", "AP", "Amapá"),
    ("17", "TO", "Tocantins"), ("21", "MA", "Maranhão"), ("22", "PI", "Piauí"),
    ("23", "CE", "Ceará"), ("24", "RN", "Rio Grande do Norte"), ("25", "PB", "Paraíba"),
    ("26", "PE", "Pernambuco"), ("27", "AL", "Alagoas"), ("28", "SE", "Sergipe"),
    ("29", "BA", "Bahia"), ("31", "MG", "Minas Gerais"), ("32", "ES", "Espírito Santo"),
    ("33", "RJ", "Rio de Janeiro"), ("35", "SP", "São Paulo"), ("41", "PR", "Paraná"),
    ("42", "SC", "Santa Catarina"), ("43", "RS", "Rio Grande do Sul"),
    ("50", "MS", "Mato Grosso do Sul"), ("51", "MT", "Mato Grosso"),
    ("52", "GO", "Goiás"), ("53", "DF", "Distrito Federal"),
)
UF_REGISTRY = tuple(UF(code, abbr, name, code[0], _REGIONS[code[0]], f"IBGE:UF:{code}")
                    for code, abbr, name in _ROWS)
UF_BY_CODE = {uf.uf_code: uf for uf in UF_REGISTRY}
UF_BY_ABBREVIATION = {uf.abbreviation: uf for uf in UF_REGISTRY}
