"""Acceso a la base de datos SQL (SQLite) y sincronización con el Excel base."""
import sqlite3
from pathlib import Path

import pandas as pd

import loader

BASE = Path(__file__).parent
DB_PATH = BASE / "mascotas.db"
SCHEMA = BASE / "schema.sql"
EXCEL_BASE = BASE / "reportes_base.xlsx"


def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def insertar(df: pd.DataFrame):
    
    if df.empty:
        return 0, 0
    filas = df[loader.COLUMNAS_DB].values.tolist()
    with conectar() as conn:
        antes = conn.total_changes
        conn.executemany(
            f"INSERT OR IGNORE INTO reportes ({','.join(loader.COLUMNAS_DB)}) "
            f"VALUES ({','.join('?' * len(loader.COLUMNAS_DB))})", filas)
        nuevos = conn.total_changes - antes
    return nuevos, len(filas) - nuevos


def version() -> tuple:
    
    with conectar() as conn:
        return conn.execute("SELECT COUNT(*), COALESCE(MAX(rowid),0) FROM reportes").fetchone()


def cargar_reportes() -> pd.DataFrame:
    with conectar() as conn:
        df = pd.read_sql_query("SELECT * FROM reportes ORDER BY fecha_perdida DESC", conn)
    df["fecha_perdida"] = pd.to_datetime(df["fecha_perdida"])
    return df


def sincronizar_base():
    
    if not EXCEL_BASE.exists():
        return ("No se encontró reportes_base.xlsx en src/.", [])
    mtime = str(EXCEL_BASE.stat().st_mtime)
    with conectar() as conn:
        fila = conn.execute("SELECT valor FROM meta WHERE clave='excel_mtime'").fetchone()
    if fila and fila[0] == mtime:
        return None
    try:
        df, alertas = loader.cargar_archivo(EXCEL_BASE, EXCEL_BASE.name)
    except Exception as e:  
        return (f"No se pudo leer el Excel base: {e}", [])
    nuevos, dup = insertar(df)
    with conectar() as conn:
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('excel_mtime', ?)", (mtime,))
    return (f"Excel base sincronizado: {nuevos} reportes nuevos, {dup} ya existentes.", alertas)
