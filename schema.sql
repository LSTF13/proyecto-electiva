-- Base de datos de reportes de mascotas perdidas (SQLite)
-- Formato base: nombre mascota, tipo animal / raza, color, fecha y hora de pérdida, descripción.
-- Las columnas tipo, raza y localidad se derivan de esos datos al importarlos.

CREATE TABLE IF NOT EXISTS reportes (
    id             TEXT PRIMARY KEY,                 -- identificador único (hash del contenido) -> evita duplicados
    nombre_mascota TEXT NOT NULL,
    tipo_raza      TEXT NOT NULL,                    -- texto original: "Perro - Labrador"
    color          TEXT NOT NULL,
    fecha_perdida  TEXT NOT NULL,                    -- ISO: YYYY-MM-DD HH:MM:SS
    descripcion    TEXT NOT NULL DEFAULT '',
    tipo           TEXT NOT NULL DEFAULT 'Otro',     -- Perro | Gato | Otro
    raza           TEXT NOT NULL DEFAULT 'No especificada',
    localidad      TEXT NOT NULL DEFAULT 'Sin identificar',
    creado_en      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reportes_fecha     ON reportes (fecha_perdida);
CREATE INDEX IF NOT EXISTS idx_reportes_tipo      ON reportes (tipo);
CREATE INDEX IF NOT EXISTS idx_reportes_localidad ON reportes (localidad);

CREATE TABLE IF NOT EXISTS meta (
    clave TEXT PRIMARY KEY,
    valor TEXT
);
