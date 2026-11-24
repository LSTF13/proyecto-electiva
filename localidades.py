
import re
import unicodedata

LOCALIDADES = [
    "Usaquén", "Chapinero", "Santa Fe", "San Cristóbal", "Usme", "Tunjuelito",
    "Bosa", "Kennedy", "Fontibón", "Engativá", "Suba", "Barrios Unidos",
    "Teusaquillo", "Los Mártires", "Antonio Nariño", "Puente Aranda",
    "La Candelaria", "Rafael Uribe Uribe", "Ciudad Bolívar", "Sumapaz",
]
SIN_LOCALIDAD = "Sin identificar"


def normalizar(texto) -> str:
    """Minúsculas y sin tildes: 'Engativá' -> 'engativa'."""
    t = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


_ALIAS = {normalizar(l): l for l in LOCALIDADES}
_ALIAS["rafael uribe"] = "Rafael Uribe Uribe"

_PATRON = re.compile(r"\b(" + "|".join(sorted(map(re.escape, _ALIAS), key=len, reverse=True)) + r")\b")


def detectar_localidad(*textos) -> str:
    
    base = normalizar(" ".join(str(t or "") for t in textos))
    m = _PATRON.search(base)
    return _ALIAS[m.group(1)] if m else SIN_LOCALIDAD
