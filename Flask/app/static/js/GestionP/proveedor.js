document.addEventListener("DOMContentLoaded", function () {
    const editProveedorForm = document.getElementById("editProveedorForm");
    const editIdProveedor = document.getElementById("edit_idProveedor");
    const editNombreProveedor = document.getElementById("edit_nombreProveedor");

    // Configurar el modal con datos dinámicos
    document.querySelectorAll(".edit-button").forEach(button => {
        button.addEventListener("click", function () {
            const idProveedor = this.dataset.id;
            const nombreProveedor = this.dataset.nombre;

            // Llenar el modal con los datos del proveedor
            editIdProveedor.value = idProveedor;
            editNombreProveedor.value = nombreProveedor;

            // Configurar la acción del formulario
            editProveedorForm.action = `/update_proveedor/${idProveedor}`;

            // Imprimir valores para depuración
            console.log("ID del proveedor:", idProveedor);
            console.log("Nombre del proveedor:", nombreProveedor);
            console.log("Action del formulario:", editProveedorForm.action);
        });
    });
});

$(document).ready(function () {
    $("#form_addProveedorModal").on("submit", function (e) {
        e.preventDefault();
        let nombreProveedor = $("#nombre_proveedor").val().trim();

        if (!nombreProveedor) {
            mostrarMensaje("El nombre del proveedor no puede estar vacío.", "warning");
            return;
        }

        // Enviar datos con AJAX
        $.post("/add_proveedor", $(this).serialize(), function (response) {
            mostrarMensaje(response.message, response.tipo_alerta);
            if (response.status === "success") {
                setTimeout(() => location.reload(), 1500);
            }
        }).fail(function (xhr) {
            let errorMsg = xhr.responseJSON?.message || "Error al agregar el proveedor.";
            let tipoAlerta = xhr.responseJSON?.tipo_alerta || "danger";
            mostrarMensaje(errorMsg, tipoAlerta);
        });
    });

    $("#eliminarSeleccionados").on("click", function () {
        let seleccionados = $(".row-checkbox:checked").closest("tr").map(function () {
            return $(this).data("id");
        }).get();

        console.log("🔍 IDs seleccionados para eliminación:", seleccionados); // 🔍 Debug

        if (seleccionados.length === 0) {
            mostrarMensaje("Debe seleccionar al menos un proveedor para eliminar.", "warning");
            return;
        }

        // Abrir el modal de confirmación
        $("#confirmDeleteModal").modal("show");

        $("#confirmDeleteBtn").off("click").on("click", function () {
            $("#confirmDeleteModal").modal("hide");

            $.ajax({
                url: "/delete_proveedor",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify({ ids: seleccionados }),
                success: function (response) {
                    console.log("✅ Respuesta del backend:", response);  // 🔍 Debug
                    mostrarMensaje(response.message, "success");
                    setTimeout(() => location.reload(), 1500);
                },
                error: function (xhr) {
                    let errorMsg = xhr.responseJSON?.message || "Error al eliminar los proveedores.";
                    console.error("❌ Error del backend:", xhr.responseJSON);  // 🔍 Debug
                    mostrarMensaje(errorMsg, "danger");
                }
            });
        });
    });

    // **Función para Mostrar Mensajes en la UI**
    function mostrarMensaje(mensaje, tipo) {
        let alertContainer = $("#alertContainer");

        if (alertContainer.length === 0) {
            console.warn("⚠️ El contenedor #alertContainer no se encontró. Creándolo...");
            $("body").prepend('<div id="alertContainer" class="alert d-none" role="alert"></div>');
            alertContainer = $("#alertContainer");
        }

        alertContainer.removeClass("d-none alert-success alert-warning alert-danger")
            .addClass(`alert alert-${tipo}`)
            .html(`<i class="bi bi-info-circle"></i> ${mensaje}`)
            .fadeIn();

        setTimeout(() => {
            alertContainer.fadeOut("slow", function () {
                $(this).addClass("d-none");
            });
        }, 4000);
    }

});

document.getElementById("editProveedorForm").addEventListener("submit", function (event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const proveedorId = document.getElementById("edit_idProveedor").value;
    const actionUrl = `/update_proveedor/${proveedorId}`;

    // Limpiar mensajes de error previos
    const errorContainer = document.getElementById("editProveedorError");
    errorContainer.classList.add("d-none");
    errorContainer.innerHTML = "";

    fetch(actionUrl, {
        method: "POST",
        body: formData,
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw errorData;
                });
            }
            return response.json();
        })
        .then(data => {
            // Mensaje de éxito y recargar la página
            alert("Proveedor actualizado correctamente");
            window.location.reload(); // Recargar la página para reflejar los cambios
        })
        .catch(error => {
            // Mostrar mensaje de error en el modal
            if (error.message) {
                errorContainer.innerHTML = error.message;
                errorContainer.classList.remove("d-none");
            } else {
                alert("Ocurrió un error inesperado. Por favor, inténtelo de nuevo.");
            }
        });
});

// --- Impresión de proveedores ---
function normalizarFiltroProveedor(valor) {
    if (!valor) return "";
    const limpio = String(valor).trim();
    if (!limpio) return "";
    return limpio;
}

function construirFiltrosImpresionProveedores() {
    return {
        q: normalizarFiltroProveedor(document.getElementById('printProveedorQuery')?.value || '')
    };
}

function imprimirProveedores() {
    const filtros = construirFiltrosImpresionProveedores();
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([key, value]) => {
        if (value) params.append(key, value);
    });
    const url = params.toString() ? `/proveedor/imprimir?${params.toString()}` : '/proveedor/imprimir';
    const win = window.open(url, '_blank');
    if (!win || win.closed || typeof win.closed === 'undefined') {
        window.location.href = url;
    } else {
        win.focus();
    }
}

function actualizarTextoBotonImprimirProveedores() {
    const filtros = construirFiltrosImpresionProveedores();
    const btn = document.getElementById('printProveedorButton');
    if (btn) {
        const tieneFiltro = Object.values(filtros).some(Boolean);
        btn.textContent = tieneFiltro ? 'Imprimir con filtro' : 'Imprimir todo';
    }
}

function limpiarFiltrosImpresionProveedores() {
    const input = document.getElementById('printProveedorQuery');
    if (input) input.value = "";
    actualizarTextoBotonImprimirProveedores();
}

document.addEventListener('DOMContentLoaded', function () {
    const printBtn = document.getElementById('printProveedorButton');
    if (printBtn) {
        printBtn.addEventListener('click', imprimirProveedores);
    }

    const clearBtn = document.getElementById('clearProveedorPrint');
    if (clearBtn) {
        clearBtn.addEventListener('click', limpiarFiltrosImpresionProveedores);
    }

    const input = document.getElementById('printProveedorQuery');
    if (input) {
        input.addEventListener('input', actualizarTextoBotonImprimirProveedores);
    }

    const modal = document.getElementById('printProveedorModal');
    if (modal) {
        modal.addEventListener('shown.bs.modal', limpiarFiltrosImpresionProveedores);
    }

    actualizarTextoBotonImprimirProveedores();
});
