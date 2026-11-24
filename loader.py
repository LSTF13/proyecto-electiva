"""Lectura, validación y limpieza de reportes desde Excel (.xlsx/.xls) y CSV."""
import hashlib
import io
import re
import warnings
from datetime import datetime

import pandas as pd

from localidades import detectar_localidad, normalizar

COLUMNAS_ENTRADA = ["Nombre mascota", "Tipo animal / raza", "Color",
                    "Fecha y hora de pérdida", "Descripción"]
COLUMNAS_DB = ["id", "nombre_mascota", "tipo_raza", "color", "fecha_perdida",
               "descripcion", "tipo", "raza", "localidad"]
FORMATO_FECHA_DB = "%Y-%m-%d %H:%M:%S"

_TEL = re.compile(r"(\+?57[\s-]?)?\b3\d{2}[\s-]?\d{3}[\s-]?\d{4}\b|\b\d{7,10}\b")
_MAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")


def enmascarar_datos_personales(texto: str) -> str:
    
    texto = _MAIL.sub("[correo oculto]", texto)
    return _TEL.sub("[teléfono oculto]", texto)


def dividir_tipo_raza(texto: str):
    
    partes = [p.strip() for p in re.split(r"\s*[-/,;|]\s*", texto, maxsplit=1) if p.strip()]
    if not partes:
        return "Otro", "No especificada"
    primero = normalizar(partes[0])
    resto = partes[1] if len(partes) > 1 else ""
    if primero.startswith(("perr", "canin")):
        return "Perro", resto or "No especificada"
    if primero.startswith(("gat", "felin")):
        return "Gato", resto or "No especificada"
    if primero == "otro":
        return "Otro", resto or "No especificada"
    return "Otro", texto.strip()


def parsear_fecha(valor):
    
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return None
    if isinstance(valor, (datetime, pd.Timestamp)):
        return pd.Timestamp(valor).to_pydatetime()
    if isinstance(valor, (int, float)):
        try:
            return pd.to_datetime(valor, unit="D", origin="1899-12-30").to_pydatetime()
        except Exception:
            return None
    texto = str(valor).strip()
    if not texto:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        f = pd.to_datetime(texto, dayfirst=True, errors="coerce")
    return None if pd.isna(f) else f.to_pydatetime()


def construir_registro(nombre, tipo_raza, color, fecha: datetime, descripcion) -> dict:
    
    nombre = str(nombre).strip() or "Sin nombre"
    tipo_raza = str(tipo_raza).strip()
    color = str(color).strip() or "No especificado"
    descripcion = enmascarar_datos_personales(str(descripcion or "").strip())
    tipo, raza = dividir_tipo_raza(tipo_raza)
    fecha_txt = fecha.strftime(FORMATO_FECHA_DB)
    clave = "|".join(normalizar(x) for x in (nombre, tipo_raza, color, fecha_txt, descripcion))
    return {
        "id": hashlib.sha1(clave.encode("utf-8")).hexdigest()[:16],
        "nombre_mascota": nombre, "tipo_raza": tipo_raza, "color": color,
        "fecha_perdida": fecha_txt, "descripcion": descripcion,
        "tipo": tipo, "raza": raza,
        "localidad": detectar_localidad(descripcion),
    }


def leer_tabla(origen, nombre_archivo: str) -> pd.DataFrame:
    
    ext = nombre_archivo.lower().rsplit(".", 1)[-1]
    if ext == "csv":
        crudo = origen.read() if hasattr(origen, "read") else open(origen, "rb").read()
        texto = None
        for codificacion in ("utf-8-sig", "latin-1"):
            try:
                texto = crudo.decode(codificacion)
                break
            except UnicodeDecodeError:
                continue
        if texto is None:
            raise ValueError("No se pudo decodificar el CSV. Guárdelo con codificación UTF-8.")
        return pd.read_csv(io.StringIO(texto), header=None, dtype=object,
                           sep=None, engine="python")
    if ext in ("xlsx", "xls"):
        return pd.read_excel(origen, header=None, dtype=object, sheet_name=0)
    raise ValueError(f"Formato no soportado: .{ext}. Use .xlsx, .xls o .csv")


def procesar(crudo: pd.DataFrame):
    
    alertas = []
    if crudo.shape[1] < 5:
        raise ValueError("El archivo debe tener 5 columnas: " + ", ".join(COLUMNAS_ENTRADA))
    crudo = crudo.iloc[:, :5]
    primera_fila = 1
    if len(crudo) and "nombre" in normalizar(crudo.iat[0, 0]):
        crudo = crudo.iloc[1:]
        primera_fila = 2

    registros, vistos = [], set()
    for n, fila in enumerate(crudo.itertuples(index=False), start=primera_fila):
        txt = ["" if (not isinstance(v, str) and pd.isna(v)) else str(v).strip() for v in fila]
        if not any(txt):
            continue
        fecha = parsear_fecha(fila[3])
        if fecha is None:
            alertas.append(f"Fila {n}: fecha vacía o con formato no reconocido ('{txt[3]}'). Fila omitida.")
            continue
        if not txt[1]:
            alertas.append(f"Fila {n}: falta tipo/raza; se registró como 'Otro'.")
        if not txt[0]:
            alertas.append(f"Fila {n}: sin nombre de mascota; se registró como 'Sin nombre'.")
        reg = construir_registro(txt[0], txt[1], txt[2], fecha, txt[4])
        if reg["id"] in vistos:
            alertas.append(f"Fila {n}: duplicada dentro del archivo. Omitida.")
            continue
        vistos.add(reg["id"])
        registros.append(reg)
    return pd.DataFrame(registros, columns=COLUMNAS_DB), alertas


def cargar_archivo(origen, nombre_archivo: str):
    return procesar(leer_tabla(origen, nombre_archivo))
