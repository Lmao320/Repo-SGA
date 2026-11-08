"""Ejecuta los 4 casos de prueba paso a paso e imprime cada petición y su respuesta.
Sirve como evidencia legible de los resultados obtenidos. Uso: python scripts/evidencias.py [F|S]"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient  # noqa: E402

from app import datos_prueba, db  # noqa: E402
from app.main import app  # noqa: E402

V, R, A, G, N = "\033[32m", "\033[31m", "\033[36m", "\033[90m", "\033[0m"


def nueva_bd():
    db.DB_PATH = os.path.join(tempfile.mkdtemp(), "evidencia.db")
    con = db.conectar()
    datos_prueba.cargar(con)
    con.close()
    return TestClient(app)


def paso(c, metodo, url, quien=None, cuerpo=None, esperado=None, h=None):
    r = c.request(metodo, url, json=cuerpo, headers=h or {})
    ok = esperado is None or r.status_code in (esperado if isinstance(esperado, tuple) else (esperado,))
    marca = f"{V}✔{N}" if ok else f"{R}✘{N}"
    if r.status_code == 204 or not r.text:
        body = "(sin contenido)"
    else:
        datos = r.json()
        if isinstance(datos, dict) and "cupo_ocupado" in datos:
            datos = {k: datos[k] for k in ("codigo", "cupo_max", "cupo_ocupado")}
        elif isinstance(datos, list) and datos and "accion" in datos[0]:
            datos = [{k: e[k] for k in ("accion", "usuario_id", "registro_id")}
                     for e in datos if e["accion"] != "LOGIN"][:1]
        body = json.dumps(datos, ensure_ascii=False)
    if len(body) > 90:
        body = body[:87] + "..."
    print(f" {marca} {A}{metodo:<4} {url}{N} {G}{('['+quien+']') if quien else ''}{N}")
    if cuerpo:
        print(f"      {G}cuerpo:{N} {json.dumps(cuerpo, ensure_ascii=False)}")
    print(f"      {G}→{N} {r.status_code} {body}   {G}(esperado: {esperado}){N}")
    return r


def login(c, correo, clave=datos_prueba.CLAVE):
    r = c.post("/api/v1/auth/login", json={"correo": correo, "contrasena": clave})
    return {"Authorization": "Bearer " + r.json()["accessToken"]}


def prueba_funcional():
    print(f"{A}PRUEBA 1 · FUNCIONAL · Módulo de Matrículas{N}\n")
    c = nueva_bd()
    h = login(c, "coordinador@sga.test")
    print("CP-F01  Matrícula exitosa con cupo disponible")
    paso(c, "GET", "/api/v1/grupos/100", "coordinador", esperado=200, h=h)
    paso(c, "POST", "/api/v1/matriculas", "coordinador", {"estudianteId": 10, "grupoId": 100}, 201, h)
    paso(c, "GET", "/api/v1/grupos/100", "coordinador", esperado=200, h=h)
    paso(c, "GET", "/api/v1/auditoria", "admin", esperado=200, h=login(c, "admin@sga.test"))
    print("\nCP-F02  Rechazo por cupo lleno, duplicidad y periodo cerrado (grupo BD-01, cupo 2)")
    paso(c, "POST", "/api/v1/matriculas", "coordinador", {"estudianteId": 10, "grupoId": 101}, 201, h)
    paso(c, "POST", "/api/v1/matriculas", "coordinador", {"estudianteId": 11, "grupoId": 101}, 201, h)
    paso(c, "POST", "/api/v1/matriculas", "coordinador", {"estudianteId": 12, "grupoId": 101}, 409, h)
    paso(c, "POST", "/api/v1/matriculas", "coordinador", {"estudianteId": 10, "grupoId": 101}, 409, h)
    paso(c, "POST", "/api/v1/matriculas", "coordinador", {"estudianteId": 12, "grupoId": 102}, 409, h)
    paso(c, "GET", "/api/v1/grupos/101", "coordinador", esperado=200, h=h)


def prueba_seguridad():
    print(f"{A}PRUEBA 2 · SEGURIDAD · Autenticación y autorización{N}\n")
    c = nueva_bd()
    hc = login(c, "coordinador@sga.test")
    mid = c.post("/api/v1/matriculas", json={"estudianteId": 10, "grupoId": 100}, headers=hc).json()["matriculaId"]
    url = f"/api/v1/matriculas/{mid}/calificaciones"
    nota = {"corte": "1", "nota": 4.5}
    print("CP-S01  Control de acceso por token y rol")
    paso(c, "PUT", url, "sin token", nota, 401)
    paso(c, "PUT", url, "token alterado", nota, 401, {"Authorization": "Bearer abc.def.ghi"})
    paso(c, "PUT", url, "estudiante", nota, 403, login(c, "est.camila@sga.test"))
    paso(c, "PUT", url, "docente de otro grupo", nota, 403, login(c, "docente.luis@sga.test"))
    paso(c, "GET", "/api/v1/estudiantes/11/matriculas", "estudiante 10", None, 403, login(c, "est.camila@sga.test"))
    hd = login(c, "docente.ana@sga.test")
    paso(c, "PUT", url, "docente del grupo", nota, 200, hd)
    paso(c, "POST", "/api/v1/auth/logout", "docente del grupo", None, 204, hd)
    paso(c, "PUT", url, "token ya revocado", nota, 401, hd)
    print("\nCP-S02  Bloqueo de cuenta tras 5 intentos fallidos")
    for i in range(5):
        paso(c, "POST", "/api/v1/auth/login", f"intento {i+1}",
             {"correo": "docente.ana@sga.test", "contrasena": f"incorrecta{i}"}, 401)
    r = paso(c, "POST", "/api/v1/auth/login", "intento 6 (clave correcta)",
             {"correo": "docente.ana@sga.test", "contrasena": datos_prueba.CLAVE}, (423, 429))
    if r.status_code == 200:
        print(f"\n {R}DEFECTO D-01: la cuenta no se bloquea; un atacante puede probar contraseñas sin límite.{N}")


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "FS"
    if "F" in modo:
        prueba_funcional()
    if "S" in modo:
        prueba_seguridad()
