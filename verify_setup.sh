#!/bin/bash

# ============================================================================
# VERIFICADOR DE INSTALACIÓN
# ============================================================================
# Este script verifica que todos los componentes necesarios estén instalados
# y que la base de datos esté correctamente configurada.
# ============================================================================

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║   VERIFICACIÓN DE INSTALACIÓN - JUNJI-Inventario                   ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Colores para la salida
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contadores
CHECKS_PASSED=0
CHECKS_FAILED=0

# Función para verificar comandos
check_command() {
    local cmd=$1
    local display_name=$2
    
    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✓${NC} $display_name instalado"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}✗${NC} $display_name NO instalado"
        ((CHECKS_FAILED++))
    fi
}

# Función para verificar archivos
check_file() {
    local file=$1
    local display_name=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $display_name encontrado"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}✗${NC} $display_name NO encontrado"
        ((CHECKS_FAILED++))
    fi
}

# Función para verificar versiones
check_version() {
    local cmd=$1
    local version_flag=$2
    local display_name=$3
    
    if command -v $cmd &> /dev/null; then
        local version=$($cmd $version_flag 2>&1 | head -n 1)
        echo -e "${GREEN}✓${NC} $display_name: $version"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}✗${NC} $display_name NO instalado"
        ((CHECKS_FAILED++))
    fi
}

echo "1️⃣ VERIFICANDO DEPENDENCIAS DEL SISTEMA"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_command "python3" "Python 3"
check_command "mysql" "MySQL Client"
check_command "git" "Git"
echo ""

echo "2️⃣ VERIFICANDO VERSIONES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_version "python3" "--version" "Python"
check_version "mysql" "--version" "MySQL Client"
echo ""

echo "3️⃣ VERIFICANDO ARCHIVOS NECESARIOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_file "$(pwd)/insert_sample_data.sql" "Script de datos de ejemplo"
check_file "$(pwd)/Flask/app/main.py" "Aplicación Flask (main.py)"
check_file "$(pwd)/Flask/app/db.py" "Módulo de base de datos"
check_file "$(pwd)/start.sh" "Script de inicio (start.sh)"
check_file "$(pwd)/README.md" "Documentación (README.md)"
check_file "$(pwd)/QUICK_START.md" "Guía rápida (QUICK_START.md)"
echo ""

echo "4️⃣ VERIFICANDO ENTORNO VIRTUAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "venv" ]; then
    echo -e "${GREEN}✓${NC} Entorno virtual (venv) encontrado"
    ((CHECKS_PASSED++))
else
    echo -e "${YELLOW}⚠${NC} Entorno virtual (venv) NO encontrado"
    echo "   Puedes crear uno con: python3 -m venv venv"
fi
echo ""

echo "5️⃣ VERIFICANDO CONEXIÓN A MYSQL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -sp "🔐 Contraseña de MySQL (usuario 'junji'): " DB_PASSWORD
echo ""

if mysql -h localhost -u junji -p"$DB_PASSWORD" -e "SELECT 1" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Conexión a MySQL exitosa"
    ((CHECKS_PASSED++))
    
    # Verificar si la base de datos existe
    if mysql -h localhost -u junji -p"$DB_PASSWORD" -e "USE inventariofinal" &>/dev/null; then
        echo -e "${GREEN}✓${NC} Base de datos 'inventariofinal' existe"
        ((CHECKS_PASSED++))
        
        # Verificar si hay datos
        TABLE_COUNT=$(mysql -h localhost -u junji -p"$DB_PASSWORD" inventariofinal -se "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='inventariofinal';" 2>/dev/null)
        if [ "$TABLE_COUNT" -gt 0 ]; then
            echo -e "${GREEN}✓${NC} Base de datos contiene tablas ($TABLE_COUNT encontradas)"
            ((CHECKS_PASSED++))
        else
            echo -e "${YELLOW}⚠${NC} Base de datos está vacía"
            echo "   Ejecuta: ./load_sample_data.sh"
        fi
    else
        echo -e "${RED}✗${NC} Base de datos 'inventariofinal' NO existe"
        ((CHECKS_FAILED++))
    fi
else
    echo -e "${RED}✗${NC} No se pudo conectar a MySQL"
    echo "   • Verifica que MySQL esté ejecutándose"
    echo "   • Verifica la contraseña"
    ((CHECKS_FAILED++))
fi
echo ""

echo "╔════════════════════════════════════════════════════════════════════╗"
if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "║   ${GREEN}✅ ¡VERIFICACIÓN COMPLETADA EXITOSAMENTE!${NC}                    ║"
else
    echo -e "║   ${RED}⚠️  VERIFICACIÓN CON PROBLEMAS${NC}                              ║"
fi
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Resultados: ${GREEN}$CHECKS_PASSED pasados${NC} | ${RED}$CHECKS_FAILED fallidos${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo "🚀 Próximos pasos:"
    echo "   1. Ejecutar: ./start.sh"
    echo "   2. Abrir navegador en: http://localhost:3300"
    echo "   3. Credenciales: admin / 1234"
else
    echo "⚠️  Por favor resuelve los problemas mencionados arriba."
    echo "   Consulta README.md para más información."
fi
echo ""
