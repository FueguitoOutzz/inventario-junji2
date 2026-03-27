#!/bin/bash

# ============================================================================
# SCRIPT DE CARGA DE DATOS DE EJEMPLO
# ============================================================================
# Este script carga automáticamente los datos de ejemplo en la base de datos
# Uso: ./load_sample_data.sh
# ============================================================================

set -e

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║   Sistema JUNJI-Inventario - Carga de Datos de Ejemplo             ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Variables de conexión a la base de datos
DB_USER="junji"
DB_HOST="localhost"
DB_NAME="inventariofinal"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/insert_sample_data.sql"

# Validar que el archivo SQL existe
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: No se encontró el archivo $SCRIPT_PATH"
    echo "Asegúrate de estar en la raíz del proyecto."
    exit 1
fi

echo "📋 Información de la base de datos:"
echo "   Host: $DB_HOST"
echo "   Usuario: $DB_USER"
echo "   Base de datos: $DB_NAME"
echo "   Script: insert_sample_data.sql"
echo ""

# Solicitar contraseña
read -sp "🔐 Ingresa la contraseña de MySQL para el usuario '$DB_USER': " DB_PASSWORD
echo ""

echo ""
echo "⏳ Cargando datos de ejemplo..."
echo ""

# Ejecutar el script SQL
if mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$SCRIPT_PATH" 2>/dev/null; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║   ✅ ¡Datos de ejemplo cargados exitosamente!                      ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📊 Puedes acceder a la aplicación con:"
    echo "   URL: http://localhost:3300"
    echo "   Usuario: admin"
    echo "   Contraseña: 1234"
    echo ""
    echo "📝 Datos incluidos:"
    echo "   • 9 funcionarios"
    echo "   • 3 unidades educativas"
    echo "   • 10 equipos de inventario"
    echo "   • 5 asignaciones activas"
    echo "   • 2 devoluciones registradas"
    echo ""
else
    echo ""
    echo "❌ Error: No se pudieron cargar los datos."
    echo "   • Verifica que la contraseña sea correcta"
    echo "   • Verifica que MySQL esté ejecutándose"
    echo "   • Verifica que la base de datos 'inventariofinal' exista"
    echo ""
    exit 1
fi
