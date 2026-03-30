# 🖥️ INSTRUCCIONES DE DEPLOYMENT AL SERVIDOR

## ⚡ Resumen Rápido

El proyecto ahora usa **variables de entorno** para la configuración. Esto significa:
- El código es **idéntico** en local y en servidor
- Solo cambias el archivo `.env` según dónde ejecutes

## 🚀 Pasos de Deployment (Servidor)

### 1️⃣ Clonar el Repositorio
```bash
cd /opt/apps  # O donde quieras instalar
git clone <url-repositorio> Junji-Inventario
cd Junji-Inventario/Flask
```

### 2️⃣ Crear el archivo `.env` con Credenciales Reales del Servidor

```bash
nano .env
```

Pega esto (CON LOS VALORES REALES DEL SERVIDOR):

```
# Base de Datos (CAMBIAR ESTOS VALORES)
DB_HOST=192.168.1.100          # IP o host del servidor MySQL
DB_USER=junji
DB_PASSWORD=Tijunji2017
DB_NAME=inventariofinal
DB_PORT=3306

# Flask
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_PORT=3300
FLASK_HOST=0.0.0.0

# Correo (Opcional)
EMAIL_USER=martin.castro@junji.cl
EMAIL_PASSWORD=junji.2024
```

**⚠️ IMPORTANTE:**
- Cambiar `DB_HOST` a la IP real del servidor MySQL
- Cambiar credenciales si son diferentes en el servidor
- **NO versionear este archivo** (ya está en `.gitignore`)
- Si usas `rsync` para desplegar, excluye `.env` para no sobrescribirlo (`--exclude '.env'`)

### 3️⃣ Crear Entorno Virtual e Instalar Dependencias

```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4️⃣ Verificar Conexión a BD

```bash
python3 << 'EOF'
from app.db import mysql, app
with app.app_context():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT 1")
        print("✓ Conexión a BD exitosa")
    except Exception as e:
        print(f"✗ Error de conexión: {e}")
EOF
```

### 5️⃣ Ejecutar la Aplicación

**Opción A: Desarrollo**
```bash
cd app
python3 main.py
```

**Opción B: Producción con Gunicorn (RECOMENDADO)**
```bash
pip install gunicorn
cd app
gunicorn -w 4 -b 0.0.0.0:3300 main:app
```

**Opción C: Con Supervisor (Para que corra como servicio)**

```bash
# 1. Instalar supervisor
sudo apt-get install supervisor

# 2. Crear archivo de configuración
sudo nano /etc/supervisor/conf.d/junji-inventario.conf
```

Pega esto:
```ini
[program:junji-inventario]
directory=/opt/apps/Junji-Inventario/Flask/app
command=/opt/apps/Junji-Inventario/Flask/venv/bin/gunicorn -w 4 -b 0.0.0.0:3300 main:app
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/junji-inventario.log
```

```bash
# 3. Cargar y iniciar
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start junji-inventario
```

### 6️⃣ Verificar que Funciona

Accede a: `http://tu-servidor:3300`

Credenciales:
- Usuario: `admin`
- Contraseña: `1234`

---

## ✅ ¿Qué pasa con los datos existentes?

**Los datos NO se pierden.** La aplicación solo:
1. Se conecta a la BD existente (`inventariofinal`)
2. Lee y escribe en las tablas
3. Respeta todos los registros históricos

No hay que hacer backup ni reimportar datos a menos que haya cambios en el schema.

---

## 🔄 Actualizar Código Desde Git

Si necesitas traer cambios nuevos:

```bash
cd /opt/apps/Junji-Inventario
git pull origin main
cd Flask
pip install -r requirements.txt  # En caso que agreguen dependencias
# Reiniciar la aplicación
sudo supervisorctl restart junji-inventario
```

---

## 🚨 Troubleshooting

### Error: "No module named 'dotenv'"
```bash
pip install python-dotenv
```

### Error: "Connection refused"
```bash
# Verificar que MySQL está corriendo
mysql -h tu-servidor -u junji -p -e "SELECT 1"
# O verificar que DB_HOST en .env sea correcto
```

### Error: "Permission denied"
```bash
# Cambiar permisos del archivo .env
chmod 600 .env
```

### Error: "Address already in use"
```bash
# Cambiar puerto en .env (FLASK_PORT)
# O buscar qué proceso usa el 3300
lsof -i :3300
```

---

## 📋 Checklist Final

- [ ] Archivo `.env` creado en `Flask/` con datos del servidor
- [ ] Credenciales BD correctas en `.env`
- [ ] Virtual environment creado
- [ ] Dependencias instaladas
- [ ] Conexión a BD verificada
- [ ] Aplicación ejecutada sin errores
- [ ] Se puede acceder en navegador
- [ ] Login funciona con `admin` / `1234`
- [ ] Datos existentes se ven en la aplicación

---

## 💡 Notas Importantes

1. **NO modificar el código** - La configuración va en `.env`
2. **Mantener `.env` seguro** - Contiene credenciales
3. En despliegues con systemd, se puede usar `/opt/inventario-junji/.env` para mantenerlo fuera del repo
4. **Hacer backup de BD** - Antes de cambios importantes
4. **Monitorear logs** - Ver `/var/log/junji-inventario.log`
