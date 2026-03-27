# Configuración

## Archivos de configuración
- Archivo ejemplo: [Flask/.env.example](Flask/.env.example)
- Archivo real (no versionado): .env
- En servidor: /opt/inventario-junji/.env (si existe, tiene prioridad)

El cargado de variables está en:
- [Flask/app/db.py](Flask/app/db.py)
- [Flask/app/main.py](Flask/app/main.py)
- [Flask/app/app.py](Flask/app/app.py)

## Variables de entorno
### Base de datos
- DB_HOST: host de MySQL/MariaDB.
- DB_PORT: puerto (por defecto 3306).
- DB_USER: usuario.
- DB_PASSWORD: contraseña.
- DB_NAME: nombre de la base de datos.

### Flask
- FLASK_ENV: development o production.
- FLASK_DEBUG: True/False.
- FLASK_PORT: puerto del servidor Flask.
- FLASK_HOST: host de bind.

### Logging (opcional)
- LOG_FILE: ruta de log.
- LOG_LEVEL: INFO|DEBUG|WARNING|ERROR.

### Correo (opcional)
- EMAIL_USER
- EMAIL_PASSWORD

## Reglas
- No subir .env al repositorio.
- No incluir credenciales reales en documentación.
- Mantener .env.example con nombres de variables.

## Validaciones
- Si DB_HOST o DB_PORT son incorrectos, falla la conexión.
- Si no existe /opt/inventario-junji/.env, se usa el .env local.
