from db import mysql
cur = mysql.connection.cursor()
cur.execute('DESCRIBE funcionario')
rows = cur.fetchall()
cur.close()
from pathlib import Path
Path('funcionario_schema.txt').write_text('\n'.join(str(r) for r in rows))
print('done')
