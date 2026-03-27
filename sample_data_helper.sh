#!/bin/bash

# ============================================================================
# HELPER SCRIPT - Gestión de datos de ejemplo
# ============================================================================
#
# Uso:
#   ./sample_data_helper.sh insert      # Insertar datos de ejemplo
#   ./sample_data_helper.sh verify      # Verificar integridad de datos
#   ./sample_data_helper.sh clean       # Limpiar datos de ejemplo
#   ./sample_data_helper.sh reset       # Limpiar e insertar nuevamente
#   ./sample_data_helper.sh help        # Mostrar esta ayuda
#
# ============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Directorio actual
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ============================================================================
# FUNCIONES
# ============================================================================

print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  $1"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# ============================================================================
# INSERTAR DATOS
# ============================================================================

insert_data() {
    print_header "INSERTAR DATOS DE EJEMPLO"
    
    print_warning "Este proceso insertará datos de ejemplo en la BD"
    print_info "Base de datos: inventariofinal"
    print_info "Usuario: junji"
    echo ""
    
    # Verificar que Python y MySQLdb estén disponibles
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 no está instalado"
        exit 1
    fi
    
    print_info "Ejecutando script de inserción..."
    echo ""
    
    cd "$SCRIPT_DIR"
    python3 generate_sample_data.py
    
    if [ $? -eq 0 ]; then
        echo ""
        print_success "Datos insertados correctamente"
        print_info "Ejecuta './sample_data_helper.sh verify' para verificar"
    else
        print_error "Error durante la inserción"
        exit 1
    fi
}

# ============================================================================
# VERIFICAR DATOS
# ============================================================================

verify_data() {
    print_header "VERIFICAR INTEGRIDAD DE DATOS"
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 no está instalado"
        exit 1
    fi
    
    print_info "Ejecutando script de verificación..."
    echo ""
    
    cd "$SCRIPT_DIR"
    python3 verify_sample_data.py
    
    if [ $? -eq 0 ]; then
        echo ""
        print_success "Verificación completada"
    else
        print_error "Error durante la verificación"
        exit 1
    fi
}

# ============================================================================
# LIMPIAR DATOS
# ============================================================================

clean_data() {
    print_header "LIMPIAR DATOS DE EJEMPLO"
    
    print_warning "ESTO ELIMINARÁ TODOS LOS DATOS INSERTADOS"
    echo ""
    read -p "¿Continuar? (s/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        print_info "Operación cancelada"
        exit 0
    fi
    
    print_info "Conectando a la BD..."
    
    mysql -u junji -p"Tijunji2017" inventariofinal << EOF
SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM devolucion;
DELETE FROM equipo_asignacion;
DELETE FROM asignacion;
DELETE FROM equipo;
DELETE FROM orden_compra;
DELETE FROM proveedor;
DELETE FROM funcionario;
DELETE FROM unidad;
DELETE FROM modelo_equipo;
DELETE FROM marca_tipo_equipo;
DELETE FROM marca_equipo;
DELETE FROM tipo_equipo;
DELETE FROM tipo_adquisicion;
DELETE FROM estado_equipo;

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'Limpieza completada' as Status;
EOF

    if [ $? -eq 0 ]; then
        print_success "Datos de ejemplo eliminados"
    else
        print_error "Error durante la limpieza"
        exit 1
    fi
}

# ============================================================================
# RESETEAR (LIMPIAR + INSERTAR)
# ============================================================================

reset_data() {
    print_header "RESETEAR DATOS DE EJEMPLO"
    
    print_warning "Esto eliminará e insertará nuevamente todos los datos"
    echo ""
    read -p "¿Continuar? (s/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        print_info "Operación cancelada"
        exit 0
    fi
    
    clean_data
    echo ""
    insert_data
}

# ============================================================================
# MOSTRAR AYUDA
# ============================================================================

show_help() {
    cat << EOF
${CYAN}╔════════════════════════════════════════════════════════════╗${NC}
${CYAN}║${NC}  HELPER - Gestión de Datos de Ejemplo
${CYAN}╚════════════════════════════════════════════════════════════╝${NC}

${GREEN}USO:${NC}
  ./sample_data_helper.sh [COMANDO]

${GREEN}COMANDOS:${NC}
  ${CYAN}insert${NC}    Insertar datos de ejemplo en la BD
  ${CYAN}verify${NC}    Verificar integridad de los datos
  ${CYAN}clean${NC}     Limpiar todos los datos de ejemplo
  ${CYAN}reset${NC}     Limpiar e insertar nuevamente
  ${CYAN}help${NC}      Mostrar esta ayuda

${GREEN}EJEMPLOS:${NC}
  ./sample_data_helper.sh insert
  ./sample_data_helper.sh verify
  ./sample_data_helper.sh reset

${GREEN}NOTAS:${NC}
  • Requiere Python3 y acceso a MySQL/MariaDB
  • Las credenciales por defecto están en los scripts
  • Asegúrate que MariaDB está corriendo (./start.sh)
  • Los datos de ejemplo son SOLO para desarrollo local

${GREEN}MÁS INFORMACIÓN:${NC}
  Consulta README_SAMPLE_DATA.md para más detalles

EOF
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    case "${1:-help}" in
        insert)
            insert_data
            ;;
        verify)
            verify_data
            ;;
        clean)
            clean_data
            ;;
        reset)
            reset_data
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            print_error "Comando desconocido: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
