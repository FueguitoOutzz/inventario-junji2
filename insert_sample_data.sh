#!/bin/bash

# ============================================================================
# Script para insertar datos de ejemplo en JUNJI Inventario
# Uso: ./insert_sample_data.sh
# ============================================================================

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  INSERTAR DATOS DE EJEMPLO - JUNJI INVENTARIO${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Validar que MariaDB está corriendo
echo -e "${CYAN}ℹ${NC} Verificando conexión a la BD..."
if ! mysql -u junji -p'Tijunji2017' -e "SELECT 1" &> /dev/null; then
    echo -e "${RED}✗${NC} No se puede conectar a la BD"
    echo -e "${YELLOW}⚠${NC} Asegúrate que MariaDB está corriendo: ./start.sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} Conexión establecida"
echo ""

# Ejecutar script SQL
echo -e "${CYAN}ℹ${NC} Insertando datos de ejemplo..."
echo ""

mysql -u junji -p'Tijunji2017' inventariofinal << 'EOF'

-- ============================================================================
-- DATOS DE EJEMPLO - JUNJI INVENTARIO
-- ============================================================================
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Insertar tipos de adquisición
INSERT IGNORE INTO tipo_adquisicion (nombre_tipo_adquisicion) VALUES ('COMPRA');
INSERT IGNORE INTO tipo_adquisicion (nombre_tipo_adquisicion) VALUES ('ARRIENDO');

-- 2. Insertar proveedores
INSERT INTO proveedor (nombreProveedor) VALUES ('Proveedor Ejemplo')
ON DUPLICATE KEY UPDATE nombreProveedor=VALUES(nombreProveedor);

-- 3. Insertar orden de compra
INSERT INTO orden_compra (idOrden_compra, nombreOrden_compra, fechacompraOrden_compra, idTipo_adquisicion, idProveedor)
VALUES ('OC-EJEMPLO-001', 'Orden de Ejemplo', '2024-01-01', 1, LAST_INSERT_ID())
ON DUPLICATE KEY UPDATE nombreOrden_compra=VALUES(nombreOrden_compra);

-- 4. Insertar estados
INSERT IGNORE INTO estado_equipo (nombreEstado_equipo) VALUES ('SIN ASIGNAR');
INSERT IGNORE INTO estado_equipo (nombreEstado_equipo) VALUES ('EN USO');
INSERT IGNORE INTO estado_equipo (nombreEstado_equipo) VALUES ('EN REPARACIÓN');
INSERT IGNORE INTO estado_equipo (nombreEstado_equipo) VALUES ('DADO DE BAJA');

-- 5. Insertar tipos de equipo
INSERT IGNORE INTO tipo_equipo (nombreTipo_equipo) VALUES ('Laptop');
INSERT IGNORE INTO tipo_equipo (nombreTipo_equipo) VALUES ('Monitor');
INSERT IGNORE INTO tipo_equipo (nombreTipo_equipo) VALUES ('Celular');

-- 6. Insertar marcas
INSERT IGNORE INTO marca_equipo (nombreMarcaEquipo) VALUES ('Dell');
INSERT IGNORE INTO marca_equipo (nombreMarcaEquipo) VALUES ('HP');
INSERT IGNORE INTO marca_equipo (nombreMarcaEquipo) VALUES ('Samsung');

-- 7. Relaciones marca-tipo
INSERT IGNORE INTO marca_tipo_equipo (idMarca_Equipo, idTipo_equipo) 
SELECT 1, 1;  -- Dell Laptop

INSERT IGNORE INTO marca_tipo_equipo (idMarca_Equipo, idTipo_equipo) 
SELECT 2, 1;  -- HP Laptop

INSERT IGNORE INTO marca_tipo_equipo (idMarca_Equipo, idTipo_equipo) 
SELECT 2, 2;  -- HP Monitor

INSERT IGNORE INTO marca_tipo_equipo (idMarca_Equipo, idTipo_equipo) 
SELECT 3, 3;  -- Samsung Celular

-- 8. Insertar modelos
INSERT IGNORE INTO modelo_equipo (nombreModeloequipo, idMarca_Tipo_Equipo) 
VALUES ('Laptop Ejemplo', 1);

INSERT IGNORE INTO modelo_equipo (nombreModeloequipo, idMarca_Tipo_Equipo) 
VALUES ('Laptop Ejemplo 2', 2);

INSERT IGNORE INTO modelo_equipo (nombreModeloequipo, idMarca_Tipo_Equipo) 
VALUES ('Monitor Ejemplo', 3);

INSERT IGNORE INTO modelo_equipo (nombreModeloequipo, idMarca_Tipo_Equipo) 
VALUES ('Celular Ejemplo', 4);

-- 9. Insertar equipos con estado SIN ASIGNAR
INSERT IGNORE INTO equipo (Cod_inventarioEquipo, Num_serieEquipo, idEstado_equipo, idUnidad, idOrden_compra, idModelo_equipo, ObservacionEquipo)
VALUES 
('INV-EJ-0001', 'SN-EJ-001', 1, 1, 'OC-EJEMPLO-001', 1, 'Laptop de ejemplo'),
('INV-EJ-0002', 'SN-EJ-002', 1, 1, 'OC-EJEMPLO-001', 2, 'Laptop ejemplo 2'),
('INV-EJ-0003', 'SN-EJ-003', 1, 1, 'OC-EJEMPLO-001', 3, 'Monitor de ejemplo'),
('INV-EJ-0004', 'SN-EJ-004', 1, 1, 'OC-EJEMPLO-001', 4, 'Celular de ejemplo'),
('INV-EJ-0005', 'SN-EJ-005', 1, 2, 'OC-EJEMPLO-001', 1, 'Laptop adicional');

SET FOREIGN_KEY_CHECKS = 1;

-- 10. Verificación
SELECT '═══════════════════════════════════════════════════════════' AS '';
SELECT 'DATOS DE EJEMPLO INSERTADOS' AS Status;
SELECT '═══════════════════════════════════════════════════════════' AS '';
SELECT COUNT(*) as 'Total Equipos Ejemplo' FROM equipo WHERE Cod_inventarioEquipo LIKE 'INV-EJ%';
SELECT COUNT(*) as 'Equipos Sin Asignar' FROM equipo WHERE Cod_inventarioEquipo LIKE 'INV-EJ%' AND idEstado_equipo=1;

EOF

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓${NC} Datos de ejemplo insertados correctamente"
    echo ""
    echo -e "${CYAN}📊 Equipos de ejemplo disponibles:${NC}"
    mysql -u junji -p'Tijunji2017' inventariofinal -e "SELECT Cod_inventarioEquipo, Num_serieEquipo, m.nombreModeloequipo FROM equipo e JOIN modelo_equipo m ON e.idModelo_equipo=m.idModelo_Equipo WHERE e.Cod_inventarioEquipo LIKE 'INV-EJ%';" 2>/dev/null
    echo ""
    echo -e "${CYAN}Próximos pasos:${NC}"
    echo "  1. Accede a http://localhost:3300"
    echo "  2. Usa las credenciales: admin / 1234"
    echo "  3. Revisa los equipos con código INV-EJ-xxxx"
    echo ""
else
    echo -e "${RED}✗${NC} Error durante la inserción"
    exit 1
fi
