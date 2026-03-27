# Funcionalidades

Resumen funcional basado en módulos de la app y documentación existente.

## Módulos principales
- Inventario y equipos: alta, edición y listado de equipos.
- Catálogos: tipo, marca, modelo, estado.
- Unidades y proveedores.
- Asignaciones y devoluciones.
- Funcionarios (activos/inactivos y motivos).
- Traslados e incidencias.
- Notificaciones y utilidades.
- Cuentas y autenticación.

## Fuentes en código
- Blueprints registrados en [Flask/app/main.py](Flask/app/main.py)
- Módulos de dominio en [Flask/app](Flask/app)

## Inventario por ciclo
- Tablas inventario_ciclo e inventario_item en BD.
- Rutas y lógica en [Flask/app/equipo.py](Flask/app/equipo.py).

## Notificaciones
- Resumen API en [Flask/app/equipo.py](Flask/app/equipo.py).
- Tabla notificacion en BD.

## Importaciones y utilidades
- Sincronización Excel de funcionarios: [sync_funcionarios_excel.py](sync_funcionarios_excel.py) y [SYNC_FUNCIONARIOS_EXCEL.md](SYNC_FUNCIONARIOS_EXCEL.md).
- Scripts de datos de ejemplo: [insert_sample_data.sql](insert_sample_data.sql) y [load_sample_data.sh](load_sample_data.sh).

## Reportes y exportación
- Exportaciones/planillas en módulos de app (Excel).
- Datos de ejemplo y verificación: [verify_sample_data.py](verify_sample_data.py) y [verify_setup.sh](verify_setup.sh).
