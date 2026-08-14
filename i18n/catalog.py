from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from i18n.locale import DEFAULT_LOCALE, normalize_locale


CATALOG_DIR = Path(__file__).parent / "locales"


@lru_cache(maxsize=None)
def load_catalog(locale: str) -> dict[str, Any]:
    locale = normalize_locale(locale)
    with (CATALOG_DIR / f"{locale}.yaml").open(encoding="utf-8") as catalog_file:
        return yaml.safe_load(catalog_file) or {}


def _lookup(catalog: dict[str, Any], key: str) -> Any:
    value: Any = catalog
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(key)
        value = value[part]
    return value


def translate(key: str, locale: str = DEFAULT_LOCALE, **values: Any) -> str:
    """Resolve a dotted translation key, falling back to English."""
    locale = normalize_locale(locale)
    try:
        value = _lookup(load_catalog(locale), key)
    except KeyError:
        try:
            value = _lookup(load_catalog(DEFAULT_LOCALE), key)
        except KeyError:
            return f"[{key}]"

    if not isinstance(value, str):
        raise TypeError(f"Translation key '{key}' must resolve to a string")
    return value.format(**values) if values else value
