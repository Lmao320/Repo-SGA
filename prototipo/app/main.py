"""API REST del prototipo del SGA (sistema bajo prueba)."""
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import db, servicios
from .seguridad import (emitir_token, requiere_rol, revocar, usuario_actual,
                        verificar_contrasena)

app = FastAPI(title="SGA - Prototipo para pruebas", version="0.1.0",
              description="Módulos de autenticación, matrículas y calificaciones.")


def conexion():
    con = db.conectar()
    try:
        yield con
    finally:
        con.close()


@app.exception_handler(servicios.ErrorNegocio)
def _error_negocio(_, exc: servicios.ErrorNegocio):
    return JSONResponse(status_code=exc.http, content={"codigo": exc.codigo, "mensaje": exc.mensaje})


class Login(BaseModel):
    correo: str
    contrasena: str


class NuevaMatricula(BaseModel):
    estudianteId: int
    grupoId: int


class Nota(BaseModel):
    corte: str = Field(min_length=1, max_length=2)
    nota: float


@app.post("/api/v1/auth/login", tags=["Autenticación"])
def login(datos: Login, con=Depends(conexion)):
    u = con.execute("SELECT id, hash_contrasena, rol, activo FROM usuario WHERE correo=?",
                    (datos.correo,)).fetchone()
    if u is None or not u["activo"] or not verificar_contrasena(datos.contrasena, u["hash_contrasena"]):
        raise HTTPException(401, "Credenciales inválidas")
    db.auditar(con, u["id"], "LOGIN", "usuario", u["id"])
    return {"accessToken": emitir_token(u["id"], u["rol"]), "tipo": "Bearer"}


@app.post("/api/v1/auth/logout", status_code=204, tags=["Autenticación"])
def logout(usuario: dict = Depends(usuario_actual)):
    revocar(usuario["jti"])


@app.post("/api/v1/matriculas", status_code=201, tags=["Matrículas"])
def crear_matricula(datos: NuevaMatricula, con=Depends(conexion),
                    usuario: dict = Depends(requiere_rol("COORDINADOR", "ESTUDIANTE"))):
    if usuario["rol"] == "ESTUDIANTE" and usuario["id"] != datos.estudianteId:
        raise HTTPException(403, "Un estudiante solo puede matricularse a sí mismo")
    mid = servicios.matricular(con, datos.estudianteId, datos.grupoId, usuario["id"])
    return {"matriculaId": mid}


@app.get("/api/v1/estudiantes/{estudiante_id}/matriculas", tags=["Matrículas"])
def ver_matriculas(estudiante_id: int, con=Depends(conexion),
                   usuario: dict = Depends(usuario_actual)):
    if usuario["rol"] == "ESTUDIANTE" and usuario["id"] != estudiante_id:
        raise HTTPException(403, "Un estudiante solo puede consultar su propia información")
    filas = con.execute(
        "SELECT m.id, g.codigo, g.asignatura FROM matricula m JOIN grupo g ON g.id=m.grupo_id "
        "WHERE m.estudiante_id=?", (estudiante_id,)).fetchall()
    return [dict(f) for f in filas]


@app.get("/api/v1/grupos/{grupo_id}", tags=["Periodos y grupos"])
def ver_grupo(grupo_id: int, con=Depends(conexion), _=Depends(usuario_actual)):
    g = con.execute("SELECT * FROM grupo WHERE id=?", (grupo_id,)).fetchone()
    if g is None:
        raise HTTPException(404, "Grupo no encontrado")
    return dict(g)


@app.put("/api/v1/matriculas/{matricula_id}/calificaciones", tags=["Calificaciones"])
def registrar_nota(matricula_id: int, datos: Nota, con=Depends(conexion),
                   usuario: dict = Depends(requiere_rol("DOCENTE"))):
    servicios.registrar_nota(con, usuario["id"], matricula_id, datos.corte, datos.nota)
    return {"estado": "registrada"}


@app.get("/api/v1/auditoria", tags=["Auditoría"])
def auditoria(con=Depends(conexion), _=Depends(requiere_rol("ADMIN"))):
    filas = con.execute("SELECT * FROM evento_auditoria ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(f) for f in filas]
