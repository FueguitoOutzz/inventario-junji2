# 🎯 PLAN ESPECÍFICO DE DEPLOYMENT

## Estado Actual del Servidor

Asumiendo que en tu servidor ya hay:
- ✅ MySQL/MariaDB corriendo
- ✅ Base de datos `inventariofinal` con datos existentes
- ✅ Usuario `junji` con contraseña `Tijunji2017` (o similar)
- ✅ Todos los datos históricos intactos

---

## 🚀 Proceso de Upload y Configuración

### FASE 1: Preparación Local (YA HECHA)

**Estado:** ✅ COMPLETADO

- [x] Código modificado para usar variables de entorno
- [x] `requirements.txt` actualizado con `python-dotenv`
- [x] `.env.example` creado (referencia)
- [x] `.env` local configurado
- [x] `.gitignore` creado (para proteger `.env`)
- [x] Documentación de deployment lista

### FASE 2: Upload a Servidor (CUANDO ESTÉS LISTO)

**1. Hacer commit de los cambios:**
```bash
cd /Users/idknoou/Documents/GIT/Junji-Inventario
git status                    # Ver qué cambió
git add .                     # Agregar todos
git commit -m "Implementar variables de entorno para deployment"
git push origin main
```

**2. En el servidor, clonar/actualizar:**
```bash
# Opción A: Primera vez
cd /opt/apps  # O donde instales apps
git clone <url-repo> Junji-Inventario
cd Junji-Inventario/Flask

# Opción B: Ya está clonado
cd /ruta/a/Junji-Inventario/Flask
git pull origin main
```

### FASE 3: Configuración del Servidor

**1. Crear archivo `.env` con datos REALES del servidor:**

```bash
cd /opt/apps/Junji-Inventario/Flask
nano .env
```

**Pegar lo siguiente (CAMBIAR LOS VALORES):**

```bash
# ==========================================
# CONFIGURACIÓN DEL SERVIDOR
# ==========================================

# Base de Datos - CAMBIAR ESTOS VALORES
DB_HOST=192.168.1.100          # ← CAMBIAR: IP o hostname real
DB_USER=junji
DB_PASSWORD=Tijunji2017         # ← CAMBIAR si es diferente
DB_NAME=inventariofinal         # ← Cambiar si BD tiene otro nombre
DB_PORT=3306                    # ← Cambiar si MySQL usa otro puerto

# Flask - Para servidor
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_PORT=3300
FLASK_HOST=0.0.0.0

# Correo (opcional)
EMAIL_USER=martin.castro@junji.cl
EMAIL_PASSWORD=junji.2024
```

**Guardar:** `Ctrl+X`, `Y`, `Enter`

### FASE 4: Instalación de Dependencias

```bash
cd /opt/apps/Junji-Inventario/Flask

# 1. Crear virtual environment
python3 -m venv venv

# 2. Activar
source venv/bin/activate

# 3. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### FASE 5: Verificar Conexión a Base de Datos

```bash
python3 << 'EOF'
import os
from dotenv import load_dotenv

# Cargar variables
load_dotenv()

# Mostrar valores
print("🔍 Verificando configuración:")
print(f"   HOST: {os.getenv('DB_HOST')}")
print(f"   USER: {os.getenv('DB_USER')}")
print(f"   DB: {os.getenv('DB_NAME')}")
print(f"   PORT: {os.getenv('DB_PORT')}")
print()

# Intentar conexión
try:
    import MySQLdb
    conn = MySQLdb.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        passwd=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_NAME'),
        port=int(os.getenv('DB_PORT', 3306))
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    count = cursor.fetchone()[0]
    print(f"✅ Conexión OK - Usuarios en BD: {count}")
    conn.close()
except Exception as e:
    print(f"❌ Error de conexión: {e}")
EOF
```

**Si ves "Conexión OK"** → ¡Continuamos!  
**Si hay error** → Verificar credenciales en `.env`

### FASE 6: Ejecutar la Aplicación

**Opción A: Prueba Rápida (Desarrollo)**
```bash
cd /opt/apps/Junji-Inventario/Flask/app
python3 main.py
```

Debería ver:
```
* Running on http://0.0.0.0:3300
```

Accede en navegador: `http://tu-servidor:3300`

**Opción B: Producción con Gunicorn (RECOMENDADO)**

```bash
# Instalar gunicorn
pip install gunicorn

# Ejecutar con 4 workers
cd /opt/apps/Junji-Inventario/Flask/app
gunicorn -w 4 -b 0.0.0.0:3300 main:app
```

**Opción C: Servicio Permanente (Supervisor)**

```bash
# Instalar supervisor (si no está)
sudo apt-get install supervisor

# Crear archivo de configuración
sudo nano /etc/supervisor/conf.d/junji-inventario.conf
```

Pegar:
```ini
[program:junji-inventario]
directory=/opt/apps/Junji-Inventario/Flask/app
command=/opt/apps/Junji-Inventario/Flask/venv/bin/gunicorn -w 4 -b 0.0.0.0:3300 main:app
user=www-data
stdout_logfile=/var/log/junji-inventario.log
stderr_logfile=/var/log/junji-inventario-error.log
autostart=true
autorestart=true
```

Cargar:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start junji-inventario
sudo supervisorctl status
```

### FASE 7: Verificar que Funciona

**En navegador:**
```
http://tu-servidor:3300
```

**Login:**
```
Usuario: admin
Contraseña: 1234
```

**Verificar datos:**
- Ve a "Equipos" → Deberías ver los equipos existentes
- Ve a "Funcionarios" → Deberías ver los funcionarios
- Ve a "Asignaciones" → Deberías ver las asignaciones

Si todo es igual que en local → ✅ **¡ÉXITO!**

---

## 🔄 Pasos si hay problemas

### Error: "Connection refused"
```bash
# Verificar que MySQL está corriendo
mysql -h 192.168.1.100 -u junji -p -e "SELECT 1"

# Si falla, verificar:
# 1. IP correcta en .env (DB_HOST)
# 2. Usuario/contraseña correctos
# 3. Puerto correcto (DB_PORT)
```

### Error: "No module named 'dotenv'"
```bash
source venv/bin/activate
pip install python-dotenv
```

### Error: "Address already in use"
```bash
# Cambiar puerto en .env
nano .env
# Cambiar FLASK_PORT=3301 (o cualquier otro)
```

### Ver logs de error
```bash
# Si usas Supervisor
tail -f /var/log/junji-inventario.log

# Si ejecutas directamente
python3 main.py 2>&1 | grep -i error
```

---

## 📊 Datos que se Mantienen

**La BD del servidor NO se modifica, solo:**
- La aplicación se conecta con las nuevas credenciales
- Lee y escribe como siempre
- Los datos históricos permanecen intactos

```sql
-- Ejemplo: Todos estos datos siguen siendo los mismos
SELECT COUNT(*) FROM equipos;        -- ✅ Mismo número
SELECT COUNT(*) FROM funcionarios;   -- ✅ Mismo número
SELECT COUNT(*) FROM asignaciones;   -- ✅ Mismo número
SELECT COUNT(*) FROM usuarios;       -- ✅ Mismo número + admin
```

---

## ✅ Checklist Pre-Launch

```
PREPARACIÓN LOCAL:
  [x] Código con variables de entorno
  [x] requirements.txt actualizado
  [x] .env local funciona
  [x] Git push realizado

SERVIDOR:
  [ ] Código clonado/actualizado
  [ ] .env creado con datos reales
  [ ] pip install -r requirements.txt
  [ ] Conexión a BD verificada
  [ ] Aplicación ejecuta sin errores
  [ ] Se puede acceder en navegador
  [ ] Login funciona (admin/1234)
  [ ] Datos se ven correctamente
  [ ] Supervisor configurado (opcional)
```

---

## 🎯 URL de Acceso Post-Deploy

```
http://192.168.1.100:3300
```

(Cambiar IP por la real de tu servidor)

---

## 📞 Soporte

Si hay problemas durante el deployment:

1. **Ver logs:** `tail -f /var/log/junji-inventario.log`
2. **Verificar conexión BD:** `mysql -h HOST -u USER -p`
3. **Reintentar instalación:** `pip install -r requirements.txt --force-reinstall`
4. **Cambiar puerto:** Editar `.env` → `FLASK_PORT=3301`

