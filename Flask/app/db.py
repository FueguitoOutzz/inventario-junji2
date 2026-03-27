from app import app
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from env_vars import cuentas
import os
import MySQLdb  # Importar para manejar errores específicos
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno (preferir /opt/inventario-junji/.env si existe)
env_path = Path("/opt/inventario-junji/.env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=False)
else:
    # Cargar .env desde la raíz del proyecto (dos niveles sobre /app o uno sobre /Flask)
    local_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if local_env_path.exists():
        load_dotenv(dotenv_path=local_env_path, override=True)
    else:
        load_dotenv()

# Configuramos la conexión a la base de datos usando variables de entorno
app.config['MYSQL_HOST'] = os.getenv('DB_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('DB_USER', 'junji')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('DB_NAME', 'inventariofinal')
app.config['MYSQL_PORT'] = int(os.getenv('DB_PORT', '3306'))
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_AUTOCOMMIT'] = True
app.config['MYSQL_INIT_COMMAND'] = "SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED"
app.config['MYSQL_DATABASE_DEBUG'] = True  # Habilitar depuración para ver más detalles

mysql = MySQL(app)
bcrypt = Bcrypt(app)

# Manejo de errores explícitos en las funciones
def add_modelo_equipo():
    try:
        cur = mysql.connection.cursor()
        cur.execute("...")
        mysql.connection.commit()
    except MySQLdb.Error as e:
        print(f"Error MySQL: {e.args[0]}, {e.args[1]}")  # Código y descripción del error
        raise
    except Exception as e:
        print(f"Error general: {e}")
        raise
