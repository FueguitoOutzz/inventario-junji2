document.addEventListener("DOMContentLoaded", () => {
  refreshCheckboxListeners();

  const btnDevolver = document.getElementById("devolver-button");

  if (btnDevolver && !window.pendientesDevolucion) {
    btnDevolver.addEventListener("click", () => {
      let checkboxes = document.querySelectorAll(".row-checkbox:checked");
      if (checkboxes.length === 0) {
        alert("Por favor, selecciona al menos un equipo para devolver.");
        return; // Evita abrir el modal
      }
      actualizarModalDevolucion();
      // Abrir el modal de confirmación
      let modal = new bootstrap.Modal(document.getElementById("modalConfirmarDevolucion"));
      modal.show();
    });
  }

  // Vincular la función de envío al botón "Continuar" dentro del modal
  const btnContinuar = document.getElementById("btnContinuarDevolucion");
  if (btnContinuar) {
    btnContinuar.addEventListener("click", devolverSeleccionados);
  }

  // Manejar el cambio de selección de checkboxes
  document.querySelectorAll(".row-checkbox").forEach(checkbox => {
    checkbox.addEventListener("change", function () {
      let idEquipoAsignacion = this.value;
      let rowModal = document.getElementById(`modal-row-${idEquipoAsignacion}`);
      let inputHidden = document.getElementById(`modal-input-${idEquipoAsignacion}`);

      if (this.checked) {
        if (rowModal) rowModal.style.display = "";
        if (inputHidden) inputHidden.style.display = "block";
      } else {
        if (rowModal) rowModal.style.display = "none";
        if (inputHidden) inputHidden.style.display = "none";
      }
      actualizarEstadoBotonFirmar();
    });
  });

  // Permitir seleccionar la fila al hacer clic en ella (sin afectar el checkbox directamente)
  document.querySelectorAll(".selectable-row").forEach(row => {
    row.addEventListener("click", function (event) {
      if (event.target.tagName === "INPUT" && event.target.type === "checkbox") return; // 1. Evitar cambio si se hace clic sobre un checkbox directamente
      if (event.target.closest("button") || event.target.closest("i")) return; // 2. Evitar cambio si el clic vino de un botón o ícono

      let checkbox = this.querySelector(".row-checkbox");
      checkbox.checked = !checkbox.checked;
      checkbox.dispatchEvent(new Event("change"));
    });
  });

  // Habilita/deshabilita el botón de devolver
  document.querySelectorAll(".row-checkbox").forEach(checkbox => {
    let idEquipoAsignacion = checkbox.value;
    let row = document.getElementById(`row-${idEquipoAsignacion}`);

    checkbox.addEventListener("change", actualizarEstadoBotonDevolver);
  });

  // Llamar a la función al cargar la página para deshabilitar el botón si no hay equipos seleccionables
  actualizarEstadoBotonDevolver();

  // Funciones asociadas al manejo del botón de Descargar PDF
  const btnDescargarPDF = document.getElementById("descargar-PDF-button");
  const btnAsignaciones = document.getElementById("descargar-asignacion");
  const btnDevoluciones = document.getElementById("descargar-devolucion");
  const checkboxes = document.querySelectorAll(".row-checkbox");

  function actualizarEstadoBotonDescargarPDF() {
    // Filtra los checkboxes que están seleccionados
    let seleccionados = Array.from(checkboxes).filter(cb => cb.checked);

    if (seleccionados.length === 1) {
      let checkbox = seleccionados[0];
      let idAsignacion = checkbox.dataset.idAsignacion;
      let idDevolucion = checkbox.dataset.idDevolucion;

      btnDescargarPDF.removeAttribute("disabled");
      btnAsignaciones.classList.remove("disabled");
      btnAsignaciones.href = `/asignacion/descargar_pdf_asignacion/${idAsignacion}`;

      // Para la opción de devolución, se habilita solo si existe un idDevolucion válido
      if (idDevolucion && idDevolucion.trim() !== "") {
        btnDevoluciones.classList.remove("disabled");
        btnDevoluciones.href = `/asignacion/descargar_pdf_devolucion/${idDevolucion}`;
      } else {
        btnDevoluciones.classList.add("disabled");
        btnDevoluciones.removeAttribute("href");
      }
    } else {
      // Si no hay ninguno o hay más de uno, se deshabilitan ambos botones
      btnDescargarPDF.setAttribute("disabled", "true");
      btnAsignaciones.classList.add("disabled");
      btnAsignaciones.removeAttribute("href");
      btnDevoluciones.classList.add("disabled");
      btnDevoluciones.removeAttribute("href");
    }
  }

  // Actualiza el estado cada vez que cambia la selección de algún checkbox
  checkboxes.forEach(checkbox => {
    checkbox.addEventListener("change", actualizarEstadoBotonDescargarPDF);
  });

  actualizarEstadoBotonDescargarPDF();
  actualizarEstadoBotonFirmar();
  // Fin de funciones asociadas al manejo del botón de Descargar PDF
});

// Función que actualiza el modal con las asignaciones seleccionadas
function actualizarModalDevolucion() {
  let checkboxes = document.querySelectorAll(".row-checkbox:checked");

  checkboxes.forEach(checkbox => {
    let idEquipoAsignacion = checkbox.value;
    let rowModal = document.getElementById(`modal-row-${idEquipoAsignacion}`);
    let inputHidden = document.getElementById(`modal-input-${idEquipoAsignacion}`);

    if (rowModal) rowModal.style.display = "";  // Mostrar la fila en el modal
    if (inputHidden) inputHidden.style.display = "block"; // Mostrar input hidden
  });
}

// **Función para devolver equipos seleccionados**
function devolverSeleccionados() {
  let checkboxes = document.querySelectorAll(".row-checkbox:checked");
  let idsEquipos = [];

  checkboxes.forEach(checkbox => {
    idsEquipos.push(checkbox.value);
  });

  if (idsEquipos.length === 0) {
    alert("Por favor, selecciona al menos un equipo para devolver.");
    return;
  }

  // Crear el formulario y enviarlo
  let form = document.getElementById("formDevolver");

  // Limpiar cualquier input oculto previo
  document.querySelectorAll("#formDevolver input[name='equiposSeleccionados']").forEach(input => input.remove());

  idsEquipos.forEach(id => {
    let input = document.createElement("input");
    input.type = "hidden";
    input.name = "equiposSeleccionados";
    input.value = id;
    form.appendChild(input);
  });

  form.submit();
}

function actualizarEstadoBotonDevolver() {
  const checkboxes = document.querySelectorAll(".row-checkbox:checked");
  const btnDevolver = document.getElementById("devolver-button");

  let hayDevuelto = false; // Variable para saber si hay al menos un equipo ya devuelto
  let idAsignacionBase = null;
  let mismaAsignacion = true; // Variable para saber si todas las checkbox marcadas pertenecen a la misma asignación

  checkboxes.forEach((checkbox, index) => {
    // 1. Verificar si ya fue devuelto
    if (checkbox.dataset.devuelto === "true") {
      hayDevuelto = true;
    }

    // 2. Validar si comparten el mismo idAsignacion
    if (index === 0) {
      // Guardamos el idAsignacion del primer checkbox seleccionado
      idAsignacionBase = checkbox.dataset.idAsignacion;
    } else {
      // Comparamos con el primer idAsignacion
      if (checkbox.dataset.idAsignacion !== idAsignacionBase) {
        mismaAsignacion = false;
      }
    }
  });

  if (!hayDevuelto && checkboxes.length > 0 && mismaAsignacion) {
    btnDevolver.removeAttribute("disabled");
  } else {
    btnDevolver.setAttribute("disabled", "true");
  }
}

function updateGuardarAsignacionState() {
  const btnGuardar = document.getElementById("btnGuardarAsignacion");
  if (!btnGuardar) return;
  const modalEl = document.getElementById("addAsignacionModal");
  if (modalEl && modalEl.classList.contains("submitting")) {
    btnGuardar.disabled = true;
    btnGuardar.setAttribute("aria-disabled", "true");
    return;
  }
  const seleccionados = document.querySelectorAll(
    'input[name="equipoSeleccionado"]:checked'
  ).length;
  btnGuardar.disabled = seleccionados === 0;
  btnGuardar.setAttribute("aria-disabled", seleccionados === 0 ? "true" : "false");
}

// Función para actualizar listeners de checkboxes
function refreshCheckboxListeners() {
  const equipoCheckboxes = document.querySelectorAll('.equipo-checkbox');
  const selectedEquiposDiv = document.getElementById('selectedEquipos');

  equipoCheckboxes.forEach(checkbox => {
    if (checkbox.dataset.listenerAttached === "true") return;
    checkbox.dataset.listenerAttached = "true";
    checkbox.addEventListener('change', function () {
      const equipoId = this.value;

      if (this.checked) {
        const existing = document.getElementById(`equipo-hidden-${equipoId}`);
        if (existing) {
          updateGuardarAsignacionState();
          return;
        }
        // Agregar input oculto con el equipo seleccionado
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = 'equiposAsignados[]';
        hiddenInput.value = equipoId;
        hiddenInput.id = `equipo-hidden-${equipoId}`;
        selectedEquiposDiv.appendChild(hiddenInput);
      } else {
        // Remover input oculto si se desmarca
        const hiddenInput = document.getElementById(`equipo-hidden-${equipoId}`);
        if (hiddenInput) {
          hiddenInput.remove();
        }
      }

      // Limpiar error si hay al menos 1 equipo seleccionado
      const equiposSeleccionados = document.querySelectorAll('input[name="equiposAsignados[]"]').length;
      if (equiposSeleccionados > 0) {
        limpiarError($("#equiposContainer"));
      }
      updateGuardarAsignacionState();
    });
  });
  enableRowClick();
  updateGuardarAsignacionState();
}

function enableRowClick() {
  const rows = document.querySelectorAll('#equiposTable tr');

  rows.forEach(row => {
    row.removeEventListener('click', rowClickHandler);
    row.addEventListener('click', rowClickHandler);
  });
}

function rowClickHandler(event) {
  // Evitar que el evento se dispare si el clic es sobre el checkbox
  if (event.target.tagName === 'INPUT' && event.target.type === 'checkbox') return;

  // Encontrar el checkbox en la fila y alternar su estado
  const checkbox = this.querySelector('.equipo-checkbox');
  if (checkbox) {
    checkbox.checked = !checkbox.checked;
    checkbox.dispatchEvent(new Event('change')); // Disparar evento 'change' manualmente
  }
}

document.getElementById('searchEquipo').addEventListener('input', function () {
  const filter = this.value.toLowerCase();
  const rows = document.querySelectorAll('#equiposTable tr');

  rows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(filter) ? '' : 'none';
  });
});

$(document).ready(function () {
  // Validación cuando se intente enviar el formulario
  $(document).on("submit", "#form-asignacion-modal", function (e) {
    // Cantidad de equipos que se han agregado dinámicamente

    const equiposSeleccionados = document.querySelectorAll('input[name="equiposAsignados[]"]').length;

    if (equiposSeleccionados === 0) {
      e.preventDefault();
      // Apuntamos al contenedor #equiposContainer
      mostrarError($("#equiposContainer"), "Debes asignar al menos un equipo");
    } else {
      limpiarError($("#equiposContainer"));
    }
  });

  $("#addAsignacionModal").on("hidden.bs.modal", function () {
    limpiarError($("#equiposContainer"));

    // Desmarcar todos los checkboxes
    $(".equipo-checkbox").prop("checked", false);

    // Eliminar los inputs ocultos que se agregaron para equipos seleccionados
    $("#selectedEquipos").empty();
    updateGuardarAsignacionState();
  });
});

function setTooltipText(element, newText) {
  $(element).attr("data-bs-title", newText);
  let tip = bootstrap.Tooltip.getInstance(element);
  if (tip) {
    tip.dispose(); // Destruye el tooltip previo
  }
  new bootstrap.Tooltip(element); // Crea uno nuevo con el texto actualizado
}
function actualizarEstadoBotonFirmar() {
  const checkboxes = document.querySelectorAll(".row-checkbox:checked");
  const btnFirmar = document.getElementById("firmar-button");
  const btnAsignacionFirmar = document.getElementById("documento-firmado-asignacion");
  const btnDevolucionFirmar = document.getElementById("documento-firmado-devolucion");

  if (checkboxes.length === 1) {
    let checkbox = checkboxes[0];
    let idAsignacion = checkbox.dataset.idAsignacion;
    let idDevolucion = checkbox.dataset.idDevolucion;

    // Habilitar el dropdown principal
    btnFirmar.removeAttribute("disabled");

    // Habilitar el botón de asignación
    btnAsignacionFirmar.classList.remove("disabled");
    btnAsignacionFirmar.href = `/asignacion/listar_pdf/${idAsignacion}`;

    // Habilitar el botón de devolución solo si ya se devolvió el equipo
    if (idDevolucion && idDevolucion.trim() !== "") {
      btnDevolucionFirmar.classList.remove("disabled");
      btnDevolucionFirmar.href = `/asignacion/listar_pdf/${idAsignacion}/devolver`;
    } else {
      btnDevolucionFirmar.classList.add("disabled");
      btnDevolucionFirmar.removeAttribute("href");
    }
  } else {
    // Deshabilitar todo si no hay exactamente una selección
    btnFirmar.setAttribute("disabled", "true");
    btnAsignacionFirmar.classList.add("disabled");
    btnAsignacionFirmar.removeAttribute("href");
    btnDevolucionFirmar.classList.add("disabled");
    btnDevolucionFirmar.removeAttribute("href");
  }
}
$(document).ready(function () {
  let listaFuncionarios = [];
  try {
    listaFuncionarios = JSON.parse($("#listaFuncionarios").attr("data-funcionarios")) || [];
  } catch (e) {
    console.error("Error al parsear funcionarios:", e);
  }
  console.log("Funcionarios cargados:", Array.isArray(listaFuncionarios) ? listaFuncionarios.length : 0);

  let label = $("#label-funcionario");
  let contenedorNombre = $("#contenedorNombre");
  let contenedorRut = $("#contenedorRut");
  let nombreInput = $("#nombre_funcionario");
  let rutInput = $("#rut_funcionario");
  let sugerenciasDiv = $("#sugerencias_funcionarios");
  let toggleBtn = $("#toggleFuncionario");

  toggleBtn.on("click", function () {
    if (contenedorNombre.is(":visible")) {
      contenedorNombre.hide();
      sugerenciasDiv.hide();
      contenedorRut.show();
      rutInput.focus();
      limpiarError(rutInput);
      setTooltipText(this, "Buscar por nombre");
      label.html('RUT del funcionario o Código Unidad<span style="color: red; margin-left: 5px">*</span>');
    } else {
      contenedorRut.hide();
      contenedorNombre.show();
      nombreInput.focus();
      limpiarError(nombreInput);
      setTooltipText(this, "Buscar por RUT");
      label.html('Nombre del funcionario<span style="color: red; margin-left: 5px">*</span>');
    }
  });

  nombreInput.on("input", function () {
    let input = $(this).val().trim().toLowerCase();

    if (input.length === 0) {
      sugerenciasDiv.hide();
      return;
    }

    let coincidencias = listaFuncionarios.filter(f =>
      String(f.nombre || "").toLowerCase().includes(input)
    );

    if (coincidencias.length > 0) {
      let listaHTML = coincidencias.map(funcionario =>
        `<button type="button" class="list-group-item list-group-item-action sugerencia-item"
                   data-nombre="${funcionario.nombre}" data-rut="${String(funcionario.rut)}">
              ${funcionario.nombre}
          </button>`
      ).join("");

      sugerenciasDiv.html(listaHTML).show();
    } else {
      sugerenciasDiv.html("<p class='list-group-item text-danger'>No encontrado</p>").show();
    }
  });

  rutInput.on("input", function () {
    let input = $(this).val().trim();

    if (input.length === 0) {
      sugerenciasDiv.hide();
      return;
    }

    let coincidencias = listaFuncionarios.filter(f => {
      let [rutSinDV] = String(f.rut || "").split("-");
      return rutSinDV.startsWith(input);
    });

    if (coincidencias.length > 0) {
      let listaHTML = coincidencias.map(funcionario =>
        `<button type="button" class="list-group-item list-group-item-action sugerencia-item"
                   data-nombre="${funcionario.nombre}" data-rut="${String(funcionario.rut)}">
              ${funcionario.rut} - ${funcionario.nombre}
          </button>`
      ).join("");

      sugerenciasDiv.html(listaHTML).show();
    } else {
      sugerenciasDiv.html("<p class='list-group-item text-danger'>No encontrado</p>").show();
    }
  });

  $(document).on("click", ".sugerencia-item", function () {
    let nombre = $(this).data("nombre");
    let rutCompleto = String($(this).data("rut")).trim();
    // Limpiar cualquier prefijo de nombre si existiera en data-rut
    let match = rutCompleto.match(/(\d{1,2}(?:\.?\d{3}){2}-[\dkK])$/);
    if (match) rutCompleto = match[1].replace(/\./g, '');
    
    let [rutSinDV, dv] = rutCompleto.split("-");

    $("#nombre_funcionario").val(nombre);
    $("#rut_funcionario").val(rutSinDV);
    $("#rut_verificador").val(dv || '');
    $("#rut_completo").val(rutCompleto);

    sugerenciasDiv.hide();
    limpiarError($("#nombre_funcionario"));
    limpiarError($("#rut_funcionario"));
  });

  $(document).click(function (event) {
    if (!$(event.target).closest("#nombre_funcionario, #rut_funcionario, #sugerencias_funcionarios").length) {
      sugerenciasDiv.hide();
    }
  });

  $(document).on("submit", "#form-asignacion-modal", function (event) {
    let esValido = true;
    const desactivarDV = $("#desactivar_dv").is(":checked");
    let funcionarioSeleccionado = null;

    if (contenedorNombre.is(":visible")) {
      let nombreIngresado = nombreInput.val().trim();
      if (!desactivarDV) {
        funcionarioSeleccionado = listaFuncionarios.find(f =>
          String(f.nombre || "").toLowerCase() === nombreIngresado.toLowerCase()
        ) || null;
        if (!funcionarioSeleccionado) {
          mostrarError(nombreInput, "No se ha encontrado el funcionario");
          esValido = false;
        } else {
          limpiarError(nombreInput);
        }
      } else {
        if (nombreIngresado.length === 0) {
          mostrarError(nombreInput, "Debe ingresar un nombre");
          esValido = false;
        } else {
          limpiarError(nombreInput);
        }
      }
    }

    if (contenedorRut.is(":visible") && !desactivarDV) {
      let rutIngresado = rutInput.val().trim();
      funcionarioSeleccionado = listaFuncionarios.find(f => {
        let [rutSinDV] = String(f.rut).split("-");
        return rutSinDV === rutIngresado;
      }) || funcionarioSeleccionado;

      if (!funcionarioSeleccionado) {
        mostrarError(rutInput, "No se ha encontrado el RUT ingresado");
        esValido = false;
      } else {
        limpiarError(rutInput);
      }
    }

    if (!esValido) {
      event.preventDefault();
    } else if (!desactivarDV && funcionarioSeleccionado) {
      // Asegura que el RUT completo viaje en el form incluso si solo se seleccionó por nombre
      const rutCompleto = String(funcionarioSeleccionado.rut);
      const [rutSinDV, dv] = rutCompleto.split("-");
      $("#rut_completo").val(rutCompleto);
      if (rutSinDV) {
        $("#rut_funcionario").val(rutSinDV);
      }
      if (dv) {
        $("#rut_verificador").val(dv);
      }
    }
  });

  function setTooltipText(button, text) {
    $(button).attr("title", text).tooltip("dispose").tooltip();
  }
});

function setCrearTrasladoHidden(form, valor) {
  form.querySelectorAll('input[name="crear_traslado"]').forEach((el) => el.remove());
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = "crear_traslado";
  input.value = valor;
  form.appendChild(input);
}

function submitAsignacionForm(form, valor) {
  setCrearTrasladoHidden(form, valor);
  form.dataset.skipTrasladoConfirm = "1";
  if (typeof form.requestSubmit === "function") {
    form.requestSubmit();
  } else {
    form.submit();
  }
}

$(document).ready(function () {
  $(document).on("submit", "#form-asignacion-modal", function (e) {
    const form = this;
    
    // Si ya validamos traslado, permitimos el envío normal
    if (form.dataset.skipTrasladoConfirm === "1") {
      return; // Permite que el evento siga su curso natural
    }

    // Antes de validar traslado, verificamos si es válido el form básico (nombre/rut)
    // El handler anterior (línea 464) ya hace validaciones y preventDefault si hay error.
    // Si llegamos aquí y ya fue cancelado por el handler anterior, paramos.
    if (e.isDefaultPrevented()) return;

    const equipos = Array.from(
      form.querySelectorAll('input[name="equipoSeleccionado"]:checked')
    ).map((cb) => cb.value);

    if (equipos.length === 0) return;

    const rutInput = form.querySelector('input[name="rut_funcionario"]');
    const rut = rutInput ? rutInput.value.trim() : "";
    if (!rut) return;

    e.preventDefault(); // Detenemos para validar traslado

    const formData = new FormData(form);
    // Asegurarnos de que el RUT y equipos viajen igual que en el submit real
    formData.delete("equiposAsignados[]");
    equipos.forEach((eq) => formData.append("equiposAsignados[]", eq));
    formData.set("rut_funcionario", rut);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    fetch("/asignacion/validar_traslado", {
      method: "POST",
      body: formData,
      signal: controller.signal,
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && data.requiere_traslado) {
          const modalEl = document.getElementById("modalConfirmarTraslado");
          if (!modalEl) {
            submitAsignacionForm(form, "0");
            return;
          }
          const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
          modal.show();

          const aceptar = document.getElementById("btnAceptarTraslado");
          const cancelar = document.getElementById("btnCancelarTraslado");

          if (aceptar) {
            aceptar.onclick = function () {
              modal.hide();
              submitAsignacionForm(form, "1");
            };
          }
          if (cancelar) {
            cancelar.onclick = function () {
              modal.hide();
              submitAsignacionForm(form, "0");
            };
          }
        } else {
          submitAsignacionForm(form, "0");
        }
      })
      .catch(() => {
        submitAsignacionForm(form, "0");
      })
      .finally(() => clearTimeout(timeoutId));
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const modalEl = document.getElementById("addAsignacionModal");
  if (!modalEl) return;

  modalEl.addEventListener("hide.bs.modal", (event) => {
    if (modalEl.classList.contains("submitting")) {
      event.preventDefault();
    }
  });

  // Lógica para pre-seleccionar equipos si vienen en la URL (?ids=1,2,3)
  const urlParams = new URLSearchParams(window.location.search);
  const idsParam = urlParams.get('ids');
  if (idsParam) {
    const ids = idsParam.split(',');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();

    setTimeout(() => {
      ids.forEach(id => {
        const checkbox = document.querySelector(`.equipo-checkbox[value="${id}"]`);
        if (checkbox) {
          checkbox.checked = true;
          checkbox.dispatchEvent(new Event('change'));
        }
      });
      // Limpiar la URL para evitar re-apertura al recargar
      window.history.replaceState({}, document.title, window.location.pathname);
    }, 500);
  }
});

$(document).on("submit", "#form-asignacion-modal", function (e) {
  setTimeout(() => {
    if (e.isDefaultPrevented()) return;

    const modalEl = document.getElementById("addAsignacionModal");
    const btnGuardar = document.getElementById("btnGuardarAsignacion");
    const spinner = btnGuardar ? btnGuardar.querySelector(".spinner-border") : null;
    const btnText = btnGuardar ? btnGuardar.querySelector(".btn-text") : null;

    if (modalEl) {
      modalEl.classList.add("submitting");
    }

    document.querySelectorAll(".btn-cerrar-asignacion").forEach((btn) => {
      btn.setAttribute("disabled", "true");
    });

    if (btnGuardar) {
      btnGuardar.setAttribute("disabled", "true");
      btnGuardar.setAttribute("aria-busy", "true");
    }
    if (spinner) spinner.classList.remove("d-none");
    if (btnText) btnText.textContent = "Guardando...";

    setTimeout(() => {
      if (!modalEl || !modalEl.classList.contains("submitting")) {
        return;
      }
      modalEl.classList.remove("submitting");
      document.querySelectorAll(".btn-cerrar-asignacion").forEach((btn) => {
        btn.removeAttribute("disabled");
      });
      if (btnGuardar) {
        btnGuardar.removeAttribute("disabled");
        btnGuardar.removeAttribute("aria-busy");
      }
      if (spinner) spinner.classList.add("d-none");
      if (btnText) btnText.textContent = "Guardar";
      alert("La operación está tardando más de lo normal. Revisa la conexión y vuelve a intentar.");
    }, 30000);
  }, 0);
});


