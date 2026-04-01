from flask import (
    Blueprint,
    render_template,
    request,
    url_for,
    redirect,
    flash,
    send_file,
    session,
    request,
    jsonify,
    current_app,
)
from pathlib import Path
from db import mysql
from fpdf import FPDF
from funciones import getPerPage
import os
import shutil
from cuentas import loguear_requerido, administrador_requerido
from werkzeug.utils import secure_filename
from env_vars import paths

traslado = Blueprint("traslado", __name__, template_folder="app/templates")

BASE_DIR = Path(__file__).resolve().parent
PDF_ROOT = BASE_DIR / "pdf"
TRASLADO_ROOT = PDF_ROOT
FIRMAS_TRASLADOS_DIR = PDF_ROOT / "firmas_traslados"

def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def _get_cursor():
    conn = mysql.connection
    try:
        conn.ping(reconnect=True)
    except Exception:
        pass
    return conn.cursor()

@traslado.route("/traslado")
@traslado.route("/traslado/<int:page>")
@loguear_requerido
def Traslado(page=1):
    if "user" not in session:
        flash("Se necesita ingresar para acceder a esa ruta")
        return redirect("/ingresar")

    page = int(page)
    perpage = getPerPage()
    offset = (page - 1) * perpage

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT t.idTraslado, t.fechatraslado, t.rutadocumentoTraslado, 
               origen.nombreUnidad as nombreOrigen, origen.idUnidad as codigoOrigen,
               destino.nombreUnidad as nombreDestino, destino.idUnidad as codigoDestino,
               t.estaFirmadoTraslado
        FROM traslado t
        INNER JOIN unidad origen on origen.idUnidad = t.idUnidadOrigen
        INNER JOIN unidad destino on destino.idUnidad = t.idUnidadDestino
        ORDER BY idTraslado DESC
        LIMIT %s OFFSET %s
    """, (perpage, offset))
    
    traslados = cur.fetchall()

    # Obtener equipos para cada traslado
    for traslado in traslados:
        cur.execute("""
            SELECT e.idEquipo, me.nombreModeloequipo, te.nombreTipo_equipo, 
                   mae.nombreMarcaEquipo, e.Cod_inventarioEquipo, e.Num_serieEquipo
            FROM traslacion tr
            INNER JOIN equipo e ON tr.idEquipo = e.idEquipo
            INNER JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_equipo
            INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
            INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
            INNER JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
            WHERE tr.idTraslado = %s
        """, (traslado["idTraslado"],))
        traslado["equipos"] = cur.fetchall()

    # Obtener el total de traslados
    cur.execute("SELECT COUNT(*) AS total FROM traslado")
    total = cur.fetchone()['total']
    
    # Calcular la última página
    lastpage = (total + perpage - 1) // perpage

    cur.execute("SELECT * FROM unidad ORDER BY nombreUnidad")
    unidades = cur.fetchall()

    return render_template(
        'Operaciones/traslado.html',
        traslado=traslados,
        unidades=unidades,
        page=page,
        lastpage=lastpage
    )
def getPerPage():
    return 10  # Cambia este número si quieres más o menos resultados por página

@traslado.route("/traslado/equipos_unidad/<int:unidad_id>")
def obtener_equipos_unidad(unidad_id):
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT e.idEquipo, me.nombreModeloequipo, e.Num_serieEquipo, e.Cod_inventarioEquipo,
           te.nombreTipo_equipo, mae.nombreMarcaEquipo
    FROM equipo e
    INNER JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_equipo
    INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
    INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
    INNER JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
    WHERE e.idUnidad = %s 
    AND e.idEstado_equipo IN (
        SELECT idEstado_equipo FROM estado_equipo 
    )
    """, (unidad_id,))

    equipos = cur.fetchall()
    return jsonify(equipos)


@traslado.route("/traslado/add_traslado", methods=["GET", "POST"])
@administrador_requerido
def add_traslado():
    if request.method == "POST":
        Origen = request.form["Origen"]
        if(Origen == ""):
            flash("seleccione un origen")
            return redirect(url_for("traslado.Traslado"))
        Origen = int(Origen)
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                """
                SELECT e.*, 
                    me.nombreModeloequipo, 
                    te.nombreTipo_equipo, 
                    mae.nombreMarcaEquipo, 
                    ee.nombreEstado_equipo,
                    u.nombreUnidad
                FROM equipo e
                INNER JOIN unidad u ON u.idUnidad = e.idUnidad
                INNER JOIN modelo_equipo me ON me.idModelo_equipo = e.idModelo_equipo
                INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
                INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
                INNER JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
                INNER JOIN estado_equipo ee ON e.idEstado_equipo = ee.idEstado_equipo
                WHERE e.idUnidad = %s

                        """,
                (Origen,),
            )
            equipos_data = cur.fetchall()
            cur.execute(
                """
                SELECT * 
                FROM unidad u
                ORDER BY u.nombreUnidad
                        """
            )
            unidades = cur.fetchall()
            if len(equipos_data) == 0:
                equipos_data = []
                flash("no hay equipos en esta Unidad")
                return redirect(url_for("traslado.Traslado"))
            return render_template(
                'Operaciones/add_traslado.html', 
                equipos=equipos_data, 
                unidades=unidades
            )

        except Exception as e:
            flash("Error al crear")
            return redirect(url_for("traslado.Traslado"))


@traslado.route("/traslado/edit_traslado/<id>", methods=["POST", "GET"])
@administrador_requerido
def edit_traslado(id):
    if "user" not in session:
        flash("Se necesita ingresar para acceder a esa ruta")
        return redirect("/ingresar")
    
    if request.method == "POST":
        # Obtener la nueva fecha del formulario
        nueva_fecha = request.form.get("fechaTraslado")
        if not nueva_fecha:
            flash("La fecha de traslado es requerida")
            return redirect(url_for("traslado.Traslado"))
        
        try:
            # Actualizar la fecha del traslado en la base de datos
            cur = mysql.connection.cursor()
            cur.execute(
                """
                UPDATE traslado
                SET fechatraslado = %s
                WHERE idTraslado = %s
                """,
                (nueva_fecha, id),
            )
            mysql.connection.commit()
            flash("Fecha de traslado actualizada correctamente")
        except Exception as e:
            print("Error al actualizar la fecha del traslado:", e)
            flash("Ocurrió un error al actualizar la fecha del traslado")
        finally:
            cur.close()
        
        return redirect(url_for("traslado.Traslado"))
    
    # Si el método es GET, cargar los datos del traslado para renderizar el modal
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            SELECT t.idTraslado, t.fechatraslado
            FROM traslado t
            WHERE t.idTraslado = %s
            """,
            (id,),
        )
        traslado = cur.fetchone()
        return render_template(
            'Operaciones/editTraslado.html',
            traslado=traslado,
        )
    except Exception as e:
        print("Error al cargar los datos del traslado:", e)
        flash("Ocurrió un error al cargar los datos del traslado")
        return redirect(url_for("traslado.Traslado"))


@traslado.route("/traslado/delete_multiple", methods=["POST"])
@administrador_requerido
def delete_multiple_traslados():
    data = request.get_json()
    traslados = data.get("traslados", [])

    if not traslados:
        return jsonify({"success": False, "message": "No se proporcionaron traslados para eliminar."}), 400

    try:
        cur = mysql.connection.cursor()

        for id in traslados:
            # Obtener información del traslado
            cur.execute("SELECT * FROM traslado WHERE idTraslado = %s", (id,))
            trasladoABorrar = cur.fetchone()

            if trasladoABorrar:
                # Obtener equipos en la traslación
                cur.execute("SELECT * FROM traslacion WHERE idTraslado = %s", (id,))
                traslaciones = cur.fetchall()

                # Restaurar la unidad original de cada equipo
                for traslacion in traslaciones:
                    cur.execute(
                        """
                        UPDATE equipo
                        SET idUnidad = %s
                        WHERE idEquipo = %s 
                        """,
                        (trasladoABorrar["idUnidadOrigen"], traslacion["idEquipo"]),
                    )

                # Eliminar registros en traslacion
                cur.execute("DELETE FROM traslacion WHERE idTraslado = %s", (id,))

                # Eliminar el traslado
                cur.execute("DELETE FROM traslado WHERE idTraslado = %s", (id,))

        mysql.connection.commit()
        cur.close()

        return jsonify({"success": True, "message": "Traslados eliminados correctamente."})

    except Exception as e:
        print("Error:", e)
        return jsonify({"success": False, "message": "Error en la eliminación de traslados."}), 500


def get_unidad_nombre(unidad_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT nombreUnidad FROM unidad WHERE idUnidad = %s", (unidad_id,))
    result = cur.fetchone()
    return result["nombreUnidad"] if result else "Desconocido"



@traslado.route("/traslado/create_traslado/<int:origen>", methods=["POST"])
@administrador_requerido
def create_traslado(origen):
    fechatraslado = request.form["fechatraslado"]
    destino = request.form["Destino"]
    equipos = request.form.getlist("trasladar[]")

    if destino == str(origen):  # Convertimos origen a str para evitar errores de comparación
        return jsonify({"success": False, "message": "El destino no puede ser igual al origen"}), 400

    if not destino or not equipos:
        return jsonify({"success": False, "message": "Destino o equipos no seleccionados"}), 400

    traslado_id = crear_traslado_generico(fechatraslado, destino, origen, equipos)

    return jsonify({
        "success": True,
        "idTraslado": traslado_id,
        "fechatraslado": fechatraslado,
        "nombreOrigen": get_unidad_nombre(origen),
        "nombreDestino": get_unidad_nombre(destino)
    })



##funcion para crear un traslado
def crear_traslado_generico(fechatraslado, Destino, Origen, equipos):
    if not equipos:
        return None

    equipos_ids = [int(e) for e in equipos if str(e).strip().isdigit()]
    if not equipos_ids:
        return None

    cur = _get_cursor()
    try:
        cur.execute("START TRANSACTION")

        cur.execute(
            """
            INSERT INTO traslado (
                fechatraslado,
                rutadocumentoTraslado,
                idUnidadDestino,
                idUnidadOrigen
            )
            VALUES (%s, %s, %s, %s)
            """,
            (fechatraslado, "ruta", Destino, Origen),
        )
        trasladoid = cur.lastrowid

        cur.executemany(
            """
            INSERT INTO traslacion (
                idTraslado,
                idEquipo
            )
            VALUES (%s, %s)
            """,
            [(str(trasladoid), idEquipo) for idEquipo in equipos_ids],
        )

        placeholders = ", ".join(["%s"] * len(equipos_ids))
        cur.execute(
            "UPDATE equipo SET idUnidad = %s WHERE idEquipo IN (" + placeholders + ")",
            tuple([Destino] + equipos_ids),
        )

        cur.execute(
            """
            SELECT e.*, 
                me.nombreModeloequipo, 
                te.nombreTipo_equipo, 
                mae.nombreMarcaEquipo, 
                ee.nombreEstado_equipo
            FROM equipo e
            INNER JOIN modelo_equipo me ON me.idModelo_equipo = e.idModelo_equipo
            INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
            INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
            INNER JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
            INNER JOIN estado_equipo ee ON ee.idEstado_equipo = e.idEstado_equipo
            WHERE e.idEquipo IN ("""
            + placeholders
            + ")",
            tuple(equipos_ids),
        )
        equipos_lista = cur.fetchall()

        cur.execute(
            """
            SELECT idTraslado, fechatraslado, idUnidadOrigen, idUnidadDestino
            FROM traslado
            WHERE idTraslado = %s
            """,
            (str(trasladoid),),
        )
        traslado = cur.fetchone()

        cur.execute(
            """
            SELECT idUnidad, nombreUnidad
            FROM unidad
            WHERE idUnidad IN (%s, %s)
            """,
            (traslado["idUnidadOrigen"], traslado["idUnidadDestino"]),
        )
        unidades = cur.fetchall()
        unidades_map = {u["idUnidad"]: u for u in unidades}
        UnidadOrigen = unidades_map.get(traslado["idUnidadOrigen"])
        UnidadDestino = unidades_map.get(traslado["idUnidadDestino"])

        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass

    flash("traslado agregado correctamente")
    try:
        create_pdf(traslado, equipos_lista, UnidadOrigen, UnidadDestino, UnidadDestino, UnidadOrigen)
    except Exception as e:
        current_app.logger.error(
            "[traslado.create] error pdf traslado id=%s error=%s",
            traslado.get("idTraslado") if isinstance(traslado, dict) else traslado,
            e,
        )
    return trasladoid

def create_pdf(traslado, equipos, UnidadOrigen, UnidadDestino,idUnidadDestino,idUnidadOrigen):
    print("create_pdf")

    class PDF(FPDF):
        def header(self):

            self.image("static/img/logo_junji.png", 10, 8, 32)
            # font
            self.set_font("times", "B", 12)
            self.set_text_color(170, 170, 170)
            # Title
            self.cell(0, 30, "", border=False, ln=1, align="L")
            self.cell(0, 5, "JUNTA NACIONAL", border=False, ln=1, align="L")
            self.cell(0, 5, "INFANTILES", border=False, ln=1, align="L")
            self.cell(0, 5, "Unidad de Inventarios", border=False, ln=1, align="L")
            # line break
            self.ln(10)
            pass

        def footer(self):
            self.set_y(-30)
            self.set_font("times", "B", 12)
            self.set_text_color(170, 170, 170)
            self.cell(0, 0, "", ln=1)
            self.cell(0, 0, "Junta Nacional de Jardines Infantiles-JUNJI", ln=1)
            self.cell(
                0, 12, "OHiggins Poniente 77 Concepción. Tel: 412125579", ln=1
            )  # problema con el caracter ’
            self.cell(0, 12, "www.junji.cl", ln=1)
            pass

    pdf = PDF("P", "mm", "A4")

    pdf.add_page()

    titulo = "ACTA DE TRASLADO N°" + str(traslado["idTraslado"])
    creado_por = "Documento creado por: " + session["user"]
    parrafo_1 = "En Concepción {}, se procede al traslado de bienes JUNJI de registro inventario desde {}:{} hasta {}:{} el siguiente detalle: ".format(
        traslado["fechatraslado"],
        idUnidadOrigen["idUnidad"],
        UnidadOrigen["nombreUnidad"],
        idUnidadDestino["idUnidad"],
        UnidadDestino["nombreUnidad"],
    )
    # encabezado de la tabla
    TABLE_DATA = [
    ("N°", "Articulos", "Serie", "Código Inventario", "Estado", "Modelo"),
    ]

    # ingresa los datos de la tabla como una tupla, donde la primera tupla es el encabezado
    for i, equipo in enumerate(equipos, start=1):
        TABLE_DATA.append((
            str(i),
            equipo["nombreTipo_equipo"],
            equipo["Num_serieEquipo"],
            str(equipo["Cod_inventarioEquipo"]),
            str(equipo["nombreEstado_equipo"]),
            equipo ["nombreModeloequipo"],
        ))
    pdf.set_font("times", "", 20)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.set_font("times", "", 12)
    pdf.cell(0, 10, creado_por, ln=True, align="L")

    pdf.multi_cell(0, 10, parrafo_1)
    # crea una tabla en base a los datos anteriores
    with pdf.table() as table:
        for datarow in TABLE_DATA:
            row = table.row()
            for datum in datarow:
                row.cell(datum)

                

    pdf.ln(10)
    nombreEncargado = "Nombre del encargado TI:"
    rutEncargado = "RUT:"
    firmaEncargado = "Firma:"
    nombreMinistro = "Nombre del funcionario:"
    rutMinistro = "RUT:"
    firma = "Firma:"
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
        cols.ln() # <-- Aquí se muestra la observación real
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
    # crear pdf con la id para diferenciar pdfs

    # crear pdf con la id para diferenciar pdfs
    nombrePdf = f"traslado_{traslado['idTraslado']}.pdf"
    file_path = TRASLADO_ROOT / nombrePdf
    
    # Asegurar que la carpeta exista
    _ensure_dir(TRASLADO_ROOT)
    
    # fpdf.output() puede tomar un string de la ruta completa
    pdf.output(str(file_path))
    
    return redirect(url_for("traslado.Traslado"))


@traslado.route("/traslado/imprimir")
@loguear_requerido
def imprimir_traslado():
    if "user" not in session:
        flash("Se necesita ingresar para acceder a esa ruta", "warning")
        return redirect("/ingresar")

    filtros = {
        "q": request.args.get("q", "").strip(),
        "origen": request.args.get("origen", "").strip(),
        "destino": request.args.get("destino", "").strip(),
        "desde": request.args.get("desde", "").strip(),
        "hasta": request.args.get("hasta", "").strip(),
    }

    cur = mysql.connection.cursor()
    cur.execute("SELECT idUnidad, nombreUnidad FROM unidad")
    unidades = {str(u["idUnidad"]): u["nombreUnidad"] for u in cur.fetchall()}

    query = """
        SELECT t.idTraslado, t.fechatraslado,
               origen.nombreUnidad AS nombreOrigen, origen.idUnidad AS codigoOrigen,
               destino.nombreUnidad AS nombreDestino, destino.idUnidad AS codigoDestino
        FROM traslado t
        INNER JOIN unidad origen ON origen.idUnidad = t.idUnidadOrigen
        INNER JOIN unidad destino ON destino.idUnidad = t.idUnidadDestino
        WHERE 1=1
    """

    condiciones = []
    params = []

    if filtros["origen"]:
        condiciones.append("t.idUnidadOrigen = %s")
        params.append(filtros["origen"])

    if filtros["destino"]:
        condiciones.append("t.idUnidadDestino = %s")
        params.append(filtros["destino"])

    if filtros["desde"]:
        condiciones.append("t.fechatraslado >= %s")
        params.append(filtros["desde"])

    if filtros["hasta"]:
        condiciones.append("t.fechatraslado <= %s")
        params.append(filtros["hasta"])

    if filtros["q"]:
        term = f"%{filtros['q'].lower()}%"
        condiciones.append(
            "(LOWER(origen.nombreUnidad) LIKE %s OR LOWER(destino.nombreUnidad) LIKE %s)"
        )
        params.extend([term, term])

    if condiciones:
        query += " AND " + " AND ".join(condiciones)

    query += " ORDER BY t.idTraslado DESC"

    cur.execute(query, params)
    traslados = cur.fetchall()

    for row in traslados:
        cur.execute(
            """
                SELECT e.idEquipo, me.nombreModeloequipo, te.nombreTipo_equipo,
                       mae.nombreMarcaEquipo, e.Cod_inventarioEquipo, e.Num_serieEquipo
                FROM traslacion tr
                INNER JOIN equipo e ON tr.idEquipo = e.idEquipo
                INNER JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_equipo
                INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
                INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
                INNER JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
                WHERE tr.idTraslado = %s
            """,
            (row["idTraslado"],),
        )
        row["equipos"] = cur.fetchall()

    cur.close()

    filtros["origen_nombre"] = unidades.get(filtros["origen"], None)
    filtros["destino_nombre"] = unidades.get(filtros["destino"], None)

    return render_template(
        "Operaciones/print_traslado.html",
        traslados=traslados,
        filtros=filtros,
    )


@traslado.route("/traslado/mostrar_pdf/<id>")
@traslado.route("/traslado/mostrar_pdf/<id>/<firmado>")
@loguear_requerido
def mostrar_pdf(id, firmado="0"):
    if "user" not in session:
        flash("Se necesita ingresar para acceder a esa ruta")
        return redirect("/ingresar")

    nombrePDF = f"traslado_{id}.pdf" if firmado == "0" else f"traslado_{id}_firmado.pdf"
    
    if firmado == "0":
        file_path = TRASLADO_ROOT / nombrePDF
    else:
        file_path = FIRMAS_TRASLADOS_DIR / nombrePDF

    if not file_path.exists():
        flash(f"El archivo PDF {nombrePDF} no se encuentra disponible.")
        return redirect("/traslado")

    return send_file(str(file_path), as_attachment=False)

@traslado.route("/traslado/buscar/<idTraslado>")
@loguear_requerido
def buscar(idTraslado):
    if "user" not in session:
        flash("Se nesesita ingresar para acceder a esa ruta")
        return redirect("/ingresar")
    cur = mysql.connection.cursor()
    cur.execute(
        """
                SELECT t.idTraslado, t.fechatraslado, t.rutadocumentoTraslado, 
                    origen.nombreUnidad as nombreOrigen, 
                    destino.nombreUnidad as nombreDestino,
                    t.estaFirmadoTraslado
                FROM traslado t
                INNER JOIN unidad origen on origen.idUnidad = t.idUnidadOrigen
                INNER JOIN unidad destino on destino.idUnidad = t.idUnidadDestino
                WHERE t.idTraslado = %s
                ORDER BY idTraslado DESC
        """,
        (idTraslado,),
    )
    data = cur.fetchall()

    cur.execute(
        """
        SELECT * 
        FROM unidad u
        ORDER BY u.nombreUnidad
                 """
    )
    unidades = cur.fetchall()

    return render_template(
        'Operaciones/traslado.html', 
        traslado=data, 
        unidades=unidades, 
        page=1, 
        lastpage=True
    )


@traslado.route("/traslado/listar_pdf/<idTraslado>")
@traslado.route("/traslado/listar_pdf/<idTraslado>/<devolver>")
@loguear_requerido
def listar_pdf(idTraslado, devolver="None"):
    if "user" not in session:
        flash("Se necesita ingresar para acceder a esa ruta")
        return redirect("/ingresar")

    dir = "pdf"   

    if devolver == "None":
        nombreFirmado = "traslado_" + str(idTraslado) + "_" + "firmado.pdf"
        location = "traslado"
    else:
        nombreFirmado = "devolucion_" + str(idTraslado) + "_" + "firmado.pdf"
        location = "devolucion"

    # Revisa si el archivo está firmado
    if not os.path.exists(os.path.join(dir, "firmas_traslados", nombreFirmado)) and not os.path.exists(os.path.join(dir, "firmas_devoluciones", nombreFirmado)):
        # Si no existe el archivo firmado
        nombreFirmado = "No existen firmas para este documento"
    
    return render_template(
        'GestionR.H/firma.html',
        nombreFirmado=nombreFirmado,
        id=idTraslado,
        location=location
    )



@traslado.route("/traslado/mostrar_pdf/<id>/")
@loguear_requerido
def mostrar_pdf_traslado_firmado(id):
    if "user" not in session:
        flash("Se necesita ingresar para acceder a esta ruta")
        return redirect("/ingresar")
    
    try:
        # Definir el nombre del archivo PDF basado en el ID
        nombrePDF = f"traslado_{id}_firmado.pdf"
        file_path = FIRMAS_TRASLADOS_DIR / nombrePDF

        # Verificar si el archivo existe antes de enviarlo
        if not file_path.exists():
            flash("No se encontró el archivo PDF solicitado.")
            return redirect(url_for("traslado.Traslado"))

        # Si el archivo existe, enviarlo para su visualización
        return send_file(str(file_path), as_attachment=False)

    except FileNotFoundError:
        flash("El archivo PDF no se encuentra en el servidor.")
        return redirect(url_for('traslado.listar_pdf', idTraslado=id))  # Redirige en caso de error con el archivo

    except Exception as e:
        # Captura cualquier otra excepción y muestra un mensaje genérico
        flash(f"Error al intentar mostrar el archivo: {str(e)}")
        return redirect(url_for('traslado.listar_pdf', idTraslado=id))  # Redirige en caso de cualquier otro error

    

# Ruta para subir un archivo PDF relacionado con el traslado
@traslado.route("/traslado/adjuntar_pdf/<idTraslado>", methods=["POST"])
@administrador_requerido
def adjuntar_pdf_traslado(idTraslado):
    if "user" not in session:
        flash("You are NOT authorized")
        return redirect("/ingresar")
        
    # Asegurar que la carpeta de firmas exista
    _ensure_dir(FIRMAS_TRASLADOS_DIR)

    # Nombre del archivo que debe eliminarse si ya existe
    filename = f"traslado_{idTraslado}_firmado.pdf"
    file_path = FIRMAS_TRASLADOS_DIR / filename

    # Verificar si el archivo ya existe y eliminarlo
    if file_path.exists():
        file_path.unlink()

    # Obtener el archivo desde la solicitud
    file = request.files["file"]

    # Guardar el archivo directamente
    file.save(str(file_path))
    
    # Actualizar la base de datos para reflejar que el traslado está firmado
    # Se asigna un valor de 1 si se ha subido el archivo de firma
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE traslado SET estaFirmadoTraslado = 1 WHERE idTraslado = %s",
            (idTraslado,)
        )
        mysql.connection.commit()
    except Exception as e:
        print(f"Error al actualizar el estado del traslado: {e}")

    flash("PDF adjuntado correctamente")
    # Redirigir a la lista de traslados(tabla)
    return redirect(url_for("traslado.Traslado"))
    #cambiado [ f"/traslado/listar_pdf/{idTraslado}" ]
    

#obtener los datos en fomato json sobre si presenta firma el traslado
@traslado.route("/traslado/firmas_json/<idTraslado>")
@loguear_requerido
def obtener_firma_json(idTraslado):
    nombre = f"traslado_{idTraslado}_firmado.pdf"
    ruta = FIRMAS_TRASLADOS_DIR / nombre
    #devuelve un resultado en formato json si tiene o no firma el traslado
    if ruta.exists():
        return jsonify({"existe":True,"nombre":nombre})
    else:
        return jsonify({"Existe":False})
    


#Obtener los detalles del traslado en formato json 
@traslado.route("/traslado/detalles_json/<idTraslado>")
@loguear_requerido
def obtener_detalles_traslado(idTraslado):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT t.idTraslado, t.fechatraslado, t.rutadocumentoTraslado, 
               origen.nombreUnidad as nombreOrigen, 
               destino.nombreUnidad as nombreDestino,
               t.estaFirmadoTraslado,me.nombreModeloequipo,
                te.nombreTipo_equipo as nombreEquipo,
                origen.direccionUnidad as direccionOrigen,
                origen.idUnidad as CodigoUnidad, destino.direccionUnidad as direccionDestino,
                destino.idUnidad as codigoDestino, mae.nombreMarcaEquipo as marcaEquipo,
                e.Num_SerieEquipo as numeroSerie, e.Cod_inventarioEquipo as codigoInventario        
         FROM traslado t
        INNER JOIN unidad origen ON origen.idUnidad = t.idUnidadOrigen
        INNER JOIN unidad destino ON destino.idUnidad = t.idUnidadDestino
        INNER JOIN traslacion tr ON tr.idTraslado = t.idTraslado
        INNER JOIN equipo e ON tr.idEquipo = e.idEquipo
        INNER JOIN modelo_equipo me ON e.idModelo_equipo = me.idModelo_equipo
        INNER JOIN marca_tipo_equipo mte ON me.idMarca_Tipo_Equipo = mte.idMarcaTipo
        INNER JOIN tipo_equipo te ON mte.idTipo_equipo = te.idTipo_equipo
        INNER JOIN marca_equipo mae ON mte.idMarca_Equipo = mae.idMarca_Equipo
        WHERE t.idTraslado = %s
    """, (idTraslado,),)
    
    traslado = cur.fetchone()
    
    if not traslado:
        return jsonify({"error": "Traslado no encontrado"}), 404
    #Se obtiene información del traslado en formato json
    return jsonify({
        "traslado":traslado
    })
