# Resumen de Cambios (Git + BD)

Este documento consolida cambios confirmables desde Git y desde la base de datos.

## Estado de evidencias Git
- Historial resumido (OK): [docs/_generated/git_log_graph.txt](docs/_generated/git_log_graph.txt)
- Diff desde commit bueno (pendiente): [docs/_generated/diff_desde_commit_bueno.patch](docs/_generated/diff_desde_commit_bueno.patch)
- Archivos tocados (pendiente): [docs/_generated/archivos_tocados.txt](docs/_generated/archivos_tocados.txt)

### Pendiente
Falta definir el hash de COMMIT_BUENO para generar los diffs:
- diff completo
- lista de archivos tocados

## Cambios en BD (evidencia en SQL y backups)
Resumen con evidencia en:
- [db_backups/inventariofinal_before_merge_2026-01-20.sql](db_backups/inventariofinal_before_merge_2026-01-20.sql)
- [db_backups/inventariofinal_views_fixed.sql](db_backups/inventariofinal_views_fixed.sql)
- [SQL_historial/add_funcionario_inactividad.sql](SQL_historial/add_funcionario_inactividad.sql)
- [SQL_historial/add_campo_activo_funcionario.sql](SQL_historial/add_campo_activo_funcionario.sql)
- [SQL_historial/16-01-2026-create-super_equipo_view.sql](SQL_historial/16-01-2026-create-super_equipo_view.sql)

Detalle en [docs/04_BD_SCHEMA.md](docs/04_BD_SCHEMA.md).
