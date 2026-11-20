/* ============================================
   SELECT CON BUSCADOR
   Uso: <select data-buscable="Buscar proveedor..."> ... </select>
   El <select> original queda oculto y sigue siendo la fuente de verdad
   (su .value, sus <option> y el evento "change" funcionan igual que antes).
   ============================================ */
(function () {
    function normalizar(t) {
        return (t || '').toString()
            .normalize('NFD').replace(/[̀-ͯ]/g, '')
            .toLowerCase().trim();
    }

    function crear(select, placeholderBusqueda) {
        if (!select || select.dataset.sbListo) return;
        select.dataset.sbListo = '1';

        var usaFormSelect = select.classList.contains('form-select');

        // ---- DOM ----
        var wrap = document.createElement('div');
        wrap.className = 'sb-wrap';

        var display = document.createElement('button');
        display.type = 'button';
        display.className = 'sb-display ' + select.className;
        display.setAttribute('aria-haspopup', 'listbox');
        display.setAttribute('aria-expanded', 'false');

        var texto = document.createElement('span');
        texto.className = 'sb-text';
        display.appendChild(texto);

        if (!usaFormSelect) {
            var caret = document.createElement('span');
            caret.className = 'sb-caret';
            display.appendChild(caret);
        }

        var panel = document.createElement('div');
        panel.className = 'sb-panel';
        panel.hidden = true;

        var buscar = document.createElement('input');
        buscar.type = 'text';
        buscar.className = 'sb-search';
        buscar.placeholder = placeholderBusqueda || 'Buscar...';
        buscar.setAttribute('autocomplete', 'off');
        buscar.setAttribute('aria-label', placeholderBusqueda || 'Buscar');

        var lista = document.createElement('ul');
        lista.className = 'sb-list';
        lista.setAttribute('role', 'listbox');

        panel.appendChild(buscar);
        panel.appendChild(lista);
        wrap.appendChild(display);
        wrap.appendChild(panel);

        select.insertAdjacentElement('afterend', wrap);
        select.style.display = 'none';

        // ---- Estado ----
        var filtrados = [];
        var activo = -1;

        function opciones() {
            return Array.prototype.map.call(select.options, function (o) {
                return { value: o.value, texto: o.textContent };
            });
        }

        function actualizarTexto() {
            var o = select.options[select.selectedIndex];
            texto.textContent = o ? o.textContent : '';
            display.classList.toggle('sb-placeholder', !select.value);
        }

        function resaltar(scroll) {
            var items = lista.querySelectorAll('.sb-item');
            items.forEach(function (li, i) {
                li.classList.toggle('sb-activo', i === activo);
            });
            if (scroll && items[activo]) items[activo].scrollIntoView({ block: 'nearest' });
        }

        function pintar() {
            var q = normalizar(buscar.value);
            filtrados = opciones().filter(function (o) {
                if (!q) return true;
                return o.value !== '' && normalizar(o.texto).indexOf(q) !== -1;
            });

            lista.innerHTML = '';
            if (!filtrados.length) {
                var vacio = document.createElement('li');
                vacio.className = 'sb-vacio';
                vacio.textContent = 'Sin resultados';
                lista.appendChild(vacio);
                activo = -1;
                return;
            }

            filtrados.forEach(function (o, i) {
                var li = document.createElement('li');
                li.className = 'sb-item' + (o.value === select.value ? ' sb-selected' : '') + (o.value === '' ? ' sb-limpiar' : '');
                li.setAttribute('role', 'option');
                li.setAttribute('data-index', i);
                li.textContent = o.texto;
                lista.appendChild(li);
            });

            // Con texto escrito, el primer resultado queda listo para Enter
            if (q) {
                activo = 0;
            } else {
                activo = filtrados.findIndex(function (o) { return o.value === select.value && o.value !== ''; });
            }
            resaltar(false);
        }

        function abrir() {
            panel.hidden = false;
            display.setAttribute('aria-expanded', 'true');
            buscar.value = '';
            pintar();
            resaltar(true);
            buscar.focus();
        }

        function cerrar(devolverFoco) {
            panel.hidden = true;
            display.setAttribute('aria-expanded', 'false');
            if (devolverFoco) display.focus();
        }

        function elegir(valor) {
            if (select.value !== valor) {
                select.value = valor;
                select.dispatchEvent(new Event('change', { bubbles: true }));
            }
            actualizarTexto();
            cerrar(true);
        }

        // ---- Eventos ----
        display.addEventListener('click', function () {
            if (panel.hidden) abrir(); else cerrar(false);
        });

        buscar.addEventListener('input', pintar);

        buscar.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (filtrados.length) { activo = Math.min(filtrados.length - 1, activo + 1); resaltar(true); }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (filtrados.length) { activo = Math.max(0, activo - 1); resaltar(true); }
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (activo >= 0 && filtrados[activo]) elegir(filtrados[activo].value);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                cerrar(true);
            } else if (e.key === 'Tab') {
                cerrar(false);
            }
        });

        lista.addEventListener('click', function (e) {
            var li = e.target.closest('.sb-item');
            if (!li) return;
            var o = filtrados[parseInt(li.getAttribute('data-index'), 10)];
            if (o) elegir(o.value);
        });

        document.addEventListener('mousedown', function (e) {
            if (!panel.hidden && !wrap.contains(e.target)) cerrar(false);
        });

        // Mantener sincronizado si otro codigo cambia el select
        select.addEventListener('change', actualizarTexto);
        new MutationObserver(function () {
            actualizarTexto();
            if (!panel.hidden) pintar();
        }).observe(select, { childList: true });

        if (select.form) {
            select.form.addEventListener('reset', function () { setTimeout(actualizarTexto, 0); });
        }

        actualizarTexto();
    }

    window.SelectBuscable = { crear: crear };

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('select[data-buscable]').forEach(function (s) {
            crear(s, s.getAttribute('data-buscable'));
        });
    });
})();