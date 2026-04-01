function buscarFuncionarios(page = 1) {
    const query = document.getElementById("buscador_funcionario").value.toLowerCase();
    const estadoSel = document.getElementById("filtro_estado_funcionario");
    const estado = estadoSel ? estadoSel.value : "todos";

    fetch(`/buscar_funcionarios?q=${encodeURIComponent(query)}&page=${page}&estado=${estado}`)
        .then(response => response.json())
        .then(data => {
            actualizarTablaFuncionarios(data.funcionarios);
            actualizarPaginacionFuncionarios(data.total_pages, data.current_page, query, data.visible_pages);
        })
        .catch(error => console.error("Error al buscar funcionarios:", error));
}

let funcionariosActuales = [];
let ordenActualFuncionario = { campo: null, asc: true };

function exportarFuncionarios() {
    // Exporta todos los funcionarios (activos por defecto en backend)
    window.location.href = `/funcionario/exportar_excel`;
}

function actualizarTablaFuncionarios(funcionarios) {
    funcionariosActuales = funcionarios;
    const tbody = document.getElementById("funcionarioTableBody");
    tbody.innerHTML = "";

    if (!funcionarios.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No hay datos disponibles.</td></tr>';
        return;
    }

    funcionarios.forEach(fun => {
        const row = document.createElement("tr");
        row.setAttribute("data-rut", fun.rutFuncionario);
        row.setAttribute("data-nombre", fun.nombreFuncionario);
        row.setAttribute("data-correo", fun.correoFuncionario);
        row.setAttribute("data-cargo", fun.cargoFuncionario);
        row.setAttribute("data-unidad", fun.idUnidad);
        row.setAttribute("data-activo", fun.activo_estado);
        row.setAttribute("data-motivo-id", fun.motivo_inactividad_id || "");
        row.setAttribute("data-detalle-inactivo", fun.detalle_inactividad || "");
        if (fun.activo_estado === 0) {
            row.classList.add("table-secondary", "opacity-75");
        }

        row.innerHTML = `
            <td>${fun.rutFuncionario}</td>
            <td>${fun.nombreFuncionario}</td>
            <td>${fun.cargoFuncionario}</td>
            <td>${fun.nombreUnidad}</td>
            <td>${fun.correoFuncionario}</td>
            <td>${fun.activo_estado === 1 ? '<span class="badge bg-success">Activo</span>' : `<span class="badge bg-danger">Inactivo</span><br><small class="text-muted">${fun.motivo_inactividad_id || 'Sin motivo'}</small>`}</td>
            <td>
                <div class="d-flex justify-content-center gap-2">
                    <button class="btn btn-warning edit-button" data-bs-toggle="modal"
                        data-bs-target="#editFuncionarioModal" data-rut="${fun.rutFuncionario}"
                        data-nombre="${fun.nombreFuncionario}" data-correo="${fun.correoFuncionario}"
                        data-cargo="${fun.cargoFuncionario}" data-unidad="${fun.idUnidad}"
                        data-activo="${fun.activo_estado}" data-motivo-id="${fun.motivo_inactividad_id || ''}"
                        data-detalle-inactivo="${fun.detalle_inactividad || ''}">
                        <i class="bi bi-pencil-square"></i>
                    </button>
                    ${fun.equipos_asignados == 0 ? `
                    <button type="button" class="btn btn-danger delete-button"
                        data-title="Eliminar funcionario"
                        data-message="¿Estás seguro de que deseas eliminar al funcionario ${fun.nombreFuncionario}?"
                        data-url="/delete_funcionario/${fun.rutFuncionario}">
                        <i class="bi bi-trash-fill"></i>
                    </button>
                    ` : `
                    <button type="button" class="btn btn-danger" data-bs-toggle="modal"
                        data-bs-target="#warningModal">
                        <i class="bi bi-trash-fill"></i>
                    </button>
                    `}
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function ordenarFuncionario(campo) {
    if (ordenActualFuncionario.campo === campo) {
        ordenActualFuncionario.asc = !ordenActualFuncionario.asc;
    } else {
        ordenActualFuncionario.campo = campo;
        ordenActualFuncionario.asc = true;
    }
    funcionariosActuales.sort((a, b) => {
        let valA = a[campo];
        let valB = b[campo];
        if (!isNaN(valA) && !isNaN(valB)) {
            valA = Number(valA);
            valB = Number(valB);
        } else {
            valA = (valA || '').toString().toLowerCase();
            valB = (valB || '').toString().toLowerCase();
        }
        if (valA < valB) return ordenActualFuncionario.asc ? -1 : 1;
        if (valA > valB) return ordenActualFuncionario.asc ? 1 : -1;
        return 0;
    });
    actualizarTablaFuncionarios(funcionariosActuales);
}

function actualizarPaginacionFuncionarios(totalPages, currentPage, query, visiblePages) {
    const pagination = document.getElementById("funcionario-pagination");
    pagination.innerHTML = "";

    visiblePages.forEach(page => {
        const li = document.createElement("li");
        if (page === "...") {
            li.className = "page-item disabled";
            li.innerHTML = `<span class="page-link">...</span>`;
        } else {
            li.className = `page-item ${page === currentPage ? "active" : ""}`;
            li.innerHTML = `<a class="page-link" href="#" onclick="buscarFuncionarios(${page});return false;">${page}</a>`;
        }
        pagination.appendChild(li);
    });

    // Botón "Anterior"
    if (currentPage > 1) {
        const prevLi = document.createElement("li");
        prevLi.className = "page-item";
        prevLi.innerHTML = `<a class="page-link" href="#" onclick="buscarFuncionarios(${currentPage - 1});return false;">Anterior</a>`;
        pagination.insertBefore(prevLi, pagination.firstChild);
    }

    // Botón "Siguiente"
    if (currentPage < totalPages) {
        const nextLi = document.createElement("li");
        nextLi.className = "page-item";
        nextLi.innerHTML = `<a class="page-link" href="#" onclick="buscarFuncionarios(${currentPage + 1});return false;">Siguiente</a>`;
        pagination.appendChild(nextLi);
    }
}

// Cargar todos los funcionarios al cargar la página
document.addEventListener("DOMContentLoaded", function () {
    buscarFuncionarios(1);

    const exportBtn = document.getElementById("exportarFuncionarios");
    if (exportBtn) {
        exportBtn.addEventListener("click", exportarFuncionarios);
    }

    const importBtn = document.getElementById("importarFuncionarios");
    const importInput = document.getElementById("importarFuncionariosInput");
    const importForm = document.getElementById("importarFuncionariosForm");

    if (importBtn && importInput && importForm) {
        importBtn.addEventListener("click", () => importInput.click());
        importInput.addEventListener("change", () => {
            if (importInput.files.length > 0) {
                importForm.submit();
            }
        });
    }

    const printBtn = document.getElementById('printFuncionarioButton');
    if (printBtn) {
        printBtn.addEventListener('click', imprimirFuncionarios);
    }

    const clearBtn = document.getElementById('clearFuncionarioPrint');
    if (clearBtn) {
        clearBtn.addEventListener('click', limpiarFiltrosImpresionFuncionarios);
    }

    ['printFuncQuery','printFuncUnidad','printFuncCargo'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', actualizarTextoBotonImprimirFuncionarios);
            el.addEventListener('change', actualizarTextoBotonImprimirFuncionarios);
        }
    });

    const printModal = document.getElementById('printFuncionarioModal');
    if (printModal) {
        printModal.addEventListener('shown.bs.modal', limpiarFiltrosImpresionFuncionarios);
    }

    toggleCamposInactivo();
    const selectEstado = document.getElementById('edit_activoFuncionario');
    if (selectEstado) {
        selectEstado.addEventListener('change', toggleCamposInactivo);
        selectEstado.addEventListener('input', toggleCamposInactivo);
    }

    const formEdit = document.getElementById('form_editFuncionarioModal');
    if (formEdit) {
        formEdit.addEventListener('submit', (e) => {
            const estado = document.getElementById('edit_activoFuncionario');
            const motivo = document.getElementById('edit_motivo_inactivo');
            const motivoId = document.getElementById('edit_motivo_inactividad_id');
            if (estado && estado.value === '0' && motivo && !motivo.value) {
                e.preventDefault();
                alert('Debes indicar un motivo para inactivar al funcionario.');
            }
            if (estado && estado.value === '0' && motivoId) {
                const selectedOption = motivo.options[motivo.selectedIndex];
                motivoId.value = selectedOption ? (selectedOption.dataset.id || '') : '';
            }
        });
    }

    const selectMotivo = document.getElementById('edit_motivo_inactivo');
    if (selectMotivo) {
        selectMotivo.addEventListener('change', () => {
            const hidden = document.getElementById('edit_motivo_inactividad_id');
            const opt = selectMotivo.options[selectMotivo.selectedIndex];
            if (hidden && opt) {
                hidden.value = opt.dataset.id || '';
            }
        });
    }
});

// --- Código para poblar el modal de edición y campos ocultos ---
$(document).ready(function () {
    $('#editFuncionarioModal').on('shown.bs.modal', function (event) {
        var button = $(event.relatedTarget);
        var rutCompleto = button.data('rut') ? String(button.data('rut')) : '';
        var nombre = button.data('nombre');
        var correoCompleto = button.data('correo');
        var cargo = button.data('cargo');
        var unidadId = button.data('unidad');
        var activoVal = button.data('activo');
        var motivoId = button.data('motivo-id');
        var detalleInactivo = button.data('detalle-inactivo');

        var rutNumero = '';
        var rutDv = '';
        if (rutCompleto && rutCompleto.includes('-')) {
            var partesRut = rutCompleto.split('-');
            rutNumero = partesRut[0];
            rutDv = partesRut[1];
        } else {
            rutNumero = rutCompleto;
        }

        var correoLocal = '';
        var correoDominio = '';
        if (correoCompleto && correoCompleto.includes('@')) {
            var partesCorreo = correoCompleto.split('@');
            correoLocal = partesCorreo[0];
            correoDominio = ('@' + partesCorreo[1]).toLowerCase();
        } else {
            correoLocal = correoCompleto;
        }

        var modal = $(this);
        modal.find('#edit_rut_funcionario').val(rutNumero);
        modal.find('#edit_rut_verificador').val(rutDv);
        modal.find('#edit_nombre_funcionario').val(nombre);
        modal.find('#edit_correo_funcionario').val(correoLocal);
        modal.find('#edit_correo_dominio').val(correoDominio);
        modal.find('#edit_cargo_funcionario').val(cargo);
        modal.find('#edit_codigo_Unidad').val(unidadId);
        modal.find('#edit_rut_actual').val(rutCompleto);
        modal.find('#rut_completo').val(rutCompleto);
        modal.find('#edit_correo_oculto').val(correoCompleto);
        modal.find('#edit_activoFuncionario').val(String(activoVal));

        // Poblar motivo y detalle si viene
        const selectMotivo = modal.find('#edit_motivo_inactivo');
        const hiddenMotivoId = modal.find('#edit_motivo_inactividad_id');
        if (motivoId && selectMotivo.length) {
            const optMatch = selectMotivo.find(`option[data-id="${motivoId}"]`).first();
            if (optMatch && optMatch.val()) {
                selectMotivo.val(optMatch.val());
                hiddenMotivoId.val(motivoId);
            } else {
                selectMotivo.val('');
                hiddenMotivoId.val('');
            }
        } else {
            selectMotivo.val('');
            hiddenMotivoId.val('');
        }
        if (detalleInactivo) {
            modal.find('#edit_detalle_inactivo').val(detalleInactivo);
        } else {
            modal.find('#edit_detalle_inactivo').val('');
        }

        toggleCamposInactivo();
    });

    $('#edit_rut_funcionario, #edit_rut_verificador').on('input', function () {
        var numero = $('#edit_rut_funcionario').val();
        var dv = $('#edit_rut_verificador').val();
        if (numero || dv) {
            $('#editFuncionarioModal').find('#rut_completo').val(numero + '-' + dv);
        } else {
            $('#editFuncionarioModal').find('#rut_completo').val('');
        }
    });

    $('#edit_correo_funcionario, #edit_correo_dominio').on('input change', function () {
        var local = $('#edit_correo_funcionario').val();
        var dominio = $('#edit_correo_dominio').val();
        if (local || dominio) {
            $('#editFuncionarioModal').find('#edit_correo_oculto').val(local + dominio);
        } else {
            $('#editFuncionarioModal').find('#edit_correo_oculto').val('');
        }
    });
});


// --- Impresión de funcionarios ---
function normalizarTextoFiltro(valor) {
    if (!valor) return "";
    const limpio = String(valor).trim();
    if (!limpio) return "";
    if (limpio.toLowerCase().startsWith("seleccione")) return "";
    return limpio;
}

function construirFiltrosImpresionFuncionarios() {
    return {
        q: normalizarTextoFiltro(document.getElementById('printFuncQuery')?.value || ''),
        unidad: normalizarTextoFiltro(document.getElementById('printFuncUnidad')?.value || ''),
        cargo: normalizarTextoFiltro(document.getElementById('printFuncCargo')?.value || ''),
    };
}

function imprimirFuncionarios() {
    const filtros = construirFiltrosImpresionFuncionarios();
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([key, value]) => {
        if (value) params.append(key, value);
    });
    const url = params.toString() ? `/funcionario/imprimir?${params.toString()}` : '/funcionario/imprimir';
    const win = window.open(url, '_blank');
    if (!win || win.closed || typeof win.closed === 'undefined') {
        window.location.href = url;
    } else {
        win.focus();
    }
}

function actualizarTextoBotonImprimirFuncionarios() {
    const filtros = construirFiltrosImpresionFuncionarios();
    const tieneFiltro = Object.values(filtros).some(Boolean);
    const btn = document.getElementById('printFuncionarioButton');
    if (btn) {
        btn.textContent = tieneFiltro ? 'Imprimir con filtro' : 'Imprimir todo';
    }
}

function limpiarFiltrosImpresionFuncionarios() {
    ['printFuncQuery','printFuncUnidad','printFuncCargo'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = "";
    });
    actualizarTextoBotonImprimirFuncionarios();
}

function toggleCamposInactivo() {
    const select = document.getElementById('edit_activoFuncionario');
    const bloque = document.getElementById('edit_inactivo_fields');
    if (!select || !bloque) return;
    if (select.value === '0') {
        bloque.classList.remove('d-none');
    } else {
        bloque.classList.add('d-none');
    }
}