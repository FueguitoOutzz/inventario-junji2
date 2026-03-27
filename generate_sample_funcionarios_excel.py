#!/usr/bin/env python3
"""
Script para generar un Excel de EJEMPLO con algunos funcionarios.
Usa este archivo como referencia para crear tu propio Excel.

Uso: python generate_sample_funcionarios_excel.py
"""

import pandas as pd
from datetime import datetime

# Datos de ejemplo basados en los que ya existen en BD
data = {
    'rutFuncionario': [
        '10299816-2',
        '17170031-0',
        '9180661-4',
        '13389399-7',
        '13724610-4',
        '11677615-4',
        '9942546-6',
        '8690330-K',
        '9863060-0',
        '16899081-2',
    ],
    'nombreFuncionario': [
        'MARIELA YOLANDA ORTEGA',
        'CYNTHIA DEL CAR ARAYA',
        'HECTOR ALEJANDR PEREZ',
        'SILVANA MARIA E GUTIERREZ',
        'MACARENA ELIZAB GARCIA',
        'PAOLA JACQUELIN GUERRERO',
        'PATRICIA IVONNE OYARCE',
        'ELIZABETH LUZ D IRIBARREN',
        'RUTH SOFANIA LILLO',
        'FERNANDA VALERI MATUS DE LA PAR',
    ],
    'cargoFuncionario': [
        'PROFESIONAL',
        'PROFESIONAL',
        'PROFESIONAL',
        'PROFESIONAL',
        'PROFESIONAL',
        'ADMINISTRATIVO',
        'PROFESIONAL',
        'PROFESIONAL',
        'PROFESIONAL',
        'PROFESIONAL',
    ],
    'correoFuncionario': [
        'MORTEGA@JUNJI.CL',
        'CARAYA@JUNJI.CL',
        'HPEREZ@JUNJI.CL',
        'SMGUTIERREZ@JUNJI.CL',
        'MGARCIAA@JUNJI.CL',
        'PGUERRERO@JUNJI.CL',
        'POYARCE@JUNJI.CL',
        'EIRIBARREN@JUNJI.CL',
        'RSLILLO@JUNJI.CL',
        'FMATUS@JUNJI.CL',
    ],
    'idUnidad': [
        8101098,
        8101098,
        8101098,
        8101098,
        8101098,
        8101098,
        8101098,
        8101098,
        8101098,
        8101098,
    ]
}

# Crear DataFrame
df = pd.DataFrame(data)

# Nombre del archivo
filename = f'FUNCIONARIOS_ACTIVOS_EJEMPLO_{datetime.now().strftime("%Y%m%d")}.xlsx'

# Guardar a Excel
df.to_excel(filename, index=False, engine='openpyxl')

print(f"✓ Excel creado: {filename}")
print(f"✓ Registros: {len(df)}")
print(f"\nPrimeras filas:")
print(df.head())
print(f"\n💡 Este es un EJEMPLO. Copia, modifica y usa para tu sincronización.")
print(f"   Comando: python sync_funcionarios_excel.py {filename}")
