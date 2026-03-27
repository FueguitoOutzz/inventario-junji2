# 📊 ARQUITECTURA DE DEPLOYMENT - DIAGRAMA VISUAL

## Antes (Problema)

```
┌─────────────────────────────────────┐
│      CÓDIGO FUENTE (GitHub)         │
├─────────────────────────────────────┤
│  db.py:                             │
│  app.config['MYSQL_HOST'] = '127.0.1'     ← HARDCODEADO
│  app.config['MYSQL_USER'] = 'junji'       ← HARDCODEADO
│  app.config['MYSQL_PASSWORD'] = '***'     ← HARDCODEADO
│  main.py:                           │
│  app.run(port=3300)                 ← PUERTO FIJO
└─────────────────────────────────────┘
         │                    │
         ↓                    ↓
  ┌────────────┐      ┌────────────┐
  │   LOCAL    │      │  SERVIDOR  │
  │ 127.0.0.1 │      │  IP:3306   │
  │  FALLA❌   │      │  FALLA❌   │
  └────────────┘      └────────────┘
  
Problema: Mismo código, diferente configuración
          No se puede usar en ambos lados
```

---

## Después (Solución)

```
┌──────────────────────────────────────────────────────────┐
│            CÓDIGO FUENTE (Github) - IDÉNTICO             │
├──────────────────────────────────────────────────────────┤
│  db.py:                                                  │
│  app.config['MYSQL_HOST'] = os.getenv('DB_HOST')        │
│  app.config['MYSQL_USER'] = os.getenv('DB_USER')        │
│  app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD')│
│  main.py:                                                │
│  port = int(os.getenv('FLASK_PORT'))                    │
└──────────────────────────────────────────────────────────┘
         │                              │
         ↓                              ↓
  ┌─────────────────┐          ┌─────────────────┐
  │  LOCAL (.env)   │          │ SERVIDOR (.env) │
  ├─────────────────┤          ├─────────────────┤
  │ DB_HOST=127.0.1 │          │ DB_HOST=192.... │
  │ DB_USER=junji   │          │ DB_USER=junji   │
  │ DB_PASS=****    │          │ DB_PASS=****    │
  │ FLASK_PORT=3300 │          │ FLASK_PORT=3300 │
  │ FLASK_ENV=dev   │          │ FLASK_ENV=prod  │
  └─────────────────┘          └─────────────────┘
         ↓                              ↓
  ┌────────────┐               ┌────────────────┐
  │   LOCAL    │               │    SERVIDOR    │
  │ 127.0.0.1  │               │  192.168.1.100 │
  │  FUNCIONA✅ │               │   FUNCIONA✅   │
  └────────────┘               └────────────────┘
  
Solución: Código único, configuración separada
          Funciona en cualquier lugar
```

---

## Flujo de Deployment

```
┌──────────────────────────────────────────────────────────────┐
│                    AMBIENTE LOCAL                            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Clonar repo:  git clone <url>                            │
│  2. Ver .env:     Variables ya configuradas ✅               │
│  3. Ejecutar:     python3 main.py                            │
│  4. Resultado:    Conecta a 127.0.0.1:3306                  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ git push
                          ↓
┌──────────────────────────────────────────────────────────────┐
│                   REPOSITORIO GITHUB                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ✅ Código actualizado                                       │
│  ✅ .env.example como referencia                             │
│  ❌ .env NO está (en .gitignore)                            │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ git pull
                          ↓
┌──────────────────────────────────────────────────────────────┐
│                   SERVIDOR (PRODUCCIÓN)                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Clonar repo:  git clone <url>                            │
│  2. Crear .env:   Con credenciales REALES del servidor      │
│  3. Ejecutar:     python3 main.py                            │
│  4. Resultado:    Conecta a 192.168.1.100:3306             │
│  5. Datos:        ¡Todos intactos! ✅                        │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Estructura de Archivos

```
Junji-Inventario/
│
├── .gitignore                    ← NUEVO: Protege .env
│
├── .env.example                  ← NUEVO: Referencia (versionado)
│   └── Variables de ejemplo
│
├── Flask/
│   ├── .env                      ← ACTUALIZADO: Configuración local
│   │                              (NO versionado, cada máquina lo tiene)
│   ├── requirements.txt          ← ACTUALIZADO: + python-dotenv
│   └── app/
│       ├── db.py                 ← ACTUALIZADO: Lee de .env
│       ├── main.py               ← ACTUALIZADO: Lee de .env
│       └── ... resto del código (sin cambios)
│
├── CAMBIOS_DEPLOYMENT.md         ← NUEVO: Documentación
├── DEPLOYMENT_SERVER.md          ← NUEVO: Documentación
├── DEPLOYMENT_SERVER_QUICK.md    ← NUEVO: Documentación
├── PLAN_DEPLOYMENT_PASO_A_PASO.md ← NUEVO: Documentación
└── SOLUCION_IMPLEMENTADA.md      ← NUEVO: Documentación
```

---

## Comparativa: Antes vs Después

```
┌────────────────────┬──────────────┬───────────────┐
│    ASPECTO         │    ANTES     │    DESPUÉS    │
├────────────────────┼──────────────┼───────────────┤
│ Credenciales en    │      ❌      │      ✅       │
│ código             │              │               │
├────────────────────┼──────────────┼───────────────┤
│ Código idéntico    │      ❌      │      ✅       │
│ local/servidor     │              │               │
├────────────────────┼──────────────┼───────────────┤
│ Seguridad          │      ⚠️      │      ✅       │
│ de credenciales    │              │               │
├────────────────────┼──────────────┼───────────────┤
│ Cambiar BD/puerto  │   Modificar  │  Editar       │
│                    │   código     │  .env         │
├────────────────────┼──────────────┼───────────────┤
│ Datos servidor     │   Riesgosos  │  Intactos ✅  │
│                    │              │               │
└────────────────────┴──────────────┴───────────────┘
```

---

## Flujo de Variables de Entorno

```
┌─────────────────────────────────────────────────┐
│  Archivo .env (LOCAL)                           │
├─────────────────────────────────────────────────┤
│  DB_HOST=127.0.0.1                              │
│  DB_USER=junji                                  │
│  DB_PASSWORD=Tijunji2017                        │
│  FLASK_PORT=3300                                │
└─────────────────────────────────────────────────┘
                      │
                      ↓
        ┌─────────────────────────────┐
        │  load_dotenv() (main.py)    │
        │  Lee variables del archivo  │
        └─────────────────────────────┘
                      │
                      ↓
   ┌──────────────────────────────────────┐
   │  os.getenv('DB_HOST') → 127.0.0.1    │
   │  os.getenv('DB_USER') → junji        │
   │  os.getenv('FLASK_PORT') → 3300      │
   └──────────────────────────────────────┘
                      │
                      ↓
   ┌──────────────────────────────────────┐
   │  app.config['MYSQL_HOST'] = 127.0.0.1│
   │  app.config['MYSQL_USER'] = junji    │
   │  app.run(port=3300)                  │
   └──────────────────────────────────────┘
                      │
                      ↓
            ┌──────────────────┐
            │  Aplicación con  │
            │  configuración   │
            │  correcta ✅     │
            └──────────────────┘
```

---

## Seguridad: Archivos Versionados vs No Versionados

```
GITHUB REPOSITORY
├── Versionado ✅         │  No Versionado ❌
├─────────────────────────┼──────────────────────
├── db.py                 │  .env (credenciales)
├── main.py               │  venv/ (dependencias)
├── .env.example          │  *.log (logs)
├── requirements.txt      │  __pycache__/
├── .gitignore            │  *.pyc
└── Documentación         │  .DS_Store


RESULTADO:
✅ Código seguro en GitHub
✅ Credenciales protegidas (nunca se suben)
✅ Cada máquina tiene su propio .env
❌ .env no está en repositorio (necesario crear en servidor)
```

---

## Ciclo de Vida del Proyecto

```
SEMANA 1: DESARROLLO LOCAL
┌────────────────────────────┐
│ 1. Clonar repo             │
│ 2. .env ya está configurado│
│ 3. pip install             │
│ 4. python3 main.py         │
│ 5. ✅ Funciona             │
└────────────────────────────┘

SEMANA N: DEPLOYMENT AL SERVIDOR
┌────────────────────────────────┐
│ 1. git push (cambios locales)  │
│ 2. En servidor: git clone/pull │
│ 3. Crear .env (datos servidor) │
│ 4. pip install -r req.txt      │
│ 5. python3 main.py             │
│ 6. ✅ Funciona igual que local │
└────────────────────────────────┘

MANTENIMIENTO:
┌────────────────────────────────┐
│ - Cambiar credenciales: editar │
│   .env (sin código)            │
│ - Actualizar código: git pull  │
│ - Cambiar puerto: editar .env  │
│ - Sin riesgo de datos ✅       │
└────────────────────────────────┘
```

---

## Variables de Entorno por Ambiente

```
LOCAL (.env)
│
├── DB_HOST=127.0.0.1          ← Tu máquina
├── FLASK_ENV=development      ← Modo debug
├── FLASK_DEBUG=True            ← Errores detallados
└── FLASK_PORT=3300

STAGING (.env)
│
├── DB_HOST=staging.example.com ← Servidor staging
├── FLASK_ENV=staging           ← Modo staging
├── FLASK_DEBUG=False           ← No errores al usuario
└── FLASK_PORT=3300

PRODUCCIÓN (.env)
│
├── DB_HOST=prod-db.example.com ← Servidor prod
├── FLASK_ENV=production        ← Modo producción
├── FLASK_DEBUG=False           ← Seguridad
├── FLASK_HOST=0.0.0.0          ← Acceso externo
└── FLASK_PORT=3300
```

---

## Resumen: De Aquí Para Allá

```
        LOCAL                          SERVIDOR
     (Tu Máquina)                   (En la nube)
         │                              │
         ├─ .env local ────┐            │
         │                 ↓            │
         ├─ Código ──────→ GitHub ←──── ├─ Código
         │                 ↑            │
         ├─ DB local       └────┬───────┤─ DB servidor
         │                      ↓       │
         └─ python3 main.py  Mismo    └─ python3 main.py
            ✅ Funciona      Código      ✅ Funciona
            (con .env local) (.py files) (con .env servidor)

Punto clave: El código Python es IDÉNTICO
             Solo la configuración (.env) cambia
```

---

