"""Métrica 3: tiempo de respuesta bajo carga concurrente + verificación de integridad del cupo.

Levanta el prototipo con uvicorn sobre una base temporal, crea 60 estudiantes ficticios y:
  1) Lanza 60 matrículas simultáneas sobre un grupo de 30 cupos (debe aceptar exactamente 30).
  2) Lanza 500 consultas con 50 clientes concurrentes y mide latencias.
Uso: python scripts/medir_rendimiento.py
"""
import asyncio
import os
import statistics
import subprocess
import sys
import tempfile
import time

import httpx

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
PUERTO = 8765
BASE = f"http://127.0.0.1:{PUERTO}/api/v1"


def preparar_bd(ruta):
    os.environ["SGA_DB"] = ruta
    from app import datos_prueba, db
    db.DB_PATH = ruta
    con = db.conectar()
    datos_prueba.cargar(con)
    h = con.execute("SELECT hash_contrasena FROM usuario WHERE id=10").fetchone()[0]
    for i in range(60):
        con.execute("INSERT INTO usuario (id, correo, hash_contrasena, rol) VALUES (?,?,?,'ESTUDIANTE')",
                    (1000 + i, f"carga{i}@sga.test", h))
    con.execute("INSERT INTO grupo (id, codigo, asignatura, periodo_id, docente_id, cupo_max) "
                "VALUES (103,'ING-01','Ingeniería de Software',1,3,30)")
    con.close()


def percentil(datos, p):
    datos = sorted(datos)
    k = (len(datos) - 1) * p / 100
    f = int(k)
    return datos[f] + (datos[min(f + 1, len(datos) - 1)] - datos[f]) * (k - f)


async def main():
    async with httpx.AsyncClient(timeout=30, trust_env=False) as c:
        r = await c.post(f"{BASE}/auth/login", json={"correo": "coordinador@sga.test", "contrasena": "Clave#2026"})
        h = {"Authorization": f"Bearer {r.json()['accessToken']}"}

        # 1) Integridad: 60 matrículas simultáneas sobre 30 cupos
        async def matricular(est):
            t = time.perf_counter()
            try:
                r = await c.post(f"{BASE}/matriculas", json={"estudianteId": est, "grupoId": 103}, headers=h)
                codigo = r.status_code
            except httpx.HTTPError:
                codigo = "conexión cortada"
            return codigo, (time.perf_counter() - t) * 1000
        res = await asyncio.gather(*[matricular(1000 + i) for i in range(60)])
        codigos = [s for s, _ in res]
        lat_mat = [ms for s, ms in res if s in (201, 409)] or [0.0]
        cupo = None
        for _ in range(3):
            try:
                cupo = (await c.get(f"{BASE}/grupos/103", headers=h)).json()["cupo_ocupado"]
                break
            except (httpx.HTTPError, ValueError):
                await asyncio.sleep(0.2)

        # 2) Rendimiento: 500 consultas, 50 clientes concurrentes
        sem = asyncio.Semaphore(50)
        async def consultar(i):
            async with sem:
                t = time.perf_counter()
                try:
                    r = await c.get(f"{BASE}/estudiantes/{1000 + i % 60}/matriculas", headers=h)
                    codigo = r.status_code
                except httpx.HTTPError:
                    codigo = "conexión cortada"
                return codigo, (time.perf_counter() - t) * 1000
        t0 = time.perf_counter()
        res2 = await asyncio.gather(*[consultar(i) for i in range(500)])
        dur = time.perf_counter() - t0
        errores = sum(1 for s, _ in res2 if s != 200)
        lat = [ms for s, ms in res2 if s == 200] or [0.0]

    print("=" * 62)
    print(" PRUEBA DE CARGA Y CONCURRENCIA - SGA prototipo")
    print("=" * 62)
    print(" [1] 60 matrículas simultáneas sobre un grupo de 30 cupos")
    print(f"     201 Created : {codigos.count(201)}")
    print(f"     409 Conflict: {codigos.count(409)}")
    otros = len(codigos) - codigos.count(201) - codigos.count(409)
    print(f"     Errores (500 o conexión cortada): {otros}")
    print(f"     Cupo ocupado final: {cupo} / 30  ->  {'OK' if cupo == 30 and codigos.count(201) == 30 else 'FALLA'}")
    print(f"     Latencia matrícula  p50={percentil(lat_mat,50):.1f} ms  p95={percentil(lat_mat,95):.1f} ms")
    print(" [2] 500 consultas con 50 clientes concurrentes")
    print(f"     Respuestas 200: {500 - errores}   Errores: {errores} ({errores/5:.1f} %)   Duración total: {dur:.2f} s   Throughput: {500/dur:.0f} req/s")
    print(f"     Latencia  media={statistics.mean(lat):.1f} ms  p50={percentil(lat,50):.1f} ms  "
          f"p95={percentil(lat,95):.1f} ms  máx={max(lat):.1f} ms")
    print(f"     Umbral RNF-02: p95 <= 3000 ms  ->  {'CUMPLE' if percentil(lat,95) <= 3000 and errores == 0 else 'NO CUMPLE'}")
    print("=" * 62)


if __name__ == "__main__":
    carpeta = tempfile.mkdtemp()
    ruta = os.path.join(carpeta, "sga_carga.db")
    preparar_bd(ruta)
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PUERTO),
                            "--log-level", "warning"], cwd=RAIZ, env={**os.environ, "SGA_DB": ruta})
    try:
        for _ in range(50):
            try:
                httpx.get(f"http://127.0.0.1:{PUERTO}/docs", timeout=1, trust_env=False)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        asyncio.run(main())
    finally:
        srv.terminate()
