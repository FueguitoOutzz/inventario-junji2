#!/usr/bin/env python3
"""
Script para verificar que los datos de ejemplo se insertaron correctamente.
Comprueba:
- Integridad de relaciones
- Estados consistentes
- Asignaciones activas vs históricas
- Equipos sin asignación vs equipos en uso

Uso: python3 verify_sample_data.py
"""

import MySQLdb
import sys

# ============================================================================
# CONFIGURACIÓN DE CONEXIÓN
# ============================================================================
DB_HOST = '127.0.0.1'
DB_USER = 'junji'
DB_PASS = 'Tijunji2017'
DB_NAME = 'inventariofinal'
DB_PORT = 3306

# ============================================================================
# COLORES PARA TERMINAL
# ============================================================================
VERDE = '\033[92m'
ROJO = '\033[91m'
AMARILLO = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

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
        return conn
    except MySQLdb.Error as e:
        print(f"{ROJO}✗ Error conectando a la BD: {e}{RESET}")
        sys.exit(1)

def ejecutar_query(conn, query):
    """Ejecuta una query y retorna los resultados."""
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(query)
        return cursor.fetchall()
    except MySQLdb.Error as e:
        print(f"{ROJO}✗ Error en query: {e}{RESET}")
        return []

def verifica_condicion(condicion, mensaje_ok, mensaje_error):
    """Verifica una condición y muestra resultado."""
    if condicion:
        print(f"  {VERDE}✓{RESET} {mensaje_ok}")
        return True
    else:
        print(f"  {ROJO}✗{RESET} {mensaje_error}")
        return False

# ============================================================================
# VERIFICACIONES
# ============================================================================

def verificar_volumen_datos(conn):
    """Verifica que se insertó una cantidad apropiada de datos."""
    print(f"\n{CYAN}📊 VOLUMEN DE DATOS{RESET}")
    
    cursor = conn.cursor()
    
    # Contar registros
    cursor.execute("SELECT COUNT(*) as count FROM funcionario")
    num_funcionarios = cursor.fetchone()[0]
    verifica_condicion(num_funcionarios >= 8, f"{num_funcionarios} funcionarios registrados", "No hay suficientes funcionarios")
    
    cursor.execute("SELECT COUNT(*) as count FROM unidad")
    num_unidades = cursor.fetchone()[0]
    verifica_condicion(num_unidades >= 3, f"{num_unidades} unidades registradas", "No hay suficientes unidades")
    
    cursor.execute("SELECT COUNT(*) as count FROM equipo")
    num_equipos = cursor.fetchone()[0]
    verifica_condicion(num_equipos >= 10, f"{num_equipos} equipos registrados", "No hay suficientes equipos")
    
    cursor.execute("SELECT COUNT(*) as count FROM asignacion WHERE ActivoAsignacion=1")
    asignaciones_activas = cursor.fetchone()[0]
    verifica_condicion(asignaciones_activas >= 3, f"{asignaciones_activas} asignaciones activas", "No hay asignaciones activas")

def verificar_estados_consistentes(conn):
    """Verifica que los estados sean consistentes."""
    print(f"\n{CYAN}🔍 CONSISTENCIA DE ESTADOS{RESET}")
    
    # Equipos EN USO deben tener asignación activa
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT e.idEquipo, e.Cod_inventarioEquipo 
        FROM equipo e
        WHERE e.idEstado_equipo = (SELECT idEstado_equipo FROM estado_equipo WHERE nombreEstado_equipo='EN USO')
        AND e.idEquipo NOT IN (
            SELECT DISTINCT ea.idEquipo 
            FROM equipo_asignacion ea
            JOIN asignacion a ON ea.idAsignacion = a.idAsignacion
            WHERE a.ActivoAsignacion = 1
        )
    """)
    equipos_inconsistentes = cursor.fetchall()
    verifica_condicion(
        len(equipos_inconsistentes) == 0,
        "Todos los equipos EN USO tienen asignación activa",
        f"{len(equipos_inconsistentes)} equipos EN USO sin asignación activa"
    )
    
    # Equipos SIN ASIGNAR no deben tener asignación activa
    cursor.execute("""
        SELECT e.idEquipo, e.Cod_inventarioEquipo 
        FROM equipo e
        WHERE e.idEstado_equipo = (SELECT idEstado_equipo FROM estado_equipo WHERE nombreEstado_equipo='SIN ASIGNAR')
        AND e.idEquipo IN (
            SELECT DISTINCT ea.idEquipo 
            FROM equipo_asignacion ea
            JOIN asignacion a ON ea.idAsignacion = a.idAsignacion
            WHERE a.ActivoAsignacion = 1
        )
    """)
    equipos_inconsistentes2 = cursor.fetchall()
    verifica_condicion(
        len(equipos_inconsistentes2) == 0,
        "Equipos SIN ASIGNAR no tienen asignaciones activas",
        f"{len(equipos_inconsistentes2)} equipos SIN ASIGNAR con asignación activa"
    )

def verificar_integridad_fk(conn):
    """Verifica integridad de relaciones."""
    print(f"\n{CYAN}🔗 INTEGRIDAD DE RELACIONES{RESET}")
    
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # Verificar equipos sin modelo válido
    cursor.execute("""
        SELECT COUNT(*) as count FROM equipo e
        WHERE e.idModelo_equipo NOT IN (SELECT idModelo_Equipo FROM modelo_equipo)
    """)
    count = cursor.fetchone()['count']
    verifica_condicion(count == 0, "Todos los equipos tienen modelo válido", f"{count} equipos con modelo inválido")
    
    # Verificar asignaciones sin funcionario
    cursor.execute("""
        SELECT COUNT(*) as count FROM asignacion a
        WHERE a.rutFuncionario NOT IN (SELECT rutFuncionario FROM funcionario)
    """)
    count = cursor.fetchone()['count']
    verifica_condicion(count == 0, "Todas las asignaciones tienen funcionario válido", f"{count} asignaciones sin funcionario")
    
    # Verificar equipos sin unidad
    cursor.execute("""
        SELECT COUNT(*) as count FROM equipo e
        WHERE e.idUnidad NOT IN (SELECT idUnidad FROM unidad)
    """)
    count = cursor.fetchone()['count']
    verifica_condicion(count == 0, "Todos los equipos tienen unidad válida", f"{count} equipos sin unidad")

def verificar_devoluciones(conn):
    """Verifica que las devoluciones sean coherentes."""
    print(f"\n{CYAN}📦 DEVOLUCIONES{RESET}")
    
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("""
        SELECT COUNT(*) as count FROM devolucion d
        WHERE d.idEquipoAsignacion NOT IN (SELECT idEquipoAsignacion FROM equipo_asignacion)
    """)
    count = cursor.fetchone()['count']
    verifica_condicion(count == 0, "Todas las devoluciones apuntan a asignaciones válidas", f"{count} devoluciones inválidas")
    
    cursor.execute("SELECT COUNT(*) as count FROM devolucion")
    num_devoluciones = cursor.fetchone()['count']
    verifica_condicion(num_devoluciones >= 1, f"{num_devoluciones} devoluciones históricas registradas", "No hay devoluciones históricas")

def mostrar_estadisticas(conn):
    """Muestra estadísticas de los datos."""
    print(f"\n{CYAN}📈 ESTADÍSTICAS{RESET}")
    
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # Equipos por estado
    cursor.execute("""
        SELECT ee.nombreEstado_equipo, COUNT(e.idEquipo) as cantidad
        FROM equipo e
        JOIN estado_equipo ee ON e.idEstado_equipo = ee.idEstado_equipo
        GROUP BY ee.nombreEstado_equipo
    """)
    resultados = cursor.fetchall()
    for fila in resultados:
        print(f"  • {fila['nombreEstado_equipo']}: {fila['cantidad']}")
    
    # Asignaciones
    cursor.execute("""
        SELECT a.ActivoAsignacion, COUNT(*) as cantidad
        FROM asignacion a
        GROUP BY a.ActivoAsignacion
    """)
    resultados = cursor.fetchall()
    for fila in resultados:
        estado = "Activas" if fila['ActivoAsignacion'] else "Históricas"
        print(f"  • Asignaciones {estado}: {fila['cantidad']}")
    
    # Funcionarios con equipos
    cursor.execute("""
        SELECT COUNT(DISTINCT a.rutFuncionario) as cantidad
        FROM asignacion a
        WHERE a.ActivoAsignacion = 1
    """)
    resultado = cursor.fetchone()
    print(f"  • Funcionarios con equipos asignados: {resultado['cantidad']}")

def mostrar_resumen_equipos(conn):
    """Muestra resumen de equipos y sus asignaciones."""
    print(f"\n{CYAN}⚙️  EQUIPOS Y ASIGNACIONES{RESET}")
    
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT 
            e.idEquipo,
            e.Cod_inventarioEquipo,
            me.nombreModeloequipo,
            ee.nombreEstado_equipo,
            f.nombreFuncionario,
            a.ActivoAsignacion
        FROM equipo e
        JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
        JOIN estado_equipo ee ON e.idEstado_equipo = ee.idEstado_equipo
        LEFT JOIN equipo_asignacion ea ON e.idEquipo = ea.idEquipo
        LEFT JOIN asignacion a ON ea.idAsignacion = a.idAsignacion
        LEFT JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
        ORDER BY e.idEquipo
        LIMIT 15
    """)
    
    resultados = cursor.fetchall()
    for fila in resultados:
        cod = fila['Cod_inventarioEquipo']
        modelo = fila['nombreModeloequipo'][:20]
        estado = fila['nombreEstado_equipo'][:15]
        
        if fila['nombreFuncionario']:
            asignacion = f"→ {fila['nombreFuncionario'][:20]}"
        else:
            asignacion = "Sin asignar"
        
        print(f"  • {cod:15} | {modelo:20} | {estado:15} | {asignacion}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal."""
    print("\n" + "="*70)
    print("🔎 VERIFICADOR DE DATOS - JUNJI INVENTARIO")
    print("="*70)
    
    conn = conectar_db()
    print(f"{VERDE}✓ Conexión a la BD establecida{RESET}")
    
    try:
        verificar_volumen_datos(conn)
        verificar_integridad_fk(conn)
        verificar_estados_consistentes(conn)
        verificar_devoluciones(conn)
        mostrar_estadisticas(conn)
        mostrar_resumen_equipos(conn)
        
        print("\n" + "="*70)
        print(f"{VERDE}✅ VERIFICACIÓN COMPLETADA{RESET}")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n{ROJO}Error durante verificación: {e}{RESET}\n")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
