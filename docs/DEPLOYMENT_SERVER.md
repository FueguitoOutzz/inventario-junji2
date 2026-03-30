# 🚀 GUÍA DE DEPLOYMENT AL SERVIDOR

## Resumen del Problema

Actualmente, las credenciales de base de datos están **hardcodeadas** en el código:
- Usuario: `junji`
- Contraseña: `Tijunji2017`
- Host: `127.0.0.1`
- BD: `inventariofinal`

Esto funciona en local, pero en el servidor el host, puerto y credenciales podrían ser diferentes.

---

## ✅ Solución: Variables de Entorno

Implementaremos un sistema que usa **variables de entorno** para que:
- El código sea **idéntico** en local y en servidor
- La configuración cambie según el ambiente (`.env` diferente)
- Los datos existentes en el servidor se usen sin modificación

---

## 📋 Plan de Implementación

### PASO 1: Crear archivo `.env.example`

Este archivo (sin valores reales) irá en el repositorio como referencia:

```bash
# Base de Datos
DB_HOST=localhost
DB_USER=junji
DB_PASSWORD=Tijunji2017
DB_NAME=inventariofinal
DB_PORT=3306

# Aplicación
FLASK_ENV=development
FLASK_DEBUG=False
FLASK_PORT=3300
FLASK_HOST=0.0.0.0

# Correo (Opcional)
EMAIL_USER=martin.castro@junji.cl
EMAIL_PASSWORD=junji.2024
```

### PASO 2: Crear archivo `.env` (local - NO versionado)

En tu máquina local:

```bash
# .env (para desarrollo local)
DB_HOST=127.0.0.1
DB_USER=junji
DB_PASSWORD=Tijunji2017
DB_NAME=inventariofinal
DB_PORT=3306
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_PORT=3300
FLASK_HOST=localhost
EMAIL_USER=martin.castro@junji.cl
EMAIL_PASSWORD=junji.2024
```

### PASO 3: Modificar `Flask/app/db.py`

Cambiar de hardcode a variables de entorno:

**ANTES:**
```python
app.config['MYSQL_USER'] = 'junji'
app.config['MYSQL_PASSWORD'] = 'Tijunji2017'
app.config['MYSQL_HOST'] = '127.0.0.1'
```

**DESPUÉS:**
```python
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app.config['MYSQL_USER'] = os.getenv('DB_USER', 'junji')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD', 'Tijunji2017')
app.config['MYSQL_HOST'] = os.getenv('DB_HOST', 'localhost')
app.config['MYSQL_PORT'] = int(os.getenv('DB_PORT', 3306))
app.config['MYSQL_DB'] = os.getenv('DB_NAME', 'inventariofinal')
```

### PASO 4: Modificar `Flask/app/main.py`

```python
# Después de los imports
import os
from dotenv import load_dotenv

load_dotenv()

# Cambiar el puerto dinámico
if __name__ == "__main__":
    port = int(os.getenv('FLASK_PORT', 3300))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
```

### PASO 5: Actualizar `requirements.txt`

Agregar `python-dotenv`:

```bash
Flask==2.1.2
flask-mysqldb==1.0.1
flask-bcrypt==1.0.1
python-dotenv==1.0.0
# ... resto de dependencias
```

### PASO 6: Agregar `.env` al `.gitignore`

Asegurar que las credenciales NO se suban al repositorio:

```bash
# En .gitignore agregar:
.env
.env.local
.env.*.local
```

---

## 🖥️ Instrucciones para el Servidor

Una vez que hayas subido el código, en el servidor:

### 1️⃣ Clonar repositorio
```bash
git clone <url-repositorio>
cd Junji-Inventario/Flask/app
```

### 2️⃣ Crear archivo `.env` con credenciales del servidor
```bash
nano .env
```

Pegar (con valores reales del servidor):
```
DB_HOST=192.168.1.100          # O la IP/host real del servidor
DB_USER=junji
DB_PASSWORD=Tijunji2017         # O la contraseña real
DB_NAME=inventariofinal
DB_PORT=3306
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_PORT=3300
FLASK_HOST=0.0.0.0
EMAIL_USER=martin.castro@junji.cl
EMAIL_PASSWORD=junji.2024
```

### 3️⃣ Instalar dependencias
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4️⃣ Verificar conexión a BD
```bash
python3 -c "from db import mysql; print('✓ Conexión OK')"
```

### 5️⃣ Ejecutar aplicación
```bash
python3 main.py
```

O con **gunicorn** (recomendado para producción):
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:3300 main:app
```

---

## 📊 ¿Qué pasa con los datos existentes en el servidor?

**Excelente noticia:** Los datos ya en el servidor **NO se tocan**. Solo es la conexión la que cambia:

1. Base de datos `inventariofinal` ya existe en el servidor
2. Contiene todos los registros históricos
3. La aplicación solo **lee y escribe** en esa BD
4. El código es idéntico, solo cambian las credenciales de acceso

---

## 🔧 Cambios Mínimos de Código

Solo necesitas modificar **2 archivos**:

1. **`Flask/app/db.py`** - Usar `os.getenv()` en vez de valores fijos
2. **`Flask/app/main.py`** - Usar `os.getenv()` para puerto y debug

---

## 📋 Checklist Pre-Deploy

- [ ] Crear `.env.example` en repositorio
- [ ] Modificar `db.py` para usar variables de entorno
- [ ] Modificar `main.py` para usar variables de entorno
- [ ] Agregar `python-dotenv` a `requirements.txt`
- [ ] Agregar `.env` a `.gitignore`
- [ ] Probar localmente que sigue funcionando
- [ ] Hacer commit y push
- [ ] En servidor: crear `.env` con credenciales reales
- [ ] En servidor: instalar dependencias y ejecutar

---

## 🎯 Ventajas de esta Solución

✅ Código idéntico en local y servidor  
✅ Datos del servidor se mantienen intactos  
✅ Fácil de cambiar credenciales sin tocar código  
✅ Seguro (credenciales no en repositorio)  
✅ Compatible con Docker/contenedores  
✅ Fácil de debuggear (mismo código en ambos lados)  

---

## ⚠️ Notas Importantes

1. **No versionear `.env`** - Agregar a `.gitignore`
2. **Usar `.env.example`** - Como referencia de qué variables se necesitan
3. **En servidor** - Las credenciales del `.env` deben ser las reales del servidor
4. **Backup** - Antes de cambiar, hacer backup de la BD del servidor

