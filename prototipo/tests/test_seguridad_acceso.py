"""PRUEBA 2 - Seguridad: autenticación y autorización.
Requerimientos: RF-01, RF-02, RNF-01, RNF-11, RN-04, RN-07."""
from tests.conftest import token

COORD = "coordinador@sga.test"


def test_CP_S01_control_de_acceso_por_token_y_rol(cliente):
    """Se intenta acceder sin credenciales válidas o con un rol sin permiso."""
    hc = token(cliente, COORD)
    mid = cliente.post("/api/v1/matriculas", json={"estudianteId": 10, "grupoId": 100}, headers=hc).json()["matriculaId"]
    nota = {"corte": "1", "nota": 4.5}
    url_nota = f"/api/v1/matriculas/{mid}/calificaciones"

    # a) Sin token y con token alterado
    assert cliente.put(url_nota, json=nota).status_code == 401
    assert cliente.put(url_nota, json=nota, headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401
    # b) Estudiante intenta registrarse una nota (rol sin permiso)
    assert cliente.put(url_nota, json=nota, headers=token(cliente, "est.camila@sga.test")).status_code == 403
    # c) Docente que NO dicta el grupo intenta registrar la nota
    ajeno = cliente.put(url_nota, json=nota, headers=token(cliente, "docente.luis@sga.test"))
    assert (ajeno.status_code, ajeno.json()["codigo"]) == (403, "GRUPO_AJENO")
    # d) Estudiante consulta las matrículas de otro estudiante (acceso horizontal)
    assert cliente.get("/api/v1/estudiantes/11/matriculas", headers=token(cliente, "est.camila@sga.test")).status_code == 403
    # e) Token reutilizado después de cerrar sesión
    hd = token(cliente, "docente.ana@sga.test")
    assert cliente.put(url_nota, json=nota, headers=hd).status_code == 200  # control positivo
    assert cliente.post("/api/v1/auth/logout", headers=hd).status_code == 204
    assert cliente.put(url_nota, json=nota, headers=hd).status_code == 401


def test_CP_S02_bloqueo_de_cuenta_por_fuerza_bruta(cliente):
    """CU-01: tras 5 intentos fallidos la cuenta debe bloquearse 15 minutos,
    incluso si el sexto intento usa la contraseña correcta."""
    login = {"correo": "docente.ana@sga.test"}
    fallidos = [cliente.post("/api/v1/auth/login", json={**login, "contrasena": f"incorrecta{i}"}).status_code
                for i in range(5)]
    assert fallidos == [401] * 5

    sexto = cliente.post("/api/v1/auth/login", json={**login, "contrasena": "Clave#2026"})

    assert sexto.status_code in (423, 429), (
        f"La cuenta no se bloqueó: el sexto intento respondió {sexto.status_code}")
