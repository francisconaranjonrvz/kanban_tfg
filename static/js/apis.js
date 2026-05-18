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

    // API externa: consejo aleatorio (adviceslip.com)
    var quoteEl = document.getElementById('daily-quote');
    if (quoteEl) {
        fetch('https://api.adviceslip.com/advice')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.slip && data.slip.advice) {
                    quoteEl.textContent = '\u201C' + data.slip.advice + '\u201D';
                }
            })
            .catch(function () {});
    }

    // API externa: colaboradores (randomuser.me)
    var teamEl = document.getElementById('team-members');
    if (teamEl) {
        fetch('https://randomuser.me/api/?results=3&nat=es')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.results || !data.results.length) return;
                var countEl = document.querySelector('[data-stat="member-count"]');
                if (countEl) countEl.textContent = data.results.length;
                teamEl.innerHTML = data.results.map(function (u) {
                    var name = u.name.first + ' ' + u.name.last;
                    return '<img class="team-avatar" src="' + esc(u.picture.thumbnail)
                        + '" alt="' + esc(name) + '" title="' + esc(name) + '">';
                }).join('');
            })
            .catch(function () {});
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
