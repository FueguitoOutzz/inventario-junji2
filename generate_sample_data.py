#!/usr/bin/env python3
"""
Script para generar datos de ejemplo para desarrollo local.
NO USAR EN PRODUCCIÓN.

Este script genera datos coherentes y respeta las relaciones entre tablas:
- Funcionarios (activos e inactivos)
- Unidades
- Equipos con estados (SIN ASIGNAR, EN USO)
- Asignaciones activas
- Devoluciones históricas

Requisitos: MySQLdb o PyMySQL configurado en env_vars.py
Uso: python3 generate_sample_data.py
"""

try:
    import MySQLdb
except ImportError:
    import pymysql as MySQLdb
    
from datetime import datetime, timedelta
import sys

# ============================================================================
# CONFIGURACIÓN DE CONEXIÓN
# ============================================================================
# Datos de conexión desde env_vars
DB_HOST = '127.0.0.1'
DB_USER = 'junji'
DB_PASS = 'Tijunji2017'
DB_NAME = 'inventariofinal'
DB_PORT = 3306

# ============================================================================
# DATOS DE EJEMPLO
# ============================================================================

# ============================================================================
# DATOS DE EJEMPLO
# ============================================================================

# Nota: Los funcionarios reales ya existen en la BD
# Estos son ejemplos de cómo se verían los datos
FUNCIONARIOS_EJEMPLO = [
    ('18123456', 'Juan García Rodríguez', 'PROFESIONAL', 'juan.garcia@junji.cl', 1),
    ('18234567', 'María López Silva', 'ADMINISTRATIVO', 'maria.lopez@junji.cl', 1),
]

# Unidades existentes - Usaremos las que ya están en la BD
# Se tomarán dinámicamente del query
UNIDADES_EJEMPLO = [
    ('Jardín de Prueba - Ejemplo 1', '22 0000001', 'Calle de Ejemplo 1', 1, 1),
    ('Salas Cuna Ejemplo 2', '22 0000002', 'Avenida de Ejemplo 2', 2, 2),
]

# EQUIPOS con estructura: (cod_inventario, num_serie, modelo_id, unidad_id, orden_compra_id, observacion)
EQUIPOS = [
    ('INV-2024-001', 'SN001-LAPTOP-001', 1, 1, 'OC-2024-001', 'Laptop para dirección'),
    ('INV-2024-002', 'SN002-LAPTOP-002', 2, 1, 'OC-2024-001', 'Laptop para administrativo'),
    ('INV-2024-003', 'SN003-MONITOR-001', 3, 1, 'OC-2024-002', 'Monitor 24 pulgadas'),
    ('INV-2024-004', 'SN004-CELULAR-001', 4, 2, 'OC-2024-003', 'Celular uso institucional'),
    ('INV-2024-005', 'SN005-CELULAR-002', 5, 2, 'OC-2024-003', 'Celular backup'),
    ('INV-2024-006', 'SN006-LAPTOP-003', 1, 2, 'OC-2024-001', 'Laptop para técnico'),
    ('INV-2024-007', 'SN007-TABLET-001', 6, 3, 'OC-2024-004', 'Tablet para aula'),
    ('INV-2024-008', 'SN008-PRINTER-001', 7, 3, 'OC-2024-005', 'Impresora multifunción'),
    ('INV-2024-009', 'SN009-MONITOR-002', 3, 3, 'OC-2024-002', 'Monitor para oficina'),
    ('INV-2024-010', 'SN010-LAPTOP-004', 2, 1, 'OC-2024-001', 'Laptop de respaldo'),
]

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def conectar_db():
    """Establece conexión con la base de datos."""
    try:
        conn = MySQLdb.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASS,
            db=DB_NAME,
            port=DB_PORT,
            charset='utf8mb4'
        )
        print("✓ Conexión a la base de datos establecida")
        return conn
    except MySQLdb.Error as e:
        print(f"✗ Error conectando a la BD: {e}")
        sys.exit(1)

def ejecutar_query(conn, query, params=None):
    """Ejecuta una query y retorna el resultado."""
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor
    except MySQLdb.Error as e:
        print(f"✗ Error en query: {e}")
        conn.rollback()
        return None

def existe_registro(conn, tabla, condicion):
    """Verifica si un registro existe."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {tabla} WHERE {condicion}")
    resultado = cursor.fetchone()
    return resultado[0] > 0 if resultado else False

# ============================================================================
# INSERCIÓN DE DATOS BÁSICOS (REFERENCIAS)
# ============================================================================

def insertar_datos_basicos(conn):
    """Inserta tipos de equipo, marcas, etc."""
    print("\n📌 Insertando datos básicos...")
    
    # Tipos de equipo
    tipos_equipo = [
        ('Laptop',),
        ('Monitor',),
        ('Celular',),
        ('Tablet',),
        ('Impresora',),
    ]
    
    for tipo in tipos_equipo:
        if not existe_registro(conn, 'tipo_equipo', f"nombreTipo_equipo='{tipo[0]}'"):
            ejecutar_query(conn, "INSERT INTO tipo_equipo (nombreTipo_equipo) VALUES (%s)", tipo)
            print(f"  ✓ Tipo: {tipo[0]}")
    
    # Marcas de equipo
    marcas_equipo = [
        ('Dell',),
        ('HP',),
        ('Samsung',),
        ('LG',),
        ('Apple',),
        ('Lenovo',),
    ]
    
    for marca in marcas_equipo:
        if not existe_registro(conn, 'marca_equipo', f"nombreMarcaEquipo='{marca[0]}'"):
            ejecutar_query(conn, "INSERT INTO marca_equipo (nombreMarcaEquipo) VALUES (%s)", marca)
            print(f"  ✓ Marca: {marca[0]}")
    
    # Relaciones marca-tipo
    marca_tipo_pairs = [
        ('Dell', 'Laptop'),
        ('HP', 'Laptop'),
        ('HP', 'Monitor'),
        ('Samsung', 'Monitor'),
        ('Samsung', 'Celular'),
        ('Apple', 'Tablet'),
        ('HP', 'Impresora'),
    ]
    
    for marca, tipo in marca_tipo_pairs:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT m.idMarca_Equipo, t.idTipo_equipo 
               FROM marca_equipo m, tipo_equipo t 
               WHERE m.nombreMarcaEquipo=%s AND t.nombreTipo_equipo=%s""",
            (marca, tipo)
        )
        result = cursor.fetchone()
        
        if result:
            marca_id, tipo_id = result
            if not existe_registro(conn, 'marca_tipo_equipo', 
                                  f"idMarca_Equipo={marca_id} AND idTipo_equipo={tipo_id}"):
                ejecutar_query(
                    conn,
                    "INSERT INTO marca_tipo_equipo (idMarca_Equipo, idTipo_equipo) VALUES (%s, %s)",
                    (marca_id, tipo_id)
                )
                print(f"  ✓ Relación: {marca} - {tipo}")

def insertar_modelos_equipo(conn):
    """Inserta modelos de equipo."""
    print("\n📌 Insertando modelos de equipo...")
    
    modelos = [
        ('Dell Inspiron 3520', 'Dell', 'Laptop'),
        ('HP Pavilion 15', 'HP', 'Laptop'),
        ('HP Z24 G3', 'HP', 'Monitor'),
        ('Samsung Galaxy A12', 'Samsung', 'Celular'),
        ('Samsung Galaxy Tab A7', 'Apple', 'Tablet'),
        ('HP LaserJet Pro M404n', 'HP', 'Impresora'),
    ]
    
    for modelo, marca, tipo in modelos:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT mt.idMarcaTipo FROM marca_tipo_equipo mt
               JOIN marca_equipo m ON mt.idMarca_Equipo=m.idMarca_Equipo
               JOIN tipo_equipo t ON mt.idTipo_equipo=t.idTipo_equipo
               WHERE m.nombreMarcaEquipo=%s AND t.nombreTipo_equipo=%s""",
            (marca, tipo)
        )
        result = cursor.fetchone()
        
        if result:
            marca_tipo_id = result[0]
            if not existe_registro(conn, 'modelo_equipo', f"nombreModeloequipo='{modelo}'"):
                ejecutar_query(
                    conn,
                    "INSERT INTO modelo_equipo (nombreModeloequipo, idMarca_Tipo_Equipo) VALUES (%s, %s)",
                    (modelo, marca_tipo_id)
                )
                print(f"  ✓ Modelo: {modelo}")

def insertar_tipos_adquisicion(conn):
    """Inserta tipos de adquisición."""
    print("\n📌 Insertando tipos de adquisición...")
    
    tipos = ['COMPRA', 'ARRIENDO', 'PRÉSTAMO', 'COMODATTO']
    
    for tipo in tipos:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tipo_adquisicion WHERE nombre_tipo_adquisicion=%s", (tipo,))
        if cursor.fetchone()[0] == 0:
            ejecutar_query(
                conn,
                "INSERT INTO tipo_adquisicion (nombre_tipo_adquisicion) VALUES (%s)",
                (tipo,)
            )
            print(f"  ✓ Tipo: {tipo}")

def insertar_proveedores(conn):
    """Inserta proveedores."""
    print("\n📌 Insertando proveedores...")
    
    proveedores = [
        ('TechMart Chile',),
        ('CompuShop',),
        ('Proveedor Oficial',),
    ]
    
    for proveedor in proveedores:
        if not existe_registro(conn, 'proveedor', f"nombreProveedor='{proveedor[0]}'"):
            ejecutar_query(
                conn,
                "INSERT INTO proveedor (nombreProveedor) VALUES (%s)",
                proveedor
            )
            print(f"  ✓ Proveedor: {proveedor[0]}")

def insertar_ordenes_compra(conn):
    """Inserta órdenes de compra."""
    print("\n📌 Insertando órdenes de compra...")
    
    ordenes = [
        ('OC-2024-001', 'Laptops', '2024-01-15', '2024-02-15', None, 1, 1),
        ('OC-2024-002', 'Monitores', '2024-02-01', '2024-03-01', None, 1, 1),
        ('OC-2024-003', 'Celulares', '2024-02-10', '2024-03-10', None, 1, 2),
        ('OC-2024-004', 'Tablets', '2024-03-01', '2024-04-01', None, 1, 1),
        ('OC-2024-005', 'Impresoras', '2024-03-15', '2024-04-15', None, 1, 3),
    ]
    
    for orden in ordenes:
        if not existe_registro(conn, 'orden_compra', f"idOrden_compra='{orden[0]}'"):
            ejecutar_query(
                conn,
                """INSERT INTO orden_compra 
                   (idOrden_compra, nombreOrden_compra, fechacompraOrden_compra, 
                    fechafin_ORDEN_COMPRA, idTipo_adquisicion, idProveedor) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (orden[0], orden[1], orden[2], orden[3], orden[5], orden[6])
            )
            print(f"  ✓ Orden: {orden[0]} - {orden[1]}")

def insertar_estados_equipo(conn):
    """Inserta estados de equipo."""
    print("\n📌 Insertando estados de equipo...")
    
    estados = [
        ('SIN ASIGNAR', None),
        ('EN USO', None),
        ('EN REPARACIÓN', None),
        ('DADO DE BAJA', None),
    ]
    
    for estado, fecha in estados:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM estado_equipo WHERE nombreEstado_equipo=%s", (estado,))
        if cursor.fetchone()[0] == 0:
            ejecutar_query(
                conn,
                "INSERT INTO estado_equipo (nombreEstado_equipo, FechaEstado_equipo) VALUES (%s, %s)",
                (estado, fecha)
            )
            print(f"  ✓ Estado: {estado}")

def insertar_unidades(conn):
    """Inserta unidades."""
    print("\n📌 Insertando unidades...")
    
    for unidad in UNIDADES:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM unidad WHERE nombreUnidad=%s", (unidad[0],))
        if cursor.fetchone()[0] == 0:
            ejecutar_query(
                conn,
                """INSERT INTO unidad (nombreUnidad, contactoUnidad, direccionUnidad, idComuna, idModalidad) 
                   VALUES (%s, %s, %s, %s, %s)""",
                unidad
            )
            print(f"  ✓ Unidad: {unidad[0]}")

# ============================================================================
# INSERCIÓN DE FUNCIONARIOS
# ============================================================================

def insertar_funcionarios(conn):
    """Inserta funcionarios."""
    print("\n👥 Insertando funcionarios...")
    
    for funcionario in FUNCIONARIOS:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM funcionario WHERE rutFuncionario=%s", (funcionario[0],))
        if cursor.fetchone()[0] == 0:
            ejecutar_query(
                conn,
                """INSERT INTO funcionario (rutFuncionario, nombreFuncionario, cargoFuncionario, 
                                           correoFuncionario, idUnidad) 
                   VALUES (%s, %s, %s, %s, %s)""",
                funcionario
            )
            print(f"  ✓ Funcionario: {funcionario[1]} ({funcionario[0]})")

# ============================================================================
# INSERCIÓN DE EQUIPOS
# ============================================================================

def insertar_equipos(conn):
    """Inserta equipos con estado SIN ASIGNAR."""
    print("\n⚙️  Insertando equipos...")
    
    # Primero obtenemos los IDs de modelos
    modelos_map = {}
    cursor = conn.cursor()
    cursor.execute("SELECT idModelo_Equipo, nombreModeloequipo FROM modelo_equipo")
    for modelo_id, nombre_modelo in cursor.fetchall():
        modelos_map[nombre_modelo] = modelo_id
    
    # Obtener ID de estado SIN ASIGNAR (debería ser 1)
    cursor.execute("SELECT idEstado_equipo FROM estado_equipo WHERE nombreEstado_equipo='SIN ASIGNAR'")
    estado_sin_asignar = cursor.fetchone()[0] if cursor.fetchone() else 1
    
    equipos_insertados = 0
    for equipo in EQUIPOS:
        cod_inventario, num_serie, modelo_id, unidad_id, orden_compra_id, observacion = equipo
        
        # Usar el modelo_id como índice en nuestra lista (1-indexed)
        modelo_names = [
            'Dell Inspiron 3520',           # 1
            'HP Pavilion 15',               # 2
            'HP Z24 G3',                    # 3
            'Samsung Galaxy A12',           # 4
            'Samsung Galaxy Tab A7',        # 5
            'HP LaserJet Pro M404n',        # 6
        ]
        
        if modelo_id <= len(modelo_names):
            nombre_modelo = modelo_names[modelo_id - 1]
            modelo_db_id = modelos_map.get(nombre_modelo)
            
            if modelo_db_id:
                cursor.execute("SELECT COUNT(*) FROM equipo WHERE Num_serieEquipo=%s", (num_serie,))
                if cursor.fetchone()[0] == 0:
                    ejecutar_query(
                        conn,
                        """INSERT INTO equipo (Cod_inventarioEquipo, Num_serieEquipo, ObservacionEquipo, 
                                              idEstado_equipo, idUnidad, idOrden_compra, idModelo_equipo) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (cod_inventario, num_serie, observacion, estado_sin_asignar, unidad_id, 
                         orden_compra_id, modelo_db_id)
                    )
                    print(f"  ✓ Equipo: {cod_inventario} - {num_serie} ({nombre_modelo})")
                    equipos_insertados += 1
    
    return equipos_insertados

# ============================================================================
# INSERCIÓN DE ASIGNACIONES Y DEVOLUCIONES
# ============================================================================

def insertar_asignaciones(conn):
    """Inserta asignaciones activas (equipos EN USO) y devoluciones históricas."""
    print("\n📋 Insertando asignaciones activas...")
    
    # Obtener funcionarios y equipos
    cursor = conn.cursor()
    cursor.execute("SELECT rutFuncionario, nombreFuncionario FROM funcionario WHERE rutFuncionario != '18901234'")
    funcionarios = cursor.fetchall()
    
    cursor.execute("""SELECT e.idEquipo, e.Cod_inventarioEquipo 
                     FROM equipo e 
                     WHERE e.idEstado_equipo=(SELECT idEstado_equipo FROM estado_equipo WHERE nombreEstado_equipo='SIN ASIGNAR')
                     ORDER BY e.idEquipo""")
    equipos = cursor.fetchall()
    
    if not funcionarios or not equipos:
        print("  ⚠ No hay funcionarios o equipos para asignar")
        return
    
    # Asignar los primeros 5 equipos a funcionarios activos
    fecha_base = datetime.now() - timedelta(days=60)
    asignaciones_creadas = 0
    
    for i, (rut, nombre) in enumerate(funcionarios[:min(5, len(funcionarios))]):
        if i < len(equipos):
            equipo_id, cod_inv = equipos[i]
            
            # Crear asignación
            cursor.execute("SELECT MAX(idAsignacion) FROM asignacion")
            max_id = cursor.fetchone()[0] or 0
            nueva_asignacion_id = max_id + 1
            
            fecha_asignacion = (fecha_base + timedelta(days=i*10)).strftime('%Y-%m-%d')
            
            ejecutar_query(
                conn,
                """INSERT INTO asignacion (idAsignacion, fecha_inicioAsignacion, ObservacionAsignacion, ActivoAsignacion, rutFuncionario) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (nueva_asignacion_id, fecha_asignacion, f'Asignación a {nombre}', 1, rut)
            )
            print(f"  ✓ Asignación: {nombre} -> {cod_inv}")
            
            # Crear relación equipo-asignacion
            ejecutar_query(
                conn,
                """INSERT INTO equipo_asignacion (idAsignacion, idEquipo) 
                   VALUES (%s, %s)""",
                (nueva_asignacion_id, equipo_id)
            )
            
            # Cambiar estado del equipo a EN USO
            cursor.execute("SELECT idEstado_equipo FROM estado_equipo WHERE nombreEstado_equipo='EN USO'")
            estado_en_uso = cursor.fetchone()[0]
            
            ejecutar_query(
                conn,
                "UPDATE equipo SET idEstado_equipo=%s WHERE idEquipo=%s",
                (estado_en_uso, equipo_id)
            )
            
            asignaciones_creadas += 1
    
    print(f"  ✓ Total asignaciones activas: {asignaciones_creadas}")
    
    # Crear devoluciones históricas
    print("\n📋 Insertando devoluciones históricas...")
    
    # Tomar los siguientes equipos para crear devoluciones históricas
    devoluciones_creadas = 0
    for i, (rut, nombre) in enumerate(funcionarios[5:7]):  # 2 devoluciones históricas
        if (5 + i) < len(equipos):
            equipo_id, cod_inv = equipos[5 + i]
            
            # Crear asignación histórica inactiva
            cursor.execute("SELECT MAX(idAsignacion) FROM asignacion")
            max_id = cursor.fetchone()[0] or 0
            asignacion_historica_id = max_id + 1
            
            fecha_asignacion = (fecha_base + timedelta(days=(5+i)*10)).strftime('%Y-%m-%d')
            
            ejecutar_query(
                conn,
                """INSERT INTO asignacion (idAsignacion, fecha_inicioAsignacion, ObservacionAsignacion, ActivoAsignacion, rutFuncionario) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (asignacion_historica_id, fecha_asignacion, f'Asignación histórica a {nombre}', 0, rut)
            )
            
            # Crear relación equipo-asignacion
            ejecutar_query(
                conn,
                """INSERT INTO equipo_asignacion (idAsignacion, idEquipo) 
                   VALUES (%s, %s)""",
                (asignacion_historica_id, equipo_id)
            )
            
            # Crear devolución
            fecha_devolucion = (fecha_base + timedelta(days=(5+i)*10 + 30)).strftime('%Y-%m-%d')
            
            # Obtener idEquipoAsignacion
            cursor.execute("SELECT idEquipoAsignacion FROM equipo_asignacion WHERE idAsignacion=%s", (asignacion_historica_id,))
            equipo_asignacion_id = cursor.fetchone()[0]
            
            ejecutar_query(
                conn,
                """INSERT INTO devolucion (fechaDevolucion, observacionDevolucion, idEquipoAsignacion) 
                   VALUES (%s, %s, %s)""",
                (fecha_devolucion, 'Equipo devuelto en buenas condiciones', equipo_asignacion_id)
            )
            
            # El equipo quedará en SIN ASIGNAR (ya lo está)
            print(f"  ✓ Devolución: {nombre} devolvió {cod_inv}")
            devoluciones_creadas += 1
    
    print(f"  ✓ Total devoluciones históricas: {devoluciones_creadas}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal."""
    print("\n" + "="*70)
    print("🔧 GENERADOR DE DATOS DE EJEMPLO - JUNJI INVENTARIO")
    print("="*70)
    print("\n⚠️  ADVERTENCIA: Este script solo es para DESARROLLO LOCAL")
    print("   NO USAR EN PRODUCCIÓN\n")
    
    conn = conectar_db()
    
    try:
        # Insertar datos en orden respetando FK
        insertar_tipos_adquisicion(conn)
        insertar_proveedores(conn)
        insertar_ordenes_compra(conn)
        insertar_estados_equipo(conn)
        insertar_datos_basicos(conn)
        insertar_modelos_equipo(conn)
        insertar_unidades(conn)
        insertar_funcionarios(conn)
        insertar_equipos(conn)
        insertar_asignaciones(conn)
        
        print("\n" + "="*70)
        print("✅ DATOS DE EJEMPLO INSERTADOS EXITOSAMENTE")
        print("="*70)
        print("\n📊 Resumen de datos:")
        print(f"  • Funcionarios: {len(FUNCIONARIOS)}")
        print(f"  • Unidades: {len(UNIDADES)}")
        print(f"  • Equipos: {len(EQUIPOS)}")
        print("  • Estados: SIN ASIGNAR, EN USO, EN REPARACIÓN, DADO DE BAJA")
        print("  • Asignaciones activas: ~5")
        print("  • Devoluciones históricas: ~2")
        print("\n💡 Próximos pasos:")
        print("  1. Accede a http://localhost:3300")
        print("  2. Usa las credenciales: admin / 1234")
        print("  3. Revisa los equipos, funcionarios y asignaciones")
        print("\n")
        
    except Exception as e:
        print(f"\n✗ Error durante la inserción: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("🔌 Conexión cerrada\n")

if __name__ == '__main__':
    main()
