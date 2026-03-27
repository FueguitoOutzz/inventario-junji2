# Runbook de Deployment

Guía operativa para ejecutar y mantener la aplicación en local y servidor.

## Pre-requisitos
- Python 3.x
- MySQL/MariaDB 8.x+
- Paquetes Python listados en [Flask/requirements.txt](Flask/requirements.txt)
- Archivo .env con credenciales (no versionado)

## Estructura de ejecución
- App Flask en [Flask/app](Flask/app)
- Entrada principal: [Flask/app/main.py](Flask/app/main.py)
- Configuración DB: [Flask/app/db.py](Flask/app/db.py)

## Variables de entorno
- La app carga primero /opt/inventario-junji/.env si existe, si no usa .env local.
- Ver detalle en [docs/03_CONFIGURACION.md](docs/03_CONFIGURACION.md).

## Ejecución local (desarrollo)
1. Crear/activar venv.
2. Instalar dependencias.
3. Configurar .env local (sin secretos en repo).
4. Iniciar app:
   - Ejecutar [Flask/app/main.py](Flask/app/main.py).

Referencias: [QUICK_START.md](QUICK_START.md) y [SETUP_LOCAL.md](SETUP_LOCAL.md).

## Ejecución en servidor (producción)
1. Clonar repo y crear venv.
2. Configurar /opt/inventario-junji/.env con valores reales.
3. Instalar dependencias.
4. Ejecutar app:
   - Opción A: gunicorn (recomendado para producción).
   - Opción B: python main.py (solo desarrollo).

Documentación existente:
- [PLAN_DEPLOYMENT_PASO_A_PASO.md](PLAN_DEPLOYMENT_PASO_A_PASO.md)
- [DEPLOYMENT_README.md](DEPLOYMENT_README.md)
- [DEPLOYMENT_SERVER.md](DEPLOYMENT_SERVER.md)

## Servicio systemd (si existe en el servidor)
El servicio suele llamarse inventario-junji. Para registrar su configuración se usa:
- systemctl cat
- systemctl show

Si ya descargaste los snapshots, déjalos en [docs/_generated](docs/_generated).

## Verificaciones post-deploy
- Abrir la UI y confirmar login.
- Validar conexión a la BD.
- Revisar logs de app (si LOG_FILE está configurado).
- Confirmar que las vistas DB devuelven datos.

## Rollback
- Revertir al commit estable.
- Restaurar backup DB más reciente.
