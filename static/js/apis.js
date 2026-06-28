/**
 * Consumo de APIs externas e internas (misma lógica que la entrega estática).
 */
(function () {
    'use strict';

    function esc(text) {
        var d = document.createElement('div');
        d.textContent = text == null ? '' : String(text);
        return d.innerHTML;
    }

    function getCsrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    // API interna: plantillas de tareas (/api/plantillas)
    var suggestionsEl = document.getElementById('suggestions');
    var boardEl = document.getElementById('board');
    if (suggestionsEl && boardEl && !suggestionsEl.querySelector('.suggestion-btn')) {
        var columnId = boardEl.getAttribute('data-first-column-id');
        if (!columnId) return;

        fetch('/api/plantillas/')
            .then(function (r) { return r.json(); })
            .then(function (templates) {
                if (!templates.length) return;
                var boardId = boardEl.getAttribute('data-board-id');
                var csrf = getCsrfToken();
                suggestionsEl.innerHTML = '<span class="board-suggestions__label">Sugerencias:</span>'
                    + templates.map(function (t) {
                        return '<form method="post" action="/board/' + esc(boardId)
                            + '/card/create/" class="suggestion-import-form">'
                            + '<input type="hidden" name="csrfmiddlewaretoken" value="' + esc(csrf) + '">'
                            + '<input type="hidden" name="column" value="' + esc(columnId) + '">'
                            + '<input type="hidden" name="title" value="' + esc(t.titulo) + '">'
                            + '<input type="hidden" name="description" value="' + esc(t.descripcion) + '">'
                            + '<input type="hidden" name="priority" value="' + esc(t.prioridad) + '">'
                            + '<button type="submit" class="suggestion-btn">' + esc(t.titulo) + '</button>'
                            + '</form>';
                    }).join('');
            })
            .catch(function () {});
    }
})();
