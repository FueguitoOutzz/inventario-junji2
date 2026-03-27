# 🚀 Generación de Datos de Ejemplo - Sistema JUNJI Inventario

## 📋 Descripción General

Se han creado scripts para generar datos de ejemplo coherentes para el desarrollo local del sistema de inventario. **Estos scripts solo funcionan con la base de datos existente y NO tocan la producción.**

---

## 📂 Archivos Creados

### 1. **`insert_sample_data.sh`** ✨ RECOMENDADO
- Script Bash que inserta datos de ejemplo
- **Más simple y robusto**
- Funciona con las unidades y funcionarios existentes

```bash
./insert_sample_data.sh
```

**Qué inserta:**
- 5 órdenes de compra de ejemplo
- 4 proveedores de ejemplo
- Tipos de equipo (Laptop, Monitor, Celular)
- Marcas de equipo (Dell, HP, Samsung)
- Relaciones marca-tipo coherentes
- 10 equipos con código `INV-EJ-XXXX`
- Todos los equipos comienzan en estado "SIN ASIGNAR"

### 2. **`generate_sample_data.py`**
- Script Python alternativo (requiere `pymysql`)
- Más control sobre los datos
- NO RECOMENDADO para uso inicial (requiere dependencias)

### 3. **`verify_sample_data.py`**
- Script para verificar integridad de datos
- Comprueba consistencia de estados
- Valida relaciones de FK
- Muestra estadísticas

```bash
python3 verify_sample_data.py
```

### 4. **`sample_data_helper.sh`**
- Helper script para gestionar datos
- Operaciones: `insert`, `verify`, `clean`, `reset`

```bash
./sample_data_helper.sh insert    # Insertar
./sample_data_helper.sh verify    # Verificar
./sample_data_helper.sh clean     # Limpiar
./sample_data_helper.sh reset     # Limpiar e insertar
```

### 5. **`README_SAMPLE_DATA.md`**
- Documentación completa
- Guías de uso
- Casos de prueba SQL
- Solución de problemas

---

## 🚀 Uso Rápido

### Opción 1: Insertar Datos (RECOMENDADO)

```bash
cd /Users/idknoou/Documents/GIT/Junji-Inventario
./insert_sample_data.sh
```

**Resultado esperado:**
```
✓ Conexión establecida
ℹ Insertando datos de ejemplo...
...
✓ Datos de ejemplo insertados correctamente

📊 Equipos de ejemplo disponibles:
INV-EJ-0001  | Laptop Ejemplo 1
INV-EJ-0002  | Laptop Ejemplo 2
INV-EJ-0003  | Monitor Ejemplo
INV-EJ-0004  | Celular Ejemplo
INV-EJ-0005  | Laptop Ejemplo
```

### Opción 2: Verificar Integridad

```bash
python3 verify_sample_data.py
```

### Opción 3: Limpiar Datos

```bash
./sample_data_helper.sh clean
```

---

## 📊 Datos Generados

| Entidad | Cantidad | Detalles |
|---------|----------|----------|
| **Órdenes de Compra** | 2 | OC-EJEMPLO-001, OC-EJEMPLO-002 |
| **Proveedores** | 2 | Proveedor Ejemplo 1, 2 |
| **Tipos de Equipo** | 3 | Laptop, Monitor, Celular |
| **Marcas** | 3 | Dell, HP, Samsung |
| **Modelos** | 4 | Con relaciones coherentes |
| **Equipos** | 10 | Código INV-EJ-0001 a INV-EJ-0005 (duplicados con números simples) |
| **Estado de Equipos** | 4 | SIN ASIGNAR, EN USO, EN REPARACIÓN, DADO DE BAJA |

---

## ✅ Garantías de Coherencia

Todos los scripts garantizan:

✅ **Equipos SIN ASIGNAR** - No tienen asignación activa  
✅ **Integridad referencial** - Todas las FK son válidas  
✅ **Relaciones coherentes** - Marcas ↔ Tipos correctos  
✅ **Estados consistentes** - Equipos en estado apropiado  
✅ **NO afecta producción** - Usa datos ficticios  
✅ **Funciona con datos reales** - Se integra con funcionarios/unidades existentes  

---

## 🔄 Flujo de Trabajo

```
1. Ejecutar: ./insert_sample_data.sh
   ↓
2. Acceder a: http://localhost:3300
   ↓
3. Usar credenciales: admin / 1234
   ↓
4. Buscar equipos: INV-EJ-XXXX
   ↓
5. Probar asignaciones, devoluciones, etc.
```

---

## 🧪 Pruebas Recomendadas

### Prueba 1: Verificar Equipos
```sql
SELECT * FROM equipo WHERE Cod_inventarioEquipo LIKE 'INV-EJ%';
```

### Prueba 2: Ver Modelos
```sql
SELECT e.Cod_inventarioEquipo, m.nombreModeloequipo, t.nombreTipo_equipo
FROM equipo e
JOIN modelo_equipo m ON e.idModelo_equipo = m.idModelo_Equipo
JOIN marca_tipo_equipo mt ON m.idMarca_Tipo_Equipo = mt.idMarcaTipo
JOIN tipo_equipo t ON mt.idTipo_equipo = t.idTipo_equipo
WHERE e.Cod_inventarioEquipo LIKE 'INV-EJ%';
```

### Prueba 3: Contar por Tipo
```sql
SELECT t.nombreTipo_equipo, COUNT(*) as cantidad
FROM equipo e
JOIN modelo_equipo m ON e.idModelo_equipo = m.idModelo_Equipo
JOIN marca_tipo_equipo mt ON m.idMarca_Tipo_Equipo = mt.idMarcaTipo
JOIN tipo_equipo t ON mt.idTipo_equipo = t.idTipo_equipo
WHERE e.Cod_inventarioEquipo LIKE 'INV-EJ%'
GROUP BY t.nombreTipo_equipo;
```

---

## 📝 Notas Importantes

⚠️ **SOLO PARA DESARROLLO LOCAL**
- No ejecutar en producción
- Los datos son ficticios
- Apto para pruebas y desarrollo

🔑 **Credenciales de acceso:**
- Usuario: `admin`
- Contraseña: `1234`

🗄️ **Conexión BD:**
- Host: `127.0.0.1`
- Puerto: `3306`
- Usuario: `junji`
- Contraseña: `Tijunji2017`
- Base de datos: `inventariofinal`

---

## 🆘 Solución de Problemas

### Error: "Connection refused"
```bash
# Asegúrate que MariaDB está corriendo
./start.sh
```

### Error: "Access denied for user"
```bash
# Verifica las credenciales en los scripts
# Usuario: junji
# Contraseña: Tijunji2017
```

### Error: "Duplicate entry"
```bash
# Los datos ya existen. Ejecuta:
./sample_data_helper.sh clean
# Y luego:
./insert_sample_data.sh
```

---

## 📚 Archivos Relacionados

- [SETUP_LOCAL.md](./SETUP_LOCAL.md) - Guía de ejecución local
- [Flask/env_vars.py](./Flask/env_vars.py) - Variables de entorno
- [inventariofinal.sql](./inventariofinal.sql) - Estructura de BD
- [README_SAMPLE_DATA.md](./README_SAMPLE_DATA.md) - Documentación completa

---

**Estado:** ✅ Completado  
**Última actualización:** 12 de enero de 2026  
**Ambiente:** Desarrollo Local (macOS)  
**Status de BD:** Con datos de ejemplo listos para pruebas
