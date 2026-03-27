# Esquema de Base de Datos (resumen)

Este resumen se basa en scripts y backups existentes en el repo.

## Evidencias consultadas
- [db_backups/inventariofinal_before_merge_2026-01-20.sql](db_backups/inventariofinal_before_merge_2026-01-20.sql)
- [db_backups/inventariofinal_views_fixed.sql](db_backups/inventariofinal_views_fixed.sql)
- [SQL_historial/add_funcionario_inactividad.sql](SQL_historial/add_funcionario_inactividad.sql)
- [SQL_historial/add_campo_activo_funcionario.sql](SQL_historial/add_campo_activo_funcionario.sql)
- [SQL_historial/16-01-2026-create-super_equipo_view.sql](SQL_historial/16-01-2026-create-super_equipo_view.sql)
- [funcionario_schema.txt](funcionario_schema.txt)

## Cambios y objetos relevantes
### Columnas nuevas en funcionario
- activoFuncionario
- motivo_inactividad_id
- detalle_inactividad
- fecha_inactividad

Fuentes:
- [SQL_historial/add_campo_activo_funcionario.sql](SQL_historial/add_campo_activo_funcionario.sql)
- [funcionario_schema.txt](funcionario_schema.txt)

### Tablas nuevas o recientes
- funcionario_inactividad
- motivo_inactividad
- notificacion
- pendiente_devolucion
- inventario_ciclo
- inventario_item

Fuentes:
- [SQL_historial/add_funcionario_inactividad.sql](SQL_historial/add_funcionario_inactividad.sql)
- [db_backups/inventariofinal_before_merge_2026-01-20.sql](db_backups/inventariofinal_before_merge_2026-01-20.sql)

### Vistas
- super_equipo
- super_equipo_vw
- vw_funcionarios_inactivos
- vw_pendientes_devolucion_detalle
- vw_pendientes_por_funcionario

Fuentes:
- [db_backups/inventariofinal_views_fixed.sql](db_backups/inventariofinal_views_fixed.sql)
- [SQL_historial/16-01-2026-create-super_equipo_view.sql](SQL_historial/16-01-2026-create-super_equipo_view.sql)

### Índices únicos
- uq_devolucion_equipoasig (tabla devolucion)

Fuente:
- [db_backups/inventariofinal_before_merge_2026-01-20.sql](db_backups/inventariofinal_before_merge_2026-01-20.sql)

## Notas importantes
- inventario_ciclo.estado no tiene ABIERTO; solo EN_PROCESO y CERRADO.
- inventario_item depende de inventario_ciclo y equipo (FK).
