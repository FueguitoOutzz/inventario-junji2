"""
Flask-MySQLdb compatible wrapper using PyMySQL.

Notas de compatibilidad:
- Habilitamos autocommit desde la configuración de Flask para evitar transacciones
    largas que dejen vistas obsoletas en la conexión reutilizada.
- Ejecutamos `ping(reconnect=True)` antes de entregar la conexión para mantenerla
    viva en despliegues largos.
"""
import pymysql
from pymysql.cursors import DictCursor

class FlaskMySQLConnection:
    """Wrapper around pymysql connection to mimic Flask-MySQLdb"""
    def __init__(self, connection):
        self._connection = connection
    
    def cursor(self, cursorclass=None):
        """Return a cursor object"""
        # Always return DictCursor for compatibility with Flask-MySQLdb
        return self._connection.cursor(DictCursor)

    def ensure_autocommit(self, autocommit: bool):
        """Make sure the wrapped connection matches desired autocommit state."""
        try:
            if hasattr(self._connection, "get_autocommit"):
                if self._connection.get_autocommit() != autocommit:
                    self._connection.autocommit(autocommit)
        except Exception:
            # Si algo falla, se dejará al siguiente `ping` forzar una reconexión.
            pass

    def ping(self, reconnect: bool = True):
        """Proxy ping to keep the connection alive."""
        return self._connection.ping(reconnect=reconnect)
    
    def commit(self):
        self._connection.commit()
    
    def rollback(self):
        self._connection.rollback()
    
    def close(self):
        self._connection.close()
    
    @property
    def open(self):
        return self._connection.open if hasattr(self._connection, 'open') else True

class MySQL:
    def __init__(self, app=None):
        self.app = app
    
    def init_app(self, app):
        self.app = app
    
    @property
    def connection(self):
        """Get a fresh database connection.

        Nota: anteriormente se cacheaba la conexión en self._connection. Eso generaba
        que varias solicitudes concurrentes compartieran la misma conexión de PyMySQL,
        lo que provoca `pymysql.err.InterfaceError: (0, '')` cuando un hilo la cierra
        o la deja en estado inválido. Para evitarlo, se devuelve una conexión nueva
        en cada acceso y se deja que el GC la cierre cuando el cursor se cierra.
        """
        try:
            conn = self._create_connection()
            # Asegura que el autocommit siga la config actual.
            desired_autocommit = self.app.config.get("MYSQL_AUTOCOMMIT", True)
            conn.ensure_autocommit(desired_autocommit)
            return conn
        except Exception:
            # Si algo falla, intenta recrear una vez más antes de propagar
            conn = self._create_connection()
            desired_autocommit = self.app.config.get("MYSQL_AUTOCOMMIT", True)
            conn.ensure_autocommit(desired_autocommit)
            return conn
    
    def _create_connection(self):
        """Create a new database connection"""
        autocommit = self.app.config.get('MYSQL_AUTOCOMMIT', True)
        init_cmd = self.app.config.get('MYSQL_INIT_COMMAND')
        pymysql_conn = pymysql.connect(
            host=self.app.config.get('MYSQL_HOST', 'localhost'),
            user=self.app.config.get('MYSQL_USER') or 'junji',
            password=self.app.config.get('MYSQL_PASSWORD', ''),
            database=self.app.config.get('MYSQL_DB') or 'inventariofinal',
            port=self.app.config.get('MYSQL_PORT', 3306),
            charset=self.app.config.get('MYSQL_CHARSET', 'utf8mb4'),
            cursorclass=DictCursor,
            autocommit=autocommit,
            init_command=init_cmd,
            read_timeout=int(self.app.config.get('MYSQL_READ_TIMEOUT', 10)),
            write_timeout=int(self.app.config.get('MYSQL_WRITE_TIMEOUT', 10)),
        )
        wrapper = FlaskMySQLConnection(pymysql_conn)
        wrapper.ensure_autocommit(autocommit)
        return wrapper

# Alias MySQLdb module for error handling
import sys
sys.modules['MySQLdb'] = pymysql
sys.modules['MySQLdb.Error'] = pymysql.Error
