document.getElementById("Origen").addEventListener("change", function () {
    fetch(`/traslado/equipos_unidad/${this.value}`)

        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log(data); // Verificar los datos en la consola
            let equiposLista = document.getElementById("equiposLista");
            equiposLista.innerHTML = "";
            data.forEach(equipo => {
                equiposLista.innerHTML += `<tr>
                    <td><input type='checkbox' name='trasladar[]' value='${equipo.idEquipo}'></td>
                    <td>${equipo.nombreModeloequipo || 'N/A'}</td>
                    <td>${equipo.nombreTipo_equipo || 'N/A'}</td>
                    <td>${equipo.nombreMarcaEquipo || 'N/A'}</td>
                    <td>${equipo.Cod_inventarioEquipo || 'N/A'}</td>
                    <td>${equipo.Num_serieEquipo || 'N/A'}</td>
                </tr>`;
            });
            if (data.length === 0) {
                equiposLista.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center">No hay equipos disponibles</td>
                </tr>`;
            }
        })
        .catch(error => {
            console.error('There was a problem with the fetch operation:', error);
            let equiposLista = document.getElementById("equiposLista");
            equiposLista.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">Seleccione una unidad para trasladar</td>
            </tr>`;
        });
});

document.getElementById("trasladoForm").addEventListener("submit", function (event) {
    event.preventDefault();
    let formData = new FormData(this);

    fetch(`/traslado/create_traslado/${document.getElementById("Origen").value}`, {
        method: "POST",
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                mostrarAlerta("✅ Traslado creado correctamente.", "success");

                // Cerrar modal y resetear formulario
                $('#trasladoModal').modal('hide');
                this.reset();
                window.location.reload(); // Recargar la página para ver el nuevo traslado
            } else {
                mostrarAlerta(`${data.message}`, "danger");
            }
        })
});


// Búsqueda en la tabla
function filtrarTabla() {
    let input = document.getElementById("busqueda").value.toLowerCase();
    let filas = document.querySelectorAll("#posts tbody tr");

    filas.forEach(fila => {
        let textoFila = fila.innerText.toLowerCase();
        fila.style.display = textoFila.includes(input) ? "" : "none";
    });
}

// Función para cargar los detalles del traslado en el modal
function cargarDetallesTraslado(id) {
    let trasladosData = document.getElementById("traslados-data").textContent;
    let traslados = JSON.parse(trasladosData);

    let trasSeleccionado = traslados.find(t => t.idTraslado == id);

    if (trasSeleccionado) {
        // ✅ Usar la nueva función corregida
        document.getElementById("detalleFecha").textContent = formatearFecha(trasSeleccionado.fechatraslado);
        document.getElementById("detalleOrigen").textContent = trasSeleccionado.nombreOrigen;
        document.getElementById("detalleDestino").textContent = trasSeleccionado.nombreDestino;

        let equiposTable = document.getElementById("detalleEquipos");
        equiposTable.innerHTML = "";

        if (!trasSeleccionado.equipos || trasSeleccionado.equipos.length === 0) {
            equiposTable.innerHTML = `<tr><td colspan="5" class="text-center">No hay equipos trasladados</td></tr>`;
        } else {
            trasSeleccionado.equipos.forEach(equipo => {
                let row = `<tr>
                        <td>${equipo.nombreModeloequipo || 'N/A'}</td>
                        <td>${equipo.nombreTipo_equipo || 'N/A'}</td>
                        <td>${equipo.nombreMarcaEquipo || 'N/A'}</td>
                        <td>${equipo.Cod_inventarioEquipo || 'N/A'}</td>
                        <td>${equipo.Num_serieEquipo || 'N/A'}</td>
                    </tr>`;
                equiposTable.innerHTML += row;
            });
        }
    }
}


// Seleccionar/Deseleccionar todos los checkboxes
document.getElementById("selectAll").addEventListener("change", function () {
    let checkboxes = document.querySelectorAll(".trasladoCheckbox");
    checkboxes.forEach(checkbox => checkbox.checked = this.checked);
});


// Función para mostrar alertas de Bootstrap
function mostrarAlerta(mensaje, tipo = "success") {
    let alertContainer = document.getElementById("alertContainer");

    // Crear el HTML de la alerta
    let alertaHTML = `
        <div class="alert alert-${tipo} alert-dismissible fade show" role="alert">
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    // Insertar la alerta en el contenedor
    alertContainer.innerHTML = alertaHTML;
    alertContainer.classList.remove("d-none");

    // Ocultar la alerta después de 5 segundos
    setTimeout(() => {
        alertContainer.innerHTML = "";
        alertContainer.classList.add("d-none");
    }, 5000);
}

const botonEliminar = document.getElementById("eliminarSeleccionados");


document.addEventListener("DOMContentLoaded", function () {
    // Seleccionar/Deseleccionar todos los checkboxes
    document.getElementById("selectAll").addEventListener("change", function () {
        let checkboxes = document.querySelectorAll(".row-checkbox");
        checkboxes.forEach(cb => cb.checked = this.checked);

        if (this.checked) {
            botonEliminar.disabled = false; // Habilita el botón de eliminar
            botonEliminar.innerHTML = '<i class="bi bi-trash"></i> Eliminar seleccionados'; //mensaje en el botón de eliminar
        } else {
            botonEliminar.disabled = true; //deshabilita el botón de eliminar
            botonEliminar.innerHTML = '<i class="bi bi-trash"></i> ' // icono sin mensaje para el botón de eliminar
        }
    });
    
    // Botón de eliminar traslados seleccionados
    document.getElementById("eliminarSeleccionados").addEventListener("click", function () {
        let seleccionados = Array.from(document.querySelectorAll(".row-checkbox:checked"))
            .map(checkbox => checkbox.value);

        if (seleccionados.length > 0) {
            Swal.fire({
                title: 'Confirmar eliminación',
                text: `¿Seguro que deseas eliminar ${seleccionados.length} traslado(s)?`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#59ae87',
                cancelButtonColor: '#d33',
                confirmButtonText: 'Sí, eliminar',
                cancelButtonText: 'Cancelar'
            }).then((result) => {
                if (result.isConfirmed) {
                    fetch('/traslado/delete_multiple', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ traslados: seleccionados })
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                Swal.fire({
                                    title: '¡Eliminados!',
                                    text: 'Traslados eliminados correctamente.',
                                    icon: 'success',
                                    confirmButtonColor: '#59ae87'
                                }).then(() => {
                                    // Eliminar filas de la tabla
                                    seleccionados.forEach(id => {
                                        let row = document.querySelector(`input[value="${id}"]`).closest("tr");
                                        if (row) row.remove();
                                    });

                                    // Desmarcar el checkbox de "Seleccionar todo"
                                    document.getElementById("selectAll").checked = false;
                                    botonEliminar.innerHTML = '<i class="bi bi-trash"></i> ';
                                    botonEliminar.disabled = true;
                                });
                            } else {
                                Swal.fire({
                                    title: 'Error',
                                    text: "Error al eliminar traslados.",
                                    icon: 'error',
                                    confirmButtonColor: '#59ae87'
                                });
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            Swal.fire({
                                title: 'Error',
                                text: "Ocurrió un error inesperado.",
                                icon: 'error',
                                confirmButtonColor: '#59ae87'
                            });
                        });
                }
            });
        } else {
            Swal.fire({
                title: 'Aviso',
                text: "No has seleccionado ningún traslado.",
                icon: 'info',
                confirmButtonColor: '#59ae87'
            });
        }
    });
});

// Función para mostrar alertas dinámicas
function mostrarAlerta(mensaje, tipo) {
    let alertContainer = document.getElementById("alertContainer");
    alertContainer.innerHTML = `<div class="alert alert-${tipo} alert-dismissible fade show" role="alert">
                                    ${mensaje}
                                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                                </div>`;
    alertContainer.classList.remove("d-none");

    setTimeout(() => {
        alertContainer.classList.add("d-none");
        alertContainer.innerHTML = "";
    }, 4000);
}


// Función para formatear la fecha en el formato deseado
function formatearFecha(fechaISO) {
    let fecha = new Date(fechaISO);

    // 🔍 Ajustar manualmente la zona horaria para evitar desfases
    let localOffset = fecha.getTimezoneOffset() * 60000; // Convertir a milisegundos
    fecha = new Date(fecha.getTime() + localOffset);

    let diasSemana = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
    let nombreDia = diasSemana[fecha.getDay()];
    let numeroDia = fecha.getDate().toString().padStart(2, '0');
    let numeroMes = (fecha.getMonth() + 1).toString().padStart(2, '0');
    let anio = fecha.getFullYear();

    return `${nombreDia} ${numeroDia}/${numeroMes}/${anio}`;
}


function validarFechaTraslado(fechaInputId) {
    let fechaInput = document.getElementById(fechaInputId);

    if (!fechaInput) return;

    // ✅ Obtener la fecha de hoy en formato YYYY-MM-DD
    let today = new Date();
    let todayStr = today.toISOString().split('T')[0];

    [fechaInput].forEach(input => {
        if (input) {
            input.setAttribute("min", todayStr);
        }
    });

}

// --- Impresión de traslados ---
function normalizarFiltroTraslado(valor) {
    if (!valor) return "";
    const limpio = String(valor).trim();
    if (!limpio) return "";
    if (limpio.toLowerCase().startsWith("seleccione")) return "";
    return limpio;
}

function construirFiltrosImpresionTraslados() {
    return {
        q: normalizarFiltroTraslado(document.getElementById('printTrasladoQuery')?.value || ''),
        origen: normalizarFiltroTraslado(document.getElementById('printTrasladoOrigen')?.value || ''),
        destino: normalizarFiltroTraslado(document.getElementById('printTrasladoDestino')?.value || ''),
        desde: normalizarFiltroTraslado(document.getElementById('printTrasladoDesde')?.value || ''),
        hasta: normalizarFiltroTraslado(document.getElementById('printTrasladoHasta')?.value || ''),
    };
}

function imprimirTraslados() {
    const filtros = construirFiltrosImpresionTraslados();
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => { if (v) params.append(k, v); });
    const url = params.toString() ? `/traslado/imprimir?${params.toString()}` : '/traslado/imprimir';
    const win = window.open(url, '_blank');
    if (!win || win.closed || typeof win.closed === 'undefined') {
        window.location.href = url;
    } else {
        win.focus();
    }
}

function actualizarTextoBotonImprimirTraslados() {
    const filtros = construirFiltrosImpresionTraslados();
    const tiene = Object.values(filtros).some(Boolean);
    const btn = document.getElementById('printTrasladoButton');
    if (btn) btn.textContent = tiene ? 'Imprimir con filtro' : 'Imprimir todo';
}

function limpiarFiltrosImpresionTraslados() {
    ['printTrasladoQuery','printTrasladoOrigen','printTrasladoDestino','printTrasladoDesde','printTrasladoHasta'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    actualizarTextoBotonImprimirTraslados();
}

document.addEventListener('DOMContentLoaded', () => {
    const btnPrint = document.getElementById('printTrasladoButton');
    if (btnPrint) btnPrint.addEventListener('click', imprimirTraslados);

    const btnClear = document.getElementById('clearTrasladoPrint');
    if (btnClear) btnClear.addEventListener('click', limpiarFiltrosImpresionTraslados);

    ['printTrasladoQuery','printTrasladoOrigen','printTrasladoDestino','printTrasladoDesde','printTrasladoHasta'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', actualizarTextoBotonImprimirTraslados);
            el.addEventListener('change', actualizarTextoBotonImprimirTraslados);
        }
    });

    const modal = document.getElementById('printTrasladoModal');
    if (modal) modal.addEventListener('shown.bs.modal', limpiarFiltrosImpresionTraslados);

    actualizarTextoBotonImprimirTraslados();
});

// ✅ Ejecutar la validación al cargar la página
document.addEventListener("DOMContentLoaded", function () {
    validarFechaTraslado("fechatraslado"); // Llamar la función para el campo del modal
});

// ✅ Función para mostrar alertas dinámicas (Bootstrap)
function mostrarAlerta(mensaje, tipo = "success") {
    let alertContainer = document.getElementById("alertContainer");

    // Crear el contenedor de alertas si no existe
    if (!alertContainer) {
        document.body.insertAdjacentHTML("afterbegin", '<div id="alertContainer" class="alert-container"></div>');
        alertContainer = document.getElementById("alertContainer");
    }

    // Limpiar alertas previas
    alertContainer.innerHTML = "";

    let alertaHTML = `
        <div class="alert alert-${tipo} alert-dismissible fade show" role="alert">
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    alertContainer.innerHTML = alertaHTML;
    alertContainer.classList.remove("d-none");

    setTimeout(() => {
        alertContainer.classList.add("d-none");
        alertContainer.innerHTML = "";
    }, 5000);
}


function cargarEditarTraslado(idTraslado, fechaTraslado) {
    // Asignar la fecha al campo correspondiente
    document.getElementById("editarFechaTraslado").value = fechaTraslado;

    // Actualizar dinámicamente la acción del formulario con el ID del traslado
    document.getElementById("editarTrasladoForm").action = `/traslado/edit_traslado/${idTraslado}`;

    console.log("Cargando traslado:", idTraslado, fechaTraslado); // Depuración
}

document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("trasladoModal");
    const equiposLista = document.getElementById("equiposLista");

    if (modalEl && equiposLista) {
        modalEl.addEventListener("hidden.bs.modal", function () {
            // Clear modal content and reset state when closed
            equiposLista.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">Seleccione una unidad para trasladar</td>
                </tr>`;
            document.getElementById("Origen").value = ""; // Reset dropdown
        });

        modalEl.addEventListener("shown.bs.modal", function () {
            // Ensure modal is properly initialized when opened
            const origenValue = document.getElementById("Origen").value;
            if (!origenValue) {
                equiposLista.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center">Seleccione una unidad para trasladar</td>
                    </tr>`;
            }
        });
    }
});


//Condiciones para habilitar el botón de firmar traslados
function habilitarBotonFirmar() {
    const firmarButton = document.getElementById("firmarTraslado");


    const checked = document.querySelector('.row-checkbox:checked');
    const seleccionado = !!checked; // Verifica si hay un checkbox activado

    if (firmarButton) firmarButton.disabled = !seleccionado;//Habilita el botón al seleccionar un checkbox

    // Condición para habilitar/deshabilitar el botón de eliminar
    if (botonEliminar) {
        botonEliminar.disabled = !seleccionado;
        botonEliminar.innerHTML = seleccionado
            ? '<i class="bi bi-trash"></i> Eliminar seleccionado(s)'
            : '<i class="bi bi-trash"></i> ';
    }

    
}

//actualizar botón de firmar traslado al seleccionar el checkbox
document.addEventListener('change', function (e) {
    if (e.target.classList.contains('row-checkbox')) {
        habilitarBotonFirmar();
    } else{
        firmarButton.disabled
    }
});

//modal para firmar traslados//
function abrirModalFirmarTraslado() {
    const modalFirmarTraslado = new bootstrap.Modal(document.getElementById("modalAdjuntarPDF"));
    let seleccionados = document.querySelectorAll(".row-checkbox:checked");
    let ids = Array.from(seleccionados).map(cb => cb.value);

    if (ids.length === 0) {
        alert("Selecciona al menos un traslado para firmar.");
        return;
    }

    if (ids.length > 1) {
        mostrarAlerta("Solo puedes firmar un traslado a la vez.", "danger");
        return;
    }

    //Obtener ID del traslado y mostrarlo
    document.getElementById("detalleIdTraslado").textContent = ids;

    const form = document.getElementById("formAdjuntarPDF");
    form.action = `/traslado/adjuntar_pdf/${ids}`;
    form.reset(); // Limpiar el formulario antes de mostrar el modal

    modalFirmarTraslado.show();//mostrar modal

    const tbody = document.getElementById("tablaFirmaTraslado");
    tbody.innerHTML = `<tr><td>Buscando...</td></tr>`;

    fetch(`/traslado/firmas_json/${ids}`)
        .then(res => res.json())
        .then(data => {
            tbody.innerHTML = "";

            if (data.existe) {
                const fila = document.createElement("tr");
                fila.innerHTML = `
                    <td>${data.nombre}</td>
                    <td>
                        <a href="/traslado/mostrar_pdf/${ids}/" class="btn btn-primary" target="_blank">Ver PDF</a>
                    </td>
                `;
                tbody.appendChild(fila);
            } else {
                const fila = document.createElement("tr");
                fila.innerHTML = `
                    <td colspan="3" class="text-center">No hay PDF adjunto</td>
                `;
                tbody.appendChild(fila);
            }
        });


    const tbody2 =
        document.getElementById("detalleEquipos")

    fetch(`/traslado/detalles_json/${ids}`)//detalles del traslado que se muestran en el modal de firma
        .then(res => res.json())
        .then(data => {
            const t = data.traslado;

            document.getElementById("unidadOrigen").textContent = t.nombreOrigen;
            document.getElementById("unidadDestino").textContent = t.nombreDestino;
            document.getElementById("direccionOrigen").textContent = t.direccionOrigen;
            document.getElementById("CodigoUnidad").textContent = t.CodigoUnidad;
            document.getElementById("direccionDestino").textContent = t.direccionDestino;
            document.getElementById("codigoDestino").textContent = t.codigoDestino;

            document.getElementById("nombreEquipo").textContent = t.nombreEquipo;
            document.getElementById("modeloEquipo").textContent = t.nombreModeloequipo;
            document.getElementById("marcaEquipo").textContent = t.marcaEquipo;
            document.getElementById("numeroSerie").textContent = t.numeroSerie;
            document.getElementById("codigoInventario").textContent = t.codigoInventario;
        });
}

//funcion para buscar traslados según las columnas que tenga la tabla
function buscarTraslados(page = 1) {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
        const query = document.getElementById("buscador_traslados").value.toLowerCase();

        fetch(`/traslado/buscar_traslados?q=${encodeURIComponent(query)}&page=${page}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error("Error al buscar traslados");
                }
                return response.json();
            })
    })
}
