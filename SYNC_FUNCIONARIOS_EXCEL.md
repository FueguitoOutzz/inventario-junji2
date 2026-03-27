# 🎯 Sistema de Sincronización de Funcionarios desde Excel

## Descripción

Este sistema permite:
1. **Agregar campo `activoFuncionario`** a la tabla `funcionario` (TINYINT 0/1)
2. **Sincronizar** funcionarios desde un archivo Excel
3. **Automatizar** el proceso: 
   - Funcionarios en Excel → `activoFuncionario = 1` (actualiza datos si cambiaron)
   - Funcionarios NO en Excel → `activoFuncionario = 0` (licencia, renuncia, transferencia, etc)
4. **Auditar** cambios con log detallado

---

## PASO 1: Agregar la columna a la BD

Ejecuta en tu MariaDB:

```bash
mysql -u junji -p inventariofinal < SQL_historial/add_campo_activo_funcionario.sql
```

Esto agrega:
- Columna `activoFuncionario` (TINYINT DEFAULT 1)
- Comentario explicativo
- Índice para búsquedas rápidas

Verifica:
```sql
DESC funcionario;
-- Deberías ver: activoFuncionario | tinyint(4) | YES | | 1 |
```

---

## PASO 2: Preparar el archivo Excel

Crea un Excel con las siguientes **EXACTAS** columnas:

```
rutFuncionario | nombreFuncionario | cargoFuncionario | correoFuncionario | idUnidad
```

### Ejemplo:

| rutFuncionario | nombreFuncionario     | cargoFuncionario | correoFuncionario          | idUnidad |
|---|---|---|---|---|
| 12345678-9     | JUAN PÉREZ            | PROFESIONAL      | jperez@junji.cl            | 8101098  |
| 87654321-2     | MARÍA GARCÍA          | ADMINISTRATIVO   | mgarcia@junjired.cl        | 8101001  |
| 11223344-8     | CARLOS LOPEZ          | TÉCNICO          | clopez@junji.cl            | 8102001  |

**Requisitos:**
- ✅ Sin filas vacías
- ✅ RUT con guión (ej: `12345678-9`) o sin guión (se agrega automático)
- ✅ Cargo en MAYÚSCULAS (el script lo convierte)
- ✅ idUnidad como número

---

## PASO 3: Instalar dependencias Python

El script necesita `pandas` y `openpyxl`:

```bash
pip install pandas openpyxl pymysql python-dotenv
```

---

## PASO 4: Ejecutar la sincronización

```bash
python sync_funcionarios_excel.py ruta/al/archivo.xlsx
```

### Ejemplos:

```bash
# En el mismo directorio
python sync_funcionarios_excel.py funcionarios_enero_2026.xlsx

# Con ruta completa
python sync_funcionarios_excel.py ~/Desktop/funcionarios.xlsx

# Con ruta relativa
python sync_funcionarios_excel.py Exel_import/FUNCIONARIOS_add.xlsx
```

---

## PASO 5: Revisar el Log

El script genera un archivo de log con nombre como:
```
sync_funcionarios_20260116_142530.log
```

Contiene:
- ✓ Funcionarios insertados (nuevos)
- ✓ Funcionarios actualizados (cambios de oficio, email, unidad)
- 🔴 Funcionarios desactivados (no en Excel)
- ❌ Errores (emails duplicados, etc)

---

## Integración Futura: Carga desde Web

Para que en el futuro se pueda subir el Excel desde la interfaz web, se agregará una ruta como:

```python
@app.route('/admin/upload_funcionarios_excel', methods=['POST'])
def upload_funcionarios_excel():
    file = request.files['excel_file']
    # Validar y procesar
    sync_funcionarios_excel(file.stream)
    # Mostrar resultados
```

---

## Ejemplos de Flujos

### Escenario 1: Nuevo funcionario (Juan)

**BD Antes:**
```
rutFuncionario | nombreFuncionario | activoFuncionario
12345678-9     | PEDRO             | 1
```

**Excel:**
```
12345678-9, PEDRO, ...
22222222-2, JUAN, ...
```

**BD Después:**
```
12345678-9     | PEDRO             | 1         (actualizado)
22222222-2     | JUAN              | 1         (insertado ✓)
```

---

### Escenario 2: Funcionario de licencia (María)

**BD Antes:**
```
rutFuncionario | nombreFuncionario | activoFuncionario
33333333-3     | MARÍA             | 1
44444444-4     | CARLOS            | 1
```

**Excel:** (María NO aparece, solo Carlos)
```
44444444-4, CARLOS, ...
```

**BD Después:**
```
33333333-3     | MARÍA             | 0         (desactivado 🔴 - de licencia)
44444444-4     | CARLOS            | 1         (actualizado)
```

---

### Escenario 3: Cambio de datos (promoción)

**BD Antes:**
```
rutFuncionario | nombreFuncionario | cargoFuncionario | activoFuncionario
55555555-5     | ROSA              | AUXILIAR         | 1
```

**Excel:**
```
55555555-5, ROSA, PROFESIONAL, ...   <-- Ascenso
```

**BD Después:**
```
55555555-5     | ROSA              | PROFESIONAL      | 1         (datos actualizados ✓)
```

---

## Operaciones en BD

### Ver funcionarios activos:
```sql
SELECT * FROM funcionario WHERE activoFuncionario = 1;
```

### Ver funcionarios inactivos:
```sql
SELECT * FROM funcionario WHERE activoFuncionario = 0;
```

### Reactivar un funcionario:
```sql
UPDATE funcionario 
SET activoFuncionario = 1 
WHERE rutFuncionario = '12345678-9';
```

### Contar por estado:
```sql
SELECT activoFuncionario, COUNT(*) as cantidad
FROM funcionario
GROUP BY activoFuncionario;
```

---

## Troubleshooting

### ❌ Error: "Archivo no encontrado"
```bash
# Verifica la ruta
ls -la funcionarios.xlsx

# Usa ruta absoluta
python sync_funcionarios_excel.py /Users/tu_usuario/Desktop/funcionarios.xlsx
```

### ❌ Error: "Columnas faltantes"
Revisa que tu Excel tenga exactamente:
- rutFuncionario
- nombreFuncionario
- cargoFuncionario
- correoFuncionario
- idUnidad

### ❌ Error: "Correo duplicado"
Un correo ya existe en la BD pero con otro RUT. Soluciones:
- Cambiar el email en Excel
- Actualizar manualmente en BD si es un error

### ❌ Error de conexión BD
Verifica variables de entorno en `Flask/.env`:
```bash
cat Flask/.env | grep DB_
```

---

## API Rest (Futuro)

Cuando se implemente API REST, se podrá:

```bash
POST /api/funcionarios/sync
Content-Type: multipart/form-data

form-data:
  file: [archivo.xlsx]
```

Respuesta:
```json
{
  "insertados": 5,
  "actualizados": 12,
  "desactivados": 3,
  "errores": 0,
  "timestamp": "2026-01-16T14:25:30"
}
```

---

## Preguntas Frecuentes

**P: ¿Se pierden datos cuando se desactivan?**  
R: No. Solo se marca `activoFuncionario = 0`. Los datos históricos se conservan.

**P: ¿Se pueden reactivar funcionarios?**  
R: Sí, con una actualización manual: `UPDATE ... SET activoFuncionario = 1`

**P: ¿Qué pasa si hay errores?**  
R: El script registra todo en el log. Los cambios válidos se guardan, los errores se reportan.

**P: ¿Puedo ejecutar el script varias veces?**  
R: Sí. Es idempotente: actualizará datos correctos y evitará duplicados.

**P: ¿Se pueden filtrar funcionarios inactivos en la aplicación?**  
R: Sí, ya hay lógica en `funcionario.py` que filtra por `activoFuncionario = 1`

---

## Archivos Relacionados

- [SQL_historial/add_campo_activo_funcionario.sql](../SQL_historial/add_campo_activo_funcionario.sql) - Migración BD
- [sync_funcionarios_excel.py](../sync_funcionarios_excel.py) - Script de sincronización
- [Flask/app/funcionario.py](../Flask/app/funcionario.py) - Módulo actualizado

---

**Fecha:** 16 de Enero de 2026  
**Autor:** Sistema de Gestión JUNJI  
**Estado:** ✅ Listo para uso
