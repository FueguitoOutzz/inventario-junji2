from db import mysql
cur = mysql.connection.cursor()
for t in ['modalidad','estado_equipo','tipo_adquisicion','marca_equipo','tipo_equipo']:
    cur.execute(f'SELECT * FROM {t} ORDER BY 1')
    print(t, cur.fetchall())
cur.execute('SELECT idMarcaTipo,idMarca_Equipo,idTipo_equipo FROM marca_tipo_equipo ORDER BY idMarcaTipo')
print('marca_tipo_equipo', cur.fetchall())
cur.close()
