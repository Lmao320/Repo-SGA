# Arquitectura de un Sistema de Gestión Académica (SGA)

Trabajo de la asignatura **Arquitectura de Software** (CUN, Ingeniería de Sistemas).
Propuesta de arquitectura para un SGA web: monolito modular en capas, API REST documentada y PostgreSQL con réplica.

> Este repositorio contiene la **arquitectura y los modelos**, no la implementación del sistema.
> No incluye datos personales reales ni credenciales.

## Estructura

| Carpeta | Contenido |
|---|---|
| `diagramas/fuentes/` | Código fuente de los diagramas: Graphviz (`.dot`) y Mermaid (`.mmd`) |
| `diagramas/exportados/` | Diagramas exportados en PNG y SVG |
| `api/openapi.yaml` | Contrato OpenAPI 3.1 de la API REST propuesta (RNF-08) |
| `docs/` | Informe final en PDF |

## Diagramas

| Figura | Archivo | Modelo |
|---|---|---|
| 1 | `casos_uso.dot` | Casos de uso (actores: administrador, coordinador, docente, estudiante) |
| 2 | `componentes.dot` | Vista lógica / componentes |
| 3 | `despliegue.dot` | Despliegue en nube |
| 4 | `datos.mmd` | Modelo de datos conceptual (ER) |
| 5 | `secuencia.mmd` | Secuencia del proceso de matrícula |

### Regenerar los diagramas

```bash
# Graphviz
dot -Tpng diagramas/fuentes/casos_uso.dot -o diagramas/exportados/casos_uso.png
# Mermaid (npm i -g @mermaid-js/mermaid-cli)
mmdc -i diagramas/fuentes/secuencia.mmd -o diagramas/exportados/secuencia.png
```

Los `.mmd` también se pueden pegar en https://mermaid.live para verlos y editarlos.

## Decisiones principales

- **ADR-01** Monolito modular en lugar de microservicios.
- **ADR-02** Matrícula en transacción con `SELECT ... FOR UPDATE` y restricción `UNIQUE`.
- **ADR-03** JWT de corta duración con lista de revocación en Redis.
- **ADR-04** PostgreSQL con réplica en otra zona y respaldos con recuperación a un punto en el tiempo.
- **ADR-05** Auditoría en la misma transacción, tabla de solo inserción.

El detalle está en el informe (`docs/`).

## Autor

Santiago, Ingeniería de Sistemas, CUN. Noviembre de 2026.
