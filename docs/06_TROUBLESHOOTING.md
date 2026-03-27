# Troubleshooting

## Access denied (using password: NO)
**Síntoma:** La app no autentica a MySQL.
**Causas comunes:** .env no cargado, variables vacías, usuario/clave incorrectos.
**Acciones:**
- Confirmar que existe .env y que DB_USER/DB_PASSWORD están definidos.
- Verificar que se esté cargando /opt/inventario-junji/.env en servidor.
- Revisar permisos del usuario en MySQL.

## root auth plugin 1698
**Síntoma:** No puedes usar root con contraseña.
**Causa:** root usa plugin auth_socket.
**Acciones:**
- En Linux: usar sudo mysql.
- Cambiar a mysql_native_password si aplica en el servidor (evaluar impacto).

## FK fails inventario_item -> inventario_ciclo
**Síntoma:** Error de clave foránea al insertar inventario_item.
**Causas comunes:** idInventario inexistente.
**Acciones:**
- Crear primero inventario_ciclo.
- Verificar idInventario e idEquipo antes de insertar.

## Collation mismatch en FK
**Síntoma:** Error de collation al crear FK.
**Acciones:**
- Unificar charset/collation entre tablas relacionadas.
- Revisar collation en tablas involucradas.

## Views devuelven 0
**Síntoma:** vistas sin resultados.
**Causas comunes:** filtros de estado, datos base vacíos o permisos.
**Acciones:**
- Verificar datos en tablas base.
- Revisar condiciones de las vistas en [db_backups/inventariofinal_views_fixed.sql](db_backups/inventariofinal_views_fixed.sql).

## Cache/recarga vista cambia resultados
**Síntoma:** al recargar la vista cambian resultados.
**Acciones:**
- Confirmar que la app no esté cacheando resultados.
- Reiniciar el servicio para limpiar estado.
- Verificar que las consultas no dependan de datos temporales.
