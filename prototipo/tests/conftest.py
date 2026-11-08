import pytest
from fastapi.testclient import TestClient

from app import datos_prueba, db
from app.main import app


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    """Base de datos nueva y aislada para cada caso de prueba."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "sga_prueba.db"))
    con = db.conectar()
    datos_prueba.cargar(con)
    con.close()
    return TestClient(app)


def token(cliente, correo, contrasena=datos_prueba.CLAVE):
    r = cliente.post("/api/v1/auth/login", json={"correo": correo, "contrasena": contrasena})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['accessToken']}"}
