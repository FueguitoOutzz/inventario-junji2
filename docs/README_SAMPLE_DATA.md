# 📋 Generador de Datos de Ejemplo - JUNJI Inventario

## ⚠️ ADVERTENCIA

Estos scripts **SOLO** son para **DESARROLLO LOCAL**. 
**NUNCA** ejecutar en producción.

---

## 📦 Contenido

Este directorio contiene scripts para generar y verificar datos de ejemplo:

1. **`generate_sample_data.py`** - Script Python para insertar datos
2. **`insert_sample_data.sql`** - Script SQL alternativo
3. **`verify_sample_data.py`** - Script para verificar integridad de datos
4. **`README_SAMPLE_DATA.md`** - Este archivo

---

## 🚀 Cómo Usar

### Opción 1: Usando Python (Recomendado)

```bash
# Activar entorno virtual (si lo tienes)
source venv/bin/activate

# Ejecutar el generador
python3 generate_sample_data.py

# Opcionalmente, verificar los datos
python3 verify_sample_data.py
```

**Ventajas:**
- ✅ Más control y validaciones
- ✅ Mensajes de progreso más detallados
- ✅ Manejo de errores mejorado

---

### Opción 2: Usando SQL directo

```bash
# Asegúrate de que MariaDB está corriendo
mysql -u junji -p inventariofinal < insert_sample_data.sql
```

**Requisitos:**
- Usuario `junji` con contraseña `Tijunji2017`
- MariaDB/MySQL corriendo en localhost:3306

**Ventajas:**
- ✅ Más rápido
- ✅ No requiere dependencias Python adicionales

---

## 📊 Qué se Inserta

### Datos Generados

| Entidad | Cantidad | Detalles |
|---------|----------|----------|
| **Funcionarios** | 9 | 8 activos + 1 inactivo |
| **Unidades** | 3 | Diferentes modalidades |
| **Equipos** | 10 | Laptops, monitores, celulares, tablets, impresoras |
| **Asignaciones Activas** | 5 | Equipos en estado EN USO |
| **Devoluciones Históricas** | 2 | Equipos devueltos (ahora SIN ASIGNAR) |
| **Estados de Equipo** | 4 | SIN ASIGNAR, EN USO, EN REPARACIÓN, DADO DE BAJA |

### Tipos y Modelos

- **5 Tipos de Equipo:** Laptop, Monitor, Celular, Tablet, Impresora
- **6 Marcas:** Dell, HP, Samsung, LG, Apple, Lenovo
- **6 Modelos:** Con relaciones coherentes marca-tipo

---

## 🎯 Reglas Respetadas

Todos los scripts garantizan:

✅ **Equipos EN USO** siempre tienen asignación activa
```
equipo (estado="EN USO") → asignacion (Activo=1) → funcionario
```

✅ **Equipos SIN ASIGNAR** nunca tienen asignación activa
```
equipo (estado="SIN ASIGNAR") → sin asignaciones activas
```

✅ **Devoluciones** dejan el equipo en estado "SIN ASIGNAR"
```
devolucion (fecha) → equipo_asignacion (inactivo) → equipo (SIN ASIGNAR)
```

✅ **Integridad referencial** completa
```
equipo → modelo → marca-tipo → marca/tipo
asignacion → funcionario → unidad
```

✅ **Funcionarios inactivos** pueden existir sin equipos
```
Marcela Castillo (rutFuncionario=18901234) sin asignaciones
```

---

## 🔍 Verificar los Datos

Después de insertar, verifica que todo está correcto:

```bash
python3 verify_sample_data.py
```

El script comprobará:
- ✅ Volumen mínimo de datos
- ✅ Consistencia de estados
- ✅ Integridad de relaciones
- ✅ Validez de devoluciones
- ✅ Estadísticas generales

**Salida esperada:**
```
✓ 9 funcionarios registrados
✓ 3 unidades registradas
✓ 10 equipos registrados
✓ Todos los equipos EN USO tienen asignación activa
✓ Integridad de relaciones: OK
...
```

---

## 🔄 Limpiar y Regenerar

Si necesitas limpiar todo e insertar nuevamente:

```bash
# Opción 1: Eliminar solo los datos de ejemplo
mysql -u junji -p inventariofinal << EOF
DELETE FROM devolucion;
DELETE FROM equipo_asignacion;
DELETE FROM asignacion;
DELETE FROM equipo;
DELETE FROM orden_compra;
DELETE FROM proveedor;
DELETE FROM funcionario;
DELETE FROM unidad;
DELETE FROM modelo_equipo;
DELETE FROM marca_tipo_equipo;
DELETE FROM marca_equipo;
DELETE FROM tipo_equipo;
DELETE FROM tipo_adquisicion;
DELETE FROM estado_equipo;
EOF

# Opción 2: Regenerar completamente
python3 generate_sample_data.py
```

---

## 🧪 Casos de Prueba

### 1. Verificar Equipos EN USO

```sql
SELECT e.Cod_inventarioEquipo, f.nombreFuncionario, ee.nombreEstado_equipo
FROM equipo e
JOIN equipo_asignacion ea ON e.idEquipo = ea.idEquipo
JOIN asignacion a ON ea.idAsignacion = a.idAsignacion
JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
JOIN estado_equipo ee ON e.idEstado_equipo = ee.idEstado_equipo
WHERE a.ActivoAsignacion = 1;
```

### 2. Verificar Equipos SIN ASIGNAR

```sql
SELECT Cod_inventarioEquipo, nombreEstado_equipo
FROM equipo e
JOIN estado_equipo ee ON e.idEstado_equipo = ee.idEstado_equipo
WHERE ee.nombreEstado_equipo = 'SIN ASIGNAR';
```

### 3. Verificar Devoluciones

```sql
SELECT f.nombreFuncionario, e.Cod_inventarioEquipo, d.fechaDevolucion
FROM devolucion d
JOIN equipo_asignacion ea ON d.idEquipoAsignacion = ea.idEquipoAsignacion
JOIN asignacion a ON ea.idAsignacion = a.idAsignacion
JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
JOIN equipo e ON ea.idEquipo = e.idEquipo;
```

---

## 📝 Notas Importantes

- **No hay datos reales:** Todos los nombres, RUTs y emails son ficticios
- **Fechas coherentes:** Las asignaciones y devoluciones usan fechas realistas
- **Funcionarios sin equipos:** `Marcela Castillo (18901234)` no tiene asignaciones para probar ese caso
- **Equipos históricos:** INV-2024-007 y INV-2024-008 tienen devoluciones documentadas

---

## 🐛 Solución de Problemas

### Error: "Access denied for user 'junji'"

```bash
# Verifica credenciales en Flask/env_vars.py
# Usuario: junji
# Contraseña: Tijunji2017
# Host: 127.0.0.1
```

### Error: "Table 'inventariofinal' doesn't exist"

```bash
# Primero ejecuta el script de inicialización
mysql -u junji -p < inventariofinal.sql
```

### Error: "Foreign key constraint fails"

```bash
# Ejecuta el SQL completo respetando el orden de inserciones
# O usa el script Python que maneja las dependencias automáticamente
python3 generate_sample_data.py
```

---

## 📚 Referencias

- [SETUP_LOCAL.md](../SETUP_LOCAL.md) - Guía de ejecución local
- [inventariofinal.sql](../inventariofinal.sql) - Estructura de BD
- [Flask/env_vars.py](../Flask/env_vars.py) - Variables de entorno

---

**Última actualización:** 12 de enero de 2026
**Ambiente:** Desarrollo Local
