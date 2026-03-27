# Inventario JUNJI — Guía Única y Resumen

Documento único, breve y en español: cómo iniciar, qué se cambió y problemas resueltos.

## 1) Inicio rápido (local)
1. Crear el archivo .env desde el ejemplo y completar variables.
2. Ejecutar el script de arranque.

Preparación del entorno local (una sola vez):
1. Tener Python y MySQL/MariaDB instalados.
2. Crear y activar un entorno virtual.
3. Instalar dependencias desde [Flask/requirements.txt](Flask/requirements.txt).
4. Crear la base inventariofinal en tu MySQL.
5. (Opcional) Cargar datos de ejemplo desde [insert_sample_data.sql](insert_sample_data.sql).

Archivos clave:
- [Flask/.env.example](Flask/.env.example)
- [start.sh](start.sh)

## 2) Flujo de ejecución
- Entrada principal: [Flask/app/main.py](Flask/app/main.py)
- Configuración DB: [Flask/app/db.py](Flask/app/db.py)
- Aplicación Flask: `app` en [Flask/app/app.py](Flask/app/app.py)

## 3) Qué se cambió (resumen)
- Configuración por variables de entorno.
- Prioridad de /opt/inventario-junji/.env en servidor.
- Logging opcional con LOG_FILE/LOG_LEVEL.
- Inventario por ciclo (inventario_ciclo e inventario_item).
- Funcionarios inactivos con motivo/fecha/detalle.

Detalle en:
- [docs/01_CAMBIOS_RESUMEN.md](docs/01_CAMBIOS_RESUMEN.md)
- [docs/04_BD_SCHEMA.md](docs/04_BD_SCHEMA.md)

## 4) Problemas y soluciones
Resumen directo en:
- [docs/06_TROUBLESHOOTING.md](docs/06_TROUBLESHOOTING.md)

## 5) BD (mínimo necesario)
- inventario_ciclo.estado solo acepta EN_PROCESO y CERRADO.
- inventario_item depende de inventario_ciclo y equipo (FK).
- funcionario tiene campos de inactividad.

## 6) Operación
- Runbook: [docs/02_DEPLOYMENT_RUNBOOK.md](docs/02_DEPLOYMENT_RUNBOOK.md)
- Configuración: [docs/03_CONFIGURACION.md](docs/03_CONFIGURACION.md)
- Checklist: [docs/07_CHECKLIST_RELEASE.md](docs/07_CHECKLIST_RELEASE.md)

## 7) Evidencias
- [docs/_generated](docs/_generated)
- [docs/_generated/git_log_graph.txt](docs/_generated/git_log_graph.txt)

## 8) Seguridad
- No publicar credenciales.
- El .env real no va al repo.
