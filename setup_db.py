#!/usr/bin/env python3
import pymysql
import sys

# Intentar conexión sin contraseña primero
credentials = [
    {'user': 'root', 'password': ''},
    {'user': 'root', 'password': 'Kiyopon10++'}, #local
    {'user': 'root', 'password': 'Tijunji2017'},
    {'user': 'mariadb', 'password': ''},
    {'user': 'root', 'password': 'root'},
]

for cred in credentials:
    try:
        conn = pymysql.connect(
            host='localhost',
            user=cred['user'],
            password=cred['password']
        )
        cursor = conn.cursor()
        print(f"✓ Conexión exitosa con {cred['user']}")
        
        # Crear base de datos
        cursor.execute('CREATE DATABASE IF NOT EXISTS inventariofinal DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci')
        print("✓ Base de datos 'inventariofinal' creada")
        
        # Crear usuario junji si no existe
        cursor.execute("CREATE USER IF NOT EXISTS 'junji'@'localhost' IDENTIFIED BY 'Tijunji2017'")
        print("✓ Usuario 'junji' creado")
        
        # Dar permisos
        cursor.execute("GRANT ALL PRIVILEGES ON inventariofinal.* TO 'junji'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")
        print("✓ Permisos otorgados")
        
        cursor.close()
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"✗ Error con {cred['user']}: {e}")
        continue

print("No se pudo conectar con ninguna credencial")
sys.exit(1)
