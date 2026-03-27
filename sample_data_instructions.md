# 📊 Guía de Datos de Ejemplo

## Descripción

El archivo `insert_sample_data.sql` contiene un conjunto completo de datos de ejemplo para desarrollo local, incluyendo:

✓ **Tipos de Adquisición** - COMPRA, ARRIENDO, PRÉSTAMO, COMODATTO  
✓ **Proveedores** - 3 proveedores de ejemplo  
✓ **Órdenes de Compra** - 5 órdenes de ejemplo  
✓ **Tipos y Marcas de Equipo** - Laptops, Monitores, Celulares, Tablets, Impresoras  
✓ **Modelos de Equipo** - Dell, HP, Samsung, Apple  
✓ **Unidades** - 3 unidades educativas de ejemplo  
✓ **Funcionarios** - 9 funcionarios con diferentes cargos  
✓ **Equipos** - 10 equipos de inventario  
✓ **Asignaciones Activas** - 5 equipos actualmente asignados  
✓ **Devoluciones Históricas** - 2 devoluciones registradas  

## ¿Cómo Usar?

### Opción 1: Desde línea de comandos (Recomendado)

```bash
mysql -u junji -p inventariofinal < insert_sample_data.sql
```

Cuando se solicite la contraseña, ingresa: `Tijunji2017`

### Opción 2: Desde un cliente MySQL

1. Abre tu cliente MySQL (MySQL Workbench, phpMyAdmin, etc.)
2. Selecciona la base de datos `inventariofinal`
3. Abre el archivo `insert_sample_data.sql`
4. Ejecuta el script completo

### Opción 3: Desde la terminal de MariaDB

```bash
mysql -u junji -p
```

Luego ejecuta:

```sql
USE inventariofinal;
SOURCE /ruta/al/insert_sample_data.sql;
```

## ⚠️ Importante

- **Solo para desarrollo local** - No usar en producción
- El script usa `INSERT IGNORE` para evitar duplicados si se ejecuta múltiples veces
- Se respetan todas las relaciones de claves foráneas (FK)
- Los datos se insertan en el orden correcto para mantener integridad referencial

## 📋 Credenciales de Acceso a la Aplicación

Una vez insertados los datos, puedes acceder a la aplicación con:

**URL:** http://localhost:3300  
**Usuario:** admin  
**Contraseña:** 1234

## 🔍 Verificación

El script muestra automáticamente un resumen al finalizar con:
- Total de funcionarios
- Total de unidades
- Total de equipos
- Equipos sin asignar
- Equipos en uso
- Asignaciones activas
- Devoluciones registradas

## 📝 Notas

- Los datos de ejemplo incluyen referencias reales a unidades (JUNJI Concepción, Coronel, Talcahuano)
- Los funcionarios tienen RUTs válidos y correos ficticios
- Los equipos tienen números de serie únicos
- Las fechas son consistentes y documentadas

---

**Última actualización:** 13 de enero de 2026
