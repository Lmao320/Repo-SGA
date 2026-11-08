"""Datos ficticios para pruebas. No contiene información personal real."""
from . import db
from .seguridad import hash_contrasena

CLAVE = "Clave#2026"
USUARIOS = [
    (1, "admin@sga.test", "ADMIN"),
    (2, "coordinador@sga.test", "COORDINADOR"),
    (3, "docente.ana@sga.test", "DOCENTE"),
    (4, "docente.luis@sga.test", "DOCENTE"),
    (10, "est.camila@sga.test", "ESTUDIANTE"),
    (11, "est.mateo@sga.test", "ESTUDIANTE"),
    (12, "est.sofia@sga.test", "ESTUDIANTE"),
]


def cargar(con) -> None:
    db.inicializar(con)
    h = hash_contrasena(CLAVE)
    for uid, correo, rol in USUARIOS:
        con.execute("INSERT INTO usuario (id, correo, hash_contrasena, rol) VALUES (?,?,?,?)",
                    (uid, correo, h, rol))
    con.execute("INSERT INTO periodo (id, codigo, estado) VALUES (1,'2026-2','ABIERTO'), (2,'2026-1','CERRADO')")
    con.execute("""INSERT INTO grupo (id, codigo, asignatura, periodo_id, docente_id, cupo_max) VALUES
        (100,'ARQ-01','Arquitectura de Software',1,3,30),
        (101,'BD-01','Bases de Datos',1,4,2),
        (102,'CAL-01','Cálculo Integral',2,3,30)""")
