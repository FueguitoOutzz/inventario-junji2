from db import mysql

# Seed reference catalogs with canonical IDs expected by the app
conn = mysql.connection
cur = conn.cursor()

modalidad = [
    (1, 'CLASICO'),
    (2, 'ALTERNATIVO'),
    (3, 'OFICINA'),
    (4, 'PMI'),
    (5, 'CECI'),
]

estado = [
    (1, 'SIN ASIGNAR'),
    (2, 'En Uso'),
    (3, 'Siniestro'),
    (4, 'Baja'),
    (5, 'Mantencion'),
]

tipo_adq = [
    (1, 'COMPRA'),
    (2, 'ARRIENDO'),
    (3, 'PRESTAMO'),
    (4, 'COMODATTO'),
]

marca = [
    (1, 'LG'),
    (2, 'Samsung'),
    (3, 'VIEWSONIC'),
    (4, 'EPSON'),
    (5, 'CANON'),
    (6, 'HP'),
    (7, 'TOSHIBA'),
    (8, 'LENOVO'),
    (9, 'PHILCO'),
]

tipo_equipo = [
    (1, 'COMPUTADORES DE ESCRITORIO Y AIO'),
    (2, 'NOTEBOOK'),
    (3, 'IMPRESORA'),
    (4, 'ESCANER'),
    (5, 'PLOTTER'),
    (6, 'PROYECTOR'),
    (7, 'MONITOR'),
]

marca_tipo = [
    (8, 1), (8, 2), (6, 2), (7, 2), (4, 3), (6, 3), (5, 3),
    (6, 4), (6, 5), (5, 5), (4, 6), (1, 6), (3, 6), (9, 6),
    (2, 7), (1, 7),
]

for table, data, cols in [
    ('modalidad', modalidad, 'idModalidad,nombreModalidad'),
    ('estado_equipo', estado, 'idEstado_equipo,nombreEstado_equipo'),
    ('tipo_adquisicion', tipo_adq, 'idTipo_adquisicion,nombre_tipo_adquisicion'),
    ('marca_equipo', marca, 'idMarca_Equipo,nombreMarcaEquipo'),
    ('tipo_equipo', tipo_equipo, 'idTipo_equipo,nombreTipo_equipo'),
]:
    id_col, name_col = cols.split(',')
    cur.executemany(
        f"INSERT INTO {table} ({id_col},{name_col}) VALUES (%s,%s) "
        f"ON DUPLICATE KEY UPDATE {name_col}=VALUES({name_col})",
        data,
    )

cur.executemany(
    "INSERT IGNORE INTO marca_tipo_equipo (idMarca_Equipo,idTipo_equipo) VALUES (%s,%s)",
    marca_tipo,
)

conn.commit()
cur.close()
print('catalogs seeded')
