"""Acceso a datos con SQLite. Cada petición abre su propia conexión."""
import os
import sqlite3

DB_PATH = os.environ.get("SGA_DB", "sga.db")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY,
    correo TEXT UNIQUE NOT NULL,
    hash_contrasena BLOB NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('ADMIN','COORDINADOR','DOCENTE','ESTUDIANTE')),
    activo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS periodo (
    id INTEGER PRIMARY KEY,
    codigo TEXT UNIQUE NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('ABIERTO','CERRADO'))
);
CREATE TABLE IF NOT EXISTS grupo (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL,
    asignatura TEXT NOT NULL,
    periodo_id INTEGER NOT NULL REFERENCES periodo(id),
    docente_id INTEGER NOT NULL REFERENCES usuario(id),
    cupo_max INTEGER NOT NULL CHECK (cupo_max > 0),
    cupo_ocupado INTEGER NOT NULL DEFAULT 0,
    CHECK (cupo_ocupado <= cupo_max)
);
CREATE TABLE IF NOT EXISTS matricula (
    id INTEGER PRIMARY KEY,
    estudiante_id INTEGER NOT NULL REFERENCES usuario(id),
    grupo_id INTEGER NOT NULL REFERENCES grupo(id),
    fecha TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (estudiante_id, grupo_id)
);
CREATE TABLE IF NOT EXISTS calificacion (
    id INTEGER PRIMARY KEY,
    matricula_id INTEGER NOT NULL REFERENCES matricula(id),
    corte TEXT NOT NULL,
    nota REAL NOT NULL CHECK (nota >= 0 AND nota <= 5),
    UNIQUE (matricula_id, corte)
);
CREATE TABLE IF NOT EXISTS evento_auditoria (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL DEFAULT (datetime('now')),
    usuario_id INTEGER,
    accion TEXT NOT NULL,
    entidad TEXT NOT NULL,
    registro_id TEXT
);
"""


def conectar() -> sqlite3.Connection:
    # check_same_thread=False: FastAPI puede abrir y cerrar la conexión en hilos distintos
    # del mismo request (defecto D-02 detectado en la prueba de carga). Cada conexión
    # sigue siendo exclusiva de una sola petición.
    con = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def inicializar(con: sqlite3.Connection) -> None:
    con.executescript(ESQUEMA)


def auditar(con, usuario_id, accion, entidad, registro_id) -> None:
    con.execute(
        "INSERT INTO evento_auditoria (usuario_id, accion, entidad, registro_id) VALUES (?,?,?,?)",
        (usuario_id, accion, entidad, str(registro_id)),
    )
