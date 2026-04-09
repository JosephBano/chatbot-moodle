document.addEventListener('DOMContentLoaded', function() {
    var widget = document.getElementById('chatbot-widget');
    if (!widget) {
        return;
    }

    var backendUrl = widget.getAttribute('data-backend-url');
    var apiToken   = widget.getAttribute('data-api-token');
    var userRole   = widget.getAttribute('data-role');
    var currentPage = widget.getAttribute('data-page');
    var courseId   = parseInt(widget.getAttribute('data-course-id'), 10);
    var career     = widget.getAttribute('data-career');

    // Crear el widget flotante
    var container = document.createElement('div');
    container.innerHTML =
        '<div id="cb-toggle" style="position:fixed;bottom:24px;left:24px;z-index:9999;' +
        'width:56px;height:56px;border-radius:50%;background:#0066cc;' +
        'cursor:pointer;display:flex;align-items:center;justify-content:center;' +
        'box-shadow:0 4px 12px rgba(0,0,0,0.2);">' +
        '<span style="color:white;font-size:24px;">&#128172;</span>' +
        '</div>' +
        '<div id="cb-panel" style="display:none;position:fixed;bottom:96px;left:24px;' +
        'z-index:9999;width:360px;height:480px;background:white;border-radius:12px;' +
        'box-shadow:0 8px 24px rgba(0,0,0,0.15);flex-direction:column;">' +
        '<div style="background:#0066cc;color:white;padding:16px;border-radius:12px 12px 0 0;' +
        'font-weight:600;">Asistente Moodle</div>' +
        '<div id="cb-messages" style="flex:1;overflow-y:auto;padding:16px;' +
        'display:flex;flex-direction:column;gap:8px;"></div>' +
        '<div style="padding:12px;border-top:1px solid #eee;display:flex;gap:8px;">' +
        '<input id="cb-input" type="text" placeholder="Escribe tu pregunta..." ' +
        'style="flex:1;padding:8px 12px;border:1px solid #ddd;border-radius:8px;font-size:14px;outline:none;" />' +
        '<button id="cb-send" style="padding:8px 16px;background:#0066cc;color:white;' +
        'border:none;border-radius:8px;cursor:pointer;font-size:14px;">Enviar</button>' +
        '</div>' +
        '</div>';
    document.body.appendChild(container);

    var history = [];
    var panelOpen = false;

    var appendMessage = function(role, text) {
        var messages = document.getElementById('cb-messages');
        var div = document.createElement('div');
        var base = 'padding:10px 14px;border-radius:10px;font-size:14px;max-width:85%;line-height:1.5;';
        div.style.cssText = base + (role === 'user'
            ? 'background:#0066cc;color:white;align-self:flex-end;'
            : 'background:#f0f0f0;color:#333;align-self:flex-start;');
        div.innerHTML = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    };

    document.getElementById('cb-toggle').addEventListener('click', function() {
        panelOpen = !panelOpen;
        document.getElementById('cb-panel').style.display = panelOpen ? 'flex' : 'none';
    });

    var sendMessage = function() {
        var input = document.getElementById('cb-input');
        var message = input.value.trim();
        if (!message) {
            return;
        }
        input.value = '';
        appendMessage('user', message);

        // Indicador de escritura
        var messages = document.getElementById('cb-messages');
        var typing = document.createElement('div');
        typing.id = 'cb-typing';
        typing.style.cssText = 'padding:10px 14px;border-radius:10px;font-size:14px;max-width:85%;line-height:1.5;background:#f0f0f0;color:#333;align-self:flex-start;';
        typing.innerHTML = '<span style="display:inline-flex;gap:4px;align-items:center;">' +
            '<span style="width:7px;height:7px;border-radius:50%;background:#999;animation:cb-bounce 1s infinite 0s;display:inline-block;"></span>' +
            '<span style="width:7px;height:7px;border-radius:50%;background:#999;animation:cb-bounce 1s infinite 0.2s;display:inline-block;"></span>' +
            '<span style="width:7px;height:7px;border-radius:50%;background:#999;animation:cb-bounce 1s infinite 0.4s;display:inline-block;"></span>' +
            '</span>';
        if (!document.getElementById('cb-style')) {
            var style = document.createElement('style');
            style.id = 'cb-style';
            style.textContent = '@keyframes cb-bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}';
            document.head.appendChild(style);
        }
        messages.appendChild(typing);
        messages.scrollTop = messages.scrollHeight;

        // Deshabilitar input mientras espera
        document.getElementById('cb-input').disabled = true;
        document.getElementById('cb-send').disabled = true;

        fetch(backendUrl + '/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Token': apiToken
            },
            body: JSON.stringify({
                message: message,
                history: history,
                user_role: userRole,
                context: currentPage,
                course_id: courseId,
                career: career
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var t = document.getElementById('cb-typing');
            if (t) { t.remove(); }
            appendMessage('assistant', data.reply);
            history.push({role: 'user', content: message});
            history.push({role: 'assistant', content: data.reply});
            if (history.length > 20) {
                history = history.slice(-20);
            }
        })
        .catch(function() {
            var t = document.getElementById('cb-typing');
            if (t) { t.remove(); }
            appendMessage('assistant', 'Ocurri\u00f3 un error. Por favor intenta de nuevo.');
        })
        .finally(function() {
            document.getElementById('cb-input').disabled = false;
            document.getElementById('cb-send').disabled = false;
            document.getElementById('cb-input').focus();
        });
    };

    document.getElementById('cb-send').addEventListener('click', sendMessage);
    document.getElementById('cb-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
