#!/usr/bin/env python3
"""
Script para sincronizar funcionarios desde Excel con la BD.

Lógica:
1. Lee el archivo Excel con los funcionarios activos
2. Los que están en el Excel: activo=1 (y actualiza datos si cambiaron)
3. Los que NO están en el Excel: activo=0 (licencia, renuncia, etc)
4. Registra cambios en un log para auditoría

Uso:
python sync_funcionarios_excel.py archivo.xlsx

Archivo Excel debe tener columnas:
- rutFuncionario (ej: 12345678-9)
- nombreFuncionario
- cargoFuncionario
- correoFuncionario
- idUnidad
"""

import sys
import os
from datetime import datetime
import pandas as pd
import pymysql
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración BD
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'junji')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Tijunji2017')
DB_NAME = os.getenv('DB_NAME', 'inventariofinal')
DB_PORT = int(os.getenv('DB_PORT', '3306'))

# Archivo de log
LOG_FILE = f'sync_funcionarios_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

def log_message(msg):
    """Escribe mensaje en consola y archivo de log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mensaje = f"[{timestamp}] {msg}"
    print(mensaje)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(mensaje + '\n')

def get_db_connection():
    """Abre conexión a la BD"""
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            charset='utf8mb4'
        )
        return conn
    except Exception as e:
        log_message(f"❌ Error de conexión a BD: {e}")
        sys.exit(1)

def normalizar_rut(rut):
    """Normaliza RUT: '12345678-9' → '12345678-9'"""
    rut = rut.strip().upper()
    if '-' not in rut and len(rut) >= 7:
        # Si no tiene guión, agregarlo: '123456789' → '12345678-9'
        rut = rut[:-1] + '-' + rut[-1]
    return rut

def check_activo_column(conn):
    """Verifica si la columna activoFuncionario existe"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'funcionario'
            AND column_name = 'activoFuncionario'
        """, (DB_NAME,))
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists
    except Exception as e:
        log_message(f"❌ Error verificando columna: {e}")
        return False

def sync_funcionarios(excel_file):
    """Sincroniza funcionarios desde Excel"""
    
    log_message(f"🔄 Iniciando sincronización desde: {excel_file}")
    
    # Verificar que el archivo existe
    if not os.path.exists(excel_file):
        log_message(f"❌ Archivo no encontrado: {excel_file}")
        sys.exit(1)
    
    # Leer Excel
    try:
        df = pd.read_excel(excel_file)
        log_message(f"✓ Archivo leído: {len(df)} registros")
    except Exception as e:
        log_message(f"❌ Error leyendo Excel: {e}")
        sys.exit(1)
    
    # Validar columnas requeridas
    columnas_requeridas = ['rutFuncionario', 'nombreFuncionario', 'cargoFuncionario', 
                           'correoFuncionario', 'idUnidad']
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if columnas_faltantes:
        log_message(f"❌ Columnas faltantes en Excel: {columnas_faltantes}")
        sys.exit(1)
    
    # Conectar a BD
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si existe columna activoFuncionario
    tiene_activo = check_activo_column(conn)
    if not tiene_activo:
        log_message("⚠️  Columna 'activoFuncionario' no existe. Agregándola...")
        try:
            cursor.execute("""
                ALTER TABLE funcionario 
                ADD COLUMN activoFuncionario TINYINT DEFAULT 1 
                COMMENT 'Estado: 1=Activo, 0=Inactivo'
            """)
            conn.commit()
            log_message("✓ Columna 'activoFuncionario' creada")
        except pymysql.Error as e:
            if 'Duplicate column' not in str(e):
                log_message(f"❌ Error creando columna: {e}")
                cursor.close()
                conn.close()
                sys.exit(1)
    
    # Normalizar RUTs del Excel
    df['rutFuncionario'] = df['rutFuncionario'].apply(normalizar_rut)
    ruts_excel = set(df['rutFuncionario'].values)
    
    log_message(f"📊 RUTs en Excel: {len(ruts_excel)}")
    
    # Obtener RUTs actuales en BD
    cursor.execute("SELECT rutFuncionario FROM funcionario")
    ruts_bd = {row[0] for row in cursor.fetchall()}
    log_message(f"📊 RUTs en BD: {len(ruts_bd)}")
    
    estadisticas = {
        'insertados': 0,
        'actualizados': 0,
        'desactivados': 0,
        'errores': 0
    }
    
    # 1. INSERTAR O ACTUALIZAR los que están en Excel
    for _, row in df.iterrows():
        rut = row['rutFuncionario']
        nombre = row['nombreFuncionario']
        cargo = row['cargoFuncionario'].upper()
        correo = row['correoFuncionario'].lower()
        id_unidad = int(row['idUnidad'])
        
        try:
            if rut in ruts_bd:
                # Actualizar
                cursor.execute("""
                    UPDATE funcionario
                    SET nombreFuncionario = %s,
                        cargoFuncionario = %s,
                        correoFuncionario = %s,
                        idUnidad = %s,
                        activoFuncionario = 1
                    WHERE rutFuncionario = %s
                """, (nombre, cargo, correo, id_unidad, rut))
                if cursor.rowcount > 0:
                    estadisticas['actualizados'] += 1
                    log_message(f"  ✓ Actualizado: {rut} - {nombre}")
            else:
                # Insertar
                cursor.execute("""
                    INSERT INTO funcionario 
                    (rutFuncionario, nombreFuncionario, cargoFuncionario, 
                     correoFuncionario, idUnidad, activoFuncionario)
                    VALUES (%s, %s, %s, %s, %s, 1)
                """, (rut, nombre, cargo, correo, id_unidad))
                estadisticas['insertados'] += 1
                log_message(f"  ➕ Insertado: {rut} - {nombre}")
        
        except pymysql.Error as e:
            if 'Duplicate entry' in str(e) and 'correoFuncionario' in str(e):
                log_message(f"  ⚠️  Correo duplicado para {rut}: {correo}")
            else:
                log_message(f"  ❌ Error con {rut}: {e}")
            estadisticas['errores'] += 1
    
    # 2. DESACTIVAR los que NO están en Excel
    ruts_para_desactivar = ruts_bd - ruts_excel
    if ruts_para_desactivar:
        placeholders = ','.join(['%s'] * len(ruts_para_desactivar))
        cursor.execute(f"""
            UPDATE funcionario
            SET activoFuncionario = 0
            WHERE rutFuncionario IN ({placeholders})
            AND activoFuncionario = 1
        """, list(ruts_para_desactivar))
        estadisticas['desactivados'] = cursor.rowcount
        for rut in ruts_para_desactivar:
            log_message(f"  🔴 Desactivado: {rut} (no en Excel)")
    
    # Guardar cambios
    try:
        conn.commit()
        log_message("✓ Cambios confirmados en BD")
    except Exception as e:
        log_message(f"❌ Error al guardar cambios: {e}")
        conn.rollback()
        estadisticas['errores'] += 1
    
    # Mostrar resumen
    log_message("\n📊 ═══════════════════════════════════")
    log_message(f"  Insertados:  {estadisticas['insertados']}")
    log_message(f"  Actualizados: {estadisticas['actualizados']}")
    log_message(f"  Desactivados: {estadisticas['desactivados']}")
    log_message(f"  Errores:     {estadisticas['errores']}")
    log_message("═══════════════════════════════════\n")
    
    # Cerrar conexión
    cursor.close()
    conn.close()
    
    log_message(f"✅ Sincronización completada. Log guardado en: {LOG_FILE}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python sync_funcionarios_excel.py archivo.xlsx")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    sync_funcionarios(excel_file)
