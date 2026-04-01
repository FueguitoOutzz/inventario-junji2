let debounceTimeout;

function getAsignacionesSearchUrl() {
    const input = document.getElementById("buscador_asignaciones");
    if (input && input.dataset && input.dataset.searchUrl) {
        return input.dataset.searchUrl;
    }
    return "/buscar_asignaciones";
}

function buscarAsignaciones(page = 1) {
    clearTimeout(debounceTimeout);

    debounceTimeout = setTimeout(() => {
        const input = document.getElementById("buscador_asignaciones");
        const query = input ? input.value.toLowerCase().trim() : "";
        const searchUrl = getAsignacionesSearchUrl();

        fetch(`${searchUrl}?q=${encodeURIComponent(query)}&page=${page}`)
            .then((response) => {
                if (!response.ok) throw new Error("Error al buscar asignaciones");
                return response.json();
            })
            .then((data) => {
                const asignaciones = Array.isArray(data.asignaciones) ? data.asignaciones : [];

                // ✅ Para que el conteo/orden quede consistente con la vista: ascendente por idEquipoAsignacion
                asignaciones.sort(
                    (a, b) => Number(a.idEquipoAsignacion) - Number(b.idEquipoAsignacion)
                );

                actualizarTablaAsignaciones(asignaciones);
                // actualizarPaginacion(data.total_pages, data.current_page, query);
            })
            .catch((error) => console.error("Error al buscar asignaciones:", error));
    }, 300);
}


function actualizarTablaAsignaciones(asignaciones) {
    const tbody = document.getElementById("myTableBody");
    tbody.innerHTML = ""; // Limpiar la tabla

    if (!Array.isArray(asignaciones) || asignaciones.length === 0) {
        tbody.innerHTML =
            '<tr><td colspan="10" class="text-center">No hay datos disponibles.</td></tr>';
        actualizarBotonesBarraSuperior();
        return;
    }

    // ✅ Orden ascendente por el ID que se muestra en la tabla (idEquipoAsignacion)
    const asignacionesOrdenadas = [...asignaciones].sort((a, b) => {
        const detA = Number(a.idEquipoAsignacion) || 0;
        const detB = Number(b.idEquipoAsignacion) || 0;
        return detA - detB;
    });

    asignacionesOrdenadas.forEach((asig) => {
        const row = document.createElement("tr");

        // ✅ Mantener atributos como en HTML
        row.id = `row-${asig.idEquipoAsignacion}`;
        row.classList.add("selectable-row");
        row.setAttribute("data-marca-equipo", asig.nombreMarcaEquipo || "");
        row.setAttribute("data-modelo-equipo", asig.nombreModeloequipo || "");
        row.setAttribute("data-id-equipo", asig.idEquipo || "");
        row.setAttribute("data-tipo-equipo", asig.nombreTipo_equipo || "");

        const obs = asig.ObservacionEquipo || '';
        const obsTruncated = obs.length > 30 ? obs.substring(0, 30) + '...' : (obs || '-');

        row.innerHTML = `
      <td>
        <input type="checkbox" class="checkbox-table row-checkbox no-delete-value"
          value="${asig.idEquipoAsignacion || ""}"
                    data-id-equipo="${asig.idEquipo || ""}"
          data-id-devolucion="${asig.idDevolucion || ""}"
          data-id-asignacion="${asig.idAsignacion || ""}"
          data-devuelto="${asig.fechaDevolucion ? "true" : "false"}">
      </td>

      <!-- ✅ ID igual al HTML: idEquipoAsignacion (NO idAsignacion) -->
      <td class="toCheck">${asig.idEquipoAsignacion || "-"}</td>

      <td class="toCheck">${asig.nombreFuncionario || "-"}</td>
      <td class="toCheck">${asig.rutFuncionario || "-"}</td>
      <td class="toCheck">${asig.nombreTipo_equipo || "-"}</td>
      <td class="toCheck">${asig.Cod_inventarioEquipo || "-"}</td>
      <td class="toCheck" data-bs-toggle="tooltip" title="${obs}">
        ${obsTruncated}
      </td>
      <td class="toCheck">${formatFecha(asig.fecha_inicioAsignacion)}</td>
      <td class="toCheck">${asig.fechaDevolucion ? formatFecha(asig.fechaDevolucion) : "Sin devolver"}</td>

      <td class="d-flex justify-content-center gap-2">
        <div data-bs-toggle="tooltip" data-bs-title="Detalles">
          <button class="btn button-info" type="button"
            data-id-equipo-asignacion="${asig.idEquipoAsignacion || ""}"
            data-id-asignacion="${asig.idAsignacion || ""}">
            <i class="bi bi-info-circle"></i>
          </button>
        </div>

        <!-- ✅ Delete igual a tu HTML actual: borrar solo este equipo -->
        <button class="btn btn-danger delete-button" data-bs-toggle="tooltip"
          data-url="/delete_equipo_asignacion/${asig.idEquipoAsignacion || ""}"
          data-title="Confirmar eliminación"
          data-message="¿Eliminar solo este equipo de la asignación?"
          data-bs-title="Eliminar">
          <i class="bi bi-trash-fill"></i>
        </button>
      </td>
    `;

        tbody.appendChild(row);
    });

    // Vuelve a enlazar eventos y refrescar botones
    rebindCheckboxEvents();
    actualizarBotonesBarraSuperior();
}

function formatFecha(fecha) {
    if (!fecha) return '-';
    try {
        const d = new Date(fecha);
        if (isNaN(d.getTime())) return '-';
        const day = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const year = d.getFullYear();
        return `${day}-${month}-${year}`;
    } catch (error) {
        return "-";
    }
}

function renderActasFirmadas(actas) {
    const tbody = document.getElementById("tablaFirmasBody");
    if (!tbody) return;

    tbody.innerHTML = "";
    const listado = Array.isArray(actas) ? actas : [];

    if (!listado.length) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center">sin actas</td></tr>`;
        return;
    }

    listado.forEach((acta) => {
        const equipoLabel = acta.equipoId ? `Equipo ${acta.equipoId}` : (acta.tipoEquipo || "-");
        const fecha = acta.uploadedAt ? new Date(acta.uploadedAt).toLocaleString() : "-";

        const fila = document.createElement("tr");
        fila.innerHTML = `
            <td>${acta.filename || ""}</td>
            <td>${equipoLabel}</td>
            <td>${fecha}</td>
            <td>
                <a href="${acta.url}" class="btn btn-primary info-button" target="_blank">Ver</a>
            </td>
        `;
        tbody.appendChild(fila);
    });
}


function abrirModalFirmarAsignacion() {
    const modalFirmarAsignacion = new bootstrap.Modal(document.getElementById("modalFirmarAsignacion"));
    let idSeleccionado = null;
    let equipoSeleccionado = "";
    let tipoEquipoSeleccionado = "";

    // Capturar el ID del ítem seleccionado
    document.querySelectorAll(".row-checkbox").forEach(checkbox => {
        if (checkbox.checked) {
            idSeleccionado = checkbox.getAttribute("data-id-asignacion");
            equipoSeleccionado = checkbox.getAttribute("data-id-equipo") || "";
            const row = checkbox.closest("tr");
            tipoEquipoSeleccionado = row?.getAttribute("data-tipo-equipo") || "";
        }
    });

    if (!idSeleccionado) {
        alert("Por favor, selecciona un ítem antes de continuar.");
        return;
    }

    // Mostrar el ID en el modal
    const idSpan = document.getElementById("idAsignacionSeleccionada");
    idSpan.textContent = idSeleccionado;

    const form = document.getElementById("formSubirFirma");
    form.action = `/asignacion/adjuntar_pdf/${idSeleccionado}`;
    form.reset(); // Limpiar el formulario antes de abrir el modal

    const equipoInput = document.getElementById("equipoIdSeleccionado");
    const tipoEquipoInput = document.getElementById("tipoEquipoSeleccionado");
    const equipoLabel = document.getElementById("equipoSeleccionLabel");

    if (equipoInput) equipoInput.value = equipoSeleccionado;
    if (tipoEquipoInput) tipoEquipoInput.value = tipoEquipoSeleccionado;
    if (equipoLabel) {
        const textoEquipo = equipoSeleccionado ? `${tipoEquipoSeleccionado || "Equipo"} #${equipoSeleccionado}` : (tipoEquipoSeleccionado || "Equipo no especificado");
        equipoLabel.textContent = textoEquipo;
    }
    // Abrir el modal
    modalFirmarAsignacion.show();
    // Limpiar contenido anterior
    const tbody = document.getElementById("tablaFirmasBody");
    tbody.innerHTML = `<tr><td colspan="4" class="text-center">Buscando archivo...</td></tr>`;

    // Obtener detalles, equipo y actas
    fetch(`/asignacion/detalles_json/${idSeleccionado}`)
        .then(res => res.json())
        .then(data => {
            const d = data.asignacion;

            document.getElementById("detalleID").textContent = d.idAsignacion;
            document.getElementById("rutFuncionario").textContent = d.rutFuncionario;
            document.getElementById("nombreFuncionario").textContent = d.nombreFuncionario;
            document.getElementById("cargoFuncionario").textContent = d.cargoFuncionario;

            document.getElementById("fechaAsignacion").textContent = formatFecha(d.fecha_inicioAsignacion);
            document.getElementById("fechaDevolucion").textContent = d.fechaDevolucion ? formatFecha(d.fechaDevolucion) : "Sin devolver";
            document.getElementById("observacionesAsignacion").textContent = d.ObservacionAsignacion || "-";

            document.getElementById("tipoEquipo").textContent = d.nombreTipo_equipo;
            document.getElementById("marcaEquipo").textContent = d.nombreMarcaEquipo;
            document.getElementById("modeloEquipo").textContent = d.nombreModeloequipo;
            document.getElementById("codigoInventario").textContent = d.Cod_inventarioEquipo;
            document.getElementById("numeroSerie").textContent = d.Num_serieEquipo;
            document.getElementById("codigoProveedor").textContent = d.codigoproveedor_equipo || "No informado";
            document.getElementById("observacionesEquipo").textContent = d.ObservacionEquipo || "-";

            renderActasFirmadas(data.actasFirmadas || []);
        })
        .catch((error) => {
            console.error("Error al cargar detalles de la asignación", error);
            renderActasFirmadas([]);
        });

}

function abrirModalFirmarDevolucion() {
    const modal = new bootstrap.Modal(document.getElementById("modalFirmarDevolucion"));
    let idAsignacion = null;

    document.querySelectorAll(".row-checkbox").forEach(checkbox => {
        if (checkbox.checked) {
            idAsignacion = checkbox.getAttribute("data-id-asignacion");
        }
    });

    if (!idAsignacion) {
        alert("Por favor, selecciona un ítem antes de continuar.");
        return;
    }

    // Mostrar el ID
    document.getElementById("detalleIDDevolucion").textContent = idAsignacion;

    // Configurar formulario
    const form = document.getElementById("formSubirFirmaDevolucion");
    form.action = `/devolucion/adjuntar_pdf/${idAsignacion}`;
    form.reset();

    // Mostrar modal
    modal.show();

    // Cargar detalles
    fetch(`/asignacion/detalles_json/${idAsignacion}`)
        .then(res => res.json())
        .then(data => {
            const d = data.asignacion;

            document.getElementById("rutFuncionarioDevolucion").textContent = d.rutFuncionario;
            document.getElementById("nombreFuncionarioDevolucion").textContent = d.nombreFuncionario;
            document.getElementById("cargoFuncionarioDevolucion").textContent = d.cargoFuncionario;

            document.getElementById("fechaAsignacionDevolucion").textContent = formatFecha(d.fecha_inicioAsignacion);
            document.getElementById("fechaDevolucionDevolucion").textContent = d.fechaDevolucion ? formatFecha(d.fechaDevolucion) : "Sin devolver";
            document.getElementById("observacionesDevolucion").textContent = d.ObservacionAsignacion || "-";

            document.getElementById("tipoEquipoDevolucion").textContent = d.nombreTipo_equipo;
            document.getElementById("marcaEquipoDevolucion").textContent = d.nombreMarcaEquipo;
            document.getElementById("modeloEquipoDevolucion").textContent = d.nombreModeloequipo;
            document.getElementById("codigoInventarioDevolucion").textContent = d.Cod_inventarioEquipo;
            document.getElementById("numeroSerieDevolucion").textContent = d.Num_serieEquipo;
            document.getElementById("codigoProveedorDevolucion").textContent = d.codigoproveedor_equipo || "No informado";
            document.getElementById("observacionesEquipoDevolucion").textContent = d.ObservacionEquipo || "-";
        });

    // Cargar archivo ya subido (si existe)
    const tbody = document.getElementById("tablaFirmasBodyDevolucion");
    tbody.innerHTML = `<tr><td colspan="2" class="text-center">Buscando archivo...</td></tr>`;

    fetch(`/asignacion/firmas_devolucion_json/${idAsignacion}`)
        .then(res => res.json())
        .then(data => {
            tbody.innerHTML = "";
            if (data.existe) {
                tbody.innerHTML = `
                    <td>${data.nombre}</td>
                    <td><a href="/devolucion/mostrar_pdf/${idAsignacion}/" class="btn btn-primary info-button" target="_blank">Abrir</a></td>
                `;
            } else {
                tbody.innerHTML = `<tr><td colspan="2" class="text-center">No existen firmas para esta devolución</td></tr>`;
            }
        });
}

// Evento para abrir el modal de devolución y poblarlo con los equipos seleccionados
document.addEventListener('DOMContentLoaded', function () {
    const devolverButton = document.getElementById('devolver-button');
    const modalEl = document.getElementById('modalConfirmarDevolucion');
    const tbody = document.getElementById('tbodyDevolucionSeleccionados');
    const form = document.getElementById('formDevolver');

    function prepararModalDevolucion() {
        const seleccionados = Array.from(document.querySelectorAll('.row-checkbox:checked'));
        tbody.innerHTML = '';
        Array.from(form.querySelectorAll('input[name="equiposSeleccionados"]')).forEach(input => input.remove());
        Array.from(form.querySelectorAll('input[name="require_firma"]')).forEach(input => input.remove());
        Array.from(form.querySelectorAll('input[name="idAsignacionPendiente"]')).forEach(input => input.remove());

        if (seleccionados.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No hay equipos seleccionados.</td></tr>';
            return false;
        }

        let idAsignacionRef = null;
        seleccionados.forEach(checkbox => {
            const row = checkbox.closest('tr');
            if (!row) return;
            const cells = row.querySelectorAll('td');
            const marcaEquipo = row.getAttribute('data-marca-equipo') || '';
            const modeloEquipo = row.getAttribute('data-modelo-equipo') || '';
            const idAsignacion = cells[1]?.textContent || '';
            const funcionario = cells[2]?.textContent || '';
            const tipoEquipo = cells[3]?.textContent || '';
            const codInventario = cells[5]?.textContent || '';

            if (!idAsignacionRef) {
                idAsignacionRef = idAsignacion;
            }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${idAsignacion}</td>
                <td>${funcionario}</td>
                <td>${tipoEquipo}</td>
                <td>${marcaEquipo}</td>
                <td>${modeloEquipo}</td>
                <td>${codInventario}</td>
            `;
            tbody.appendChild(tr);

            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'equiposSeleccionados';
            input.value = checkbox.value;
            form.appendChild(input);
        });

        if (window.pendientesDevolucion) {
            const inputFirma = document.createElement('input');
            inputFirma.type = 'hidden';
            inputFirma.name = 'require_firma';
            inputFirma.value = '1';
            form.appendChild(inputFirma);

            if (idAsignacionRef) {
                const inputAsignacion = document.createElement('input');
                inputAsignacion.type = 'hidden';
                inputAsignacion.name = 'idAsignacionPendiente';
                inputAsignacion.value = idAsignacionRef;
                form.appendChild(inputAsignacion);
            }
        }

        return true;
    }

    function mostrarModalDevolucion() {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }

    if (devolverButton && modalEl && tbody && form) {
        devolverButton.addEventListener('click', function () {
            if (!prepararModalDevolucion()) {
                return;
            }
            if (window.pendientesDevolucion) {
                abrirModalFirmarDevolucion();
            } else {
                mostrarModalDevolucion();
            }
        });

        modalEl.addEventListener('hidden.bs.modal', function () {
            tbody.innerHTML = '';
            Array.from(form.querySelectorAll('input[name="equiposSeleccionados"]')).forEach(input => input.remove());
            Array.from(form.querySelectorAll('input[name="require_firma"]')).forEach(input => input.remove());
            Array.from(form.querySelectorAll('input[name="idAsignacionPendiente"]')).forEach(input => input.remove());
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
        });
    }

    const formFirma = document.getElementById("formSubirFirmaDevolucion");
    const modalFirmaEl = document.getElementById("modalFirmarDevolucion");

    if (formFirma && modalFirmaEl && window.pendientesDevolucion) {
        formFirma.addEventListener("submit", function (e) {
            e.preventDefault();
            const inputFile = formFirma.querySelector('input[type="file"]');
            if (!inputFile || !inputFile.files || inputFile.files.length === 0) {
                alert("Debes seleccionar un archivo PDF para la firma.");
                return;
            }

            const formData = new FormData(formFirma);
            fetch(formFirma.action, {
                method: "POST",
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" },
            })
                .then((res) => res.json())
                .then((data) => {
                    if (!data || !data.ok) {
                        alert((data && data.error) || "No se pudo subir la firma.");
                        return;
                    }
                    const modal = bootstrap.Modal.getOrCreateInstance(modalFirmaEl);
                    modal.hide();
                    mostrarModalDevolucion();
                })
                .catch(() => {
                    alert("No se pudo subir la firma.");
                });
        });
    }
});

function actualizarBotonesBarraSuperior() {
    // Actualizar enlaces de descarga PDF según el seleccionado
    const descargarAsignacion = document.getElementById("descargar-asignacion");
    const descargarDevolucion = document.getElementById("descargar-devolucion");
    const firmarButton = document.getElementById("firmar-button");
    const devolverButton = document.getElementById("devolver-button");
    const descargarPDFButton = document.getElementById("descargar-PDF-button");
    // Siempre obtener los botones de firma del dropdown
    const btnFirmarAsignacion = document.getElementById("documento-firmado-asignacion");
    const btnFirmarDevolucion = document.getElementById("documento-firmado-devolucion");

    // Siempre dejar los botones de firma activos (no bloqueados)
    if (btnFirmarAsignacion) {
        btnFirmarAsignacion.disabled = false;
        btnFirmarAsignacion.classList.remove('disabled');
        btnFirmarAsignacion.tabIndex = 0;
        btnFirmarAsignacion.style.pointerEvents = 'auto';
    }
    if (btnFirmarDevolucion) {
        btnFirmarDevolucion.disabled = false;
        btnFirmarDevolucion.classList.remove('disabled');
        btnFirmarDevolucion.tabIndex = 0;
        btnFirmarDevolucion.style.pointerEvents = 'auto';
    }

    // Buscar el primer checkbox seleccionado
    const checked = document.querySelector('.row-checkbox:checked');
    const haySeleccion = !!checked;

    if (firmarButton) firmarButton.disabled = !haySeleccion;
    if (devolverButton) devolverButton.disabled = !haySeleccion;
    if (descargarPDFButton) descargarPDFButton.disabled = !haySeleccion;

    // Habilitar los botones del dropdown de firma SOLO si hay selección
    if (btnFirmarAsignacion) btnFirmarAsignacion.disabled = !haySeleccion;
    if (btnFirmarDevolucion) btnFirmarDevolucion.disabled = !haySeleccion;

    if (haySeleccion) {
        const idAsignacion = checked.getAttribute('data-id-asignacion');
        const idDevolucion = checked.getAttribute('data-id-devolucion');
        if (descargarAsignacion) {
            descargarAsignacion.href = `/asignacion/descargar_pdf_asignacion/${idAsignacion}`;
            descargarAsignacion.classList.remove('disabled');
            descargarAsignacion.removeAttribute('aria-disabled');
        }
        if (descargarDevolucion) {
            if (idDevolucion) {
                descargarDevolucion.href = `/asignacion/descargar_pdf_devolucion/${idDevolucion}`;
                descargarDevolucion.classList.remove('disabled');
                descargarDevolucion.removeAttribute('aria-disabled');
            } else {
                descargarDevolucion.href = "#";
                descargarDevolucion.classList.add('disabled');
                descargarDevolucion.setAttribute('aria-disabled', 'true');
            }
        }
    } else {
        if (descargarAsignacion) {
            descargarAsignacion.href = "#";
            descargarAsignacion.classList.add('disabled');
            descargarAsignacion.setAttribute('aria-disabled', 'true');
        }
        if (descargarDevolucion) {
            descargarDevolucion.href = "#";
            descargarDevolucion.classList.add('disabled');
            descargarDevolucion.setAttribute('aria-disabled', 'true');
        }
    }
}

// --- Impresión de asignaciones ---
function normalizarFiltroAsignacion(valor) {
    if (!valor) return "";
    const limpio = String(valor).trim();
    if (!limpio) return "";
    if (limpio.toLowerCase().startsWith("seleccione")) return "";
    return limpio;
}

function construirFiltrosImpresionAsignaciones() {
    return {
        q: normalizarFiltroAsignacion(document.getElementById('printAsigQuery')?.value || ''),
        funcionario: normalizarFiltroAsignacion(document.getElementById('printAsigFuncionario')?.value || ''),
        estado: normalizarFiltroAsignacion(document.getElementById('printAsigEstado')?.value || ''),
        fecha_inicio: normalizarFiltroAsignacion(document.getElementById('printAsigFechaInicio')?.value || ''),
        fecha_fin: normalizarFiltroAsignacion(document.getElementById('printAsigFechaFin')?.value || ''),
    };
}

function imprimirAsignaciones() {
    const filtros = construirFiltrosImpresionAsignaciones();
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => { if (v) params.append(k, v); });
    const url = params.toString() ? `/asignacion/imprimir?${params.toString()}` : '/asignacion/imprimir';
    const win = window.open(url, '_blank');
    if (!win || win.closed || typeof win.closed === 'undefined') {
        window.location.href = url;
    } else {
        win.focus();
    }
}

function actualizarTextoBotonImprimirAsignaciones() {
    const filtros = construirFiltrosImpresionAsignaciones();
    const tiene = Object.values(filtros).some(Boolean);
    const btn = document.getElementById('printAsignacionButton');
    if (btn) btn.textContent = tiene ? 'Imprimir con filtro' : 'Imprimir todo';
}

function limpiarFiltrosImpresionAsignaciones() {
    ['printAsigQuery', 'printAsigFuncionario', 'printAsigEstado', 'printAsigFechaInicio', 'printAsigFechaFin'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    actualizarTextoBotonImprimirAsignaciones();
}

document.addEventListener('DOMContentLoaded', () => {
    const btnPrint = document.getElementById('printAsignacionButton');
    if (btnPrint) btnPrint.addEventListener('click', imprimirAsignaciones);

    const btnClear = document.getElementById('clearAsignacionPrint');
    if (btnClear) btnClear.addEventListener('click', limpiarFiltrosImpresionAsignaciones);

    ['printAsigQuery', 'printAsigFuncionario', 'printAsigEstado', 'printAsigFechaInicio', 'printAsigFechaFin'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', actualizarTextoBotonImprimirAsignaciones);
            el.addEventListener('change', actualizarTextoBotonImprimirAsignaciones);
        }
    });

    const modal = document.getElementById('printAsignacionModal');
    if (modal) modal.addEventListener('shown.bs.modal', limpiarFiltrosImpresionAsignaciones);

    actualizarTextoBotonImprimirAsignaciones();
});

// Actualizar los enlaces de descarga y botones cada vez que se selecciona un checkbox
document.addEventListener('change', function (e) {
    if (e.target.classList.contains('row-checkbox')) {
        actualizarBotonesBarraSuperior();
    }
});

// También actualizar al cargar la tabla por primera vez
document.addEventListener('DOMContentLoaded', function () {
    actualizarBotonesBarraSuperior();
    rebindCheckboxEvents();
    // Descargar PDF dinámicamente según selección
    const descargarAsignacion = document.getElementById("descargar-asignacion");
    const descargarDevolucion = document.getElementById("descargar-devolucion");

    if (descargarAsignacion) {
        descargarAsignacion.addEventListener('click', function (e) {
            if (descargarAsignacion.classList.contains('disabled')) {
                e.preventDefault();
                return;
            }
            const checked = document.querySelector('.row-checkbox:checked');
            if (!checked) {
                e.preventDefault();
                alert("Selecciona una asignación para descargar el PDF.");
                return;
            }
            const idAsignacion = checked.getAttribute('data-id-asignacion');
            if (idAsignacion) {
                descargarAsignacion.href = `/asignacion/descargar_pdf_asignacion/${idAsignacion}`;
            } else {
                e.preventDefault();
                alert("No se encontró el ID de asignación.");
            }
        });
    }

    if (descargarDevolucion) {
        descargarDevolucion.addEventListener('click', function (e) {
            if (descargarDevolucion.classList.contains('disabled')) {
                e.preventDefault();
                return;
            }
            const checked = document.querySelector('.row-checkbox:checked');
            if (!checked) {
                e.preventDefault();
                alert("Selecciona una asignación para descargar el PDF de devolución.");
                return;
            }
            const idDevolucion = checked.getAttribute('data-id-devolucion');
            if (idDevolucion) {
                descargarDevolucion.href = `/asignacion/descargar_pdf_devolucion/${idDevolucion}`;
            } else {
                e.preventDefault();
                alert("No se encontró el ID de devolución para esta asignación.");
            }
        });
    }
});

// Asegura que los eventos de los checkboxes funcionen después de buscar
function rebindCheckboxEvents() {
    document.querySelectorAll('.row-checkbox').forEach(cb => {
        cb.onchange = actualizarBotonesBarraSuperior;
    });

    // Botón de información: abrir modal genérico y cargar datos dinámicamente
    document.querySelectorAll('.button-info').forEach(btn => {
        btn.onclick = function (e) {
            e.preventDefault();
            e.stopPropagation();
            // Usar idEquipoAsignacion para obtener el equipo correcto en asignaciones múltiples.
            const idEquipoAsignacion = btn.getAttribute('data-id-equipo-asignacion');
            if (!idEquipoAsignacion) return;
            abrirModalDetalleAsignacion(idEquipoAsignacion);
        };
    });
}

// Modal genérico para detalles de asignación
function abrirModalDetalleAsignacion(idEquipoAsignacion) {
    // Mostrar el id de detalle mientras se carga (se reemplaza con idAsignacion si existe)
    document.getElementById('modalDetalleAsignacionId').textContent = `#${idEquipoAsignacion}`;
    // Limpia el contenido anterior
    document.getElementById('modalDetalleAsignacionBody').innerHTML = '<div class="text-center">Cargando...</div>';
    const modal = new bootstrap.Modal(document.getElementById('modalDetalleAsignacion'));
    modal.show();

    fetch(`/asignacion/detalle_equipo_asignacion_json/${idEquipoAsignacion}`)
        .then(res => res.json())
        .then(data => {
            if (!data.asignacion) {
                document.getElementById('modalDetalleAsignacionBody').innerHTML = '<div class="text-danger">No se encontraron datos.</div>';
                return;
            }
            const d = data.asignacion;
            if (d.idAsignacion) {
                document.getElementById('modalDetalleAsignacionId').textContent = `#${d.idAsignacion}`;
            }
            document.getElementById('modalDetalleAsignacionBody').innerHTML = `
                <h5>Datos del Funcionario</h5>
                <table class="table table-bordered" style="table-layout: fixed">
                    <tr><td><strong>RUT</strong></td><td>${d.rutFuncionario || 'Sin información'}</td></tr>
                    <tr><td><strong>Nombre</strong></td><td>${d.nombreFuncionario || 'Sin información'}</td></tr>
                    <tr><td><strong>Cargo</strong></td><td>${d.cargoFuncionario || 'Sin información'}</td></tr>
                </table>
                <br>
                <h5>Datos de la Asignación</h5>
                <table class="table table-bordered" style="table-layout: fixed">
                    <tr><td><strong>Fecha de asignación</strong></td><td>${d.fecha_inicioAsignacion ? new Date(d.fecha_inicioAsignacion).toLocaleDateString() : 'Sin información'}</td></tr>
                    <tr><td><strong>Fecha de devolución</strong></td><td>${d.fechaDevolucion ? new Date(d.fechaDevolucion).toLocaleDateString() : 'Sin devolver'}</td></tr>
                    <tr><td><strong>Observaciones</strong></td><td>${d.ObservacionAsignacion || 'Sin información'}</td></tr>
                </table>
                <br>
                <h5>Datos del Equipo</h5>
                <table class="table table-bordered" style="table-layout: fixed">
                    <tr><td><strong>Tipo</strong></td><td>${d.nombreTipo_equipo || 'Sin información'}</td></tr>
                    <tr><td><strong>Marca</strong></td><td>${d.nombreMarcaEquipo || 'Sin información'}</td></tr>
                    <tr><td><strong>Modelo</strong></td><td>${d.nombreModeloequipo || 'Sin información'}</td></tr>
                    <tr><td><strong>Cód. inventario</strong></td><td>${d.Cod_inventarioEquipo || 'Sin información'}</td></tr>
                    <tr><td><strong>N° serie</strong></td><td>${d.Num_serieEquipo || 'Sin información'}</td></tr>
                    <tr><td><strong>Cód. proveedor</strong></td><td>${d.codigoproveedor_equipo || 'Sin información'}</td></tr>
                    <tr><td><strong>Observaciones</strong></td><td>${d.ObservacionEquipo || 'Sin información'}</td></tr>
                </table>
            `;
        })
        .catch(() => {
            document.getElementById('modalDetalleAsignacionBody').innerHTML = '<div class="text-danger">Error al cargar los datos.</div>';
        });
}
