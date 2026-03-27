#!/bin/bash

# ====================================================
# Script para ejecutar el Sistema de Gestión de Inventario JUNJI
# ====================================================

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=3300

cd "$REPO_DIR" || exit 1

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Sistema de Gestión de Inventario${NC}"
echo -e "${BLUE}          JUNJI - Inventario${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar que MariaDB esté corriendo
echo "✓ Verificando MariaDB..."
if ! brew services list | grep mariadb | grep -q "started"; then
    echo "  ⚠️  Iniciando MariaDB..."
    brew services start mariadb
    sleep 2
fi
echo "  ✓ MariaDB está corriendo"
echo ""

# Liberar el puerto si está ocupado
if lsof -ti tcp:${PORT} >/dev/null 2>&1; then
    echo "⚠️  Puerto ${PORT} en uso, deteniendo procesos previos..."
    lsof -ti tcp:${PORT} | xargs kill -9 || true
    sleep 1
fi

# Activar entorno virtual
echo "✓ Activando entorno virtual..."
if [ ! -f "$REPO_DIR/venv/bin/activate" ]; then
    echo "❌ No se encontró el entorno virtual en $REPO_DIR/venv"
    exit 1
fi
source "$REPO_DIR/venv/bin/activate"
echo "  ✓ Entorno virtual activado"
echo ""

# Variables de entorno para Flask
export PYTHONPATH="$REPO_DIR/Flask/app"
export FLASK_APP=main
export FLASK_ENV=development

# Mostrar información de acceso
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ SISTEMA LISTO PARA ACCEDER${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Acceso a la aplicación:"
echo "  🌐 URL: http://localhost:3300"
echo ""
echo "Credenciales por defecto:"
echo "  👤 Usuario: admin"
echo "  🔐 Contraseña: 1234"
echo ""
echo "Información de la BD:"
echo "  🗄️  Host: localhost"
echo "  📊 Base de datos: inventariofinal"
echo "  👥 Usuario BD: junji"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo ""

# Ejecutar la aplicación (foreground; detener con Ctrl+C)
cd "$REPO_DIR/Flask/app"
echo "Iniciando servidor Flask en puerto ${PORT}..."
flask run --host 0.0.0.0 --port ${PORT}
