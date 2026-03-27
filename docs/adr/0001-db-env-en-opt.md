# ADR 0001: .env de BD en /opt/inventario-junji/.env

## Contexto
Se requiere separar credenciales de la base de datos del código fuente y permitir que local y servidor usen la misma base de código con distinta configuración.

## Decisión
El archivo .env en servidor vive en /opt/inventario-junji/.env y es cargado con prioridad desde [Flask/app/db.py](Flask/app/db.py).

## Consecuencias
- Mejora la seguridad al no versionar credenciales.
- Simplifica el deployment porque no se cambia código entre ambientes.
- Exige mantener permisos de lectura adecuados sobre /opt/inventario-junji/.env.
