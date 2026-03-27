#!/usr/bin/env python3
"""
Script para crear un usuario admin en la BD
"""
import pymysql
from flask_bcrypt import Bcrypt

# Configuración
HOST = 'localhost'
USER = 'junji'
PASSWORD = 'Tijunji2017'
DATABASE = 'inventariofinal'

# Crear instancia de bcrypt
bcrypt = Bcrypt()

# Credenciales del nuevo admin
ADMIN_USER = 'admin'
ADMIN_PASS = '1234'
ADMIN_PRIV = 1  # 1 = administrador

try:
    # Conectar a la BD
    conn = pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    
    # Verificar si el usuario ya existe
    cursor.execute("SELECT * FROM usuario WHERE nombreUsuario = %s", (ADMIN_USER,))
    if cursor.fetchone():
        print(f"⚠️  El usuario '{ADMIN_USER}' ya existe en la BD")
        cursor.close()
        conn.close()
        exit(0)
    
    # Hashear la contraseña
    hashed_password = bcrypt.generate_password_hash(ADMIN_PASS).decode('utf-8')
    
    # Insertar el nuevo usuario
    cursor.execute(
        """
        INSERT INTO usuario 
        (nombreUsuario, contrasennaUsuario, privilegiosAdministrador) 
        VALUES (%s, %s, %s)
        """,
        (ADMIN_USER, hashed_password, ADMIN_PRIV)
    )
    conn.commit()
    
    print(f"✓ Usuario '{ADMIN_USER}' creado exitosamente")
    print(f"  Contraseña: {ADMIN_PASS}")
    print(f"  Privilegios: Administrador")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
