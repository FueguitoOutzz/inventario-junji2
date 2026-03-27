# 🚀 GUÍA DE EJECUCIÓN - Sistema JUNJI-Inventario (LOCAL)

## ⚡ Forma más rápida de ejecutar

```bash
cd /Users/idknoou/Documents/GIT/Junji-Inventario
./start.sh
```

O si prefieres manualmente:

```bash
cd /Users/idknoou/Documents/GIT/Junji-Inventario
source venv/bin/activate
cd Flask/app
python3 main.py
```

## 🌐 Acceso a la Aplicación

Una vez ejecutado el script, accede a:

**URL:** http://localhost:3300

**Credenciales:**
- Usuario: `admin`
- Contraseña: `1234`

## 📊 Información de Base de Datos

- **Host:** localhost
- **Puerto:** 3306
- **Base de datos:** inventariofinal
- **Usuario:** junji
- **Contraseña:** Tijunji2017
- **Motor:** MariaDB 12.0.2

## 👥 Gestión de Usuarios

### Crear nuevos usuarios:
1. Inicia sesión con `admin` / `1234`
2. Ve a la sección de **Cuentas** o **Administración**
3. Crea nuevos usuarios con sus contraseñas

### Cambiar contraseña:
- Desde el perfil del usuario (esquina superior derecha)

## 🛠️ Requisitos Instalados

- ✓ Python 3.9.6
- ✓ Flask 2.1.2
- ✓ MariaDB 12.0.2
- ✓ PyMySQL (para conexión DB)
- ✓ Otras dependencias en `Flask/requirements.txt`

## ⚠️ Notas Importantes

- **No modificar el código** - Este proyecto es una copia local del servidor
- **Cambios en DB** - Si necesitas modificaciones, prueba primero aquí
- **Sincronización** - Antes de subir cambios al servidor, asegúrate que funciona correctamente
- MariaDB inicia automáticamente con el script `start.sh`

## 🔄 Sincronizar con Servidor

Cuando quieras actualizar cambios:

```bash
git pull origin main
```

Antes de hacer push:

```bash
git status
git add [archivos]
git commit -m "Descripción del cambio"
git push origin main
```

## 📝 Estructura del Proyecto

```
Junji-Inventario/
├── Flask/
│   ├── app/
│   │   ├── main.py          # Punto de entrada
│   │   ├── app.py           # Config de Flask
│   │   ├── db.py            # Conexión DB
│   │   └── [módulos].py     # Funcionalidades
│   ├── requirements.txt      # Dependencias
│   └── .env                  # Variables de entorno
├── venv/                     # Entorno virtual
├── start.sh                  # Script para ejecutar
└── [archivos SQL]            # Backups y SQL
```

---

**Última actualización:** 12 de enero de 2026
**Ambiente:** Desarrollo Local (macOS)
