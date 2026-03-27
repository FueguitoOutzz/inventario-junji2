function cargarEquipos(estado) {
    $.ajax({
        url: `/mostrar_equipos_segun_tipo/${encodeURIComponent(estado)}`, // 🔹 Evita problemas con caracteres especiales
        method: "GET",
        dataType: "json", // 🔹 Aseguramos que recibimos JSON
        success: function (data) {
            let tbody = $("#detalleEquipos");
            tbody.empty(); // 🔹 Limpiamos el contenido antes de agregar nuevos datos

            if (data.length === 0) {
                tbody.append(`
                    <tr>
                        <td colspan="4" class="text-center text-muted">No hay equipos en este estado</td>
                    </tr>
                `);
                return; // 🔹 No sigue ejecutando el código si no hay datos
            }

            data.forEach(equipo => {
                tbody.append(`
                    <tr>
                        <td>${equipo.nombreModeloequipo || 'N/A'}</td>
                        <td>${equipo.nombreTipo_equipo || 'N/A'}</td>
                        <td>${equipo.Num_serieEquipo || 'N/A'}</td>
                        <td>${equipo.nombreUnidad || 'N/A'}</td>
                    </tr>
                `);
            });
        },
        error: function (xhr) {
            console.error("❌ Error al cargar los equipos:", xhr.responseText);
            mostrarAlerta("Error al obtener los equipos.", "danger"); // 🔹 Mostrar alerta en caso de error
        }
    });
}

document.addEventListener("DOMContentLoaded", function () {
    const filtroUnidad = document.getElementById("filtroUnidad");
    const tablaEstados = document.getElementById("tablaEstados");
    if (!filtroUnidad || !tablaEstados) {
        return;
    }
    const filasEstados = tablaEstados.querySelectorAll("tbody tr");

    filtroUnidad.addEventListener("change", function () {
        let unidadSeleccionada = this.value;

        filasEstados.forEach(fila => {
            let unidadFila = fila.getAttribute("data-unidad");

            if (unidadSeleccionada === "" || unidadSeleccionada === unidadFila) {
                fila.style.display = "";
            } else {
                fila.style.display = "none";
            }
        });
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const sortableHeaders = document.querySelectorAll(".sortable-column");
    const tableBody = document.getElementById("myTableBody");
    if (!sortableHeaders.length || !tableBody) {
        return;
    }

    let currentSortColumn = null; // Columna actualmente ordenada
    let currentSortOrder = "neutral"; // Estados: 'neutral', 'asc', 'desc'

    // 🔹 Agregar iconos de ordenamiento dinámicamente a cada encabezado
    sortableHeaders.forEach(header => {


        // Asignar evento de clic a cada encabezado para ordenar la tabla
        header.addEventListener("click", function () {
            sortTable(parseInt(this.dataset.column), this);
        });
    });

    // 🔹 Función para Ordenar la Tabla y Cambiar Íconos
    function sortTable(columnIndex, headerElement) {
        const rows = Array.from(tableBody.querySelectorAll("tr"));

        // Alternar entre ascendente y descendente
        if (currentSortColumn === columnIndex) {
            currentSortOrder = currentSortOrder === "asc" ? "desc" : "asc";
        } else {
            currentSortColumn = columnIndex;
            currentSortOrder = "asc";
        }

        // Ordenar las filas
        rows.sort((rowA, rowB) => {
            const cellA = rowA.cells[columnIndex].innerText.trim();
            const cellB = rowB.cells[columnIndex].innerText.trim();

            const valueA = parseCellValue(cellA);
            const valueB = parseCellValue(cellB);

            if (currentSortOrder === "asc") {
                return valueA > valueB ? 1 : valueA < valueB ? -1 : 0;
            } else {
                return valueA < valueB ? 1 : valueA > valueB ? -1 : 0;
            }
        });

        // Actualizar la tabla con las filas ordenadas
        tableBody.innerHTML = "";
        rows.forEach(row => tableBody.appendChild(row));

        // Actualizar los iconos de las flechas
        updateSortIcons(headerElement);
    }

    // 🔹 Función para Actualizar Íconos de Ordenación
    function updateSortIcons(headerElement) {
        const allHeaders = document.querySelectorAll(".sortable-column");

        // 🔹 Resetear las clases de todas las columnas
        allHeaders.forEach(header => {
            const upIcon = header.querySelector(".bi-caret-up, .bi-caret-up-fill");
            const downIcon = header.querySelector(".bi-caret-down, .bi-caret-down-fill");

            if (upIcon) upIcon.className = "bi bi-caret-up d-none"; // Ocultar flecha ascendente
            if (downIcon) downIcon.className = "bi bi-caret-down d-none"; // Ocultar flecha descendente
        });

        // 🔹 Actualizar las flechas en la columna actualmente ordenada
        const upIcon = headerElement.querySelector(".bi-caret-up, .bi-caret-up-fill");
        const downIcon = headerElement.querySelector(".bi-caret-down, .bi-caret-down-fill");

        if (currentSortOrder === "asc" && upIcon) {
            upIcon.className = "bi bi-caret-up-fill"; // Mostrar flecha ascendente rellena
            downIcon.className = "bi bi-caret-down d-none"; // Ocultar descendente
        } else if (currentSortOrder === "desc" && downIcon) {
            downIcon.className = "bi bi-caret-down-fill"; // Mostrar flecha descendente rellena
            upIcon.className = "bi bi-caret-up d-none"; // Ocultar ascendente
        }
    }

    // 🔹 Función para convertir el valor de una celda para ordenamiento
    function parseCellValue(cellValue) {
        // Intentar convertir el valor a número, si falla, usar como string
        let parsed = parseFloat(cellValue.replace(/,/g, ""));
        return isNaN(parsed) ? cellValue.toLowerCase() : parsed;
    }
});

// --- Impresión de estados de equipo ---
function normalizarFiltroEstado(valor) {
    if (!valor) return "";
    const limpio = String(valor).trim();
    return limpio || "";
}

function construirFiltrosImpresionEstados() {
    return { q: normalizarFiltroEstado(document.getElementById('printEstadoQuery')?.value || '') };
}

function imprimirEstados() {
    const filtros = construirFiltrosImpresionEstados();
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => { if (v) params.append(k, v); });
    const url = params.toString() ? `/estado_equipo/imprimir?${params.toString()}` : '/estado_equipo/imprimir';
    const win = window.open(url, '_blank');
    if (!win || win.closed || typeof win.closed === 'undefined') {
        window.location.href = url;
    } else {
        win.focus();
    }
}

function actualizarTextoBotonImprimirEstados() {
    const filtros = construirFiltrosImpresionEstados();
    const tiene = Object.values(filtros).some(Boolean);
    const btn = document.getElementById('printEstadoButton');
    if (btn) btn.textContent = tiene ? 'Imprimir con filtro' : 'Imprimir todo';
}

function limpiarFiltrosImpresionEstados() {
    const query = document.getElementById('printEstadoQuery');
    if (query) query.value = '';
    actualizarTextoBotonImprimirEstados();
}

document.addEventListener('DOMContentLoaded', () => {
    const btnPrint = document.getElementById('printEstadoButton');
    if (btnPrint) btnPrint.addEventListener('click', imprimirEstados);

    const btnClear = document.getElementById('clearEstadoPrint');
    if (btnClear) btnClear.addEventListener('click', limpiarFiltrosImpresionEstados);

    const query = document.getElementById('printEstadoQuery');
    if (query) query.addEventListener('input', actualizarTextoBotonImprimirEstados);

    const modal = document.getElementById('printEstadoModal');
    if (modal) modal.addEventListener('shown.bs.modal', limpiarFiltrosImpresionEstados);

    actualizarTextoBotonImprimirEstados();
});

