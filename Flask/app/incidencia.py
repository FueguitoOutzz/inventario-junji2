from flask import Blueprint, render_template, request, url_for, redirect, flash, send_file, session, jsonify
from db import mysql
from fpdf import FPDF
from funciones import getPerPage
from cuentas import loguear_requerido, administrador_requerido
import os
from MySQLdb import IntegrityError 
from werkzeug.utils import secure_filename
from flask import current_app
from env_vars import paths
from pathlib import Path
from datetime import datetime
incidencia = Blueprint("incidencia", __name__, template_folder="app/templates")
PDFS_INCIDENCIAS = paths['pdf_path']

BASE_DIR = Path(__file__).resolve().parent
INCIDENCIA_ROOT = BASE_DIR / "pdf" / "Incidencias"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _latest_uploaded_file(directory: Path, pattern: str):
    if not directory.exists():
        return None
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _save_incidencia_pdf(file_storage, incidencia_id, prefix="incidencia") -> Path:
    target_dir = INCIDENCIA_ROOT / f"incidencia_{incidencia_id}" / "uploads"
    _ensure_dir(target_dir)
    original_name = secure_filename(file_storage.filename) or "documento.pdf"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{prefix}_{incidencia_id}_{timestamp}_{original_name}"
    file_path = target_dir / filename
    file_storage.save(file_path)
    return file_path

@incidencia.route("/incidencia")
@incidencia.route("/incidencia/<int:page>")
@loguear_requerido
def Incidencia(page=1):
    page = int(page)
    perpage = getPerPage()
    offset = (page - 1) * perpage

    cur = mysql.connection.cursor()

    # Consulta para obtener las incidencias (lógica existente)
    cur.execute("""
        SELECT i.idIncidencia, i.nombreIncidencia, i.observacionIncidencia,
               i.rutaactaIncidencia, i.fechaIncidencia, i.idEquipo,
               e.cod_inventarioEquipo, e.Num_serieEquipo, 
               te.nombreTipo_equipo, me.nombreModeloequipo,
               i.numDocumentos, i.estadoIncidencia
        FROM incidencia i
        INNER JOIN equipo e ON i.idEquipo = e.idEquipo
        INNER JOIN modelo_equipo me ON e.idModelo_Equipo = me.idModelo_Equipo
        INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        ORDER BY 
            CASE 
                WHEN i.estadoIncidencia IN ('pendiente', 'abierta', 'servicio tecnico') THEN 1
                WHEN i.estadoIncidencia IN ('cerrado', 'equipo reparado') THEN 2
                WHEN i.estadoIncidencia = 'equipo cambiado' THEN 3
                ELSE 4
            END,
            i.fechaIncidencia DESC
        LIMIT %s OFFSET %s
    """, (perpage, offset))
    data = cur.fetchall()

    # Consulta para contar el total de incidencias (lógica existente)
    cur.execute('SELECT COUNT(*) AS total FROM incidencia')
    total = cur.fetchone()['total']

    # Nueva consulta para obtener equipos con estado "SIN ASIGNAR" o "EN USO"
    cur.execute("""
        SELECT e.idEquipo, te.nombreTipo_equipo, m.nombreMarcaEquipo, me.nombreModeloequipo,
               e.Cod_inventarioEquipo, e.Num_serieEquipo, u.nombreUnidad, e.ObservacionEquipo
        FROM equipo e
        INNER JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_Equipo
        INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        INNER JOIN marca_equipo m ON mte.idMarca_Equipo = m.idMarca_Equipo
        
        INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        INNER JOIN unidad u ON e.idUnidad = u.idUnidad
        INNER JOIN estado_equipo ee ON e.idEstado_equipo = ee.idEstado_equipo
        WHERE UPPER(TRIM(ee.nombreEstado_equipo)) IN ('SIN ASIGNAR', 'EN USO')
    """)
    equipos_sin_asignar = cur.fetchall()

    cur.close()

    # Calcular la última página para la paginación
    lastpage = (total + perpage - 1) // perpage

    # Renderizar la plantilla con las incidencias y los equipos disponibles
    return render_template(
        "Operaciones/incidencia.html",
        incidencia=data,
        equipos_sin_asignar=equipos_sin_asignar,  # Nueva variable para los equipos
        page=page,
        lastpage=lastpage
    )


@incidencia.route("/incidencia/imprimir")
@loguear_requerido
def imprimir_incidencias():
    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")

    filtros = {
        "q": request.args.get("q", "").strip(),
        "estado": request.args.get("estado", "").strip(),
        "desde": request.args.get("desde", "").strip(),
        "hasta": request.args.get("hasta", "").strip(),
    }

    cur = mysql.connection.cursor()

    query = """
        SELECT i.idIncidencia, i.nombreIncidencia, i.observacionIncidencia,
               i.fechaIncidencia, i.estadoIncidencia,
               e.cod_inventarioEquipo, e.Num_serieEquipo,
               te.nombreTipo_equipo, me.nombreModeloequipo
        FROM incidencia i
        INNER JOIN equipo e ON i.idEquipo = e.idEquipo
        INNER JOIN modelo_equipo me ON e.idModelo_Equipo = me.idModelo_Equipo
        INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        WHERE 1=1
    """

    condiciones = []
    params = []

    if filtros["estado"]:
        condiciones.append("LOWER(i.estadoIncidencia) = %s")
        params.append(filtros["estado"].lower())

    if filtros["desde"]:
        condiciones.append("i.fechaIncidencia >= %s")
        params.append(filtros["desde"])

    if filtros["hasta"]:
        condiciones.append("i.fechaIncidencia <= %s")
        params.append(filtros["hasta"])

    if filtros["q"]:
        term = f"%{filtros['q'].lower()}%"
        condiciones.append(
            "(LOWER(i.nombreIncidencia) LIKE %s OR LOWER(i.observacionIncidencia) LIKE %s OR "
            "LOWER(e.cod_inventarioEquipo) LIKE %s OR LOWER(e.Num_serieEquipo) LIKE %s OR "
            "LOWER(te.nombreTipo_equipo) LIKE %s OR LOWER(me.nombreModeloequipo) LIKE %s)"
        )
        params.extend([term, term, term, term, term, term])

    if condiciones:
        query += " AND " + " AND ".join(condiciones)

    query += " ORDER BY i.fechaIncidencia DESC"

    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()

    return render_template(
        "Operaciones/print_incidencia.html",
        incidencias=data,
        filtros=filtros,
    )



#form que se accede desde equipo para crear incidencia
@incidencia.route("/incidencia/form/<idEquipo>")
@administrador_requerido
def incidencia_form(idEquipo):
    cur = mysql.connection.cursor()
    cur.execute("""
                SELECT *
                FROM super_equipo e
                WHERE e.idEquipo = %s
                """, (idEquipo,))
    equipo = cur.fetchone()
    print("equipo")
    print(equipo)
    return render_template(
        'Operaciones/add_incidencia.html', 
        equipo=equipo
        )

# Ruta para agregar una incidencia
@incidencia.route("/incidencia/add_incidencia", methods=['POST'])
@administrador_requerido
def add_incidencia():

    if "user" not in session:
        flash("No estás autorizado para ingresar a esta ruta", 'warning')
        return redirect("/ingresar")


    if request.method != "POST":
        flash("Método no permitido", "danger")
        return redirect(url_for("incidencia.Incidencia"))
    

    # 1. Recepción de datos del formulario
    datos = {
        'nombreIncidencia': request.form['nombreIncidencia'],
        'observacionIncidencia': request.form['observacionIncidencia'],
        'fechaIncidencia': request.form['fechaIncidencia'],
        'idEquipo': request.form['idEquipo']
    }

    # 2. Validar que el ID del equipo sea válido
    if not datos['idEquipo']:
        flash("Error: No se seleccionó un equipo.", "warning")
        return redirect(url_for("equipo.Equipo"))

    try:
        datos['idEquipo'] = int(datos['idEquipo'])
    except ValueError:
        flash("Error: ID de equipo inválido.", "warning")
        return redirect(url_for("equipo.Equipo"))

    cur = mysql.connection.cursor()

    # 3. Verificar si el equipo existe
    cur.execute("SELECT idEquipo FROM equipo WHERE idEquipo = %s", (datos['idEquipo'],))
    equipo_existente = cur.fetchone()
    if not equipo_existente:
        flash("Error: El equipo no existe.", "warning")
        cur.close()
        return redirect(url_for("equipo.Equipo"))
    
    # 4. Verificar si existe una incidencia activa para el equipo
    cur.execute("""
        SELECT idIncidencia
        FROM incidencia
        WHERE idEquipo = %s
        AND estadoIncidencia IN ('pendiente', 'abierta', 'servicio tecnico') 
    """, (datos['idEquipo'],))
    incidencia_activa = cur.fetchone()
    if incidencia_activa:
        flash("Error: Ya existe una incidencia pendiente para este equipo.", "warning")
        cur.close()
        return redirect(url_for("incidencia.Incidencia"))
    
    # 5. Determinar el nuevo estado del equipo
    estados_incidencia = {
        'Robo': 3,             # Siniestro
        'Perdido': 4,          # Baja
        'Dañado/Averiado': 5   # Dañado
    }
    nuevo_estado = estados_incidencia.get(datos['nombreIncidencia'])

    if nuevo_estado is None:
        flash("Tipo de incidencia inválido.", "warning")
        cur.close()
        return redirect(url_for("incidencia.Incidencia"))

    # 6. Actualizar el estado del equipo
    try:
        cur.execute("""
            UPDATE equipo
            SET idEstado_equipo = %s
            WHERE idEquipo = %s
        """, (nuevo_estado, datos['idEquipo']))
        mysql.connection.commit()
    except Exception as e:
        flash("Error al actualizar el estado del equipo: " + str(e), "danger")
        cur.close()
        return redirect(url_for("incidencia.Incidencia"))

    # 7. Insertar la incidencia en la base de datos
    try:
        cur.execute("""
            INSERT INTO incidencia (
                nombreIncidencia,
                observacionIncidencia,
                rutaactaIncidencia,
                fechaIncidencia,
                idEquipo,
                numDocumentos
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            datos['nombreIncidencia'],
            datos['observacionIncidencia'],
            None,  # Ruta del archivo (se actualizará después)
            datos['fechaIncidencia'],
            datos['idEquipo'],
            0
        ))
        mysql.connection.commit()

        # Obtener el ID de la incidencia recién creada
        cur.execute("SELECT LAST_INSERT_ID() as idIncidencia")
        idIncidencia = cur.fetchone()['idIncidencia']
        datos['idIncidencia'] = idIncidencia

        # Crear el PDF y obtener la ruta
        ruta_pdf = create_pdf(datos)
        if ruta_pdf:
            try:
                cur.execute("""
                    UPDATE incidencia
                    SET rutaactaIncidencia = %s
                    WHERE idIncidencia = %s
                """, (str(ruta_pdf), idIncidencia))
                mysql.connection.commit()
            except Exception as e:
                mysql.connection.rollback()
                flash(f"PDF generado, pero no se pudo registrar la ruta: {e}", "warning")
        flash("Incidencia registrada y PDF generado correctamente.", "success")

    except IntegrityError as e:
        mensaje_error = str(e)
        if "Duplicate entry" in mensaje_error:
            flash("Error: La incidencia ya existe.", "warning")
        else:
            flash("Error de integridad en la base de datos: " + mensaje_error, "danger")
    except Exception as e:
        flash("Error al crear la incidencia: " + str(e), "danger")

    finally:
        cur.close()

    return redirect(url_for("incidencia.Incidencia"))

@incidencia.route("/incidencia/delete_incidencia/<id>", methods=["GET", "POST"])
@administrador_requerido
def delete_incidencia(id):
    # Se asume que la validación de sesión se hace en el decorador @administrador_requerido.
    cur = mysql.connection.cursor()
    try:
        # Verificar el estado de la incidencia
        cur.execute("SELECT estadoIncidencia FROM incidencia WHERE idIncidencia = %s", (id,))
        incidencia = cur.fetchone()

        if not incidencia:
            flash("Error: La incidencia no existe.", "danger")
            return redirect(url_for("incidencia.Incidencia"))

        estado = incidencia['estadoIncidencia']
        estados_validos = ["cerrado", "equipo reparado", "equipo cambiado"]

        if estado not in estados_validos:
            flash(f"Error Solo se permite eliminar incidencias con estado {', '.join(estados_validos)}. Estado actual: '{estado}' ", "warning")
            return redirect(url_for("incidencia.Incidencia"))

        # Eliminar la incidencia si el estado es válido
        cur.execute("DELETE FROM incidencia WHERE idIncidencia = %s", (id,))
        mysql.connection.commit()
        flash("Incidencia eliminada correctamente.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash("Error al eliminar la incidencia: " + str(e), "danger")
    finally:
        cur.close()

    return redirect(url_for("incidencia.Incidencia"))


@incidencia.route("/incidencia/edit_incidencia/<id>", methods=["GET", "POST"])
@administrador_requerido
def edit_incidencia(id):
    if "user" not in session:
        flash("you are NOT authorized")
        return redirect("/ingresar")
    cur = mysql.connection.cursor()
    cur.execute("""
            SELECT *
            FROM incidencia
            WHERE incidencia.idIncidencia = %s
                """, (id,))
    incidencia = cur.fetchone()
    return render_template(
        "Operaciones/edit_incidencia.html", 
        incidencia=incidencia
        )

@incidencia.route("/incidencia/update_incidencia/<id>", methods=["POST"])
@administrador_requerido
def update_incidencia(id):
    if "user" not in session:
        flash("you are NOT authorized")
        return redirect("/ingresar")

    # Obtener datos del formulario
    estadoIncidencia = request.form.get('estadoIncidencia', '').strip()
    nombreIncidencia = request.form.get('nombreIncidencia', '').strip()
    ObservacionIncidencia = request.form.get('observacionIncidencia', '').strip()
    fechaIncidencia = request.form.get('fechaIncidencia', '').strip()

     # Validar si el estado actual permite cambios, para descartar que no sea Cerrado, Equipo cambiado o Equipo reparad
    cur = mysql.connection.cursor()
    cur.execute("SELECT estadoIncidencia FROM incidencia WHERE idIncidencia = %s", (id,))
    estado_actual = cur.fetchone()['estadoIncidencia']

    if estado_actual.lower() in ["cerrado", "equipo cambiado", "equipo reparado"]:
        return redirect(url_for("incidencia.Incidencia"))

    # Si ObservacionIncidencia está vacío, asignar None (para almacenar NULL en la BD)
    if not ObservacionIncidencia:
        ObservacionIncidencia = None

    print(f"DEBUG: Valor recibido para estadoIncidencia: {repr(estadoIncidencia)}")

    # Mapear estados de incidencia a estados de equipo
    estados_equipo = {
        'pendiente': {
            'Robo': 3,              # Siniestro
            'Perdido': 4,           # Baja
            'Dañado/Averiado': 5    # Mantención
        },
        'abierta': {
            'Robo': 3,
            'Perdido': 4,
            'Dañado/Averiado': 5
        },
        'servicio tecnico': 5,       # Mantención
        'equipo reparado': None,     # Depende de si está asignado
        'equipo cambiado': 2,        # En Uso
        'cerrado': None              # Depende de si está asignado
    }

    cur = mysql.connection.cursor()

    # Actualizar la incidencia
    cur.execute("""
        UPDATE incidencia
        SET estadoIncidencia = %s,
            nombreIncidencia = %s,
            observacionIncidencia = %s,
            fechaIncidencia = %s
        WHERE idIncidencia = %s
    """, (estadoIncidencia, nombreIncidencia, ObservacionIncidencia, fechaIncidencia, id))
    mysql.connection.commit()

    # Obtener el ID del equipo relacionado con la incidencia
    cur.execute("SELECT idEquipo FROM incidencia WHERE idIncidencia = %s", (id,))
    equipo = cur.fetchone()
    if not equipo:
        flash("No se encontró el equipo relacionado con la incidencia.", "danger")
        return redirect(url_for("incidencia.Incidencia"))

    idEquipo = equipo['idEquipo']

    # Determinar el nuevo estado del equipo
    nuevo_estado_equipo = None
    if estadoIncidencia in ['pendiente', 'abierta']:
        nuevo_estado_equipo = estados_equipo[estadoIncidencia].get(nombreIncidencia)
    elif estadoIncidencia == 'servicio tecnico':
        nuevo_estado_equipo = estados_equipo['servicio tecnico']
    elif estadoIncidencia in ['equipo reparado', 'cerrado']:
        # Verificar si el equipo está asignado a un funcionario
        cur.execute("""
            SELECT nombreFuncionario
            FROM super_equipo
            WHERE idEquipo = %s
        """, (idEquipo,))
        asignacion = cur.fetchone()
        if asignacion and asignacion['nombreFuncionario']:
            nuevo_estado_equipo = 2  # En Uso
        else:
            nuevo_estado_equipo = 1  # Sin Asignar
    elif estadoIncidencia == 'equipo cambiado':
        nuevo_estado_equipo = estados_equipo['equipo cambiado']

    # Actualizar el estado del equipo si se determinó un nuevo estado
    if nuevo_estado_equipo is not None:
        cur.execute("""
            UPDATE equipo
            SET idEstado_equipo = %s
            WHERE idEquipo = %s
        """, (nuevo_estado_equipo, idEquipo))
        mysql.connection.commit()

    flash("Incidencia y estado del equipo actualizados correctamente.", "success")
    return redirect(url_for("incidencia.Incidencia"))

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@incidencia.route("/incidencia/adjuntar_pdf/<id>", methods=["POST"])
@administrador_requerido
def adjuntar_pdf(id):
    if "user" not in session:
        flash("you are NOT authorized")
        return redirect("/ingresar")

    # Obtener el archivo subido
    file = request.files.get("file")
    if not file or file.filename == '':
        flash("No se seleccionó ningún archivo.", "warning")
        return redirect(url_for("incidencia.Incidencia"))

    # Verificar si el archivo tiene una extensión permitida
    if not allowed_file(file.filename):
        flash("Solo se permiten archivos PDF.", "warning")
        return redirect(url_for("incidencia.Incidencia"))

    cur = mysql.connection.cursor()
    cur.execute("SELECT idIncidencia FROM incidencia WHERE idIncidencia = %s", (id,))
    obj_incidencia = cur.fetchone()

    if not obj_incidencia:
        flash("No se encontró la incidencia.", "danger")
        return redirect(url_for("incidencia.Incidencia"))

    saved_path = _save_incidencia_pdf(file, id)
    try:
        cur.execute("""
            UPDATE incidencia
            SET rutaactaIncidencia = %s
            WHERE idIncidencia = %s
        """, (str(saved_path), id))
        mysql.connection.commit()
        current_app.logger.info("[incidencia.adjuntar_pdf] id=%s guardado=%s", id, saved_path)
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Archivo guardado pero no se pudo registrar la ruta: {e}", "warning")
        return redirect(url_for("incidencia.Incidencia"))

    # Redirigir al listado de PDFs de la incidencia
    flash("El archivo se subió correctamente.", "success")
    return redirect("/incidencia/listar_pdf/" + str(obj_incidencia['idIncidencia']))

@incidencia.route("/incidencia/listar_pdf/<idIncidencia>")
@loguear_requerido
def listar_pdf(idIncidencia):
    base_dir = INCIDENCIA_ROOT / f"incidencia_{idIncidencia}"
    uploads_dir = base_dir / "uploads"

    if not base_dir.exists() and not uploads_dir.exists():
        flash("No hay documentos para esta incidencia.", "warning")
        return redirect(url_for("incidencia.Incidencia"))

    pdf_list = []
    if base_dir.exists():
        pdf_list.extend([p.name for p in base_dir.glob("*.pdf")])
    if uploads_dir.exists():
        pdf_list.extend([p.name for p in uploads_dir.glob("*.pdf")])

    pdfTupla = tuple(pdf_list)

    # 🔄 Actualizar el número de documentos en la base de datos
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE incidencia
        SET numDocumentos = %s
        WHERE idIncidencia = %s
    """, (len(pdfTupla), idIncidencia))
    mysql.connection.commit()

    # 📊 Obtener datos del equipo relacionado con la incidencia
    cur.execute("""
        SELECT * FROM super_equipo WHERE idEquipo = (
            SELECT idEquipo FROM incidencia WHERE idIncidencia = %s
        )
    """, (idIncidencia,))
    data_equipo = cur.fetchone()

    return render_template(
        'Operaciones/mostrar_pdf_incidencia.html', 
        idIncidencia=idIncidencia, 
        documentos=pdfTupla,  # Lista de PDFs encontrados
        equipo=data_equipo, 
        location='incidencia'
    )
            
@incidencia.route("/incidencia/mostrar_pdf/<id>/")
@loguear_requerido
def mostrar_pdf(id):
    if "user" not in session:
        flash("you are NOT authorized")
        return redirect("/ingresar")
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT rutaactaIncidencia FROM incidencia WHERE idIncidencia = %s", (id,))
        row = cur.fetchone()
    finally:
        try:
            cur.close()
        except Exception:
            pass

    base_dir = INCIDENCIA_ROOT / f"incidencia_{id}"
    uploads_dir = base_dir / "uploads"

    ruta_bd = Path(row["rutaactaIncidencia"]).expanduser() if row and row.get("rutaactaIncidencia") else None
    candidates = [
        ruta_bd,
        _latest_uploaded_file(uploads_dir, f"incidencia_{id}_*.pdf"),
        base_dir / f"incidencia_{id}.pdf",
    ]

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            current_app.logger.info("[incidencia.mostrar_pdf] id=%s usando=%s", id, candidate)
            return send_file(candidate, as_attachment=False)

    flash("No se encontró el archivo PDF.", "warning")
    return redirect(url_for("incidencia.Incidencia"))


def create_pdf(incidencia):
    from flask import current_app

    cur = mysql.connection.cursor()

    # 📌 Consultar la información del equipo dentro de esta función
    cur.execute("""
        SELECT nombreTipo_equipo, nombreMarcaEquipo, nombreModeloequipo, Num_serieEquipo, Cod_inventarioEquipo
        FROM super_equipo
        WHERE idEquipo = %s
    """, (incidencia['idEquipo'],))

    equipo = cur.fetchone()

    if not equipo:
        current_app.logger.error(f"No se encontró información del equipo con ID {incidencia['idEquipo']}")
        return None  # Evita errores si no hay equipo

    class PDF(FPDF):
        def header(self):
            self.image('static/img/logo_junji.png', 10, 8, 25)
            self.set_font('Arial', 'B', 12)
            self.set_text_color(50, 50, 50)
            self.cell(0, 10, 'JUNTA NACIONAL DE JARDINES INFANTILES', ln=True, align='C')
            self.cell(0, 10, 'Unidad de Inventarios', ln=True, align='C')
            self.ln(10)

        def footer(self):
            self.set_y(-30)
            self.set_font('Arial', 'I', 10)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, 'Junta Nacional de Jardines Infantiles - JUNJI', ln=True, align='C')
            self.cell(0, 10, 'OHiggins Poniente 77 Concepción - Tel: 041-2125541', ln=True, align='C')
            self.cell(0, 10, 'www.junji.cl', ln=True, align='C')

    # 📂 Crear la carpeta de la incidencia si no existe
    _ensure_dir(INCIDENCIA_ROOT)
    incidencia_folder = _ensure_dir(INCIDENCIA_ROOT / f"incidencia_{incidencia['idIncidencia']}")

    # 📄 Crear el PDF
    pdf = PDF("P", "mm", "A4")
    pdf.add_page()
    pdf.set_font('Arial', '', 12)

    # 📌 Título del documento
    titulo = f"ACTA de Incidencia N° {incidencia['idIncidencia']}"
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.set_font('Arial', '', 12)
    pdf.ln(10)

    # 📌 Información general de la incidencia
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Información de la Incidencia:", ln=True)
    pdf.set_font("Arial", "", 12)

    pdf.cell(50, 10, "Nombre:", border=0)
    pdf.cell(100, 10, incidencia["nombreIncidencia"], border=0, ln=True)

    pdf.cell(50, 10, "Fecha:", border=0)
    pdf.cell(100, 10, incidencia["fechaIncidencia"], border=0, ln=True)

    pdf.ln(10)

    # 📌 Información del equipo afectado
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Equipo Afectado:", ln=True)
    pdf.set_font("Arial", "", 12)

    pdf.cell(50, 10, "Tipo de Equipo:", border=0)
    pdf.cell(100, 10, equipo["nombreTipo_equipo"], border=0, ln=True)

    pdf.cell(50, 10, "Marca:", border=0)
    pdf.cell(100, 10, equipo["nombreMarcaEquipo"], border=0, ln=True)

    pdf.cell(50, 10, "Modelo:", border=0)
    pdf.cell(100, 10, equipo["nombreModeloequipo"], border=0, ln=True)

    pdf.cell(50, 10, "Número de Serie:", border=0)
    pdf.cell(100, 10, equipo["Num_serieEquipo"], border=0, ln=True)

    pdf.cell(50, 10, "Código de Inventario:", border=0)
    pdf.cell(100, 10, equipo["Cod_inventarioEquipo"], border=0, ln=True)

    pdf.ln(10)

    # 📌 Observaciones
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Observaciones:", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, incidencia["observacionIncidencia"])
    pdf.ln(10)

    # 📌 Sección para firmas
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Firmas:", ln=True)
    pdf.ln(15)

    # 📌 Espacio para firmas
    pdf.cell(90, 10, "Nombre del Encargado:", border=0)
    pdf.cell(90, 10, "Nombre del Funcionario:", border=0, ln=True)
    pdf.cell(90, 10, "_____________________________", border=0)
    pdf.cell(90, 10, "_____________________________", border=0, ln=True)
    pdf.ln(5)

    pdf.cell(90, 10, "Firma del Encargado:", border=0)
    pdf.cell(90, 10, "Firma del Funcionario:", border=0, ln=True)
    pdf.cell(90, 10, "_____________________________", border=0)
    pdf.cell(90, 10, "_____________________________", border=0, ln=True)

    # 📄 Guardar el PDF en la carpeta de la incidencia
    nombre_pdf = f"incidencia_{incidencia['idIncidencia']}.pdf"
    ruta_pdf = incidencia_folder / nombre_pdf
    pdf.output(str(ruta_pdf))

    return ruta_pdf

    

@incidencia.route("/incidencia/buscar/<idIncidencia>")
@loguear_requerido
def buscar(idIncidencia):
    if "user" not in session:
        flash("you are NOT authorized")
        return redirect("/ingresar")
    
    cur = mysql.connection.cursor()
    
    # Obtener la incidencia por su ID
    cur.execute("""
        SELECT i.idIncidencia, i.nombreIncidencia, i.observacionIncidencia,
            i.rutaactaIncidencia, i.fechaIncidencia, i.idEquipo,
            e.cod_inventarioEquipo, e.Num_serieEquipo, 
            te.nombreTipo_equipo, me.nombreModeloequipo,
            i.numDocumentos, e.idEquipo
        FROM incidencia i
        INNER JOIN equipo e ON i.idEquipo = e.idEquipo
        INNER JOIN modelo_equipo me ON e.idModelo_Equipo = me.idModelo_Equipo
        INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        WHERE i.idIncidencia = %s
    """, (idIncidencia,))
    data = cur.fetchone()  # Cambiado a fetchone() porque idIncidencia es único.

    # Obtener el total de incidencias
    cur.execute('SELECT COUNT(*) AS total FROM incidencia')
    total = cur.fetchone()['total']  # Simplificado.

    return render_template(
        "Operaciones/incidencia.html", 
        Incidencia=[data],  # Envolvemos en una lista para mantener compatibilidad con el template.
        page=1, 
        lastpage=True
    )

@incidencia.route("/buscar_incidencias", methods=["GET"])
def buscar_incidencias():
    query = request.args.get("q", "").lower()  # Obtener el término de búsqueda
    page = request.args.get("page", default=1, type=int)  # Página actual
    per_page = 10  # Número de resultados por página
    offset = (page - 1) * per_page

    cur = mysql.connection.cursor()

    # Consulta para buscar incidencias
    cur.execute(f"""
        SELECT i.idIncidencia, i.nombreIncidencia, i.observacionIncidencia,
               i.fechaIncidencia, i.estadoIncidencia, e.cod_inventarioEquipo,
               e.Num_serieEquipo, te.nombreTipo_equipo, me.nombreModeloequipo
        FROM incidencia i
        INNER JOIN equipo e ON i.idEquipo = e.idEquipo
        INNER JOIN modelo_equipo me ON e.idModelo_Equipo = me.idModelo_Equipo
        INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        WHERE LOWER(i.nombreIncidencia) LIKE %s
           OR LOWER(i.observacionIncidencia) LIKE %s
           OR LOWER(e.cod_inventarioEquipo) LIKE %s
           OR LOWER(e.Num_serieEquipo) LIKE %s
           OR LOWER(te.nombreTipo_equipo) LIKE %s
           OR LOWER(me.nombreModeloequipo) LIKE %s
        LIMIT %s OFFSET %s
    """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%",
          f"%{query}%", f"%{query}%", per_page, offset))
    incidencias = cur.fetchall()

    # Total de resultados para la búsqueda
    cur.execute(f"""
        SELECT COUNT(*) AS total
        FROM incidencia i
        INNER JOIN equipo e ON i.idEquipo = e.idEquipo
        INNER JOIN modelo_equipo me ON e.idModelo_Equipo = me.idModelo_Equipo
        INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        WHERE LOWER(i.nombreIncidencia) LIKE %s
           OR LOWER(i.observacionIncidencia) LIKE %s
           OR LOWER(e.cod_inventarioEquipo) LIKE %s
           OR LOWER(e.Num_serieEquipo) LIKE %s
           OR LOWER(te.nombreTipo_equipo) LIKE %s
           OR LOWER(me.nombreModeloequipo) LIKE %s
    """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%",
          f"%{query}%", f"%{query}%"))
    total = cur.fetchone()["total"]
    total_pages = (total + per_page - 1) // per_page

    return jsonify({
        "incidencias": incidencias,
        "total": total,
        "total_pages": total_pages,
        "current_page": page
    })
