from flask import Blueprint, request, render_template, flash, url_for, redirect, session, jsonify, send_file, current_app
from db import mysql
from cuentas import loguear_requerido, administrador_requerido
from cerberus import Validator
from MySQLdb import IntegrityError
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from io import BytesIO
import re
import csv
import io
import json
from datetime import datetime

MOTIVOS_INACTIVIDAD_BASE = [
    "DESPIDO",
    "RENUNCIA",
    "INJUSTIFICADO",
    "NO_EN_EXCEL",
    "OTRO",
]
MOTIVOS_INACTIVIDAD = set(MOTIVOS_INACTIVIDAD_BASE) | {"REACTIVADO"}
MOTIVOS_INACTIVIDAD_ID = {
    "DESPIDO": 1,
    "RENUNCIA": 2,
    "INJUSTIFICADO": 3,
    "NO_EN_EXCEL": 4,
    "OTRO": 5,
}

funcionario = Blueprint('funcionario', __name__, template_folder='app/templates')

# Asegura que la conexión a MySQL esté viva antes de abrir cursores
def _get_cursor():
    conn = mysql.connection
    try:
        conn.ping(reconnect=True)
    except Exception:
        # Si falla el ping, dejar que flask-mysqldb reprovisione en el siguiente cursor
        pass
    return conn.cursor()

def _col_exists(table, column):
    cur = _get_cursor()
    try:
        cur.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND column_name = %s
            LIMIT 1
        """, (table, column))
        return cur.fetchone() is not None
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _table_exists(table):
    cur = _get_cursor()
    try:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = %s
            LIMIT 1
            """,
            (table,),
        )
        return cur.fetchone() is not None
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _activo_column():
    for col in ("activoFuncionario", "activo"):
        if _col_exists("funcionario", col):
            return col
    return None


def _inactividad_columns():
    """Regresa las columnas de inactividad disponibles en funcionario."""
    return {
        "motivo_id": "motivo_inactividad_id" if _col_exists("funcionario", "motivo_inactividad_id") else None,
        "detalle": "detalle_inactividad" if _col_exists("funcionario", "detalle_inactividad") else None,
        "fecha": "fecha_inactividad" if _col_exists("funcionario", "fecha_inactividad") else None,
    }


def _motivo_label(nombre):
    labels = {
        "DESPIDO": "Despido",
        "RENUNCIA": "Renuncia",
        "INJUSTIFICADO": "Injustificado",
        "NO_EN_EXCEL": "No viene en Excel",
        "OTRO": "Otro",
    }
    nombre = (nombre or "").upper()
    return labels.get(nombre, nombre.replace("_", " ").title())


def _get_motivos_catalogo():
    if not _table_exists("motivo_inactividad"):
        return []
    cur = _get_cursor()
    try:
        cur.execute(
            """
            SELECT id, UPPER(nombre) AS nombre, activo
            FROM motivo_inactividad
            ORDER BY id
            """
        )
        rows = cur.fetchall()
        existentes = {row.get("nombre") for row in rows if row.get("nombre")}
        faltantes = [m for m in MOTIVOS_INACTIVIDAD_BASE if m not in existentes]
        if faltantes:
            cur.executemany(
                "INSERT INTO motivo_inactividad (nombre, activo) VALUES (%s, %s)",
                [(m, 1) for m in faltantes],
            )
            mysql.connection.commit()
            cur.execute(
                """
                SELECT id, UPPER(nombre) AS nombre, activo
                FROM motivo_inactividad
                ORDER BY id
                """
            )
            rows = cur.fetchall()
        motivos = []
        for row in rows:
            nombre = row.get("nombre") or ""
            motivos.append({
                "id": row.get("id"),
                "nombre": nombre,
                "label": _motivo_label(nombre),
            })
        return motivos
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _resolve_motivo_id(motivo_id_raw, motivo_nombre):
    motivos = _get_motivos_catalogo()
    if not motivos:
        return None, None
    if motivo_id_raw is not None:
        try:
            motivo_id_raw = int(motivo_id_raw)
        except (TypeError, ValueError):
            motivo_id_raw = None
    if motivo_id_raw is not None:
        for motivo in motivos:
            if motivo.get("id") == motivo_id_raw:
                return motivo_id_raw, motivo.get("nombre")
    if motivo_nombre:
        objetivo = str(motivo_nombre).upper()
        for motivo in motivos:
            if motivo.get("nombre") == objetivo:
                return motivo.get("id"), motivo.get("nombre")
    return None, None


def _motivo_valido(motivo):
    if not motivo:
        return False
    if str(motivo).upper() == "REACTIVADO":
        return True
    return _resolve_motivo_id(None, motivo)[0] is not None


def _registrar_inactividad(rut, motivo, detalle=None, fuente="manual", registrado_por=None):
    if not _motivo_valido(motivo):
        return
    if not _table_exists("funcionario_inactividad"):
        return
    cur = _get_cursor()
    try:
        cur.execute(
            """
            INSERT INTO funcionario_inactividad (
                rutFuncionario, motivo, detalle, fuente, registrado_por
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (rut, motivo, detalle if detalle else None, fuente, registrado_por),
        )
        mysql.connection.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _registrar_inactivacion_masiva(ruts, detalle, fuente, registrado_por=None):
    if not ruts:
        return 0
    count = 0
    for rut in ruts:
        _registrar_inactividad(rut, "NO_EN_EXCEL", detalle, fuente=fuente, registrado_por=registrado_por)
        count += 1
    return count


def _normalizar_rut(valor):
    if valor is None:
        return ""
    rut = str(valor).strip().upper().replace(" ", "").replace(".", "")
    if rut.endswith(".0"):
        rut = rut[:-2]
    if rut and "-" not in rut and len(rut) > 1:
        rut = f"{rut[:-1]}-{rut[-1]}"
    return rut


def _rut_key(valor):
    """Llave de comparación: solo dígitos y dv en minúscula, sin guion."""
    norm = _normalizar_rut(valor)
    return re.sub(r"[^0-9k]", "", norm.lower()) if norm else ""

# Esquemas de validación
schema_agregar_funcionario = {
    'rut_funcionario': {
        'type': 'string',
        'minlength': 7,
        'maxlength': 10,
        'regex': r'^\d{7,8}(-[0-9kK])?$',  # Aceptar formato 1234567-K o 12345678-9
    },
    'nombre_funcionario': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 100,
        'regex': r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s.\'\-]+$'  # Permitir letras, números, tildes, espacios, punto, guion y apóstrofe
    },
    'cargo_funcionario': {
        'type': 'string',
        'allowed': ['ADMINISTRATIVO', 'AUXILIAR', 'PROFESIONAL', 'TÉCNICO', 'DIRECTOR REGIONAL', 'ENCARGADA/O', 'REEMPLAZO', 'REMPLAZO', 'PRACTICANTE'],  # Valores permitidos
    },
    'codigo_Unidad': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 10
    },
    'correo_funcionario': {
        'type': 'string',
        'minlength': 5,
        'maxlength': 100,
        'regex': r'^[a-zA-Z0-9._%+-]+@(junji\.cl|junjired\.cl)$'  # Perm itir formato de correo electrónico
    },
    'activo': {
        'type': 'integer',
        'allowed': [0, 1],
        'nullable': True
    },
    'activoFuncionario': {
        'type': 'integer',
        'allowed': [0, 1],
        'nullable': True
    }
}

schema_editar_funcionario = schema_agregar_funcionario.copy()
schema_editar_funcionario['rut_actual'] = {
    'type': 'string',
    'minlength': 7,
    'maxlength': 10,
    'regex': r'^\d{7,8}(-[0-9kK])?$',
}
# Campos opcionales para gestionar inactividades
schema_editar_funcionario.update({
    'motivo_inactivo': {
        'type': 'string',
        'maxlength': 100,
        'nullable': True,
        'empty': True,
    },
    'detalle_inactivo': {
        'type': 'string',
        'maxlength': 255,
        'nullable': True,
        'empty': True,
    },
    'motivo_inactividad_id': {
        'type': 'integer',
        'nullable': True,
        'coerce': (lambda v: int(v) if str(v).strip() else None),
    },
})


# Vista principal de funcionario
@funcionario.route('/funcionario')
@loguear_requerido
def Funcionario():
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")

    page = request.args.get("page", default=1, type=int)
    per_page = 8
    offset = (page - 1) * per_page

    cur = _get_cursor()
    activo_col = _activo_column()
    inact_cols = _inactividad_columns()
    motivo_expr = f"f.{inact_cols['motivo_id']}" if inact_cols["motivo_id"] else "NULL"
    detalle_expr = f"f.{inact_cols['detalle']}" if inact_cols["detalle"] else "NULL"
    fecha_expr = f"f.{inact_cols['fecha']}" if inact_cols["fecha"] else "NULL"

    # Consulta que obtiene todos los funcionarios y cuenta las asignaciones activas (sin subconsulta por fila)
    base_query = """
    SELECT 
        f.rutFuncionario,
        f.nombreFuncionario,
        f.cargoFuncionario, 
        f.idUnidad,
        u.idUnidad,
        COALESCE(u.nombreUnidad, 'Sin unidad') AS nombreUnidad,
        f.correoFuncionario,
        {activo_col_expr} AS activo_estado,
        {motivo_expr} AS motivo_inactividad_id,
        {detalle_expr} AS detalle_inactividad,
        {fecha_expr} AS fecha_inactividad,
        COALESCE(ac.activos, 0) AS equipos_asignados
    FROM funcionario f
    LEFT JOIN unidad u ON f.idUnidad = u.idUnidad
    LEFT JOIN (
        SELECT a.rutFuncionario, COUNT(*) AS activos
        FROM asignacion a
        JOIN equipo_asignacion ea ON a.idAsignacion = ea.idAsignacion
        WHERE a.ActivoAsignacion = 1
        GROUP BY a.rutFuncionario
    ) ac ON ac.rutFuncionario = f.rutFuncionario
    """
    activo_col_expr = f"f.{activo_col}" if activo_col else "1"
    base_query = base_query.format(
        activo_col_expr=activo_col_expr,
        motivo_expr=motivo_expr,
        detalle_expr=detalle_expr,
        fecha_expr=fecha_expr,
    )
    order_clause = f" ORDER BY {activo_col_expr} DESC, f.nombreFuncionario ASC"
    paginacion = f" LIMIT %s OFFSET %s"
    cur.execute(base_query + order_clause + paginacion, (per_page, offset))
    data = cur.fetchall()

    cur.execute("SELECT * FROM unidad")
    ubi_data = cur.fetchall()

    if activo_col:
        cur.execute(
            f"""
            SELECT 
                COUNT(*) AS total,
                SUM({activo_col} = 1) AS activos,
                SUM({activo_col} = 0) AS inactivos
            FROM funcionario
            """
        )
        counts = cur.fetchone()
    else:
        cur.execute("SELECT COUNT(*) AS total FROM funcionario")
        total_only = cur.fetchone()["total"]
        counts = {"total": total_only, "activos": total_only, "inactivos": 0}

    total = counts.get("total") or 0
    total_pages = (total + per_page - 1) // per_page if total else 1
    total_activos = counts.get("activos") or 0
    total_inactivos = counts.get("inactivos") or 0
    cur.close()

    return render_template(
        'GestionR.H/funcionario.html', 
        funcionario=data, 
        Unidad=ubi_data,
        current_page=page,
        total_pages=total_pages,
        total_funcionarios=total,
        total_activos=total_activos,
        total_inactivos=total_inactivos,
        motivos_inactividad=_get_motivos_catalogo(),
    )


@funcionario.route('/funcionario/imprimir')
@loguear_requerido
def imprimir_funcionarios():
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")

    filtros = {
        "q": (request.args.get("q", "") or "").strip(),
        "unidad": (request.args.get("unidad", "") or "").strip(),
        "cargo": (request.args.get("cargo", "") or "").strip(),
    }

    # Sanitizar filtros para evitar caídas por datos inesperados
    allowed_cargos = set(schema_agregar_funcionario["cargo_funcionario"]["allowed"])
    unidad_val = filtros["unidad"] if filtros["unidad"].isdigit() else None
    cargo_val = filtros["cargo"].upper()
    if cargo_val and cargo_val not in allowed_cargos:
        cargo_val = None
    q_val = filtros["q"][:80]  # limitar longitud de búsqueda

    base_query = """
        SELECT 
            f.rutFuncionario,
            f.nombreFuncionario,
            f.cargoFuncionario,
            f.correoFuncionario,
            f.idUnidad,
            u.nombreUnidad
        FROM funcionario f
        LEFT JOIN unidad u ON f.idUnidad = u.idUnidad
    """

    condiciones = []
    params = []

    activo_col = _activo_column()
    if activo_col:
        condiciones.append(f"f.{activo_col} = 1")

    if unidad_val:
        condiciones.append("u.idUnidad = %s")
        params.append(unidad_val)

    if cargo_val:
        condiciones.append("UPPER(f.cargoFuncionario) = %s")
        params.append(cargo_val)

    if q_val:
        term = f"%{q_val.lower()}%"
        condiciones.append(
            "(LOWER(f.nombreFuncionario) LIKE %s OR LOWER(f.rutFuncionario) LIKE %s OR "
            "LOWER(f.correoFuncionario) LIKE %s OR LOWER(u.nombreUnidad) LIKE %s OR LOWER(f.cargoFuncionario) LIKE %s)"
        )
        params.extend([term, term, term, term, term])

    if condiciones:
        base_query += " WHERE " + " AND ".join(condiciones)

    base_query += " ORDER BY f.nombreFuncionario ASC"

    cur = _get_cursor()
    try:
        cur.execute(base_query, params)
        funcionarios = cur.fetchall()
    except Exception as e:
        current_app.logger.exception("Error al imprimir funcionarios con filtros")
        flash(f"No se pudo generar la impresión: {str(e)}", "danger")
        return redirect(url_for('funcionario.Funcionario'))
    finally:
        try:
            cur.close()
        except Exception:
            pass

    return render_template(
        'GestionR.H/print_funcionario.html',
        funcionarios=funcionarios,
        filtros=filtros
    )


#agregar funcionario
@funcionario.route('/add_funcionario', methods=['POST'])
@administrador_requerido
def add_funcionario():
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")
    
    if request.method == 'POST':
        activo_col = _activo_column()
        raw_activo = request.form.get(activo_col, '1') if activo_col else None
        try:
            activo_val = int(raw_activo) if raw_activo not in (None, "") else 1
        except (ValueError, TypeError):
            activo_val = 1

        data = {
            'rut_funcionario': request.form.get('rut_funcionario', '').strip(),
            'nombre_funcionario': request.form.get('nombre_funcionario', '').strip(),
            'cargo_funcionario': request.form.get('cargo_funcionario', '').strip(),
            'codigo_Unidad': request.form.get('codigo_Unidad', '').strip(),
            'correo_funcionario': request.form.get('correo_funcionario', '').strip(),
            'activoFuncionario': activo_val if activo_col == 'activoFuncionario' else None,
            'activo': activo_val if activo_col == 'activo' else None
        }
        if data['cargo_funcionario']:
            data['cargo_funcionario'] = data['cargo_funcionario'].upper()

        v = Validator(schema_agregar_funcionario)
        if not v.validate(data):
            errores = v.errors  # Diccionario con los errores específicos por campo
            for campo, mensaje in errores.items():
                if "min length is 7" in mensaje:
                    flash("Error: El RUT debe contener 7 u 8 dígitos", 'warning')
                else:
                    flash(f"Error en '{campo}': {mensaje[0]}", 'warning')
            return redirect(url_for('funcionario.Funcionario'))
        
        try:
            # Insertar datos en la base de datos
            cur = _get_cursor()
            if activo_col:
                cur.execute(
                    f"""
                            INSERT INTO funcionario 
                            (rutFuncionario, nombreFuncionario, 
                            cargoFuncionario, idUnidad, correoFuncionario, {activo_col}) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                    (data['rut_funcionario'], data['nombre_funcionario'], data['cargo_funcionario'], data['codigo_Unidad'], data['correo_funcionario'], activo_val),
                )
            else:
                cur.execute(
                    """
                            INSERT INTO funcionario 
                            (rutFuncionario, nombreFuncionario, 
                            cargoFuncionario, idUnidad, correoFuncionario) 
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                    (data['rut_funcionario'], data['nombre_funcionario'], data['cargo_funcionario'], data['codigo_Unidad'], data['correo_funcionario']),
                )
            mysql.connection.commit()
            flash('Funcionario agregado correctamente', "success")
            return redirect(url_for('funcionario.Funcionario'))
        
        except IntegrityError as e:
            error_message = str(e)
            if "Duplicate entry" in error_message:
                if "PRIMARY" in error_message:
                    flash("Error: El RUT ya está registrado", 'warning')
                elif "correoFuncionario" in error_message:
                    flash("Error: El correo electrónico ya está registrado", 'warning')
                else:
                    flash("Error de duplicación en la base de datos", 'warning')
            else:
                flash("Error de integridad en la base de datos", 'danger')
            return redirect(url_for('funcionario.Funcionario'))
        
        except Exception as e:
            flash(f"Error al crear el funcionario: {str(e)}", 'danger')
            return redirect(url_for('funcionario.Funcionario'))

# Editar funcionario
@funcionario.route('/edit_funcionario', methods=['POST'])
@administrador_requerido
def edit_funcionario():
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")
    
    try:
        activo_col = _activo_column()
        inact_cols = _inactividad_columns()
        has_motivo_col = bool(inact_cols["motivo_id"])
        has_detalle_col = bool(inact_cols["detalle"])
        has_fecha_col = bool(inact_cols["fecha"])
        raw_activo = request.form.get(activo_col, None) if activo_col else None
        try:
            activo_val = int(raw_activo) if raw_activo not in (None, "") else 1
        except (ValueError, TypeError):
            activo_val = 1

        data = {
            'rut_actual': request.form.get('edit_rut_actual', '').strip(),
            'rut_funcionario': request.form.get('edit_rut_actual', '').strip(),
            'nombre_funcionario': request.form.get('nombre_funcionario', '').strip(),
            'correo_funcionario': request.form.get('correo_funcionario', '').strip(),
            'cargo_funcionario': request.form.get('cargo_funcionario', '').strip(),
            'codigo_Unidad': request.form.get('codigo_Unidad', '').strip(),
            'motivo_inactivo': request.form.get('motivo_inactivo', '').strip().upper(),
            'detalle_inactivo': request.form.get('detalle_inactivo', '').strip(),
            'motivo_inactividad_id': request.form.get('motivo_inactividad_id', '').strip(),
            'activoFuncionario': None,
            'activo': None,
        }
        if data['cargo_funcionario']:
            data['cargo_funcionario'] = data['cargo_funcionario'].upper()
        if activo_val is not None:
            try:
                activo_val = int(activo_val)
            except ValueError:
                activo_val = 1
        if activo_col and activo_val is None:
            activo_val = 1
        if activo_col == 'activoFuncionario':
            data['activoFuncionario'] = activo_val
        elif activo_col == 'activo':
            data['activo'] = activo_val

        motivo_inactividad_id = None
        if data['motivo_inactividad_id']:
            try:
                motivo_inactividad_id = int(data['motivo_inactividad_id'])
            except ValueError:
                motivo_inactividad_id = None
        motivo_inactividad_id, motivo_nombre = _resolve_motivo_id(
            motivo_inactividad_id,
            data['motivo_inactivo'],
        )
        if motivo_nombre:
            data['motivo_inactivo'] = motivo_nombre

        required_keys = ['rut_actual', 'rut_funcionario', 'nombre_funcionario', 'correo_funcionario', 'cargo_funcionario', 'codigo_Unidad']
        if any(not data[k] for k in required_keys):
            flash("Todos los campos son obligatorios", 'warning')
            return redirect(url_for('funcionario.Funcionario'))

        validator = Validator(schema_editar_funcionario)
        if not validator.validate(data):
            # Obtiene el primer campo con error y su mensaje
            campo, mensajes = next(iter(validator.errors.items()))
            flash(f"Error en {campo}: {mensajes[0]}", 'warning')  # Muestra solo el primer error
            return redirect(url_for('funcionario.Funcionario'))


        # Validación de motivo si se inactiva
        has_activo = bool(activo_col)
        if has_activo and has_motivo_col and activo_val == 0:
            if motivo_inactividad_id is None:
                flash("Debes seleccionar un motivo válido para marcar inactivo", 'warning')
                return redirect(url_for('funcionario.Funcionario'))

        # Actualizar el funcionario en la base de datos
        cur = _get_cursor()
        prev_estado = None
        prev_fecha_inactividad = None
        fecha_inactividad = None
        if has_activo:
            select_cols = [activo_col]
            if has_motivo_col:
                select_cols.append(inact_cols["motivo_id"])
            if has_fecha_col:
                select_cols.append(inact_cols["fecha"])
            cur.execute(
                f"SELECT {', '.join(select_cols)} FROM funcionario WHERE rutFuncionario = %s",
                (data['rut_actual'],),
            )
            row_prev = cur.fetchone()
            if row_prev is not None:
                if isinstance(row_prev, dict):
                    prev_estado = row_prev.get(activo_col)
                    if has_fecha_col:
                        prev_fecha_inactividad = row_prev.get(inact_cols["fecha"])
                else:
                    prev_estado = row_prev[0]
                    if has_fecha_col:
                        fecha_idx = select_cols.index(inact_cols["fecha"]) if inact_cols.get("fecha") in select_cols else None
                        if fecha_idx is not None and len(row_prev) > fecha_idx:
                            prev_fecha_inactividad = row_prev[fecha_idx]

        update_fields = [
            "rutFuncionario = %s",
            "nombreFuncionario = %s",
            "correoFuncionario = %s",
            "cargoFuncionario = %s",
            "idUnidad = %s",
        ]
        params = [
            data['rut_funcionario'],
            data['nombre_funcionario'],
            data['correo_funcionario'],
            data['cargo_funcionario'],
            data['codigo_Unidad'],
        ]

        if has_activo:
            update_fields.append(f"{activo_col} = %s")
            params.append(activo_val)

        if has_motivo_col:
            update_fields.append(f"{inact_cols['motivo_id']} = %s")
            params.append(motivo_inactividad_id if has_activo and activo_val == 0 else None)

        if has_detalle_col:
            update_fields.append(f"{inact_cols['detalle']} = %s")
            params.append(data['detalle_inactivo'] if has_activo and activo_val == 0 else None)

        if has_fecha_col:
            if has_activo and activo_val == 0:
                fecha_inactividad = prev_fecha_inactividad or datetime.now()
            else:
                fecha_inactividad = None
            update_fields.append(f"{inact_cols['fecha']} = %s")
            params.append(fecha_inactividad)

        params.append(data['rut_actual'])
        cur.execute(
            f"UPDATE funcionario SET {', '.join(update_fields)} WHERE rutFuncionario = %s",
            tuple(params),
        )
        mysql.connection.commit()
        cur.close()

        registrado_por = session.get("user")
        if isinstance(registrado_por, dict):
            registrado_por = (
                registrado_por.get("correo")
                or registrado_por.get("email")
                or registrado_por.get("username")
                or registrado_por.get("nombre")
            )
        if registrado_por is not None:
            registrado_por = str(registrado_por)

        pendientes_total = None
        if has_activo:
            if activo_val == 0 and prev_estado != 0:
                _registrar_inactividad(
                    data['rut_funcionario'],
                    data['motivo_inactivo'],
                    data['detalle_inactivo'] or None,
                    fuente="manual",
                    registrado_por=registrado_por,
                )
            if activo_val == 1 and prev_estado == 0:
                _registrar_inactividad(
                    data['rut_funcionario'],
                    "REACTIVADO",
                    data['detalle_inactivo'] or "Reactivado manual",
                    fuente="manual",
                    registrado_por=registrado_por,
                )
            # Calcular pendientes de devolución tras el cambio
            cur_count = _get_cursor()
            cur_count.execute(
                f"""
                SELECT COUNT(*) as total
                FROM funcionario f
                JOIN asignacion a ON a.rutFuncionario = f.rutFuncionario AND a.ActivoAsignacion = 1
                JOIN equipo_asignacion ea ON ea.idAsignacion = a.idAsignacion
                LEFT JOIN devolucion d ON d.idEquipoAsignacion = ea.idEquipoAsignacion
                WHERE f.{activo_col} = 0
                  AND d.idDevolucion IS NULL
                """
            )
            pendientes_total = cur_count.fetchone()["total"]
            cur_count.close()

        flash("Funcionario editado exitosamente", 'success')
        return redirect(url_for('funcionario.Funcionario'))

    except Exception as e:
        flash(f"Error al editar el funcionario: {str(e)}", 'danger')
        return redirect(url_for('funcionario.Funcionario'))

#eliminar registro segun id
@funcionario.route('/delete_funcionario/<id>', methods = ['POST', 'GET'])
@administrador_requerido
def delete_funcionario(id):
    try:
        cur = _get_cursor()
        # Evitar eliminar funcionarios con asignaciones asociadas
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM asignacion
            WHERE rutFuncionario = %s
        """, (id,))
        asignaciones_count = cur.fetchone()["count"]
        if asignaciones_count:
            flash("No se puede eliminar el funcionario: tiene asignaciones registradas.", 'warning')
            return redirect(url_for('funcionario.Funcionario'))

        activo_col = _activo_column()
        if activo_col:
            cur.execute(
                f"""
                UPDATE funcionario
                SET {activo_col} = 0
                WHERE rutFuncionario = %s
            """,
                (id,),
            )
        else:
            cur.execute('DELETE FROM funcionario WHERE rutFuncionario = %s', (id,))
        mysql.connection.commit()
        flash('Funcionario eliminado correctamente', 'success')
        return redirect(url_for('funcionario.Funcionario'))
    except Exception as e:
        flash(e.args[1], 'warning')
        return redirect(url_for('funcionario.Funcionario'))

@funcionario.route("/funcionario/buscar_funcionario/<id>")
@loguear_requerido
def buscar_funcionario(id):
    cur = _get_cursor()
    cur.execute("""
    SELECT * 
    FROM (
        SELECT f.rutFuncionario, f.nombreFuncionario, f.cargoFuncionario, 
            f.idUnidad, u.idUnidad, u.nombreUnidad, f.correoFuncionario
        FROM funcionario f
        INNER JOIN unidad u on f.idUnidad = u.idUnidad
        WHERE f.rutFuncionario = %s
        UNION ALL
        SELECT f.rutFuncionario, f.nombreFuncionario, f.cargoFuncionario, 
            f.idUnidad, u.idUnidad, u.nombreUnidad, f.correoFuncionario
        FROM funcionario f
        INNER JOIN unidad u on f.idUnidad = u.idUnidad
        WHERE f.correoFuncionario = %s)
    """, (id, id))
    funcionarios = cur.fetchall()

    cur.execute("""
    SELECT *
    FROM unidad u 
                """)
    unidades = cur.fetchall()
    return render_template(
        'GestionR.H/funcionario.html', 
        funcionario = funcionarios, 
        Unidad = unidades, 
        page=1, lastpage=True
        )

@funcionario.route('/buscar_funcionarios', methods=['GET'])
@loguear_requerido
def buscar_funcionarios():
    query = request.args.get("q", "").lower()
    estado_filtro = request.args.get("estado", "todos")  # todos, activos, inactivos
    page = request.args.get("page", default=1, type=int)
    per_page = 8

    offset = (page - 1) * per_page
    cur = _get_cursor()
    activo_col = _activo_column()
    inact_cols = _inactividad_columns()
    motivo_expr = f"f.{inact_cols['motivo_id']}" if inact_cols["motivo_id"] else "NULL"
    detalle_expr = f"f.{inact_cols['detalle']}" if inact_cols["detalle"] else "NULL"
    fecha_expr = f"f.{inact_cols['fecha']}" if inact_cols["fecha"] else "NULL"

    estado_clause = ""
    if activo_col:
        if estado_filtro == "activos":
            estado_clause = f" AND f.{activo_col} = 1"
        elif estado_filtro == "inactivos":
            estado_clause = f" AND f.{activo_col} = 0"

    activo_expr = f"f.{activo_col}" if activo_col else "1"

    cur.execute(f"""
        SELECT 
            f.rutFuncionario,
            f.nombreFuncionario,
            f.cargoFuncionario, 
            f.idUnidad,
            COALESCE(u.nombreUnidad, 'Sin unidad') AS nombreUnidad,
            f.correoFuncionario,
            {activo_expr} AS activo_estado,
            {motivo_expr} AS motivo_inactividad_id,
            {detalle_expr} AS detalle_inactividad,
            {fecha_expr} AS fecha_inactividad,
            COALESCE((SELECT COUNT(*)
                        FROM asignacion a
                        JOIN equipo_asignacion ea ON a.idAsignacion = ea.idAsignacion
                        WHERE a.rutFuncionario = f.rutFuncionario
                        AND a.ActivoAsignacion = 1), 0) AS equipos_asignados
        FROM funcionario f
        LEFT JOIN unidad u ON f.idUnidad = u.idUnidad
        WHERE (LOWER(f.rutFuncionario) LIKE %s
           OR LOWER(f.nombreFuncionario) LIKE %s
           OR LOWER(f.cargoFuncionario) LIKE %s
           OR LOWER(u.nombreUnidad) LIKE %s
           OR LOWER(f.correoFuncionario) LIKE %s)
        {estado_clause}
        ORDER BY {activo_expr} DESC, f.nombreFuncionario ASC
        LIMIT %s OFFSET %s
    """, (f"%{query}%",)*5 + (per_page, offset))
    funcionarios = cur.fetchall()

    cur.execute(f"""
        SELECT COUNT(*) as total
        FROM funcionario f
        JOIN unidad u ON f.idUnidad = u.idUnidad
        WHERE (LOWER(f.rutFuncionario) LIKE %s
           OR LOWER(f.nombreFuncionario) LIKE %s
           OR LOWER(f.cargoFuncionario) LIKE %s
           OR LOWER(u.nombreUnidad) LIKE %s
           OR LOWER(f.correoFuncionario) LIKE %s)
          {estado_clause}
    """, (f"%{query}%",)*5)
    total = cur.fetchone()["total"]
    total_pages = (total + per_page - 1) // per_page

    visible_pages = []
    if total_pages <= 7:
        visible_pages = list(range(1, total_pages + 1))
    else:
        if page > 4:
            visible_pages.append(1)
            if page > 5:
                visible_pages.append("...")
        visible_pages.extend(range(max(1, page - 2), min(total_pages + 1, page + 3)))
        if page < total_pages - 3:
            if page < total_pages - 4:
                visible_pages.append("...")
            visible_pages.append(total_pages)

    return jsonify({
        "funcionarios": funcionarios,
        "total": total,
        "total_pages": total_pages,
        "current_page": page,
        "visible_pages": visible_pages
    })


# 🎯 NUEVO: Cambiar estado activo/inactivo
@funcionario.route('/funcionario/cambiar_estado/<rut>', methods=['POST'])
@administrador_requerido
def cambiar_estado_funcionario(rut):
    """Cambia el estado activo/inactivo de un funcionario (AJAX)"""
    if "user" not in session:
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        nuevo_estado = request.json.get('activoFuncionario')
        motivo = request.json.get('motivo') if request.json else None
        detalle = request.json.get('detalle', '').strip() if request.json else ""
        motivo_id = None
        if nuevo_estado not in [0, 1]:
            return jsonify({"error": "Estado inválido"}), 400
        if nuevo_estado == 0 and (not motivo or not _motivo_valido(motivo)):
            return jsonify({"error": "Debes indicar un motivo de inactividad"}), 400
        if nuevo_estado == 1:
            motivo = "REACTIVADO"
            detalle = detalle or "Reactivado manual"
        else:
            motivo_id, motivo_nombre = _resolve_motivo_id(None, motivo)
            if motivo_id is None:
                return jsonify({"error": "Motivo de inactividad inválido"}), 400
            motivo = motivo_nombre
        registrado_por = session.get("user")
        if isinstance(registrado_por, dict):
            registrado_por = (
                registrado_por.get("correo")
                or registrado_por.get("email")
                or registrado_por.get("username")
                or registrado_por.get("nombre")
            )
        if registrado_por is not None:
            registrado_por = str(registrado_por)
        
        cur = _get_cursor()
        inact_cols = _inactividad_columns()
        motivo_col = inact_cols["motivo_id"]
        detalle_col = inact_cols["detalle"]
        fecha_col = inact_cols["fecha"]
        
        # Verificar que la columna existe
        activo_col = _activo_column()
        if not activo_col:
            return jsonify({"error": "Columna de estado no existe"}), 400
        
        # Actualizar estado
        fecha_inactividad = datetime.now() if nuevo_estado == 0 else None
        update_fields = [f"{activo_col} = %s"]
        params = [nuevo_estado]
        if motivo_col:
            update_fields.append(f"{motivo_col} = %s")
            params.append(motivo_id if nuevo_estado == 0 else None)
        if detalle_col:
            update_fields.append(f"{detalle_col} = %s")
            params.append(detalle if nuevo_estado == 0 else None)
        if fecha_col:
            update_fields.append(f"{fecha_col} = %s")
            params.append(fecha_inactividad)
        params.append(rut)
        cur.execute(
            f"UPDATE funcionario SET {', '.join(update_fields)} WHERE rutFuncionario = %s",
            tuple(params),
        )
        
        mysql.connection.commit()
        cur.close()
        _registrar_inactividad(rut, motivo, detalle, fuente="manual", registrado_por=registrado_por)
        
        estado_texto = "ACTIVO ✓" if nuevo_estado == 1 else "INACTIVO ✗"

        cur_count = _get_cursor()
        cur_count.execute(
            f"""
            SELECT COUNT(*) as total
            FROM funcionario f
            JOIN asignacion a ON a.rutFuncionario = f.rutFuncionario AND a.ActivoAsignacion = 1
            JOIN equipo_asignacion ea ON ea.idAsignacion = a.idAsignacion
            LEFT JOIN devolucion d ON d.idEquipoAsignacion = ea.idEquipoAsignacion
            WHERE f.{activo_col} = 0
              AND d.idDevolucion IS NULL
            """
        )
        pendientes_total = cur_count.fetchone()["total"]
        cur_count.close()
        
        return jsonify({
            "success": True,
            "rut": rut,
            "activoFuncionario": nuevo_estado,
            "estado": estado_texto,
            "motivo": motivo,
            "motivo_inactividad_id": motivo_id,
            "detalle": detalle,
            "message": f"Funcionario marcado como {estado_texto}",
            "pendientes_total": pendientes_total,
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@funcionario.route('/funcionario/estado', methods=['GET'])
@loguear_requerido
def ver_estado_funcionarios():
    """Vista para ver y cambiar estado de funcionarios activos/inactivos"""
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")
    
    cur = _get_cursor()
    
    # Verificar que la columna existe
    activo_col = _activo_column()
    if not activo_col:
        flash("La columna de estado activo no existe en la BD", 'warning')
        return redirect(url_for('funcionario.Funcionario'))
    
    # Obtener filtro
    filtro = request.args.get('filtro', 'todos')  # todos, activos, inactivos
    
    query = f"""
        SELECT 
            f.rutFuncionario,
            f.nombreFuncionario,
            f.cargoFuncionario,
            f.idUnidad,
            u.nombreUnidad,
            f.{activo_col},
            CASE WHEN f.{activo_col}=1 THEN '✓ ACTIVO' ELSE '✗ INACTIVO' END as estado
        FROM funcionario f
        JOIN unidad u ON f.idUnidad = u.idUnidad
    """
    
    if filtro == 'activos':
        query += f" WHERE f.{activo_col} = 1"
    elif filtro == 'inactivos':
        query += f" WHERE f.{activo_col} = 0"
    
    query += " ORDER BY f.nombreFuncionario ASC"
    
    cur.execute(query)
    funcionarios = cur.fetchall()
    cur.close()
    
    # Contar totales
    cur = _get_cursor()
    cur.execute(f"SELECT COUNT(*) FROM funcionario WHERE {activo_col}=1")
    total_activos = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM funcionario WHERE {activo_col}=0")
    total_inactivos = cur.fetchone()[0]
    cur.close()

    motivos_inactivos = {}
    if _table_exists("funcionario_inactividad"):
        cur = _get_cursor()
        cur.execute(
            """
            SELECT fi.rutFuncionario, fi.motivo, fi.detalle, fi.creado_en
            FROM funcionario_inactividad fi
            JOIN (
                SELECT rutFuncionario, MAX(creado_en) AS max_fecha
                FROM funcionario_inactividad
                GROUP BY rutFuncionario
            ) ult ON ult.rutFuncionario = fi.rutFuncionario AND ult.max_fecha = fi.creado_en
            """
        )
        for row in cur.fetchall():
            motivos_inactivos[row["rutFuncionario"]] = row
        cur.close()
    
    return render_template(
        'GestionR.H/estado_funcionarios.html',
        funcionarios=funcionarios,
        total_activos=total_activos,
        total_inactivos=total_inactivos,
        filtro=filtro,
        motivos_inactivos=motivos_inactivos,
        motivos_inactividad=_get_motivos_catalogo(),
    )
    @funcionario.route('/funcionario/estado', methods=['GET'])
    def ver_estado_funcionarios():
        return redirect(url_for('funcionario.Funcionario'))


@funcionario.route('/funcionario/exportar_excel')
@loguear_requerido
def exportar_funcionarios_excel():
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")

    ruts_param = request.args.get("ruts", "")
    ruts_lista = [rut.strip() for rut in ruts_param.split(",") if rut.strip()]

    cur = _get_cursor()
    activo_col = _activo_column()

    base_query = [
        "SELECT",
        "    f.rutFuncionario,",
        "    f.nombreFuncionario,",
        "    f.cargoFuncionario,",
        "    u.nombreUnidad,",
        "    f.correoFuncionario",
        "FROM funcionario f",
        "JOIN unidad u ON f.idUnidad = u.idUnidad",
    ]

    filters = []
    params = []
    if activo_col:
        filters.append(f"f.{activo_col} = 1")
    if ruts_lista:
        placeholders = ",".join(["%s"] * len(ruts_lista))
        filters.append(f"f.rutFuncionario IN ({placeholders})")
        params.extend(ruts_lista)

    if filters:
        base_query.append("WHERE " + " AND ".join(filters))

    base_query.append("ORDER BY f.nombreFuncionario")

    query = "\n".join(base_query)
    cur.execute(query, params)
    funcionarios = cur.fetchall()

    if not funcionarios:
        flash("No hay funcionarios para exportar", "warning")
        return redirect(request.referrer or url_for('funcionario.Funcionario'))

    wb = Workbook()
    ws = wb.active
    ws.title = "Funcionarios"

    headers = ["RUT", "Nombre", "Cargo", "Unidad", "Correo"]
    for idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=idx, value=header)
        cell.fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
        ws.column_dimensions[cell.column_letter].width = 25

    for row_idx, fun in enumerate(funcionarios, start=2):
        ws.cell(row=row_idx, column=1, value=fun.get("rutFuncionario"))
        ws.cell(row=row_idx, column=2, value=fun.get("nombreFuncionario"))
        ws.cell(row=row_idx, column=3, value=fun.get("cargoFuncionario"))
        ws.cell(row=row_idx, column=4, value=fun.get("nombreUnidad"))
        ws.cell(row=row_idx, column=5, value=fun.get("correoFuncionario"))

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="funcionarios.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@funcionario.route('/funcionario/importar_excel', methods=['POST'])
@administrador_requerido
def importar_funcionarios_excel():
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")

    file = request.files.get('file')
    if not file or not file.filename:
        flash("Debes seleccionar un archivo .xlsx o .csv", "warning")
        return redirect(request.referrer or url_for('funcionario.Funcionario'))

    filename = (file.filename or "").lower()
    is_csv = filename.endswith(".csv")
    is_excel = filename.endswith(".xlsx") or filename.endswith(".xls")
    if not (is_csv or is_excel):
        flash("Tipo de archivo no soportado. Usa .xlsx o .csv", "warning")
        return redirect(request.referrer or url_for('funcionario.Funcionario'))

    data = file.read()
    if not data:
        flash("El archivo está vacío.", "warning")
        return redirect(request.referrer or url_for('funcionario.Funcionario'))

    try:
        if is_csv:
            text = None
            for encoding in ("utf-8-sig", "latin-1"):
                try:
                    text = data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    text = None
            if text is None:
                raise ValueError("No se pudo decodificar el CSV.")
            sample = text[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample)
                delimiter = dialect.delimiter
            except Exception:
                delimiter = ";" if ";" in sample and "," not in sample else ","
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
            if not rows:
                flash("El archivo CSV está vacío.", "warning")
                return redirect(request.referrer or url_for('funcionario.Funcionario'))
            headers = [re.sub(r"[\s_]+", "", (str(cell or '')).strip().lower()) for cell in rows[0]]
            rows_iter = rows[1:]
        else:
            wb = load_workbook(filename=BytesIO(data), data_only=True)
            ws = wb["Funcionarios"] if "Funcionarios" in wb.sheetnames else wb.active
            try:
                headers = [re.sub(r"[\s_]+", "", (cell.value or '').strip().lower()) for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            except StopIteration:
                flash("El Excel está vacío.", "warning")
                return redirect(request.referrer or url_for('funcionario.Funcionario'))
            rows_iter = ws.iter_rows(min_row=2, values_only=True)
    except Exception as e:
        flash(f"No se pudo leer el archivo: {str(e)}", "danger")
        return redirect(request.referrer or url_for('funcionario.Funcionario'))

    def _col_idx(keys):
        keys_norm = {re.sub(r"[\s_]+", "", k.lower()) for k in keys}
        for idx, header in enumerate(headers):
            if header in keys_norm:
                return idx
        return None

    idx_rut = _col_idx({"rut", "rut_funcionario", "rutfuncionario, idUnidad"})
    idx_nombre = _col_idx({"nombre", "nombre_funcionario", "nombrefuncionario", "nombre completo"})
    idx_cargo = _col_idx({"cargo", "cargo_funcionario", "cargofuncionario"})
    idx_unidad = _col_idx({"idunidad", "unidad", "codigo_unidad"})
    idx_correo = _col_idx({"correo", "correo_funcionario", "correofuncionario", "email"})
    idx_activo = _col_idx({"activo", "activo_funcionario", "activofuncionario"})

    if idx_rut is None or idx_nombre is None or idx_unidad is None:
        flash("El archivo debe tener columnas de RUT, Nombre y Unidad", "warning")
        return redirect(request.referrer or url_for('funcionario.Funcionario'))

    inserted = 0
    reactivated = 0  # cuenta reactivaciones desde activo=0 a activo=1
    updated = 0
    deactivated = 0
    duplicate_ruts = []
    updated_existing = []  # list of (rut, nombre)
    skipped_exist = 0
    skipped_invalid = 0
    reasons = {
        "faltan_datos": 0,
        "unidad_no_encontrada": 0,
        "excepcion": 0,
    }

    cur = _get_cursor()
    activo_col = _activo_column()

    def _resolver_unidad(valor):
        if valor is None:
            return None
        val_str = str(valor).strip()
        if not val_str:
            return None
        try:
            try:
                val_num = int(float(val_str))
            except (TypeError, ValueError):
                val_num = int(val_str)
            cur.execute("SELECT idUnidad FROM unidad WHERE idUnidad = %s", (val_num,))
            row = cur.fetchone()
            if row:
                return row.get("idUnidad") if isinstance(row, dict) else row[0]
        except Exception:
            pass
        cur.execute("SELECT idUnidad FROM unidad WHERE LOWER(nombreUnidad) = %s", (val_str.lower(),))
        row = cur.fetchone()
        if row:
            return row.get("idUnidad") if isinstance(row, dict) else row[0]
        val_norm = re.sub(r"\s+", "", val_str.lower())
        cur.execute(
            "SELECT idUnidad FROM unidad WHERE REPLACE(LOWER(nombreUnidad), ' ', '') = %s LIMIT 1",
            (val_norm,),
        )
        row = cur.fetchone()
        if row:
            return row.get("idUnidad") if isinstance(row, dict) else row[0]
        return None

    try:
        def _row_get(row, idx):
            if idx is None:
                return None
            if idx >= len(row):
                return None
            return row[idx]

        ruts_excel = set()
        ruts_excel_keys = set()
        for row in rows_iter:
            rut_cell = _row_get(row, idx_rut)
            nombre_cell = _row_get(row, idx_nombre)
            cargo_cell = _row_get(row, idx_cargo)
            unidad_raw = _row_get(row, idx_unidad)
            correo_cell = _row_get(row, idx_correo)

            rut = _normalizar_rut(rut_cell)
            rut_plain = rut.replace("-", "") if rut else ""
            nombre = str(nombre_cell).strip() if nombre_cell is not None else ""
            cargo_val = str(cargo_cell).strip() if cargo_cell is not None else ""
            correo = str(correo_cell).strip() if correo_cell is not None else ""

            # Registrar presencia del RUT apenas lo tenemos para evitar desactivaciones falsas
            if rut:
                ruts_excel.add(rut)
            rut_key = _rut_key(rut)
            if rut_key:
                ruts_excel_keys.add(rut_key)

            if not rut or not nombre or unidad_raw is None:
                reasons["faltan_datos"] += 1
                skipped_invalid += 1
                continue

            cargo = cargo_val.upper() if cargo_val else None

            # Resolver unidad. Si no se encuentra, probar con la parte numérica del RUT (caso jardines rut=idUnidad)
            id_unidad = _resolver_unidad(unidad_raw)
            if not id_unidad and rut_plain:
                try:
                    rut_num = int(rut_plain)
                    cur.execute("SELECT idUnidad FROM unidad WHERE idUnidad = %s", (rut_num,))
                    row_un = cur.fetchone()
                    if row_un:
                        id_unidad = row_un.get("idUnidad") if isinstance(row_un, dict) else row_un[0]
                    else:
                        # Si el RUT es igual al idUnidad (caso jardín), úsalo como fallback
                        id_unidad = rut_num
                except Exception:
                    pass
            if not id_unidad:
                reasons["unidad_no_encontrada"] += 1
                skipped_invalid += 1
                continue

            activo_val = 1
            activo_cell = _row_get(row, idx_activo)
            if idx_activo is not None and activo_cell is not None:
                try:
                    activo_val = 1 if int(activo_cell) not in (0, False) else 0
                except Exception:
                    activo_val = 1

            try:
                # Traer estado actual para decidir si es reactivación
                # Considerar variantes con y sin guion por posibles formatos en BD
                rut_candidates = [rut]
                if rut_plain and rut_plain != rut:
                    rut_candidates.append(rut_plain)

                existe = None
                rut_en_bd = rut
                for rut_cand in rut_candidates:
                    if activo_col:
                        cur.execute(f"SELECT {activo_col} FROM funcionario WHERE REPLACE(rutFuncionario, '-', '') = REPLACE(%s, '-', '')", (rut_cand,))
                    else:
                        cur.execute("SELECT 1 FROM funcionario WHERE REPLACE(rutFuncionario, '-', '') = REPLACE(%s, '-', '')", (rut_cand,))
                    existe = cur.fetchone()
                    if existe:
                        rut_en_bd = rut_cand
                        break

                if existe:
                    prev_activo = None
                    if activo_col:
                        prev_activo = existe.get(activo_col) if isinstance(existe, dict) else existe[0]

                    # Si estaba inactivo y ahora queda activo, trátalo como reactivado (no mostrar "ya existía")
                    es_reactivacion = activo_col and prev_activo == 0 and activo_val == 1

                    if activo_col:
                        cur.execute(
                            f"""
                            UPDATE funcionario
                            SET nombreFuncionario = %s,
                                cargoFuncionario = %s,
                                idUnidad = %s,
                                correoFuncionario = %s,
                                {activo_col} = %s
                            WHERE REPLACE(rutFuncionario, '-', '') = REPLACE(%s, '-', '')
                            """,
                            (nombre, cargo, id_unidad, correo, activo_val, rut_en_bd),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE funcionario
                            SET nombreFuncionario = %s,
                                cargoFuncionario = %s,
                                idUnidad = %s,
                                correoFuncionario = %s
                            WHERE REPLACE(rutFuncionario, '-', '') = REPLACE(%s, '-', '')
                            """,
                            (nombre, cargo, id_unidad, correo, rut_en_bd),
                        )

                    if es_reactivacion:
                        reactivated += 1
                    else:
                        updated_existing.append((rut, nombre))
                        updated += 1
                else:
                    if activo_col:
                        cur.execute(
                            f"""
                            INSERT INTO funcionario (rutFuncionario, nombreFuncionario, cargoFuncionario, idUnidad, correoFuncionario, {activo_col})
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (rut, nombre, cargo, id_unidad, correo, activo_val),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO funcionario (rutFuncionario, nombreFuncionario, cargoFuncionario, idUnidad, correoFuncionario)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (rut, nombre, cargo, id_unidad, correo),
                        )
                    inserted += 1
            except IntegrityError:
                skipped_exist += 1
                duplicate_ruts.append((rut, nombre))
            except Exception as e:
                skipped_invalid += 1
                reasons["excepcion"] += 1
                current_app.logger.error("[importar_funcionarios_excel] error en fila rut=%s: %s", rut, e)

        registrado_por = session.get("user")
        if isinstance(registrado_por, dict):
            registrado_por = (
                registrado_por.get("correo")
                or registrado_por.get("email")
                or registrado_por.get("username")
                or registrado_por.get("nombre")
            )
        if registrado_por is not None:
            registrado_por = str(registrado_por)

        total_validos = inserted + updated + reactivated + skipped_exist
        # Desactivar funcionarios que NO aparecen en el Excel
        # (EXCEPTO jardines: rut numérico == idUnidad => siempre activos)
        if activo_col and ruts_excel_keys and total_validos > 0:

            # 1) Forzar que los jardines siempre queden activos (y limpiar motivo/detalle/fecha si aplica)
            inact_cols_j = _inactividad_columns()
            jardines_set_fields = [f"{activo_col} = 1"]
            if inact_cols_j.get("motivo_id"):
                jardines_set_fields.append(f"{inact_cols_j['motivo_id']} = NULL")
            if inact_cols_j.get("detalle"):
                jardines_set_fields.append(f"{inact_cols_j['detalle']} = NULL")
            if inact_cols_j.get("fecha"):
                jardines_set_fields.append(f"{inact_cols_j['fecha']} = NULL")

            cur.execute(
                f"""
                UPDATE funcionario
                SET {', '.join(jardines_set_fields)}
                WHERE REPLACE(rutFuncionario, '-', '') REGEXP '^[0-9]+$'
                  AND CAST(REPLACE(rutFuncionario, '-', '') AS UNSIGNED) = idUnidad
                """
            )

            # 2) Traer funcionarios activos y construir mapa rut_key -> rut_db
            #    Además, detectar cuáles son jardines para excluirlos de la desactivación.
            cur.execute(f"SELECT rutFuncionario, idUnidad FROM funcionario WHERE {activo_col} = 1")
            ruts_bd_activos_map = {}
            jardines_keys = set()

            for row in cur.fetchall():
                rut_db = row.get("rutFuncionario") if isinstance(row, dict) else row[0]
                id_un = row.get("idUnidad") if isinstance(row, dict) else row[1]

                key = _rut_key(rut_db)
                if key:
                    ruts_bd_activos_map[key] = rut_db

                    # Jardín: rut sin guion es numérico y coincide con idUnidad
                    rut_no_dash = str(rut_db or "").replace("-", "").strip()
                    try:
                        if rut_no_dash.isdigit() and id_un is not None and int(rut_no_dash) == int(id_un):
                            jardines_keys.add(key)
                    except Exception:
                        pass

            ruts_bd_keys = set(ruts_bd_activos_map.keys())
            interseccion = ruts_bd_keys & ruts_excel_keys

            # Candidatos a desactivar = activos en BD - presentes en Excel - jardines
            ruts_para_desactivar_keys = (ruts_bd_keys - ruts_excel_keys) - jardines_keys

            # Salvaguarda: si no hay ninguna intersección, asumimos problema de mapeo y no desactivamos
            if not interseccion:
                current_app.logger.warning(
                    "[importar_funcionarios_excel] sin interseccion de RUTs (bd=%s, excel=%s). Se omite desactivacion masiva",
                    len(ruts_bd_keys),
                    len(ruts_excel_keys),
                )
                ruts_para_desactivar_keys = set()

            if ruts_para_desactivar_keys:
                inact_cols = _inactividad_columns()
                motivo_id, _ = _resolve_motivo_id(None, "NO_EN_EXCEL")
                detalle = f"No está en Excel ({filename})"
                update_fields = [f"{activo_col} = 0"]
                params = []

                if inact_cols["motivo_id"] and motivo_id is not None:
                    update_fields.append(f"{inact_cols['motivo_id']} = %s")
                    params.append(motivo_id)
                if inact_cols["detalle"]:
                    update_fields.append(f"{inact_cols['detalle']} = %s")
                    params.append(detalle)
                if inact_cols["fecha"]:
                    update_fields.append(f"{inact_cols['fecha']} = %s")
                    params.append(datetime.now())

                ruts_para_desactivar = [ruts_bd_activos_map[k] for k in ruts_para_desactivar_keys]
                placeholders = ",".join(["%s"] * len(ruts_para_desactivar))
                params.extend(ruts_para_desactivar)

                cur.execute(
                    f"UPDATE funcionario SET {', '.join(update_fields)} WHERE rutFuncionario IN ({placeholders})",
                    tuple(params),
                )
                deactivated = cur.rowcount
                _registrar_inactivacion_masiva(ruts_para_desactivar, detalle, fuente="excel", registrado_por=registrado_por)

        elif activo_col and not ruts_excel:
            current_app.logger.warning("[importar_funcionarios_excel] No se encontraron filas válidas; se omite desactivación masiva.")


        mysql.connection.commit()
        cur.close()

        current_app.logger.info(
            "[importar_funcionarios_excel] resumen inserted=%s updated=%s reactivated=%s deactivated=%s skipped_exist=%s skipped_invalid=%s detalle=%s",
            inserted, updated, reactivated, deactivated, skipped_exist, skipped_invalid, reasons,
        )

        total_nuevos = inserted + reactivated

        existentes = duplicate_ruts + updated_existing
        if existentes:
            # Dedup por rut, conservar primer nombre disponible
            seen = {}
            for rut, nom in existentes:
                if rut not in seen:
                    seen[rut] = nom
            items = [f"{seen[r]} ({r})" if seen[r] else r for r in sorted(seen.keys())]
            nombres_text = ", ".join(items)
            flash(f"Importación finalizada: {total_nuevos} nuevos. Ya existían: {nombres_text}", "info")
        else:
            # Si solo reactivamos, muéstralo como agregado exitosamente
            if reactivated and not inserted:
                flash("Usuario agregado exitosamente", "success")
            else:
                flash(f"Importación exitosa: {total_nuevos} nuevos", "success")

        if deactivated:
            flash(f"Funcionarios desactivados por NO_EN_EXCEL: {deactivated}", "warning")
        if skipped_invalid or skipped_exist:
            detalle_omitidos = []
            if skipped_invalid:
                detalle_omitidos.append(
                    f"inválidos={skipped_invalid} (faltan_datos={reasons.get('faltan_datos')}, "
                    f"unidad_no_encontrada={reasons.get('unidad_no_encontrada')}, "
                    f"excepcion={reasons.get('excepcion')})"
                )
            if skipped_exist:
                detalle_omitidos.append(f"duplicados={skipped_exist}")
            flash(
                f"Registros omitidos: {', '.join(detalle_omitidos)}",
                "info",
            )
        return redirect(request.referrer or url_for('funcionario.Funcionario'))

    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        flash(f"Error al importar el Excel: {e}", "danger")
        return redirect(request.referrer or url_for('funcionario.Funcionario'))
