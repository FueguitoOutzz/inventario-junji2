# 🚀 GUÍA RÁPIDA PARA COMPAÑEROS DE TRABAJO

## Inicio Rápido (3 pasos)

### 1️⃣ Clonar el Repositorio
```bash
git clone <url-del-repositorio>
cd Junji-Inventario
```

### 2️⃣ Crear Base de Datos y Cargar Datos de Ejemplo

**Opción A (Recomendado - Script automático):**
```bash
./load_sample_data.sh
```

**Opción B (Manual):**
```bash
mysql -u junji -p inventariofinal < insert_sample_data.sql
```
Contraseña: `Tijunji2017`

### 3️⃣ Ejecutar la Aplicación
```bash
./start.sh
```

Accede en tu navegador: **http://localhost:3300**

---

## 🔐 Credenciales de Acceso

| Campo | Valor |
|-------|-------|
| **URL** | http://localhost:3300 |
| **Usuario** | admin |
| **Contraseña** | 1234 |

---

## 📊 Datos Incluidos en el Ejemplo

Al ejecutar `insert_sample_data.sql` obtendrás:

✅ **9 Funcionarios** con diferentes cargos (Profesional, Técnico, Auxiliar, etc.)  
✅ **3 Unidades Educativas** (Jardín Infantil Los Álamos, Salas Cuna Esperanza, Centro Educativo Mi Futuro)  
✅ **10 Equipos de Inventario** (Laptops, Monitores, Celulares, Tablets, Impresoras)  
✅ **5 Asignaciones Activas** de equipos a funcionarios  
✅ **2 Devoluciones Registradas** (Historial)  
✅ **5 Órdenes de Compra** con diferentes proveedores  

---

## 🛠️ Stack Tecnológico

- **Python 3.12** + **Flask**
- **MySQL 8.0+** / **MariaDB 12.0+**
- **Frontend:** HTML5, CSS3, JavaScript
- **ORM/Librería DB:** MySQLdb

---

## 📁 Estructura Principal

```
Junji-Inventario/
├── Flask/
│   └── app/              ← Código principal de la aplicación
├── insert_sample_data.sql ← Datos de ejemplo
├── load_sample_data.sh    ← Script automático para cargar datos
├── start.sh               ← Script para ejecutar la aplicación
├── setup_db.py            ← Setup inicial de base de datos
└── README.md              ← Documentación completa
```

---

## ❓ Preguntas Frecuentes

### ¿Qué pasa si ejecuto `insert_sample_data.sql` dos veces?

No hay problema. El script usa `INSERT IGNORE`, así que no creará duplicados.

### ¿Puedo cambiar la contraseña del usuario `admin`?

Sí. Dentro de la aplicación, ve a **Cuentas** > Administración de Usuarios y cambia la contraseña.

### ¿Dónde está la configuración de la base de datos?

En el archivo `Flask/env_vars.py` (credenciales) y `.env` (variables de entorno si existe).

### ¿Qué hacer si tengo un error de conexión a MySQL?

1. Verifica que MySQL esté corriendo: `brew services list` (macOS)
2. Verifica las credenciales en `Flask/env_vars.py`
3. Verifica que la base de datos `inventariofinal` exista
4. Verifica que el usuario `junji` tenga permisos suficientes

### ¿Puedo usar un usuario MySQL diferente?

Sí, pero deberás:
1. Crear el usuario en MySQL
2. Modificar `Flask/env_vars.py` con el nuevo usuario
3. Asegurarte de que tenga permisos en la base de datos `inventariofinal`

---

## 📞 Soporte

Si encuentras problemas:
1. Consulta el [README.md](README.md) para documentación completa
2. Revisa [sample_data_instructions.md](sample_data_instructions.md) para detalles de los datos
3. Verifica la sección de "Requisitos" en el README

---

**Última actualización:** 13 de enero de 2026
