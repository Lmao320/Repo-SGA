# Prototipo del SGA y pruebas de software

Prototipo funcional de los módulos de **autenticación, matrículas y calificaciones** del Sistema de Gestión Académica, usado como sistema bajo prueba en la actividad *Diseño y elaboración de dos pruebas de software y tres métricas de calidad*.

Tecnología: Python 3.13, FastAPI, SQLite, JWT (PyJWT) y bcrypt. Todos los datos son ficticios.

## Cómo ejecutarlo

```bash
cd prototipo
pip install -r requirements.txt
python -m pytest -v --cov=app --cov-report=term-missing   # pruebas + métrica de cobertura
python scripts/evidencias.py                               # recorrido paso a paso de los 4 casos
python scripts/medir_rendimiento.py                        # carga, concurrencia y tiempos de respuesta
```

Para explorar la API: `python -c "from app import db,datos_prueba as d;c=db.conectar();d.cargar(c)"` y luego `uvicorn app.main:app`, abrir http://127.0.0.1:8000/docs (usuarios en `app/datos_prueba.py`, clave `Clave#2026`).

## Pruebas

| Prueba | Tipo | Caso | Resultado |
|---|---|---|---|
| 1 | Funcional (caja negra) – Matrículas | CP-F01 Matrícula exitosa con cupo | Aprobado |
| 1 | Funcional (caja negra) – Matrículas | CP-F02 Rechazo por cupo lleno, duplicidad y periodo cerrado | Aprobado |
| 2 | Seguridad – Autenticación y autorización | CP-S01 Control de acceso por token y rol | Aprobado |
| 2 | Seguridad – Autenticación y autorización | CP-S02 Bloqueo de cuenta por fuerza bruta | **Fallido (defecto D-01)** |

## Defectos encontrados

- **D-01 (abierto, severidad alta):** la cuenta no se bloquea tras 5 intentos fallidos de inicio de sesión.
- **D-02 (corregido):** bajo carga concurrente el servidor fallaba al compartir conexiones SQLite entre hilos (96 % de errores). Se corrigió en `app/db.py`; tras la corrección, 0 errores.

## Métricas

| Métrica | Resultado |
|---|---|
| Cobertura de sentencias | 96 % (153 de 159) |
| Densidad de defectos | 8,4 defectos/KLOC (2 en 238 líneas de código) |
| Tiempo de respuesta p95 (50 clientes concurrentes) | 197,6 ms, 0 % de errores |

Las capturas y salidas completas están en `evidencias/`.
