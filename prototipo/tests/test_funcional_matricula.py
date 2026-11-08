"""PRUEBA 1 - Funcional (caja negra) del módulo de Matrículas.
Requerimientos: RF-07, RN-01, RN-02, RN-03, RF-12."""
from tests.conftest import token

COORD = "coordinador@sga.test"
ADMIN = "admin@sga.test"


def test_CP_F01_matricula_exitosa_con_cupo_disponible(cliente):
    """Un coordinador matricula a un estudiante activo en un grupo con cupo de un periodo abierto."""
    h = token(cliente, COORD)
    antes = cliente.get("/api/v1/grupos/100", headers=h).json()["cupo_ocupado"]

    r = cliente.post("/api/v1/matriculas", json={"estudianteId": 10, "grupoId": 100}, headers=h)

    assert r.status_code == 201
    assert "matriculaId" in r.json()
    despues = cliente.get("/api/v1/grupos/100", headers=h).json()["cupo_ocupado"]
    assert despues == antes + 1
    matriculas = cliente.get("/api/v1/estudiantes/10/matriculas", headers=h).json()
    assert [m["codigo"] for m in matriculas] == ["ARQ-01"]
    eventos = cliente.get("/api/v1/auditoria", headers=token(cliente, ADMIN)).json()
    assert any(e["accion"] == "MATRICULA_CREADA" and e["usuario_id"] == 2 for e in eventos)


def test_CP_F02_rechazo_por_cupo_lleno_duplicidad_y_periodo_cerrado(cliente):
    """El sistema rechaza matrículas que violan las reglas de negocio sin alterar el cupo."""
    h = token(cliente, COORD)
    # El grupo BD-01 (id 101) tiene cupo máximo 2
    assert cliente.post("/api/v1/matriculas", json={"estudianteId": 10, "grupoId": 101}, headers=h).status_code == 201
    assert cliente.post("/api/v1/matriculas", json={"estudianteId": 11, "grupoId": 101}, headers=h).status_code == 201

    sin_cupo = cliente.post("/api/v1/matriculas", json={"estudianteId": 12, "grupoId": 101}, headers=h)
    duplicada = cliente.post("/api/v1/matriculas", json={"estudianteId": 10, "grupoId": 101}, headers=h)
    cerrado = cliente.post("/api/v1/matriculas", json={"estudianteId": 12, "grupoId": 102}, headers=h)

    assert (sin_cupo.status_code, sin_cupo.json()["codigo"]) == (409, "SIN_CUPO")
    assert (duplicada.status_code, duplicada.json()["codigo"]) == (409, "MATRICULA_DUPLICADA")
    assert (cerrado.status_code, cerrado.json()["codigo"]) == (409, "PERIODO_CERRADO")
    assert cliente.get("/api/v1/grupos/101", headers=h).json()["cupo_ocupado"] == 2
    assert cliente.get("/api/v1/grupos/102", headers=h).json()["cupo_ocupado"] == 0
