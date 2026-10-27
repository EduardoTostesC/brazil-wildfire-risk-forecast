"""Central business-language catalog; feature identifiers remain unchanged."""

import json
from pathlib import Path

CATALOGS = json.loads(Path(__file__).with_name("locales.json").read_text(encoding="utf-8"))
LANGUAGES = {"pt-BR": "Português do Brasil", "en": "English"}


def translate(key, language="pt-BR", **values):
    if language not in LANGUAGES:
        raise ValueError("Unsupported language")
    return CATALOGS[language][key].format(**values)


def horizon_label(horizon, language):
    if horizon == 1:
        return "1 dia · D+1" if language == "pt-BR" else "1 day · D+1"
    return translate("horizon_value", language, h=horizon)
