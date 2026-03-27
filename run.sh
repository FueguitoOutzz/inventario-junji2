#!/bin/bash

# Script para instalar y ejecutar el proyecto Junji-Inventario

echo "🚀 Iniciando configuración del proyecto Junji-Inventario"
echo "=========================================="

# Navegar al directorio del proyecto
cd "$(dirname "$0")" || exit 1

# Activar entorno virtual
echo "✓ Activando entorno virtual..."
source venv/bin/activate

# Verificar que las dependencias están instaladas
echo "✓ Verificando dependencias..."
pip3 install -q -r Flask/requirements_minimal.txt

# Verificar MariaDB está corriendo
echo "✓ Verificando Base de Datos..."
brew services list | grep mariadb

# Mostrar información de configuración
echo ""
echo "=========================================="
echo "📋 Configuración del Proyecto:"
echo "=========================================="
echo "✓ Python version: $(python3 --version)"
echo "✓ Flask app: $(pwd)/Flask/app"
echo "✓ Database: inventariofinal"
echo "✓ Database user: junji"
echo "✓ Server: http://localhost:3300"
echo ""
echo "Iniciando aplicación Flask..."
echo "Presiona CTRL+C para detener"
echo "=========================================="
echo ""

# Ejecutar la aplicación
cd Flask/app && python3 main.py

