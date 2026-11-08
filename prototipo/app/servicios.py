"""Reglas de negocio de matrícula y calificaciones."""
from . import db


class ErrorNegocio(Exception):
    def __init__(self, codigo: str, mensaje: str, http: int = 409):
        self.codigo, self.mensaje, self.http = codigo, mensaje, http


def matricular(con, estudiante_id: int, grupo_id: int, actor_id: int) -> int:
    """Matricula dentro de una transacción con bloqueo (RN-01, RN-02, RN-03, ADR-02)."""
    con.execute("BEGIN IMMEDIATE")  # bloquea escrituras concurrentes
    try:
        est = con.execute("SELECT rol, activo FROM usuario WHERE id=?", (estudiante_id,)).fetchone()
        if est is None or est["rol"] != "ESTUDIANTE" or not est["activo"]:
            raise ErrorNegocio("ESTUDIANTE_INVALIDO", "El estudiante no existe o está inactivo", 404)
        g = con.execute(
            "SELECT g.cupo_max, g.cupo_ocupado, p.estado FROM grupo g "
            "JOIN periodo p ON p.id = g.periodo_id WHERE g.id=?", (grupo_id,)).fetchone()
        if g is None:
            raise ErrorNegocio("GRUPO_INEXISTENTE", "El grupo no existe", 404)
        if g["estado"] != "ABIERTO":
            raise ErrorNegocio("PERIODO_CERRADO", "El periodo no está abierto para matrícula")
        if con.execute("SELECT 1 FROM matricula WHERE estudiante_id=? AND grupo_id=?",
                       (estudiante_id, grupo_id)).fetchone():
            raise ErrorNegocio("MATRICULA_DUPLICADA", "El estudiante ya está matriculado en este grupo")
        if g["cupo_ocupado"] >= g["cupo_max"]:
            raise ErrorNegocio("SIN_CUPO", "El grupo no tiene cupos disponibles")
        cur = con.execute("INSERT INTO matricula (estudiante_id, grupo_id) VALUES (?,?)",
                          (estudiante_id, grupo_id))
        con.execute("UPDATE grupo SET cupo_ocupado = cupo_ocupado + 1 WHERE id=?", (grupo_id,))
        db.auditar(con, actor_id, "MATRICULA_CREADA", "matricula", cur.lastrowid)
        con.execute("COMMIT")
        return cur.lastrowid
    except Exception:
        con.execute("ROLLBACK")
        raise


def registrar_nota(con, docente_id: int, matricula_id: int, corte: str, nota: float) -> None:
    """Solo el docente del grupo registra notas (RN-04, RN-05)."""
    fila = con.execute(
        "SELECT g.docente_id FROM matricula m JOIN grupo g ON g.id = m.grupo_id WHERE m.id=?",
        (matricula_id,)).fetchone()
    if fila is None:
        raise ErrorNegocio("MATRICULA_INEXISTENTE", "La matrícula no existe", 404)
    if fila["docente_id"] != docente_id:
        raise ErrorNegocio("GRUPO_AJENO", "El docente no dicta este grupo", 403)
    if not 0 <= nota <= 5:
        raise ErrorNegocio("NOTA_FUERA_DE_RANGO", "La nota debe estar entre 0,0 y 5,0", 422)
    con.execute("BEGIN IMMEDIATE")
    con.execute(
        "INSERT INTO calificacion (matricula_id, corte, nota) VALUES (?,?,?) "
        "ON CONFLICT(matricula_id, corte) DO UPDATE SET nota=excluded.nota",
        (matricula_id, corte, round(nota, 1)))
    db.auditar(con, docente_id, "NOTA_REGISTRADA", "matricula", matricula_id)
    con.execute("COMMIT")
