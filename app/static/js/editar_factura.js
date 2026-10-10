// Validación en vivo (comodidad visual). La validación real está en el backend.
(function () {
    const form = document.getElementById("formEditarFactura");
    if (!form) return;

    const $ = id => document.getElementById(id);
    const total = $("total"), proveedor = $("proveedor"), fecha = $("fecha"), motivo = $("motivo");
    const montos = [...document.querySelectorAll(".ef-monto")];
    const estado = $("estado"), btn = $("btnGuardar"), dialogo = $("efConfirmar");

    // Se trabaja en centavos para evitar errores de punto flotante
    const aCentavos = v => Math.round((parseFloat(v) || 0) * 100);
    const dinero = c => (c < 0 ? "-$" : "$") + (Math.abs(c) / 100).toFixed(2);
    const nombreCat = m => m.closest(".ef-fila").querySelector("label").textContent.trim();

    // Valores originales, para mostrar el antes/después y avisar de cambios sin guardar
    const original = {
        proveedor: proveedor.value, fecha: fecha.value, total: aCentavos(total.value),
        montos: montos.map(m => aCentavos(m.value))
    };
    let guardado = false;
    const hayCambios = () =>
        proveedor.value !== original.proveedor || fecha.value !== original.fecha ||
        aCentavos(total.value) !== original.total ||
        montos.some((m, i) => aCentavos(m.value) !== original.montos[i]);

    let cuadra = false, dif = 0;

    function validar() {
        const t = aCentavos(total.value);
        const suma = montos.reduce((s, m) => s + aCentavos(m.value), 0);
        dif = t - suma;
        cuadra = dif === 0 && t > 0;

        $("rIngresado").textContent = dinero(suma);
        $("rTotal").textContent = dinero(t);
        $("rDif").textContent = dinero(dif);
        $("rDif").style.color = dif === 0 ? "var(--ef-verde-2)" : "var(--ef-rojo)";

        montos.forEach(m => m.classList.toggle("ef-invalido", !cuadra));
        $("efAjuste").hidden = dif === 0 || t <= 0;

        estado.className = "ef-estado " + (cuadra ? "ok" : "error");
        estado.textContent = cuadra
            ? "Factura validada"
            : (t <= 0 ? "Ingresa el total de la factura"
                : "El desglose no coincide con la factura. Diferencia: " + dinero(dif));
        actualizarBoton();
    }

    function actualizarBoton() {
        const estadoFactura = form.dataset.estadoFactura;
        const rolUsuario = form.dataset.rolUsuario;

        // Regla: si la factura esta Observada y el usuario es owner,
        // puede validarla SIN necesidad de cambios
        const esOwner = rolUsuario === 'owner';
        const estaObservada = estadoFactura === 'Observada';
        const puedeValidarSinCambios = esOwner && estaObservada;

        const cumpleRequisitos = cuadra
            && motivo.value.trim().length >= 5
            && (hayCambios() || puedeValidarSinCambios);

        btn.disabled = !cumpleRequisitos;

        if (btn.disabled) {
            const faltantes = [];
            if (!cuadra) faltantes.push("desglose cuadrado");
            if (motivo.value.trim().length < 5) faltantes.push("motivo");
            if (!hayCambios() && !puedeValidarSinCambios) faltantes.push("al menos un cambio");
            btn.title = "Requiere: " + faltantes.join(", ");
        } else {
            btn.title = "";
        }
    }
    [total, proveedor, fecha, ...montos].forEach(el => el.addEventListener("input", validar));
    motivo.addEventListener("input", actualizarBoton);

    // Asignar la diferencia a una categoría con un clic
    $("efBtnAjuste").addEventListener("click", () => {
        const input = $("cat" + $("efCategoriaAjuste").value);
        input.value = ((aCentavos(input.value) + dif) / 100).toFixed(2);
        validar();
    });

    // Paso 1: mostrar qué va a cambiar
    form.addEventListener("submit", e => {
        e.preventDefault();
        if (btn.disabled) return;
        const filas = [];
        const fila = (campo, a, d) => a !== d && filas.push(`<tr><td>${campo}</td><td>${a}</td><td>${d}</td></tr>`);
        const optOrig = proveedor.querySelector(`[value="${original.proveedor}"]`); fila("Proveedor", optOrig ? optOrig.textContent : `(id ${original.proveedor})`, proveedor.selectedOptions[0]?.textContent ?? "");
        fila("Fecha", original.fecha, fecha.value);
        fila("Total", dinero(original.total), dinero(aCentavos(total.value)));
        montos.forEach((m, i) => fila(nombreCat(m), dinero(original.montos[i]), dinero(aCentavos(m.value))));
        $("efCambios").innerHTML = filas.join("");
        dialogo.showModal();
    });

    $("efCancelarDialogo").addEventListener("click", () => dialogo.close());

    // Paso 2: guardar
    $("efConfirmarGuardar").addEventListener("click", async () => {
        const confirmar = $("efConfirmarGuardar");
        confirmar.disabled = true;
        try {
            const r = await fetch(form.dataset.url, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    proveedor_id: proveedor.value, fecha: fecha.value, total_factura: total.value,
                    motivo: motivo.value.trim(),
                    detalle: montos.map(m => ({ categoria_id: +m.dataset.categoria, monto: m.value }))
                })
            });
            const data = await r.json();
            if (!r.ok) throw new Error(data.error || "Error al guardar");
            guardado = true;
            dialogo.close();
            toast("Cambios guardados");
            setTimeout(() => location.reload(), 1200);   // recarga para ver el historial actualizado
        } catch (err) {
            dialogo.close();
            estado.className = "ef-estado error";
            estado.textContent = err.message;
        } finally {
            confirmar.disabled = false;
        }
    });

    window.addEventListener("beforeunload", e => {
        if (hayCambios() && !guardado) { e.preventDefault(); e.returnValue = ""; }
    });

    function toast(msg) {
        const t = $("efToast");
        t.textContent = msg;
        t.style.display = "block";
        setTimeout(() => (t.style.display = "none"), 2500);
    }

    validar();
})();