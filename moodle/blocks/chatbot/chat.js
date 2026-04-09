document.addEventListener('DOMContentLoaded', function() {
    var widget = document.getElementById('chatbot-widget');
    if (!widget) {
        return;
    }

    var backendUrl  = widget.getAttribute('data-backend-url');
    var apiToken    = widget.getAttribute('data-api-token');
    var userRole    = widget.getAttribute('data-role');
    var currentPage = widget.getAttribute('data-page');
    var courseId    = parseInt(widget.getAttribute('data-course-id'), 10);
    var career      = widget.getAttribute('data-career');

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

    var history  = [];
    var panelOpen = false;

    // Convierte markdown básico a HTML
    var renderMarkdown = function(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            // Headings ### ## #
            .replace(/^#{1,3} (.+)$/gm, '<strong>$1</strong>')
            // Negrita **texto** (sin cruzar saltos de línea)
            .replace(/\*\*([^*\r\n]+)\*\*/g, '<strong>$1</strong>')
            // Cursiva *texto* (sin cruzar saltos de línea)
            .replace(/\*([^*\r\n]+)\*/g, '<em>$1</em>')
            // Listas - item y • item
            .replace(/^[-•]\s+(.+)$/gm, '&bull; $1')
            // Saltos de línea
            .replace(/\n/g, '<br>');
    };

    var appendMessage = function(role, text) {
        var messages = document.getElementById('cb-messages');
        var div = document.createElement('div');
        var base = 'padding:10px 14px;border-radius:10px;font-size:14px;max-width:85%;line-height:1.5;word-wrap:break-word;';
        div.style.cssText = base + (role === 'user'
            ? 'background:#0066cc;color:white;align-self:flex-end;'
            : 'background:#f0f0f0;color:#333;align-self:flex-start;');
        div.innerHTML = renderMarkdown(text);
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    };

    // Indicador de escritura animado con JS (sin CSS keyframes)
    var typingTimer  = null;
    var typingFrames = ['Escribiendo .', 'Escribiendo ..', 'Escribiendo ...'];
    var typingIndex  = 0;

    var showTyping = function() {
        var messages = document.getElementById('cb-messages');
        var div = document.createElement('div');
        div.id = 'cb-typing';
        div.style.cssText = 'padding:10px 14px;border-radius:10px;font-size:14px;' +
            'max-width:85%;background:#f0f0f0;color:#888;align-self:flex-start;font-style:italic;';
        div.textContent = typingFrames[0];
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
        typingIndex = 0;
        typingTimer = setInterval(function() {
            typingIndex = (typingIndex + 1) % typingFrames.length;
            var el = document.getElementById('cb-typing');
            if (el) { el.textContent = typingFrames[typingIndex]; }
        }, 400);
    };

    var hideTyping = function() {
        clearInterval(typingTimer);
        var el = document.getElementById('cb-typing');
        if (el) { el.remove(); }
    };

    document.getElementById('cb-toggle').addEventListener('click', function() {
        panelOpen = !panelOpen;
        document.getElementById('cb-panel').style.display = panelOpen ? 'flex' : 'none';
    });

    var sendMessage = function() {
        var input   = document.getElementById('cb-input');
        var message = input.value.trim();
        if (!message) { return; }
        input.value = '';

        appendMessage('user', message);
        showTyping();

        document.getElementById('cb-input').disabled = true;
        document.getElementById('cb-send').disabled  = true;

        fetch(backendUrl + '/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Token': apiToken
            },
            body: JSON.stringify({
                message:   message,
                history:   history,
                user_role: userRole,
                context:   currentPage,
                course_id: courseId,
                career:    career
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            hideTyping();
            appendMessage('assistant', data.reply);
            history.push({role: 'user',      content: message});
            history.push({role: 'assistant', content: data.reply});
            if (history.length > 20) { history = history.slice(-20); }
        })
        .catch(function() {
            hideTyping();
            appendMessage('assistant', 'Ocurrió un error. Por favor intenta de nuevo.');
        })
        .finally(function() {
            document.getElementById('cb-input').disabled = false;
            document.getElementById('cb-send').disabled  = false;
            document.getElementById('cb-input').focus();
        });
    };

    document.getElementById('cb-send').addEventListener('click', sendMessage);
    document.getElementById('cb-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') { sendMessage(); }
    });
});
