"""URL-safe slug generation for landing pages and other resources."""

import re
import unicodedata


def slugify(name: str) -> str:
    """Converts a name to a URL-safe slug.

    Examples:
    - "Peluquería El Buen Corte" -> "peluqueria-el-buen-corte"
    - "Café & Bar" -> "cafe-bar"
    - "Dr. Juan's Clínica" -> "dr-juans-clinica"
    """
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    text = text.strip("-")
    return text or "cliente"


def generate_unique_slug(base_name: str, existing_slugs: set[str]) -> str:
    """Generates a unique slug from a base name.

    If the base slug already exists, appends a numerical suffix: -2, -3, etc.
    """
    base_slug = slugify(base_name)

    if base_slug not in existing_slugs:
        return base_slug

    counter = 2
    while f"{base_slug}-{counter}" in existing_slugs:
        counter += 1

    return f"{base_slug}-{counter}"
