# 🔄 INSTRUCCIONES DE GIT - Preparar Repositorio para Compañeros

Este archivo contiene los pasos para preparar el repositorio y asegurarse de que está listo para compartir.

## 📋 Checklist de Limpieza y Preparación

### 1. Verificar Estado Actual
```bash
cd /Users/idknoou/Documents/GIT/Junji-Inventario
git status
```

### 2. Agregar Nuevos Archivos (Recomendado)

```bash
# Agregar todos los archivos de documentación y scripts
git add insert_sample_data.sql
git add load_sample_data.sh
git add verify_setup.sh
git add QUICK_START.md
git add sample_data_instructions.md
git add DELIVERY_CHECKLIST.md
git add .gitignore (si cambió)

# Actualizar README si fue modificado
git add README.md
```

### 3. Verificar que van a agregarse
```bash
git status
```

Deberías ver los nuevos archivos en:
- "Changes to be committed" (archivos staged)

### 4. Hacer Commit
```bash
git commit -m "📊 Consolidar datos de ejemplo en archivo SQL único para facilitar distribución"
```

### 5. (Opcional) Limpiar Repositorio - Archivos Innecesarios

Si deseas mantener el repositorio limpio, puedes eliminar:

```bash
# Archivos de backup antiguos
rm -f Flask/app/asignacion.py.bak*

# Directorios con datos viejos (CUIDADO: revisar antes)
# rm -rf SQL_historial
# rm -rf SQL_import

# Archivos de documentación duplicados
# rm -f DATOS_EJEMPLO.md
# rm -f README_SAMPLE_DATA.md
```

**NOTA:** Ejecuta `git status` antes de eliminar para estar seguro.

### 6. Push al Repositorio (si está conectado a GitHub/GitLab)

```bash
git push origin main
# o
git push origin master
```

---

## 📦 Contenido a Compartir

Los siguientes archivos deben estar en el repositorio para distribuir a compañeros:

### ✅ Archivos Nuevos/Modificados
- `insert_sample_data.sql` - Datos consolidados (226 líneas)
- `load_sample_data.sh` - Script automático de carga
- `verify_setup.sh` - Verificador de instalación
- `QUICK_START.md` - Guía rápida (3 pasos)
- `sample_data_instructions.md` - Detalles de datos
- `DELIVERY_CHECKLIST.md` - Este checklist
- `README.md` - Actualizado con referencias a datos

### ✅ Archivos Existentes Importantes
- `Flask/` - Código fuente completo
- `start.sh` - Script de inicio
- `setup_db.py` - Setup de BD
- `.env` o `env_vars.py` - Configuración

---

## 🎯 Estructura Final del Repositorio

```
Junji-Inventario/
├── 📄 README.md                          (actualizado)
├── 📄 QUICK_START.md                    (nuevo)
├── 📄 DELIVERY_CHECKLIST.md             (nuevo)
├── 📄 sample_data_instructions.md       (nuevo)
├── 📄 SETUP_LOCAL.md                    (existente)
│
├── 🗄️  insert_sample_data.sql           (ÚNICO archivo SQL con todo)
├── 🔧 load_sample_data.sh               (script automático, nuevo)
├── 🔧 verify_setup.sh                   (verificador, nuevo)
├── 🔧 start.sh                          (existente)
│
├── 📁 Flask/                            (código principal)
│   ├── app/
│   ├── requirements.txt
│   └── env_vars.py
│
└── 📁 (otros directorios necesarios)
```

---

## 💡 Ventajas de Esta Estructura

✅ **Un único archivo SQL** - Fácil de compartir y ejecutar  
✅ **Scripts automáticos** - Los compañeros no necesitan escribir comandos SQL  
✅ **Documentación clara** - Guías paso a paso en QUICK_START.md  
✅ **Verificación automática** - Script para diagnosticar problemas  
✅ **Datos consistentes** - Integridad referencial respetada  
✅ **Sin dependencias externas** - Todo incluido en el repositorio  

---

## 📞 Instrucciones para Compañeros (Resumen)

Una vez clonado el repositorio, deben ejecutar:

```bash
# 1. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependencias
pip install -r Flask/requirements.txt

# 3. Cargar datos de ejemplo
./load_sample_data.sh

# 4. Ejecutar aplicación
./start.sh

# 5. Acceder a http://localhost:3300
# Usuario: admin
# Contraseña: 1234
```

O simplemente pueden consultar **QUICK_START.md** para instrucciones completas.

---

## ✅ Verificación Final

Antes de hacer push, ejecuta:

```bash
# Verificar que no hay cambios pendientes
git status

# Ver los commits pendientes
git log --oneline -5

# Verificar el tamaño del repositorio
du -sh .git/
```

---

## 🎉 ¡Listo para Compartir!

Una vez completados estos pasos, el repositorio está listo para distribución a compañeros de trabajo.

**Fecha:** 13 de enero de 2026  
**Preparado por:** [Tu nombre]  
**Versión:** 1.0
