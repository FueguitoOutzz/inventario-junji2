# 🎯 Sistema de Control de Funcionarios Activos/Inactivos

## 📋 Resumen Ejecutivo

Se ha implementado un **sistema de sincronización automática** de funcionarios desde Excel que:

✅ **Mantiene actualizado** el estado de los funcionarios (activo/inactivo)  
✅ **Inserta automáticamente** nuevos funcionarios del Excel  
✅ **Actualiza datos** si hay cambios (cargo, oficina, email)  
✅ **Desactiva** funcionarios que no aparecen en Excel (licencia, renuncia, etc)  
✅ **Registra auditoría** completa en logs  

---

## 🏗️ Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│                    FLUJO DE SINCRONIZACIÓN                    │
└──────────────────────────────────────────────────────────────┘

    Excel Upload
        │
        ▼
    ┌─────────────────────────┐
    │ sync_funcionarios_      │
    │ excel.py                │
    │                         │
    │ 1. Lee Excel ✓          │
    │ 2. Valida columnas      │
    │ 3. Normaliza datos      │
    └─────────────────────────┘
        │
        ├─────┬──────────┬──────────┐
        │     │          │          │
        ▼     ▼          ▼          ▼
    INSERTA ACTUALIZA DESACTIVA REGISTRA
       │        │         │         │
       ▼        ▼         ▼         ▼
    BD UPDATE   BD UPDATE BD UPDATE LOG.txt
       │        │         │         │
       └────────┴─────────┴─────────┘
              │
              ▼
        ┌──────────────┐
        │ BD (MySQL)   │
        │              │
        │ funcionario  │
        │ ├ rut        │
        │ ├ nombre     │
        │ ├ email      │
        │ ├ cargo      │
        │ ├ unidad     │
        │ └ ACTIVO (0/1)
        └──────────────┘
```

---

## 📂 Archivos Creados

### 1️⃣ SQL Migration
**Archivo:** [SQL_historial/add_campo_activo_funcionario.sql](SQL_historial/add_campo_activo_funcionario.sql)

```sql
ALTER TABLE funcionario ADD COLUMN activoFuncionario TINYINT DEFAULT 1;
CREATE INDEX idx_activoFuncionario ON funcionario (activoFuncionario);
```

**Ejecutar:**
```bash
mysql -u junji -p inventariofinal < SQL_historial/add_campo_activo_funcionario.sql
```

---

### 2️⃣ Python Script
**Archivo:** [sync_funcionarios_excel.py](sync_funcionarios_excel.py)

```python
def sync_funcionarios(excel_file):
    """
    Sincroniza funcionarios desde Excel:
    - INSERT: Funcionarios nuevos
    - UPDATE: Cambios en datos existentes
    - SET INACTIVO: No presentes en Excel
    """
```

**Características:**
- ✓ Lee Excel con pandas
- ✓ Normaliza RUTs
- ✓ Maneja errores de email duplicado
- ✓ Genera log detallado
- ✓ Es idempotente (seguro ejecutar múltiples veces)

**Uso:**
```bash
python sync_funcionarios_excel.py ruta/funcionarios.xlsx
```

---

### 3️⃣ Módulo Flask Actualizado
**Archivo:** [Flask/app/funcionario.py](Flask/app/funcionario.py)

**Cambios:**
- Agrega campo `activoFuncionario` a formularios
- Filtra solo funcionarios activos en vistas
- Compatible con BD antiguas (sin la columna)

```python
if _col_exists("funcionario", "activoFuncionario"):
    query += "WHERE f.activoFuncionario = 1"
```

---

### 4️⃣ Documentación Completa
**Archivo:** [SYNC_FUNCIONARIOS_EXCEL.md](SYNC_FUNCIONARIOS_EXCEL.md)

Incluye:
- Guía paso a paso
- Ejemplos de flujos
- SQL útiles
- Troubleshooting
- FAQ

---

## 🚀 Inicio Rápido

### Paso 1: Agregar columna a BD
```bash
mysql -u junji -p inventariofinal < SQL_historial/add_campo_activo_funcionario.sql

# Verificar:
mysql -u junji -p inventariofinal -e "DESC funcionario;"
```

**Esperado:**
```
activoFuncionario | tinyint(4) | YES | | 1 |
```

### Paso 2: Crear archivo Excel

**Formato requerido:**

| rutFuncionario | nombreFuncionario | cargoFuncionario | correoFuncionario | idUnidad |
|---|---|---|---|---|
| 12345678-9 | JUAN PÉREZ | PROFESIONAL | jperez@junji.cl | 8101098 |
| 87654321-2 | MARÍA GARCÍA | ADMINISTRATIVO | mgarcia@junjired.cl | 8101001 |

O generar un ejemplo:
```bash
python generate_sample_funcionarios_excel.py
```

### Paso 3: Ejecutar sincronización
```bash
python sync_funcionarios_excel.py archivo.xlsx
```

**Salida:**
```
[2026-01-16 14:25:30] 🔄 Iniciando sincronización desde: archivo.xlsx
[2026-01-16 14:25:30] ✓ Archivo leído: 15 registros
...
[2026-01-16 14:25:31] 📊 ═══════════════════════════════════
[2026-01-16 14:25:31]   Insertados:  2
[2026-01-16 14:25:31]   Actualizados: 13
[2026-01-16 14:25:31]   Desactivados: 1
[2026-01-16 14:25:31]   Errores:     0
[2026-01-16 14:25:31] ═══════════════════════════════════
```

---

## 📊 Ejemplos de Uso

### Caso 1: Cargar funcionarios nuevos
**Excel tiene:** 15 funcionarios (incluyendo 2 nuevos)

```sql
RESULTADO:
- INSERT: 2 nuevos funcionarios
- UPDATE: 13 actualizados (con sus datos)
- DELETE: Ninguno (todos en Excel)
```

### Caso 2: Funcionario de licencia
**Excel tiene:** Solo 14 funcionarios (falta "HECTOR")

```sql
RESULTADO:
- INSERT: 0
- UPDATE: 14 (HECTOR sigue en BD pero...)
- UPDATE SET activoFuncionario=0 WHERE rut='9180661-4' ← HECTOR
```

### Caso 3: Cambio de cargo (promoción)
**Excel tiene:** ROSA como PROFESIONAL (antes era AUXILIAR)

```sql
RESULTADO:
- UPDATE cargoFuncionario='PROFESIONAL' WHERE rut='55555555-5'
- activoFuncionario sigue siendo 1
```

---

## 🔍 Queries Útiles

### Ver funcionarios activos
```sql
SELECT rutFuncionario, nombreFuncionario, cargoFuncionario, activoFuncionario
FROM funcionario
WHERE activoFuncionario = 1
ORDER BY nombreFuncionario;
```

### Ver funcionarios inactivos
```sql
SELECT rutFuncionario, nombreFuncionario, activoFuncionario
FROM funcionario
WHERE activoFuncionario = 0;
```

### Reactivar un funcionario
```sql
UPDATE funcionario
SET activoFuncionario = 1
WHERE rutFuncionario = '9180661-4';
```

### Contar por estado
```sql
SELECT activoFuncionario, COUNT(*) as cantidad
FROM funcionario
GROUP BY activoFuncionario;

-- Resultado esperado:
-- activoFuncionario | cantidad
-- 1                 | 85
-- 0                 | 3
```

---

## 🛠️ Dependencias

Todas ya instaladas en `Flask/requirements.txt`:

```
pandas==2.2.3       # Lectura de Excel
openpyxl==3.1.2     # Soporte .xlsx
pymysql==1.0.2      # Conexión MySQL
python-dotenv       # Variables de entorno
```

**Si necesitas instalar manualmente:**
```bash
pip install pandas openpyxl pymysql python-dotenv
```

---

## 🔐 Consideraciones de Seguridad

✅ **No hay credenciales hardcodeadas**
- Lee desde `Flask/.env`
- RUT y email validados
- SQL inyection prevenida con prepared statements

✅ **Integridad de datos**
- Transacciones ACID
- Rollback si hay errores
- Log de auditoría

✅ **Compatibilidad backwards**
- Flask.app.funcionario funciona incluso sin la columna
- Migración segura (DEFAULT 1)

---

## 📈 Casos de Uso Futuro

### 1. Carga desde Web UI
```python
@app.route('/admin/sincronizar_funcionarios', methods=['POST'])
def sincronizar_funcionarios():
    file = request.files['excel_file']
    result = sync_funcionarios(file.stream)
    return jsonify(result)
```

### 2. Sincronización automática (Cron)
```bash
# /etc/cron.d/junji-inventario
0 6 * * * /usr/bin/python3 /app/sync_funcionarios_excel.py /shared/funcionarios.xlsx
```

### 3. Reportes e dashboards
```python
SELECT 
    COUNT(CASE WHEN activoFuncionario=1 THEN 1 END) as activos,
    COUNT(CASE WHEN activoFuncionario=0 THEN 1 END) as inactivos,
    COUNT(*) as total
FROM funcionario;
```

---

## 🐛 Troubleshooting

### ❌ "Archivo no encontrado"
```bash
# Verifica la ruta existe
ls -la mi_archivo.xlsx

# Usa ruta absoluta
python sync_funcionarios_excel.py /Users/usuario/Desktop/funcionarios.xlsx
```

### ❌ "Columnas faltantes en Excel"
Excel debe tener exactamente estas columnas:
- `rutFuncionario`
- `nombreFuncionario`
- `cargoFuncionario`
- `correoFuncionario`
- `idUnidad`

### ❌ "Error de conexión a BD"
```bash
# Verifica variables de entorno
cat Flask/.env

# Intenta conectar manualmente
mysql -u junji -p -h localhost inventariofinal -e "SELECT COUNT(*) FROM funcionario;"
```

### ❌ "Correo duplicado"
Un email ya existe en BD pero con otro RUT.

Soluciones:
- Cambiar el email en Excel
- Actualizar manualmente en BD

```bash
UPDATE funcionario SET correoFuncionario='newemail@junji.cl' WHERE rutFuncionario='12345678-9';
```

---

## 📞 Soporte & Documentación

| Recurso | Ubicación |
|---------|-----------|
| Guía completa | [SYNC_FUNCIONARIOS_EXCEL.md](SYNC_FUNCIONARIOS_EXCEL.md) |
| Resumen visual | [RESUMEN_ACTIVO_FUNCIONARIOS.txt](RESUMEN_ACTIVO_FUNCIONARIOS.txt) |
| SQL migration | [SQL_historial/add_campo_activo_funcionario.sql](SQL_historial/add_campo_activo_funcionario.sql) |
| Script Python | [sync_funcionarios_excel.py](sync_funcionarios_excel.py) |
| Ejemplo Excel | `FUNCIONARIOS_ACTIVOS_EJEMPLO_*.xlsx` (generado) |

---

## ✅ Checklist de Implementación

- [x] Crear SQL migration
- [x] Crear script Python
- [x] Actualizar Flask app
- [x] Generar documentación
- [x] Crear ejemplos
- [x] Validar sin bugs
- [x] Listo para producción

---

**Creado:** 16 de Enero de 2026  
**Versión:** 1.0  
**Estado:** ✅ **LISTO PARA USO**

---
