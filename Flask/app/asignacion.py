from email.mime.application import MIMEApplication
from flask import Blueprint, render_template, request, url_for, redirect, flash, send_file, session, jsonify, current_app, abort
from db import mysql
from fpdf import FPDF
from funciones import getPerPage
import os
import shutil
from werkzeug.utils import secure_filename
from datetime import date, datetime
from cuentas import loguear_requerido, administrador_requerido
from traslado import crear_traslado_generico
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
import fitz
from env_vars import paths, inLinux
from cerberus import Validator
from MySQLdb import IntegrityError, OperationalError
from pathlib import Path

schema_asignacion = {
    'fecha_asignacion': {
        'type': 'string',
        'regex': r'^\d{4}-\d{2}-\d{2}$',  # Formato YYYY-MM-DD
        'required': True,
    },
    'rut_funcionario': {
        'type': 'string',
        'minlength': 6,
        'maxlength': 10,
        'regex': r'^\d{7,8}(-[0-9Kk])?$',
        'required': True,
    },
    'observacion': {
        'type': 'string',
        'minlength': 0,
        'maxlength': 250,
    },
    'equipos_asignados': {
        'type': 'list',
        'minlength': 1,  # Al menos un equipo debe ser seleccionado
        'schema': {'type': 'integer'},  # Los valores deben ser enteros
        'required': True,
    }
}

asignacion = Blueprint("asignacion", __name__, template_folder="app/templates")

# Rutas base para PDFs generados y PDFs cargados por usuarios
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_ROOT = BASE_DIR / "pdf" / "uploads"
FIRMAS_ASIGNACIONES_DIR = UPLOAD_ROOT / "firmas_asignaciones"
FIRMAS_DEVOLUCIONES_DIR = UPLOAD_ROOT / "firmas_devoluciones"
GENERATED_ASIGNACIONES_DIR = BASE_DIR / "pdf" / "asignaciones"
GENERATED_DEVOLUCIONES_DIR = BASE_DIR / "pdf" / "devoluciones"
ACTAS_FIRMADAS_DIR = UPLOAD_ROOT / "actas_firmadas"
LEGACY_FIRMAS_ASIGNACIONES_DIR = BASE_DIR / "pdf" / "firmas_asignaciones"

def _get_cursor():
    conn = mysql.connection
    try:
        conn.ping(reconnect=True)
    except Exception:
        pass
    return conn.cursor()


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_uploaded_pdf(file_storage, target_dir: Path, prefix: str) -> Path:
    _ensure_dir(target_dir)
    original_name = secure_filename(file_storage.filename) or "documento.pdf"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{prefix}_{timestamp}_{original_name}"
    file_path = target_dir / filename
    file_storage.save(file_path)
    return file_path


def _actas_dir_for_asignacion(id_asignacion: str) -> Path:
    return _ensure_dir(ACTAS_FIRMADAS_DIR / f"asignacion_{id_asignacion}")


def _sanitize_equipo_label(equipo_id: str = None, tipo_equipo: str = None) -> str:
    if equipo_id:
        return secure_filename(str(equipo_id)) or "equipo"
    if tipo_equipo:
        cleaned = secure_filename(tipo_equipo).replace("-", "_")
        return cleaned or "equipo"
    return "equipo"


def _save_acta_firmada(file_storage, id_asignacion: str, equipo_id: str = None, tipo_equipo: str = None) -> Path:
    target_dir = _actas_dir_for_asignacion(id_asignacion)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    equipo_label = _sanitize_equipo_label(equipo_id, tipo_equipo)
    base_name = f"acta_{id_asignacion}_{equipo_label}_{timestamp}.pdf"
    file_path = target_dir / base_name
    suffix = 1
    while file_path.exists():
        file_path = target_dir / f"acta_{id_asignacion}_{equipo_label}_{timestamp}_{suffix}.pdf"
        suffix += 1
    file_storage.save(file_path)
    return file_path


def _list_acta_paths(id_asignacion: str):
    paths = []
    actas_dir = ACTAS_FIRMADAS_DIR / f"asignacion_{id_asignacion}"
    if actas_dir.exists():
        paths.extend(sorted(actas_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True))

    legacy_pattern = f"asignacion_{id_asignacion}_*.pdf"
    for directory in (FIRMAS_ASIGNACIONES_DIR, LEGACY_FIRMAS_ASIGNACIONES_DIR):
        if directory.exists():
            paths.extend(sorted(directory.glob(legacy_pattern), key=lambda p: p.stat().st_mtime, reverse=True))

    unique = []
    seen = set()
    for p in paths:
        resolved = p.resolve()
        if resolved not in seen:
            unique.append(p)
            seen.add(resolved)
    return unique


def _parse_acta_filename(filename: str):
    parts = Path(filename).stem.split("_")
    if len(parts) >= 4 and parts[0].lower() == "acta":
        equipo_token = parts[2]
        timestamp = parts[3]
        return equipo_token, timestamp
    return None, None


def _list_actas_firmadas(id_asignacion: str):
    actas = []
    for path in _list_acta_paths(id_asignacion):
        equipo_token, _ = _parse_acta_filename(path.name)
        equipo_id = int(equipo_token) if equipo_token and equipo_token.isdigit() else None
        tipo_equipo = None if equipo_id is not None else (equipo_token or "")
        actas.append({
            "filename": path.name,
            "url": url_for("asignacion.descargar_acta_firmada", idAsignacion=id_asignacion, filename=path.name),
            "equipoId": equipo_id,
            "tipoEquipo": tipo_equipo,
            "uploadedAt": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        })
    return actas


def _latest_uploaded_file(directory: Path, pattern: str):
    if not directory.exists():
        return None
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _find_signed_asignacion(id_asignacion):
    # Prioridad: ruta guardada en BD -> último archivo cargado -> nombres legados -> PDF generado
    ruta_bd = None
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT rutaactaAsignacion FROM asignacion WHERE idAsignacion = %s", (id_asignacion,))
        row = cur.fetchone()
        if row and row.get("rutaactaAsignacion"):
            ruta_bd = Path(row["rutaactaAsignacion"]).expanduser()
    except Exception:
        ruta_bd = None
    finally:
        try:
            cur.close()
        except Exception:
            pass

    acta_paths = _list_acta_paths(str(id_asignacion))

    candidates = [
        ruta_bd,
        acta_paths[0] if acta_paths else None,
        _latest_uploaded_file(FIRMAS_ASIGNACIONES_DIR, f"asignacion_{id_asignacion}_*.pdf"),
        BASE_DIR / "pdf" / "firmas_asignaciones" / f"asignacion_{id_asignacion}_firmado.pdf",
        GENERATED_ASIGNACIONES_DIR / f"asignacion_{id_asignacion}.pdf",
    ]

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _find_signed_devolucion(id_devolucion):
    ruta_bd = None
    cur = None
    try:
        if _col_exists("devolucion", "rutaactaDevolucion"):
            cur = mysql.connection.cursor()
            cur.execute("SELECT rutaactaDevolucion FROM devolucion WHERE idDevolucion = %s", (id_devolucion,))
            row = cur.fetchone()
            if row and row.get("rutaactaDevolucion"):
                ruta_bd = Path(row["rutaactaDevolucion"]).expanduser()
    except Exception:
        ruta_bd = None
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass

    candidates = [
        ruta_bd,
        _latest_uploaded_file(FIRMAS_DEVOLUCIONES_DIR, f"devolucion_{id_devolucion}_*.pdf"),
        BASE_DIR / "pdf" / "firmas_devoluciones" / f"devolucion_{id_devolucion}_firmado.pdf",
        GENERATED_DEVOLUCIONES_DIR / f"devolucion_{id_devolucion}.pdf",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _funcionario_activo_col():
    if _col_exists("funcionario", "activoFuncionario"):
        return "activoFuncionario"
    if _col_exists("funcionario", "activo"):
        return "activo"
    return None


def _devolucion_ids_for_asignacion(id_asignacion):
    cur = _get_cursor()
    try:
        cur.execute(
            """
            SELECT d.idDevolucion
            FROM devolucion d
            JOIN equipo_asignacion ea ON d.idEquipoAsignacion = ea.idEquipoAsignacion
            WHERE ea.idAsignacion = %s
            ORDER BY d.idDevolucion DESC
            """,
            (id_asignacion,),
        )
        rows = cur.fetchall()
        return [row["idDevolucion"] for row in rows]
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _find_pending_devolucion_firma(id_asignacion):
    return (
        _latest_uploaded_file(FIRMAS_DEVOLUCIONES_DIR, f"devolucion_asignacion_{id_asignacion}_*.pdf")
        or _latest_uploaded_file(FIRMAS_DEVOLUCIONES_DIR, f"devolucion_{id_asignacion}_*.pdf")
    )


def _copy_signed_devolucion_file(source_path: Path, id_devolucion: str) -> Path:
    _ensure_dir(FIRMAS_DEVOLUCIONES_DIR)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    dest = FIRMAS_DEVOLUCIONES_DIR / f"devolucion_{id_devolucion}_{timestamp}.pdf"
    shutil.copy2(source_path, dest)
    return dest


def _resolve_devolucion_id(id_value):
    try:
        id_int = int(id_value)
    except (TypeError, ValueError):
        return None
    cur = _get_cursor()
    try:
        cur.execute("SELECT idDevolucion FROM devolucion WHERE idDevolucion = %s", (id_int,))
        row = cur.fetchone()
        if row:
            return id_int
    finally:
        try:
            cur.close()
        except Exception:
            pass
    ids = _devolucion_ids_for_asignacion(id_int)
    return ids[0] if ids else None


def _col_exists(table, column):
    cur = _get_cursor()
    try:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND column_name = %s
            LIMIT 1
            """,
            (table, column),
        )
        return cur.fetchone() is not None
    finally:
        try:
            cur.close()
        except Exception:
            pass
@asignacion.route("/asignacion")
@asignacion.route("/asignacion/<int:page>")
@loguear_requerido
def Asignacion(page=1):
    perpage = getPerPage()
    offset = (page - 1) * perpage

    cur = mysql.connection.cursor()

    # Paginación de asignaciones
    cur.execute(f"""
    SELECT
        a.idAsignacion,
        a.fecha_inicioAsignacion,
        a.ObservacionAsignacion,
        a.ActivoAsignacion,
        COALESCE(f.rutFuncionario, a.rutFuncionario) AS rutFuncionario,
        COALESCE(f.nombreFuncionario, '') AS nombreFuncionario,
        COALESCE(f.cargoFuncionario, '') AS cargoFuncionario,
        ea.idEquipoAsignacion,
        e.idEquipo,
        d.idDevolucion,
        d.fechaDevolucion,
        me.nombreModeloequipo,
        te.nombreTipo_equipo,
        mae.nombreMarcaEquipo,
        e.Cod_inventarioEquipo,
        e.Num_serieEquipo,
        e.codigoproveedor_equipo,
        e.ObservacionEquipo
    FROM asignacion a
    LEFT JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
    JOIN equipo_asignacion ea ON a.idAsignacion = ea.idAsignacion
    LEFT JOIN devolucion d ON ea.idEquipoAsignacion = d.idEquipoAsignacion
    LEFT JOIN equipo e ON e.idEquipo = ea.idEquipo
    LEFT JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
    LEFT JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
    LEFT JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
    LEFT JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
    ORDER BY a.idAsignacion DESC, ea.idEquipoAsignacion DESC
    LIMIT %s OFFSET %s
    """, (perpage, offset))
    data = cur.fetchall()

    # Formatear fechas
    for row in data:
        row['fecha_inicio'] = row['fecha_inicioAsignacion'].strftime('%d-%m-%Y') if row['fecha_inicioAsignacion'] else 'N/A'
        row['fecha_devolucion'] = row['fechaDevolucion'].strftime('%d-%m-%Y') if row['fechaDevolucion'] else 'Sin devolver'

    # Total para paginación
    cur.execute("SELECT COUNT(*) AS total FROM asignacion")
    total = cur.fetchone()['total']
    lastpage = (total + perpage - 1) // perpage

    # Funcionarios (payload para autocompletado)
    activo_col = _funcionario_activo_col()
    filtros_func = ""
    if activo_col:
        filtros_func = f"""
        WHERE (
            f.{activo_col} = 1
            OR f.{activo_col} IS NULL
            OR (
                REPLACE(f.rutFuncionario, '-', '') REGEXP '^[0-9]+$'
                AND CAST(REPLACE(f.rutFuncionario, '-', '') AS UNSIGNED) = f.idUnidad
            )
        )
        """
    cur.execute(f"""
        SELECT
            COALESCE(f.rutFuncionario, '') AS rutFuncionario,
            COALESCE(f.nombreFuncionario, '') AS nombreFuncionario,
            COALESCE(f.cargoFuncionario, '') AS cargoFuncionario,
            COALESCE(f.correoFuncionario, '') AS correoFuncionario,
            COALESCE(f.idUnidad, '') AS idUnidad
        FROM funcionario f
        {filtros_func}
        ORDER BY f.nombreFuncionario
    """)
    funcionarios = cur.fetchall()

    # Equipos sin asignar
    cur.execute("""
        SELECT 
            e.idEquipo, e.Cod_inventarioEquipo, e.Num_serieEquipo,
            e.codigoproveedor_equipo, e.ObservacionEquipo,
            me.nombreModeloequipo, te.nombreTipo_equipo,
            mae.nombreMarcaEquipo, COALESCE(u.nombreUnidad, 'Sin unidad') AS nombreUnidad
        FROM equipo e
        LEFT JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
        LEFT JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        LEFT JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        LEFT JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
        LEFT JOIN estado_equipo ee ON e.idEstado_equipo = ee.idEstado_equipo
        LEFT JOIN unidad u ON e.idUnidad = u.idUnidad
        WHERE UPPER(TRIM(ee.nombreEstado_equipo)) = 'SIN ASIGNAR' OR ee.idEstado_equipo IS NULL
    """)
    equipos_sin_asignar = cur.fetchall()

    cur.close()

    funcionarios_json = [
        {
            "nombre": f.get("nombreFuncionario") or "",
            "rut": f.get("rutFuncionario") or "",
            "cargo": f.get("cargoFuncionario") or "",
            "correo": f.get("correoFuncionario") or "",
            "idUnidad": f.get("idUnidad") or "",
        }
        for f in funcionarios
    ]

    return render_template(
        'GestionR.H/asignacion.html',
        funcionarios=funcionarios,
        funcionarios_json=funcionarios_json,
        asignacion=data,
        equipos_sin_asignar=equipos_sin_asignar,
        page=page,
        lastpage=lastpage
    )


@asignacion.route("/asignacion/imprimir")
@loguear_requerido
def imprimir_asignaciones():
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")

    filtros = {
        "q": request.args.get("q", "").strip(),
        "funcionario": request.args.get("funcionario", "").strip(),
        "estado": request.args.get("estado", "").strip(),
        "fecha_inicio": request.args.get("fecha_inicio", "").strip(),
        "fecha_fin": request.args.get("fecha_fin", "").strip(),
    }

    cur = mysql.connection.cursor()

    query = """
    SELECT
        a.idAsignacion,
        a.fecha_inicioAsignacion,
        a.ObservacionAsignacion,
        a.ActivoAsignacion,
        f.rutFuncionario,
        f.nombreFuncionario,
        f.cargoFuncionario,
        ea.idEquipoAsignacion,
        d.idDevolucion,
        d.fechaDevolucion,
        me.nombreModeloequipo,
        te.nombreTipo_equipo,
        mae.nombreMarcaEquipo,
        e.Cod_inventarioEquipo,
        e.Num_serieEquipo,
        e.codigoproveedor_equipo,
        e.ObservacionEquipo
    FROM asignacion a
    JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
    JOIN equipo_asignacion ea ON a.idAsignacion = ea.idAsignacion
    LEFT JOIN devolucion d ON ea.idEquipoAsignacion = d.idEquipoAsignacion
    JOIN equipo e ON e.idEquipo = ea.idEquipo
    JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
    JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
    JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
    JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
    WHERE 1=1
    """

    condiciones = []
    params = []

    if filtros["funcionario"]:
        condiciones.append("a.rutFuncionario = %s")
        params.append(filtros["funcionario"])

    if filtros["estado"] == "devuelto":
        condiciones.append("d.fechaDevolucion IS NOT NULL")
    elif filtros["estado"] == "pendiente":
        condiciones.append("d.fechaDevolucion IS NULL")

    if filtros["fecha_inicio"]:
        condiciones.append("a.fecha_inicioAsignacion >= %s")
        params.append(filtros["fecha_inicio"])

    if filtros["fecha_fin"]:
        condiciones.append("a.fecha_inicioAsignacion <= %s")
        params.append(filtros["fecha_fin"])

    if filtros["q"]:
        term = f"%{filtros['q'].lower()}%"
        condiciones.append(
            "(LOWER(f.nombreFuncionario) LIKE %s OR LOWER(f.rutFuncionario) LIKE %s OR "
            "LOWER(te.nombreTipo_equipo) LIKE %s OR LOWER(me.nombreModeloequipo) LIKE %s OR "
            "LOWER(mae.nombreMarcaEquipo) LIKE %s)"
        )
        params.extend([term, term, term, term, term])

    if condiciones:
        query += " AND " + " AND ".join(condiciones)

    query += " ORDER BY a.idAsignacion ASC, ea.idEquipoAsignacion ASC"


    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()

    # Formatear fechas para impresión
    for row in data:
        row['fecha_inicio_formateada'] = row['fecha_inicioAsignacion'].strftime('%d-%m-%Y') if row['fecha_inicioAsignacion'] else 'N/A'
        row['fecha_devolucion_formateada'] = row['fechaDevolucion'].strftime('%d-%m-%Y') if row['fechaDevolucion'] else 'Sin devolver'

    return render_template(
        'GestionR.H/print_asignaciones.html',
        asignaciones=data,
        filtros=filtros
    )
def getPerPage():
    return 10 

@asignacion.route("/asignacion/validar_traslado", methods=["POST"])
@loguear_requerido
def validar_traslado():
    """
    Recibe rut_funcionario y equipos_asignados, retorna si se requiere traslado.
    """
    rut_funcionario = request.form.get('rut_funcionario')
    id_equipos = request.form.getlist('equiposAsignados[]')
    if not id_equipos:
        id_equipos = (
            request.form.getlist('equipoSeleccionado')
            or request.form.getlist('equiposSeleccionados')
        )
    if not rut_funcionario or not id_equipos:
        return jsonify({"requiere_traslado": False})

    cur = _get_cursor()
    try:
        cur.execute("SELECT idUnidad FROM funcionario WHERE rutFuncionario = %s", (rut_funcionario,))
        funcionario_data = cur.fetchone()
        id_unidad_funcionario = funcionario_data['idUnidad'] if funcionario_data else None

        requiere_traslado = False
        for id_equipo in id_equipos:
            try:
                id_equipo_int = int(id_equipo)
            except (TypeError, ValueError):
                continue
            cur.execute("SELECT idUnidad FROM equipo WHERE idEquipo = %s", (id_equipo_int,))
            equipo_data = cur.fetchone()
            id_unidad_origen = equipo_data['idUnidad'] if equipo_data else None
            if id_unidad_funcionario and id_unidad_origen and id_unidad_origen != id_unidad_funcionario:
                requiere_traslado = True
                break
        return jsonify({"requiere_traslado": requiere_traslado})
    except Exception as e:
        current_app.logger.error("[asignacion.validar_traslado] error=%s", e)
        return jsonify({"requiere_traslado": False})
    finally:
        try:
            cur.close()
        except Exception:
            pass

@asignacion.route("/asignacion/create_asignacion", methods=["POST"])
@administrador_requerido
def create_asignacion():
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")

    if request.method != "POST":
        return redirect(url_for("asignacion.Asignacion"))

    # Obtiene los datos del formulario
    fecha_asignacion = request.form.get('fecha-asignacion') 
    rut_funcionario = request.form.get('rut_funcionario')
    observacion = request.form.get('observacion')
    raw_equipos = request.form.getlist('equiposAsignados[]')
    if not raw_equipos:
        # Fallback si el JS no alcanzó a crear inputs ocultos
        raw_equipos = request.form.getlist('equipoSeleccionado') or request.form.getlist('equiposSeleccionados')
    id_equipos = []
    for equipo in raw_equipos:
        try:
            id_equipos.append(int(equipo))
        except (TypeError, ValueError):
            continue
    # evitar equipos duplicados en la misma solicitud
    id_equipos_original = list(id_equipos)
    id_equipos = list(dict.fromkeys(id_equipos))
    if len(id_equipos) < len(id_equipos_original):
        flash("Se detectaron equipos duplicados y fueron removidos de la asignación.", "warning")
    crear_traslado = request.form.get('crear_traslado', '1')  # Nuevo: por defecto sí

    # Se crea un objeto para poder validar los datos recibidos
    data = {
        'fecha_asignacion': fecha_asignacion,
        'rut_funcionario': rut_funcionario,
        'observacion': observacion,
        'equipos_asignados': id_equipos,
    }
    current_app.logger.info(
        "[asignacion.create] fecha=%s rut=%s equipos=%s",
        fecha_asignacion,
        rut_funcionario,
        id_equipos,
    )

    # Valida los campos y muestra solo el primer mensaje de error
    v = Validator(schema_asignacion)
    
    if not v.validate(data):
        for campo, mensaje in v.errors.items():
            flash(f"Error en '{campo}': {mensaje[0]}", 'warning')
            break
        return redirect(url_for("asignacion.Asignacion"))

    conn = mysql.connection
    try:
        conn.ping(reconnect=True)
    except Exception:
        pass
    cur = conn.cursor()
    id_asignacion = None
    try:
        # Validar que el funcionario exista y esté activo
        activo_col = _funcionario_activo_col()
        cols = "idUnidad"
        if activo_col:
            cols += f", {activo_col}"
        cur.execute(f"SELECT {cols} FROM funcionario WHERE rutFuncionario = %s", (rut_funcionario,))
        funcionario_data = cur.fetchone()
        if not funcionario_data:
            flash("Error: El funcionario seleccionado no existe.", "warning")
            return redirect(url_for("asignacion.Asignacion"))
        id_unidad_funcionario = funcionario_data['idUnidad']
        if activo_col and str(funcionario_data.get(activo_col)) == "0":
            flash("No se puede asignar equipos a un funcionario inactivo.", "warning")
            return redirect(url_for("asignacion.Asignacion"))

        # Validar estado de equipos y que no estén ya asignados
        cur.execute("""
            SELECT idEstado_equipo
            FROM estado_equipo
            WHERE UPPER(TRIM(nombreEstado_equipo)) = %s
            ORDER BY idEstado_equipo
            LIMIT 1
        """, ("EN USO",))
        estado_en_uso = cur.fetchone()
        if not estado_en_uso:
            flash("No se encontró el estado 'EN USO' en la configuración.", "danger")
            return redirect(url_for("asignacion.Asignacion"))
        id_estado_en_uso = estado_en_uso["idEstado_equipo"]

        if not id_equipos:
            flash("Debes asignar al menos un equipo.", "warning")
            return redirect(url_for("asignacion.Asignacion"))

        placeholders = ", ".join(["%s"] * len(id_equipos))

        # Cargar datos base de equipos (estado y unidad)
        cur.execute("""
            SELECT e.idEquipo, e.idUnidad, ee.nombreEstado_equipo
            FROM equipo e
            LEFT JOIN estado_equipo ee ON ee.idEstado_equipo = e.idEstado_equipo
            WHERE e.idEquipo IN (""" + placeholders + """)
        """, tuple(id_equipos))
        equipos_rows = cur.fetchall()
        equipos_map = {row["idEquipo"]: row for row in equipos_rows}
        if len(equipos_map) != len(id_equipos):
            faltantes = sorted(set(id_equipos) - set(equipos_map.keys()))
            flash(f"Equipos no encontrados: {', '.join(map(str, faltantes))}", "warning")
            return redirect(url_for("asignacion.Asignacion"))

        for id_equipo in id_equipos:
            row = equipos_map.get(id_equipo)
            nombre_estado = (row.get("nombreEstado_equipo") or "").strip().upper()
            if nombre_estado and nombre_estado != "SIN ASIGNAR":
                flash("Uno o más equipos ya están en uso o no están disponibles para asignar.", "warning")
                return redirect(url_for("asignacion.Asignacion"))

        # Verificar asignaciones activas en bloque
        cur.execute("""
            SELECT ea.idEquipo, COUNT(*) AS count
            FROM equipo_asignacion ea
            LEFT JOIN devolucion d ON d.idEquipoAsignacion = ea.idEquipoAsignacion
            LEFT JOIN asignacion a ON a.idAsignacion = ea.idAsignacion
            WHERE ea.idEquipo IN (""" + placeholders + """)
              AND a.ActivoAsignacion = 1
              AND d.idDevolucion IS NULL
            GROUP BY ea.idEquipo
        """, tuple(id_equipos))
        if cur.fetchall():
            flash("Uno o más equipos ya tienen una asignación activa.", "warning")
            return redirect(url_for("asignacion.Asignacion"))
        current_app.logger.info(
            "[asignacion.create] inicio transaccion equipos=%s funcionario=%s",
            id_equipos,
            rut_funcionario,
        )
        cur.execute("START TRANSACTION")

        # Insertar asignación
        cur.execute("""
            INSERT INTO asignacion (
                fecha_inicioAsignacion,
                ObservacionAsignacion,
                rutFuncionario,
                ActivoAsignacion
            )
            VALUES (%s, %s, %s, 1)
            """, (fecha_asignacion, observacion, rut_funcionario))
        id_asignacion = cur.lastrowid # Recupera el ID de la asignación recién insertada
        current_app.logger.info("[asignacion.create] insert asignacion id=%s", id_asignacion)

        # Inserta los datos en la tabla equipo_asignacion
        cur.executemany(
            "INSERT INTO equipo_asignacion (idAsignacion, idEquipo) VALUES (%s, %s)",
            [(id_asignacion, id_equipo) for id_equipo in id_equipos],
        )
        current_app.logger.info(
            "[asignacion.create] insert equipo_asignacion filas=%s id_asignacion=%s",
            len(id_equipos),
            id_asignacion,
        )

        # Cambia el estado del equipo a "EN USO"
        cur.execute(
            "UPDATE equipo SET idEstado_equipo = %s WHERE idEquipo IN (" + placeholders + ")",
            tuple([id_estado_en_uso] + id_equipos),
        )
        current_app.logger.info(
            "[asignacion.create] update estado equipos=%s estado=%s",
            id_equipos,
            id_estado_en_uso,
        )

        conn.commit()
        current_app.logger.info("[asignacion.create] commit ok id_asignacion=%s", id_asignacion)

        # Preparar traslados si aplica (agrupar por unidad de origen)
        equipos_por_origen = {}
        if crear_traslado == '1' and id_unidad_funcionario:
            for id_equipo in id_equipos:
                row = equipos_map.get(id_equipo)
                id_unidad_origen = row.get("idUnidad") if row else None
                if id_unidad_origen and id_unidad_origen != id_unidad_funcionario:
                    equipos_por_origen.setdefault(id_unidad_origen, []).append(id_equipo)

        # Seleccionar los equipos para el PDF en una sola consulta
        cur.execute("""
            SELECT e.*, 
                me.nombreModeloequipo, 
                te.nombreTipo_equipo, 
                mae.nombreMarcaEquipo, 
                ee.nombreEstado_equipo
            FROM equipo e
            INNER JOIN modelo_equipo me ON me.idModelo_Equipo = e.idModelo_Equipo
            INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
            INNER JOIN tipo_equipo te ON te.idTipo_equipo = mte.idTipo_equipo
            INNER JOIN marca_equipo mae ON mae.idMarca_Equipo = mte.idMarca_Equipo
            INNER JOIN estado_equipo ee ON ee.idEstado_equipo = e.idEstado_equipo
            WHERE e.idEquipo IN (""" + placeholders + """)
            ORDER BY e.idEquipo ASC
        """, tuple(id_equipos))
        TuplaEquipos = cur.fetchall()

        # Obtiene información relevante del funcionario para añadir al PDF
        cur.execute("""
            SELECT
                f.nombreFuncionario,
                a.idAsignacion,
                a.fecha_inicioAsignacion,
                u.nombreUnidad,
                u.idUnidad
            FROM funcionario f
            JOIN asignacion a ON f.rutFuncionario = a.rutFuncionario
            JOIN unidad u ON f.idUnidad = u.idUnidad
            WHERE a.idAsignacion = %s
        """, (id_asignacion,))
        query = cur.fetchone()

        funcionario = {
            "nombre": query["nombreFuncionario"],
            "id_asignacion": str(query["idAsignacion"]),
            "fecha_asignacion": str(query["fecha_inicioAsignacion"].strftime("%d-%m-%Y")),
            "unidad": query["nombreUnidad"],
            "idUnidad": query["idUnidad"],
            "observacion": observacion  # <-- Agrega esta línea
        }

        # Crear traslados después de la asignación (para no bloquear el commit principal)
        if equipos_por_origen:
            for origen, equipos in equipos_por_origen.items():
                try:
                    crear_traslado_generico(
                        fecha_asignacion,
                        id_unidad_funcionario,
                        origen,
                        equipos
                    )
                except Exception as e:
                    current_app.logger.error(
                        "[asignacion.create] traslado fallo origen=%s equipos=%s error=%s",
                        origen,
                        equipos,
                        e,
                    )
                    flash("Asignación creada, pero no se pudo generar el traslado para algunos equipos.", "warning")
    except IntegrityError as e:
        conn.rollback()
        current_app.logger.exception(
            "[asignacion.create] integrity error id_asignacion=%s error=%s",
            id_asignacion,
            e,
        )
        error_message = str(e)
        if "FOREIGN KEY (`rutFuncionario`) REFERENCES `funcionario` (`rutFuncionario`)" in error_message:
            flash("Error: No se selecciono funcionario Unidad", 'warning')
        return ("Error al crear la asignación (integridad de datos).", 500)

    except OperationalError as e:
        conn.rollback()
        current_app.logger.exception(
            "[asignacion.create] error operativo BD id_asignacion=%s error=%s",
            id_asignacion,
            e,
        )
        return ("Error de conexión con la base de datos. Intenta nuevamente.", 500)

    except Exception as e:
        conn.rollback()  # En caso de error, se revierten los cambios
        current_app.logger.exception(
            "[asignacion.create] error inesperado id_asignacion=%s",
            id_asignacion,
        )
        return ("Error al crear la asignación. Revisa los logs para más detalles.", 500)
    finally:
        try:
            cur.close()
        except Exception:
            pass

    flash("Asignación agregada exitosamente", 'success')

    try:
        # Intentamos crear el PDF, pero si falla, no bloqueamos la respuesta al usuario
        crear_pdf_asignacion(funcionario, TuplaEquipos)
    except Exception as e:
        # Logueamos el error para revisarlo después sin interrumpir el flujo
        current_app.logger.error(
            "[asignacion.create] error pdf asignacion id=%s error=%s",
            id_asignacion,
            e,
        )
        # Opcional: avisar que el PDF falló pero la asignación sí se guardó
        flash("La asignación se guardó, pero hubo un problema al generar el PDF.", "warning")
    
    # Esta línea DEBE ser la última y estar fuera del bloque try/except del PDF
    return redirect(url_for('asignacion.Asignacion'))

# enviar datos a vista editar
@asignacion.route("/asignacion/edit_asignacion/<id>", methods=["POST", "GET"])
@administrador_requerido
def edit_asignacion(id):
    try:
        cur = mysql.connection.cursor()
        #se obtiene la asignacion actual
        cur.execute(
            """ 
           SELECT  
                a.idAsignacion,
                a.fecha_inicioAsignacion,
                a.observacionAsignacion,
                a.rutaactaAsignacion,
                a.rutFuncionario,
                f.nombreFuncionario,
                d.fechaDevolucion
                FROM asignacion a
                INNER JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
                LEFT JOIN devolucion d ON a.idDevolucion = d.idDevolucion
            WHERE idAsignacion = %s""",
            (id,),
        )
        #esto para los select
        data = cur.fetchone()
        cur.execute("SELECT * FROM funcionario")
        f_data = cur.fetchall()
        #creo que el equipo se deberia porder borrar
        cur.execute("SELECT * FROM equipo")
        eq_data = cur.fetchall()
        #print(data)
        #print(data['observacionAsignacion'])
        return render_template(
            'GestionR.H/editAsignacion.html', 
            asignacion=data, 
            funcionario=f_data, 
            equipo=eq_data
        )
    except Exception as e:
        flash("Error al crear")
        #flash(e.args[1])
        return redirect(url_for("asignacion.Asignacion"))


# actualizar
@asignacion.route("/asignacion/update_asignacion/<id>", methods=["POST"])
@administrador_requerido
def update_asignacion(id):
    if request.method == "POST":
        #obtener informacion del formulario
        fechaasignacion = request.form["fechaasignacion"]
        observacionasignacion = request.form["observacionasignacion"]
        rutFuncionario = request.form["rutFuncionario"]
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                """
            UPDATE asignacion
            SET fecha_inicioAsignacion = %s,
                ObservacionAsignacion = %s,
                rutFuncionario = %s
            WHERE idAsignacion = %s
            """,
                (
                    fechaasignacion,
                    observacionasignacion,
                    rutFuncionario,
                    id,
                ),
            )
            mysql.connection.commit()
            flash("asignacion actualizado correctamente")
            return redirect(url_for("asignacion.Asignacion"))
        except Exception as e:

            flash("Error al crear")
            #flash(e.args[1])
            return redirect(url_for("asignacion.Asignacion"))


# eliminar
@asignacion.route("/delete_asignacion/<id>", methods=["POST", "GET"])
@administrador_requerido
def delete_asignacion(id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
                    SELECT *
                    FROM asignacion
                    WHERE idAsignacion = %s
                    """, (id,))
        asignacionAborrar = cur.fetchone()
        #encontrar todas las tablas equipo_asignacion que contengan la id de la asignacion
        cur.execute("""SELECT *
                        FROM equipo_asignacion
                        WHERE idAsignacion= %s
        """, (id,))
        asignaciones = cur.fetchall()
        #revisar cada equipo_asignacion individualmente
        for asignacion in asignaciones:
            idEquipo = asignacion['idEquipo']
            #encontrar la id del estado sin asignar
            cur.execute("""
                        SELECT *
                        FROM estado_equipo
                        WHERE UPPER(TRIM(nombreEstado_equipo)) = %s
                        """, ("SIN ASIGNAR",))
            estado_equipo_data = cur.fetchone()
            #cambiar el estado de cada equipo en la asignacion eliminada a sin asignar
            cur.execute("""
                        UPDATE equipo
                        SET idEstado_equipo = %s
                        WHERE idEquipo = %s
                        """, (estado_equipo_data['idEstado_equipo'], idEquipo))
            mysql.connection.commit()
        cur.execute("DELETE FROM equipo_asignacion WHERE idAsignacion = %s", (id,))
        mysql.connection.commit()
        cur.execute("DELETE FROM asignacion WHERE idAsignacion = %s", (id,))
        mysql.connection.commit()

        flash("Asignación eliminada exitosamente", "success")
        return redirect(url_for("asignacion.Asignacion"))
    except Exception as e:
        flash(f"Error al eliminar: {e}", "danger")
        return redirect(url_for("asignacion.Asignacion"))

def crear_pdf_asignacion(funcionario, equipos):
    if "user" not in session:
        flash("you are NOT authorized")
        return redirect("/ingresar")
    class PDF(FPDF):
        def header(self):
            # imagen del encabezado (ruta absoluta para evitar FileNotFound)
            logo_path = Path(current_app.root_path) / "static" / "img" / "logo_junji.png"
            if logo_path.exists():
                self.image(str(logo_path), 10, 8, 32)
            else:
                current_app.logger.warning("Logo no encontrado en %s", logo_path)
            # font
            self.set_font("times", "B", 12)
            self.set_text_color(170, 170, 170)
            # Title
            self.cell(0, 30, "", border=False, ln=1, align="L")
            self.cell(0, 5, "JUNTA NACIONAL DE", border=False, ln=1, align="L")
            self.cell(0, 5, "JARDINES INFANTILES", border=False, ln=1, align="L")
            self.cell(0, 5, "Unidad de Inventarios", border=False, ln=1, align="L")
            # line break
            self.ln(10)

        def footer(self):
            self.set_y(-30)
            self.set_font("times", "B", 12)
            self.set_text_color(170, 170, 170)
            self.cell(0, 0, "", ln=1)
            self.cell(0, 0, "Junta Nacional de Jardines Infantiles - JUNJI", ln=1)
            self.cell(0, 12, "O'Higgins Poniente 77 Concepción. Tel: 412125579", ln=1)
            self.cell(0, 12, "www.junji.cl", ln=1)

    #P Portrait -> Vertical
    #mm milimetros
    #A4 formato de tamaño

    pdf = PDF("P", "mm", "A4")
    pdf.add_page()
    titulo = "ACTA de Asignación de Equipo Informático N°" + funcionario["id_asignacion"]

    pdf.set_font("times", "", 20)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.set_font("times", "", 12)
    creado_por = "Documento creado por: " + session['user']
    pdf.cell(0, 10, creado_por, ln=True, align="L")
    presentacion1 = "Por el presente se hace entrega a: "
    presentacion2 = "Dependiente de la unidad: "
    presentacion22 = "En la fecha: "
    presentacion3 = "Del siguiente equipo computacional"

    nombre_funcionario = funcionario["nombre"]
    unidad_funcionario = funcionario["unidad"]
    fecha_asignacion = funcionario["fecha_asignacion"]

    pdf.ln(10)
    #se hace en columnas para que quede ordenado
    with pdf.text_columns(text_align="J", ncols=2, gutter=20) as cols:
        cols.write(presentacion1)
        cols.ln()
        cols.write(presentacion2)
        cols.ln()
        cols.write(presentacion22)
        cols.ln()
        cols.ln()
        cols.write(presentacion3)
        cols.ln()
        cols.new_column()
        #lo que se escribe despues de new_column va en la siguiente columna
        cols.write(nombre_funcionario)
        cols.ln()
        cols.write(unidad_funcionario)
        cols.ln()
        cols.write(fecha_asignacion)

    pdf.ln(20)
    #Encabezado de la tabla
    TABLE_DATA = (
        ("N°", "Tipo equipo", "Marca", "Modelo", "N° Serie", "N° Inventario"),
    )
    i = 0
    for equipo in equipos:
        tipo_equipo = equipo["nombreTipo_equipo"]
        marca = equipo["nombreMarcaEquipo"]
        modelo = equipo["nombreModeloequipo"]
        num_serie = str(equipo["Num_serieEquipo"])
        num_inventario = str(equipo["Cod_inventarioEquipo"])

        i += 1

        TABLE_DATA = TABLE_DATA + (
            (str(i), tipo_equipo, marca, modelo, num_serie, num_inventario),
        )
    with pdf.table() as table:
        for datarow in TABLE_DATA:
            row = table.row()
            for datum in datarow:
                row.cell(datum)

    observacion = "Observación: " + (funcionario.get("observacion") or "")

    pdf.ln(10)
    nombreEncargado = "Nombre del encargado TI:"
    rutEncargado = "RUT:"
    firmaEncargado = "Firma:"
    nombreMinistro = "Nombre del funcionario:"
    rutMinistro = "RUT:"
    firma = "Firma"
    with pdf.text_columns(text_align="J", ncols=2, gutter=30) as cols:
        cols.write(nombreEncargado)
        cols.ln()
        cols.ln()
        cols.write(rutEncargado)
        cols.ln()
        cols.ln()
        cols.write(firmaEncargado)
        cols.ln()
        cols.ln()
        cols.ln()
        cols.ln()

        cols.write(nombreMinistro)
        cols.ln()
        cols.ln()
        cols.write(rutMinistro)
        cols.ln()
        cols.ln()
        cols.write(firma)
        cols.ln()
        cols.ln()
        cols.ln()
        cols.write(observacion)  # <-- Aquí se muestra la observación real
        cols.new_column()
        for i in range(0, 3):
            if i == 0:
                cols.write(text= session['user'])
            else:
                cols.write(text="___________________________________")
            cols.ln()
            cols.ln()
        cols.ln()
        cols.ln()
        for i in range(0, 3):
            cols.write(text="___________________________________")
            cols.ln()
            cols.ln()
    #*(path cambiado y creacion de carpeta asignaciones)
    ruta_asignaciones = "pdf/asignaciones"
    # Asegurar que la carpeta "pdf/asignaciones" exista
    os.makedirs(ruta_asignaciones, exist_ok=True)
    nombrePdf = "asignacion_" + funcionario["id_asignacion"] + ".pdf"
    pdf.output(nombrePdf)
    shutil.move(nombrePdf, os.path.join(ruta_asignaciones, nombrePdf))
    #******
    #try:
    #funcion para enviar un correo a un funcionario (se envia el acta)
        #enviar_correo(nombrePdf, 'correo')
    #except:
        #TODO: agregar error
        #flash("no se pudo enviar el correo")
    return nombrePdf


def generar_pdf_asignacion_por_id(id_asignacion):
    """
    Genera el PDF en pdf/asignaciones/asignacion_<id>.pdf usando datos desde la BD.
    Requiere contexto de request (porque crear_pdf_asignacion usa session['user']).
    """
    cur = mysql.connection.cursor()

    # Datos base de la asignación + funcionario (ajusta nombres si tu esquema difiere)
    cur.execute("""
        SELECT
            a.idAsignacion AS id_asignacion,
            DATE_FORMAT(a.fecha_inicioAsignacion, '%%Y-%%m-%%d') AS fecha_asignacion,
            a.ObservacionAsignacion AS observacion,
            a.rutFuncionario AS rut,
            f.nombreFuncionario AS nombre,
            u.nombreUnidad AS unidad
        FROM asignacion a
        LEFT JOIN funcionario f ON f.rutFuncionario = a.rutFuncionario
        LEFT JOIN unidad u ON u.idUnidad = f.idUnidad
        WHERE a.idAsignacion = %s
    """, (id_asignacion,))
    row = cur.fetchone()
    if not row:
        raise Exception(f"No existe Asignacion id={id_asignacion}")

    funcionario = {
        "id_asignacion": str(row["id_asignacion"]),
        "nombre": row.get("nombre") or str(row.get("rut") or ""),
        "unidad": row.get("unidad") or "",
        "fecha_asignacion": row.get("fecha_asignacion") or "",
        "observacion": row.get("observacion") or "",
    }

    # --- FORZAR FORMATO DD-MM-YYYY (siempre) ---
    try:
        from datetime import date, datetime
        fa = funcionario.get("fecha_asignacion")

        if isinstance(fa, (date, datetime)):
            funcionario["fecha_asignacion"] = fa.strftime("%d-%m-%Y")
        elif isinstance(fa, str) and fa:
            txt = fa.strip()
            # Si viene como YYYY-MM-DD, convertir a DD-MM-YYYY
            parts = txt.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                y, mo, d = parts[0], parts[1], parts[2]
                funcionario["fecha_asignacion"] = f"{d}-{mo}-{y}"
    except Exception:
        pass
    # --- FIN FORMATO FECHA ---


    # Equipos de la asignación (ajusta nombres si tu esquema difiere)
    cur.execute("""
        SELECT
            t.nombreTipo_equipo,
            m.nombreMarcaEquipo,
            mo.nombreModeloequipo,
            e.Num_serieEquipo,
            e.Cod_inventarioEquipo
        FROM equipo_asignacion ea
        JOIN equipo e ON e.idEquipo = ea.idEquipo
        JOIN modelo_equipo mo ON mo.idModelo_Equipo = e.idModelo_equipo
        JOIN marca_tipo_equipo mt ON mt.idMarcaTipo = mo.idMarca_Tipo_Equipo
        JOIN tipo_equipo t ON t.idTipo_equipo = mt.idTipo_equipo
        JOIN marca_equipo m ON m.idMarca_Equipo = mt.idMarca_Equipo
        WHERE ea.idAsignacion = %s
        ORDER BY ea.idEquipoAsignacion ASC
    """, (id_asignacion,))
    equipos = cur.fetchall() or []

    return crear_pdf_asignacion(funcionario, equipos)

@asignacion.route("/asignacion/descargar_pdf_asignacion/<id>")
@loguear_requerido
def descargar_pdf_asignacion(id):
    nombrePDF = f"asignacion_{id}.pdf"
    file_path = os.path.join("pdf/asignaciones", nombrePDF)

    # Si el PDF no existe, lo generamos desde BD
    if not os.path.exists(file_path):
        try:
            generar_pdf_asignacion_por_id(id)
        except Exception as e:
            flash(f"Error generando PDF: {e}", "danger")
            return redirect(url_for('asignacion.Asignacion'))

    # Servir si existe
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=False)

    flash("Error: No se encontró el PDF", "danger")
    return redirect(url_for('asignacion.Asignacion'))


@asignacion.route("/asignacion/devolver_equipos", methods=["POST"])
@administrador_requerido
def devolver_equipos():
    # Obtener los ID de equipo_asignacion desde el formulario
    ids_equipos_asignacion = request.form.getlist("equiposSeleccionados")

    if not ids_equipos_asignacion:
        flash("No se seleccionó ningún equipo para devolver", "danger")
        return redirect(url_for("asignacion.Asignacion"))

    require_firma = request.form.get("require_firma") == "1"
    id_asignacion_ref = request.form.get("idAsignacionPendiente")
    firma_path = None
    if require_firma:
        if not id_asignacion_ref:
            flash("Debe adjuntar la firma antes de devolver.", "warning")
            return redirect(url_for("asignacion.Asignacion"))
        firma_path = _find_pending_devolucion_firma(id_asignacion_ref)
        if not firma_path:
            flash("Debes adjuntar la firma antes de devolver.", "warning")
            return redirect(url_for("asignacion.Asignacion"))

    today = date.today()
    cur = mysql.connection.cursor()
    obs_col = _col_exists("devolucion", "observacionDevolucion")
    obs_cache = {}

    def _obs_for_asignacion(id_asig):
        if id_asig in obs_cache:
            return obs_cache[id_asig]
        obs = "Devolución pendiente"
        try:
            cur.execute(
                """
                SELECT mi.nombre AS motivo, f.detalle_inactividad AS detalle
                FROM asignacion a
                JOIN funcionario f ON f.rutFuncionario = a.rutFuncionario
                LEFT JOIN motivo_inactividad mi ON mi.id = f.motivo_inactividad_id
                WHERE a.idAsignacion = %s
                """,
                (id_asig,),
            )
            row = cur.fetchone()
            if row:
                partes = ["Devolución pendiente"]
                if row.get("motivo"):
                    partes.append(f"Motivo: {row['motivo']}")
                if row.get("detalle"):
                    partes.append(f"Detalle: {row['detalle']}")
                obs = " | ".join(partes)
        except Exception:
            obs = "Devolución pendiente"
        obs_cache[id_asig] = obs
        return obs

    # Iniciar una transacción
    cur.execute("START TRANSACTION")

    # Obtener el ID del estado "SIN ASIGNAR"
    cur.execute("SELECT idEstado_equipo FROM estado_equipo WHERE UPPER(TRIM(nombreEstado_equipo)) = 'SIN ASIGNAR'")
    estado_sin_asignar = cur.fetchone()

    if not estado_sin_asignar:
        flash("No se encontró el estado 'SIN ASIGNAR'", "danger")
        cur.execute("ROLLBACK")  # Cancelar cualquier cambio
        return redirect(url_for("asignacion.Asignacion"))

    id_estado_sin_asignar = estado_sin_asignar["idEstado_equipo"]

    for id_equipo_asignacion in ids_equipos_asignacion:
        # Verificar si ya fue devuelto
        cur.execute("""
            SELECT idDevolucion 
            FROM devolucion 
            WHERE idEquipoAsignacion = %s
        """, (id_equipo_asignacion,))
        if cur.fetchone():  # Si existe, detener todo el proceso
            flash("Error: Uno o más equipos seleccionados ya fueron devueltos", "danger")
            cur.execute("ROLLBACK")  # Cancelar todo el proceso
            return redirect(url_for("asignacion.Asignacion"))

    # Si no hay errores, proceder con la devolución
    for id_equipo_asignacion in ids_equipos_asignacion:
        # Obtener la asignación y el equipo correspondiente
        cur.execute("""
            SELECT ea.idAsignacion, ea.idEquipo
            FROM equipo_asignacion ea
            WHERE ea.idEquipoAsignacion = %s
        """, (id_equipo_asignacion,))
        equipo_asignacion_info = cur.fetchone()

        if not equipo_asignacion_info:
            flash(f"No se encontró información para el equipo asignado {id_equipo_asignacion}.", "warning")
            cur.execute("ROLLBACK")  # Cancelar todo el proceso
            return redirect(url_for("asignacion.Asignacion"))

        id_asignacion = equipo_asignacion_info["idAsignacion"]
        id_equipo = equipo_asignacion_info["idEquipo"]

        # Registrar la devolución en la tabla devolucion
        if obs_col and require_firma:
            observacion = _obs_for_asignacion(id_asignacion)
            cur.execute(
                """
                INSERT INTO devolucion (fechaDevolucion, idEquipoAsignacion, observacionDevolucion)
                VALUES (%s, %s, %s)
                """,
                (today, id_equipo_asignacion, observacion),
            )
        else:
            cur.execute(
                """
                INSERT INTO devolucion (fechaDevolucion, idEquipoAsignacion)
                VALUES (%s, %s)
                """,
                (today, id_equipo_asignacion),
            )
        id_devolucion = str(cur.lastrowid) # Recupera el ID de la devolución recién insertada

        if firma_path:
            if _col_exists("devolucion", "rutaactaDevolucion"):
                cur.execute(
                    "UPDATE devolucion SET rutaactaDevolucion = %s WHERE idDevolucion = %s",
                    (str(firma_path), id_devolucion),
                )
            else:
                _copy_signed_devolucion_file(firma_path, id_devolucion)

        # Actualizar el estado del equipo a "SIN ASIGNAR"
        cur.execute("""
            UPDATE equipo
            SET idEstado_equipo = %s
            WHERE idEquipo = %s
        """, (id_estado_sin_asignar, id_equipo))

        # Verificar si todos los equipos de la asignación ya fueron devueltos
        cur.execute("""
            SELECT COUNT(*) AS equipos_no_devueltos
            FROM equipo_asignacion ea
            LEFT JOIN devolucion d ON ea.idEquipoAsignacion = d.idEquipoAsignacion
            WHERE ea.idAsignacion = %s AND d.idDevolucion IS NULL
        """, (id_asignacion,))
        equipos_pendientes = cur.fetchone()

        # Si no hay más equipos pendientes, actualizar la asignación como cerrada
        if equipos_pendientes["equipos_no_devueltos"] == 0:
            cur.execute("""
                UPDATE asignacion
                SET ActivoAsignacion = 0
                WHERE idAsignacion = %s
            """, (id_asignacion,))

    # Obtiene información relevante del funcionario y la observación para añadir al PDF
    cur.execute("""
        SELECT 
            f.nombreFuncionario,
            a.idAsignacion,
            a.fecha_inicioAsignacion,
            u.nombreUnidad,
            a.ObservacionAsignacion
        FROM funcionario f
        JOIN asignacion a ON f.rutFuncionario = a.rutFuncionario
        JOIN unidad u ON f.idUnidad = u.idUnidad
        WHERE a.idAsignacion = %s
    """, (id_asignacion,))
    query = cur.fetchone()

    data_funcionario_PDF = {
        "nombre": query["nombreFuncionario"],
        "id_asignacion": str(query["idAsignacion"]),
        "fecha_asignacion": str(query["fecha_inicioAsignacion"].strftime("%d-%m-%Y")),
        "unidad": query["nombreUnidad"],
        "observacion": query["ObservacionAsignacion"] or ""
    }

    # Obtiene información relevante de los equipos seleccionados para devolver para añadir al PDF
    placeholders = ', '.join(['%s'] * len(ids_equipos_asignacion))
    cur.execute(f"""
        SELECT
            te.nombreTipo_equipo,
            mae.nombreMarcaEquipo,
            me.nombreModeloequipo,
            e.Num_serieEquipo,
            e.Cod_inventarioEquipo
        FROM equipo e
        JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
        JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
        JOIN equipo_asignacion ea ON e.idEquipo = ea.idEquipo
        WHERE ea.idEquipoAsignacion IN ({placeholders})
    """, tuple(ids_equipos_asignacion))
    query = cur.fetchall()

    data_equipos_PDF = [
        {
            "tipo": equipo["nombreTipo_equipo"],
            "marca": equipo["nombreMarcaEquipo"],
            "modelo": equipo["nombreModeloequipo"],
            "num_serie": str(equipo["Num_serieEquipo"]),
            "cod_inventario": str(equipo["Cod_inventarioEquipo"])
        }
        for equipo in query
    ]

    # Si todo fue exitoso, confirmar cambios
    cur.execute("COMMIT")
    crear_pdf_devolucion(data_funcionario_PDF, data_equipos_PDF, id_devolucion, data_funcionario_PDF["observacion"])
    flash("Devolución de equipos realizada exitosamente", "success")
    return redirect(url_for("asignacion.Asignacion"))


# Modifica la función para aceptar la observación
def crear_pdf_devolucion(funcionario, equipos, id_devolucion, observacion=""):
    class PDF(FPDF):
        def header(self):
            #logo
            self.image("static/img/logo_junji.png", 10, 8, 32)
            #font
            self.set_font('times', 'B', 12)
            self.set_text_color(170, 170, 170)
            #Title
            self.cell(0, 30, '', border=False, ln=1, align='L')
            self.cell(0, 5, 'JUNTA NACIONAL DE', border=False, ln=1, align='L')
            self.cell(0, 5, 'JARDINES INFANTILES', border=False, ln=1, align='L')
            self.cell(0, 5, 'Unidad de Inventarios', border=False, ln=1, align='L')
            #line break
            self.ln(10)

        def footer(self):
            self.set_y(-30)
            self.set_font('times', 'B', 12)
            self.set_text_color(170, 170, 170)
            self.cell(0, 0, "", ln=1)
            self.cell(0, 0, "Junta Nacional de Jardines Infantiles - JUNJI", ln=1)
            self.cell(0, 12, "O'Higgins Poniente 77 Concepción. Tel: 412125579", ln=1)
            self.cell(0, 12, "www.junji.cl", ln=1)

    cur = mysql.connection.cursor()

    # 📌 Consultar la fecha de devolución en la base de datos
    cur.execute("""
        SELECT fechaDevolucion
        FROM devolucion
        WHERE idDevolucion = %s
    """, (id_devolucion,))

    devolucion_data = cur.fetchone()

    # Convertir a string para evitar errores con fpdf ademas se cambia el orden de la fecha 
    fecha_devolucion = (
    devolucion_data["fechaDevolucion"].strftime("%d/%m/%Y") if devolucion_data else "FECHA NO DISPONIBLE"
    )
    
    pdf = PDF("P", "mm", "A4")
    pdf.add_page()
    titulo = "ACTA de Devolución de Equipo Informático N°" + id_devolucion
    creado_por = "Documento creado por: " + session['user']

    pdf.set_font("times", "", 20)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.set_font("times", "", 12)
    pdf.cell(0, 10, creado_por, ln=True, align="L")
    presentacion1 = "Por el presente se hace entrega a: "
    presentacion2 = "Dependiente de la unidad: "
    presentacion22 = "En la fecha: "
    presentacion3 = "Del siguiente equipo computacional"

    nombre_funcionario = funcionario["nombre"]
    unidad_funcionario = funcionario["unidad"]

    pdf.ln(10)
    with pdf.text_columns(text_align="J", ncols=2, gutter=20) as cols:
        cols.write(presentacion1)
        cols.ln()
        cols.write(presentacion2)
        cols.ln()
        cols.write(presentacion22)
        cols.ln()
        cols.ln()
        cols.write(presentacion3)
        cols.ln()
        cols.new_column()
        cols.write(nombre_funcionario)
        cols.ln()
        cols.write(unidad_funcionario)
        cols.ln()
        cols.write(fecha_devolucion)  # ✅ Ahora ya no dará error

    pdf.ln(20)
    TABLE_DATA = (
        ("N°", "Tipo equipo", "Marca", "Modelo", "N° Serie", "N° Inventario"),
    )
    i = 0
    for equipo in equipos:
        tipo = equipo["tipo"]
        marca = equipo["marca"]
        modelo = equipo["modelo"]
        num_serie = equipo["num_serie"]
        num_inventario = equipo["cod_inventario"]

        i += 1

        TABLE_DATA = TABLE_DATA + (
            (str(i), tipo, marca, modelo, num_serie, num_inventario),
        )
    with pdf.table() as table:
        for datarow in TABLE_DATA:
            row = table.row()
            for datum in datarow:
                row.cell(datum)
 
    # Mostrar la observación real
    pdf.ln(10)
    nombreEncargado = "Nombre del encargado TI:" 
    rutEncargado = "RUT:"
    firmaEncargado = "Firma:"
    nombreMinistro = "Nombre del funcionario:"
    rutMinistro = "RUT:"
    firma = "Firma"
    with pdf.text_columns(text_align="J", ncols=2, gutter=20) as cols:
        cols.write(nombreEncargado)
        cols.ln()
        cols.ln()
        cols.write(rutEncargado)
        cols.ln()
        cols.ln()
        cols.write(firmaEncargado)
        cols.ln()
        cols.ln()
        cols.ln()
        cols.ln()

        cols.write(nombreMinistro)
        cols.ln()
        cols.ln()
        cols.write(rutMinistro)
        cols.ln()
        cols.ln()
        cols.write(firma)
        cols.ln()
        cols.ln()
        cols.ln()
        cols.write("Observación: " + (observacion or ""))
        cols.ln()
        cols.new_column()
        for i in range(0, 3):
            if i == 0:
                cols.write(text= session['user'])
            else:
                cols.write(text="___________________________________")
            cols.ln()
            cols.ln()
        cols.ln()
        cols.ln()
        for i in range(0, 3):
            cols.write(text="___________________________________")
            cols.ln()
            cols.ln()
    creado_por = "documento creado por: " + session['user']
    #* Definir la ruta donde se almacenarán los PDFs de devoluciones
    ruta_devoluciones = "pdf/devoluciones"
    # Asegurar que la carpeta "pdf/devoluciones" exista
    os.makedirs(ruta_devoluciones, exist_ok=True)
    nombrePdf = "devolucion_" + id_devolucion + ".pdf"
    pdf.output(nombrePdf)
    shutil.move(nombrePdf, os.path.join(ruta_devoluciones, nombrePdf))


def generar_pdf_devolucion_por_id(id_devolucion):
    """
    Genera pdf/devoluciones/devolucion_<id>.pdf desde BD.
    Ajustado al esquema real:
      equipo -> modelo_equipo -> marca_tipo_equipo -> marca_equipo / tipo_equipo
      devolucion -> equipo_asignacion -> asignacion -> funcionario -> unidad
    """
    cur = mysql.connection.cursor()

    # Cabecera (devolucion + funcionario + unidad)
    cur.execute("""
        SELECT
            d.idDevolucion AS id_devolucion,
            d.fechaDevolucion AS fecha_devolucion,
            f.nombreFuncionario AS nombre,
            u.nombreUnidad AS unidad,
            f.rutFuncionario AS rut
        FROM devolucion d
        JOIN equipo_asignacion ea ON ea.idEquipoAsignacion = d.idEquipoAsignacion
        JOIN asignacion a ON a.idAsignacion = ea.idAsignacion
        JOIN funcionario f ON f.rutFuncionario = a.rutFuncionario
        JOIN unidad u ON u.idUnidad = f.idUnidad
        WHERE d.idDevolucion = %s
        LIMIT 1
    """, (id_devolucion,))
    row = cur.fetchone()
    if not row:
        raise Exception(f"No existe Devolucion id={id_devolucion}")

    funcionario = {
        "id_devolucion": str(row["id_devolucion"]),
        "nombre": row.get("nombre") or str(row.get("rut") or ""),
        "unidad": row.get("unidad") or "",
        "fecha_devolucion": row.get("fecha_devolucion") or "",
    }

    # --- FORZAR FORMATO DD-MM-YYYY (siempre) ---
    try:
        from datetime import date, datetime
        fd = funcionario.get("fecha_devolucion")
        if isinstance(fd, (date, datetime)):
            funcionario["fecha_devolucion"] = fd.strftime("%d-%m-%Y")
        elif isinstance(fd, str) and fd:
            txt = fd.strip()
            parts = txt.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                y, mo, d = parts[0], parts[1], parts[2]
                funcionario["fecha_devolucion"] = f"{d}-{mo}-{y}"
    except Exception:
        pass
    # --- FIN FORMATO FECHA ---

    # Equipos asociados a ESA devolución (por idEquipoAsignacion)
    cur.execute("""
        SELECT
            t.nombreTipo_equipo      AS tipo,
            m.nombreMarcaEquipo      AS marca,
            me.nombreModeloequipo    AS modelo,
            e.Num_serieEquipo        AS num_serie,
            e.Cod_inventarioEquipo   AS cod_inventario
        FROM devolucion d
        JOIN equipo_asignacion ea ON ea.idEquipoAsignacion = d.idEquipoAsignacion
        JOIN equipo e ON e.idEquipo = ea.idEquipo
        JOIN modelo_equipo me ON me.idModelo_Equipo = e.idModelo_equipo
        JOIN marca_tipo_equipo mte ON mte.idMarcaTipo = me.idMarca_Tipo_Equipo
        JOIN marca_equipo m ON m.idMarca_Equipo = mte.idMarca_Equipo
        JOIN tipo_equipo t ON t.idTipo_equipo = mte.idTipo_equipo
        WHERE d.idDevolucion = %s
        ORDER BY ea.idEquipoAsignacion ASC
    """, (id_devolucion,))
    equipos = cur.fetchall() or []

    # Intentar usar creador existente si está en el archivo; si no, fallar con mensaje claro
    if "crear_pdf_devolucion" not in globals():
        raise Exception("No existe crear_pdf_devolucion() en asignacion.py. Hay que reutilizar/crear esa función con el formato del acta de devolución.")
    return crear_pdf_devolucion(funcionario, equipos, str(id_devolucion))


@asignacion.route("/asignacion/descargar_pdf_devolucion/<id>")
@loguear_requerido
def descargar_pdf_devolucion(id):
    nombrePDF = f"devolucion_{id}.pdf"
    file_path = os.path.join("pdf/devoluciones", nombrePDF)

    # Si no existe, generar desde BD
    if not os.path.exists(file_path):
        try:
            generar_pdf_devolucion_por_id(id)
        except Exception as e:
            flash(f"Error generando PDF: {e}", "danger")
            return redirect(url_for('asignacion.Asignacion'))

    # Servir si existe
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=False)

    flash("Error: No se encontró el PDF", "danger")
    return redirect(url_for('asignacion.Asignacion'))

@asignacion.route("/asignacion/buscar/<idAsignacion>")
@loguear_requerido
def buscar(idAsignacion):
    cur = mysql.connection.cursor()
    cur.execute(
        """ 
    SELECT  
        a.idAsignacion,
        a.fecha_inicioAsignacion,
        a.observacionAsignacion,
        a.rutaactaAsignacion,
        f.nombreFuncionario,
        f.rutFuncionario,
        a.fechaDevolucion,
        a.ActivoAsignacion
    FROM asignacion a
    INNER JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
    WHERE a.idAsignacion = %s
        """, (idAsignacion,)
    )
    #solo tiene un elemento pero se extraen todas para reusar el html
    Asignaciones = cur.fetchall()

    cur.execute(
        """ SELECT 
            f.rutFuncionario,
            f.nombreFuncionario 
        FROM funcionario f
        ORDER BY f.nombreFuncionario
        """
    )
    funcionarios = cur.fetchall()

    return render_template(
        'GestionR.H/asignacion.html',  
        funcionarios=funcionarios, 
        asignacion=Asignaciones,
        page=1, 
        lastpage=True
    )

@asignacion.route("/asignacion/detalles_json/<idAsignacion>")
@loguear_requerido
def obtener_detalles_asignacion(idAsignacion):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            a.idAsignacion,
            a.fecha_inicioAsignacion,
            d.fechaDevolucion,
            a.ObservacionAsignacion,
            f.rutFuncionario,
            f.nombreFuncionario,
            f.cargoFuncionario,
            te.nombreTipo_equipo,
            mae.nombreMarcaEquipo,
            me.nombreModeloequipo,
            e.Cod_inventarioEquipo,
            e.Num_serieEquipo,
            e.codigoproveedor_equipo,
            e.ObservacionEquipo,
            ea.idEquipoAsignacion,
            e.idEquipo
        FROM asignacion a
        JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
        JOIN equipo_asignacion ea ON a.idAsignacion = ea.idAsignacion
        JOIN equipo e ON ea.idEquipo = e.idEquipo
        LEFT JOIN devolucion d ON ea.idEquipoAsignacion = d.idEquipoAsignacion
        JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
        JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
        WHERE a.idAsignacion = %s
    """, (idAsignacion,))
    rows = cur.fetchall()
    cur.close()

    if not rows:
        return jsonify({"error": "No se encontró la asignación"}), 404

    equipos = []
    for item in rows:
        equipos.append({
            "idEquipoAsignacion": item.get("idEquipoAsignacion"),
            "idEquipo": item.get("idEquipo"),
            "nombreTipo_equipo": item.get("nombreTipo_equipo"),
            "nombreMarcaEquipo": item.get("nombreMarcaEquipo"),
            "nombreModeloequipo": item.get("nombreModeloequipo"),
        })

    return jsonify({
        "asignacion": rows[0],
        "equipos": equipos,
        "actasFirmadas": _list_actas_firmadas(str(idAsignacion)),
    })


@asignacion.route("/asignacion/detalle_equipo_asignacion_json/<int:idEquipoAsignacion>")
@loguear_requerido
def obtener_detalle_equipo_asignacion_json(idEquipoAsignacion):
    cur = mysql.connection.cursor()
    # Filtrar por idEquipoAsignacion para obtener el equipo correcto (evita repetir el primero de la asignación).
    cur.execute("""
        SELECT
            ea.idEquipoAsignacion,
            a.idAsignacion,
            a.fecha_inicioAsignacion,
            d.fechaDevolucion,
            a.ObservacionAsignacion,
            f.rutFuncionario,
            f.nombreFuncionario,
            f.cargoFuncionario,
            te.nombreTipo_equipo,
            mae.nombreMarcaEquipo,
            me.nombreModeloequipo,
            e.Cod_inventarioEquipo,
            e.Num_serieEquipo,
            e.codigoproveedor_equipo,
            e.ObservacionEquipo
        FROM equipo_asignacion ea
        JOIN asignacion a ON ea.idAsignacion = a.idAsignacion
        JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
        JOIN equipo e ON ea.idEquipo = e.idEquipo
        LEFT JOIN devolucion d ON ea.idEquipoAsignacion = d.idEquipoAsignacion
        JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
        JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
        WHERE ea.idEquipoAsignacion = %s
    """, (idEquipoAsignacion,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return jsonify({"error": "No se encontró el detalle de la asignación"}), 404

    return jsonify({
        "asignacion": row
    })


@asignacion.route("/buscar_asignaciones", methods=["GET"])
@loguear_requerido
def buscar_asignaciones():
    query = request.args.get("q", "").lower()  # Obtener el término de búsqueda
    page = request.args.get("page", default=1, type=int)  # Página actual
    per_page = 10  # Número de resultados por página
    offset = (page - 1) * per_page

    cur = mysql.connection.cursor()

    # Consulta para buscar asignaciones (ahora incluye todos los campos necesarios)
    cur.execute(f"""
        SELECT
            a.idAsignacion,
            a.fecha_inicioAsignacion,
            a.ObservacionAsignacion,
            a.ActivoAsignacion,
            COALESCE(f.nombreFuncionario, '') AS nombreFuncionario,
            COALESCE(f.rutFuncionario, a.rutFuncionario) AS rutFuncionario,
            COALESCE(f.cargoFuncionario, '') AS cargoFuncionario,
            ea.idEquipoAsignacion,
            e.idEquipo,
            d.idDevolucion,
            d.fechaDevolucion,
            e.Cod_inventarioEquipo,
            e.Num_serieEquipo,
            te.nombreTipo_equipo,
            me.nombreModeloequipo,
            mae.nombreMarcaEquipo,
            e.codigoproveedor_equipo,
            e.ObservacionEquipo
        FROM asignacion a
        LEFT JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
        JOIN equipo_asignacion ea ON a.idAsignacion = ea.idAsignacion
        LEFT JOIN devolucion d ON ea.idEquipoAsignacion = d.idEquipoAsignacion
        LEFT JOIN equipo e ON e.idEquipo = ea.idEquipo
        LEFT JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
        LEFT JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        LEFT JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        LEFT JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
          WHERE LOWER(COALESCE(f.nombreFuncionario, '')) LIKE %s
              OR LOWER(COALESCE(f.cargoFuncionario, '')) LIKE %s
              OR LOWER(COALESCE(e.Cod_inventarioEquipo, '')) LIKE %s
              OR LOWER(COALESCE(e.Num_serieEquipo, '')) LIKE %s
              OR LOWER(COALESCE(te.nombreTipo_equipo, '')) LIKE %s
              OR LOWER(COALESCE(a.ObservacionAsignacion, '')) LIKE %s
              OR LOWER(COALESCE(f.rutFuncionario, a.rutFuncionario, '')) LIKE %s
          ORDER BY a.idAsignacion DESC, ea.idEquipoAsignacion DESC
          LIMIT %s OFFSET %s
    """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%",
          f"%{query}%", f"%{query}%", f"%{query}%", per_page, offset))
    asignaciones = cur.fetchall()

    # Total de resultados para la búsqueda
    cur.execute(f"""
        SELECT COUNT(*) AS total
        FROM asignacion a
        LEFT JOIN funcionario f ON a.rutFuncionario = f.rutFuncionario
        JOIN equipo_asignacion ea ON a.idAsignacion = ea.idAsignacion
        LEFT JOIN equipo e ON e.idEquipo = ea.idEquipo
        LEFT JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
        LEFT JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        LEFT JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        WHERE LOWER(COALESCE(f.nombreFuncionario, '')) LIKE %s
           OR LOWER(COALESCE(f.cargoFuncionario, '')) LIKE %s
           OR LOWER(COALESCE(e.Cod_inventarioEquipo, '')) LIKE %s
           OR LOWER(COALESCE(e.Num_serieEquipo, '')) LIKE %s
           OR LOWER(COALESCE(te.nombreTipo_equipo, '')) LIKE %s
           OR LOWER(COALESCE(a.ObservacionAsignacion, '')) LIKE %s
           OR LOWER(COALESCE(f.rutFuncionario, a.rutFuncionario, '')) LIKE %s
    """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%",
          f"%{query}%", f"%{query}%", f"%{query}%"))
    total = cur.fetchone()["total"]
    total_pages = (total + per_page - 1) // per_page

    return jsonify({
        "asignaciones": asignaciones,
        "total": total,
        "total_pages": total_pages,
        "current_page": page
    })

@asignacion.route("/asignacion/firmar/<id>", methods=["GET"])
@loguear_requerido
def firmar_asignacion(id):
    if "user" not in session:
        flash("You are NOT authorized")
        return redirect("/ingresar")

    # Ruta de la carpeta donde se almacenan las firmas
    dir_firmas = "pdf/firmas_asignaciones"
    nombreFirmado = None

    # Buscar el archivo firmado relacionado con el ID
    try:
        for filename in os.listdir(dir_firmas):
            if filename.startswith(f"asignacion_{id}_") and filename.endswith("_firmado.pdf"):
                nombreFirmado = filename
                break
    except FileNotFoundError:
        flash("No se encontró la carpeta de firmas", "danger")

    # Renderizar la plantilla con los datos necesarios
    return render_template(
        "GestionR.H/asignacion.modals.html",
        id=id,
        location="asignacion",
        nombreFirmado=nombreFirmado
    )

@asignacion.route("/asignacion/listar_pdf/<idAsignacion>")
@asignacion.route("/asignacion/listar_pdf/<idAsignacion>/<devolver>")
@loguear_requerido
def listar_pdf(idAsignacion, devolver="None"):
    if "user" not in session:
        flash("you are NOT authorized")
        return redirect("/ingresar")
    dir = 'pdf'
    if devolver == "None":
        candidate = _find_signed_asignacion(idAsignacion)
        location = "asignacion"
    else:
        resolved_id = _resolve_devolucion_id(idAsignacion)
        candidate = _find_signed_devolucion(resolved_id) if resolved_id else None
        if not candidate:
            candidate = _find_pending_devolucion_firma(idAsignacion)
        location = "devolucion"

    nombreFirmado = candidate.name if candidate else "No existen firmas para este documento"
    return render_template(
        'GestionR.H/firma.html', 
        nombreFirmado=nombreFirmado, 
        id=idAsignacion, 
        location=location
        )


#**APARTADO DE FIRMAS**** 

@asignacion.route("/devolucion/mostrar_pdf/<id>/")
@loguear_requerido
def mostrar_pdf_devolucion_firmado(id):
    if "user" not in session:
        flash("you are NOT authorized")
        return redirect("/ingresar")
    resolved_id = _resolve_devolucion_id(id)
    candidate = _find_signed_devolucion(resolved_id) if resolved_id else None
    if not candidate:
        candidate = _find_pending_devolucion_firma(id)
    if candidate:
        return send_file(candidate, as_attachment=False)

    flash("No se encontró el PDF de devolución firmado", "warning")
    return redirect(url_for('asignacion.Asignacion'))

@asignacion.route("/asignacion/mostrar_pdf/<id>/")
@loguear_requerido
def mostrar_pdf_asignacion_firmado(id):
    if "user" not in session:
        flash("you are NOT authorized")
        return redirect("/ingresar")
    candidate = _find_signed_asignacion(id)
    if candidate:
        return send_file(candidate, as_attachment=False)

    flash("No se encontró el PDF de asignación firmado", "warning")
    return redirect(url_for('asignacion.Asignacion'))


@asignacion.route("/asignacion/actas/<idAsignacion>/<path:filename>")
@loguear_requerido
def descargar_acta_firmada(idAsignacion, filename):
    base_dir = ACTAS_FIRMADAS_DIR / f"asignacion_{idAsignacion}"
    target = (base_dir / filename).resolve()
    if base_dir.resolve() not in target.parents or not target.exists():
        abort(404)
    return send_file(target, as_attachment=False)
    
#*************************

@asignacion.route("/asignacion/firmas_json/<idAsignacion>")
@loguear_requerido
def obtener_firma_json(idAsignacion):
    actas = _list_actas_firmadas(str(idAsignacion))
    ultimo = actas[0] if actas else None
    return jsonify({
        "existe": bool(actas),
        "actasFirmadas": actas,
        "nombre": ultimo.get("filename") if ultimo else "",
        "ruta": ultimo.get("url") if ultimo else "",
    })


@asignacion.route("/asignacion/adjuntar_pdf/<idAsignacion>", methods=["POST"])
@administrador_requerido
def adjuntar_pdf_asignacion(idAsignacion):
    if "user" not in session:
        flash("You are NOT authorized")
        return redirect("/ingresar")

    # Obtener el archivo
    file = request.files.get("archivoFirma")
    if not file or not file.filename:
        flash("No se seleccionó archivo para adjuntar.", "warning")
        return redirect(url_for("asignacion.Asignacion"))

    equipo_id = request.form.get("equipoId") or request.form.get("equipo_id")
    tipo_equipo = request.form.get("tipoEquipo") or request.form.get("tipo_equipo")

    if not equipo_id and not tipo_equipo:
        # Fallback: tomar el primer equipo de la asignación para no bloquear si el front no envía el campo
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                """
                SELECT e.idEquipo, te.nombreTipo_equipo
                FROM equipo_asignacion ea
                JOIN equipo e ON ea.idEquipo = e.idEquipo
                JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
                JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
                JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
                WHERE ea.idAsignacion = %s
                ORDER BY ea.idEquipoAsignacion ASC
                LIMIT 1
                """,
                (idAsignacion,),
            )
            row = cur.fetchone()
            cur.close()
            if row:
                equipo_id = row.get("idEquipo")
                tipo_equipo = row.get("nombreTipo_equipo")
        except Exception:
            pass

    if not equipo_id and not tipo_equipo:
        flash("Debe indicar el equipo o tipo de equipo para esta acta.", "warning")
        return redirect(url_for("asignacion.Asignacion"))

    # Guardar con nombre único sin sobrescribir
    saved_path = _save_acta_firmada(file, str(idAsignacion), equipo_id, tipo_equipo)
    current_app.logger.info("[asignacion.adjuntar_pdf] id=%s guardado=%s", idAsignacion, saved_path)

    # Persistir la ruta absoluta en la BD (compatible con registros existentes)
    try:
        if _col_exists("asignacion", "rutaactaAsignacion"):
            cur = mysql.connection.cursor()
            cur.execute(
                "UPDATE asignacion SET rutaactaAsignacion = %s WHERE idAsignacion = %s",
                (str(saved_path), idAsignacion),
            )
            mysql.connection.commit()
            cur.close()
        else:
            current_app.logger.warning("[asignacion.adjuntar_pdf] Columna rutaactaAsignacion no existe; se omite update.")
    except OperationalError as e:
        mysql.connection.rollback()
        current_app.logger.warning("[asignacion.adjuntar_pdf] No se pudo registrar ruta (columna faltante): %s", e)
        flash("Se guardó el archivo pero no se pudo registrar la ruta en BD (columna faltante).", "warning")
        return redirect(url_for("asignacion.Asignacion"))
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Se guardó el archivo pero no se pudo registrar la ruta: {e}", "warning")
        return redirect(url_for("asignacion.Asignacion"))

    flash("Se subió la firma correctamente")
    return redirect(url_for("asignacion.Asignacion"))


@asignacion.route("/asignacion/firmas_devolucion_json/<idDevolucion>")
@loguear_requerido
def obtener_firma_devolucion_json(idDevolucion):
    resolved_id = _resolve_devolucion_id(idDevolucion)
    candidate = _find_signed_devolucion(resolved_id) if resolved_id else None
    if not candidate:
        candidate = _find_pending_devolucion_firma(idDevolucion)
    if candidate:
        return jsonify({"existe": True, "nombre": candidate.name, "ruta": str(candidate), "firmas": str(candidate.parent)})
    return jsonify({"existe": False, "firmas": ""})


@asignacion.route("/devolucion/adjuntar_pdf/<idAsignacion>", methods=["POST"])
@administrador_requerido
def adjuntar_pdf_devolucion(idAsignacion):
    file = request.files.get("archivoFirma")
    if not file or not file.filename:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "error": "No se seleccionó archivo para adjuntar."}), 400
        flash("No se seleccionó archivo para adjuntar.", "warning")
        return redirect(url_for("asignacion.Asignacion"))

    saved_path = _save_uploaded_pdf(file, FIRMAS_DEVOLUCIONES_DIR, f"devolucion_asignacion_{idAsignacion}")
    current_app.logger.info("[devolucion.adjuntar_pdf] id=%s guardado=%s", idAsignacion, saved_path)

    devolucion_ids = _devolucion_ids_for_asignacion(idAsignacion)

    # Guardar ruta si existen devoluciones (compatibilidad hacia atrás)
    try:
        if devolucion_ids:
            if _col_exists("devolucion", "rutaactaDevolucion"):
                cur = mysql.connection.cursor()
                cur.executemany(
                    "UPDATE devolucion SET rutaactaDevolucion = %s WHERE idDevolucion = %s",
                    [(str(saved_path), str(dev_id)) for dev_id in devolucion_ids],
                )
                mysql.connection.commit()
                cur.close()
            else:
                for dev_id in devolucion_ids:
                    _copy_signed_devolucion_file(saved_path, str(dev_id))
        else:
            current_app.logger.info(
                "[devolucion.adjuntar_pdf] no hay devoluciones para asignacion=%s; se deja archivo en staging",
                idAsignacion,
            )
    except OperationalError as e:
        mysql.connection.rollback()
        current_app.logger.warning("[devolucion.adjuntar_pdf] No se pudo registrar ruta (columna faltante): %s", e)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "error": "Se guardó el archivo pero no se pudo registrar la ruta."}), 500
        flash("Se guardó el archivo pero no se pudo registrar la ruta en BD (columna faltante).", "warning")
        return redirect(url_for("asignacion.Asignacion"))
    except Exception as e:
        mysql.connection.rollback()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "error": f"No se pudo registrar la ruta: {e}"}), 500
        flash(f"Se guardó el archivo pero no se pudo registrar la ruta: {e}", "warning")
        return redirect(url_for("asignacion.Asignacion"))

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "ruta": str(saved_path)})

    flash("PDF de devolución adjuntado correctamente")
    return redirect(url_for("asignacion.Asignacion"))


@asignacion.route("/delete_equipo_asignacion/<int:id_equipo_asignacion>", methods=["POST", "GET"])
@administrador_requerido
def delete_equipo_asignacion(id_equipo_asignacion):
    conn = mysql.connection
    cur = conn.cursor()
    try:
        cur.execute("START TRANSACTION")

        # ✅ Traer la fila exacta (PK del detalle)
        cur.execute("""
            SELECT idEquipoAsignacion, idAsignacion, idEquipo
            FROM equipo_asignacion
            WHERE idEquipoAsignacion = %s
        """, (id_equipo_asignacion,))
        ea = cur.fetchone()
        if not ea:
            conn.rollback()
            flash("No existe esa asignación individual.", "warning")
            return redirect(url_for("asignacion.Asignacion"))

        id_equipo = ea["idEquipo"]
        id_asignacion = ea["idAsignacion"]

        # ✅ Si ya tiene devolución, no borrar para no romper historial
        cur.execute("SELECT 1 FROM devolucion WHERE idEquipoAsignacion = %s LIMIT 1", (id_equipo_asignacion,))
        if cur.fetchone():
            conn.rollback()
            flash("No se puede eliminar: esta asignación ya tiene devolución registrada.", "warning")
            return redirect(url_for("asignacion.Asignacion"))

        # ✅ Borrar SOLO esa fila (un equipo)
        cur.execute("DELETE FROM equipo_asignacion WHERE idEquipoAsignacion = %s", (id_equipo_asignacion,))

        # ✅ Si el equipo ya no está asignado en ninguna otra asignación activa, volver a SIN ASIGNAR
        cur.execute("""
            SELECT 1
            FROM equipo_asignacion ea
            JOIN asignacion a ON a.idAsignacion = ea.idAsignacion AND a.ActivoAsignacion = 1
            LEFT JOIN devolucion d ON d.idEquipoAsignacion = ea.idEquipoAsignacion
            WHERE ea.idEquipo = %s
              AND d.idDevolucion IS NULL
            LIMIT 1
        """, (id_equipo,))
        sigue_asignado = cur.fetchone() is not None

        if not sigue_asignado:
            cur.execute("""
                SELECT idEstado_equipo
                FROM estado_equipo
                WHERE UPPER(TRIM(nombreEstado_equipo)) = %s
                LIMIT 1
            """, ("SIN ASIGNAR",))
            est = cur.fetchone()
            if est:
                cur.execute(
                    "UPDATE equipo SET idEstado_equipo = %s WHERE idEquipo = %s",
                    (est["idEstado_equipo"], id_equipo),
                )

        # ✅ Si la asignación quedó sin equipos, opcional: borrar cabecera
        cur.execute("SELECT 1 FROM equipo_asignacion WHERE idAsignacion = %s LIMIT 1", (id_asignacion,))
        if cur.fetchone() is None:
            cur.execute("DELETE FROM asignacion WHERE idAsignacion = %s", (id_asignacion,))

        conn.commit()
        flash("Equipo eliminado de la asignación.", "success")
        return redirect(url_for("asignacion.Asignacion"))

    except Exception as e:
        conn.rollback()
        flash(f"Error al eliminar: {e}", "danger")
        return redirect(url_for("asignacion.Asignacion"))
    finally:
        try:
            cur.close()
        except Exception:
            pass
