# Checklist de Release

## Antes del release
- Actualizar documentación en docs/.
- Validar .env.example sin secretos.
- Ejecutar scripts de verificación local.
- Confirmar conexión a BD y vistas.

## Evidencias
- Generar snapshots locales en [docs/_generated](docs/_generated).
- Generar snapshots del servidor y copiarlos a [docs/_generated](docs/_generated).
- Generar diff desde COMMIT_BUENO (pendiente si no se define).

## Validación funcional
- Login con usuario admin.
- CRUD de equipos y catálogos.
- Asignaciones y devoluciones.
- Inventario por ciclo.
- Notificaciones.

## Preparación para servidor
- Crear /opt/inventario-junji/.env con valores reales.
- Instalar dependencias.
- Validar puerto y firewall.
- Confirmar servicio systemd si aplica.

## Post-release
- Verificar logs.
- Confirmar vistas con datos.
- Registrar commit/tag del release.
