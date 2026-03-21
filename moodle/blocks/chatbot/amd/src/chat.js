export const init = (
  backendUrl,
  apiToken,
  userRole,
  currentPage,
  courseId,
  career,
) => {
  // Crear el widget flotante
  const widget = document.createElement("div");
  widget.innerHTML = `
        <div id="cb-toggle" style="position:fixed;bottom:24px;right:24px;z-index:9999;
             width:56px;height:56px;border-radius:50%;background:#0066cc;
             cursor:pointer;display:flex;align-items:center;justify-content:center;
             box-shadow:0 4px 12px rgba(0,0,0,0.2);">
            <span style="color:white;font-size:24px;">💬</span>
        </div>
        <div id="cb-panel" style="display:none;position:fixed;bottom:96px;right:24px;
             z-index:9999;width:360px;height:480px;background:white;border-radius:12px;
             box-shadow:0 8px 24px rgba(0,0,0,0.15);display:flex;flex-direction:column;">
            <div style="background:#0066cc;color:white;padding:16px;border-radius:12px 12px 0 0;
                 font-weight:600;">Asistente Moodle</div>
            <div id="cb-messages" style="flex:1;overflow-y:auto;padding:16px;
                 display:flex;flex-direction:column;gap:8px;"></div>
            <div style="padding:12px;border-top:1px solid #eee;display:flex;gap:8px;">
                <input id="cb-input" type="text" placeholder="Escribe tu pregunta..."
                    style="flex:1;padding:8px 12px;border:1px solid #ddd;border-radius:8px;
                    font-size:14px;outline:none;" />
                <button id="cb-send" style="padding:8px 16px;background:#0066cc;color:white;
                    border:none;border-radius:8px;cursor:pointer;font-size:14px;">Enviar</button>
            </div>
        </div>
    `;
  document.body.appendChild(widget);

  let history = [];
  let panelOpen = false;

  // Toggle del panel
  document.getElementById("cb-toggle").addEventListener("click", () => {
    panelOpen = !panelOpen;
    document.getElementById("cb-panel").style.display = panelOpen
      ? "flex"
      : "none";
  });

  // Enviar mensaje
  const sendMessage = async () => {
    const input = document.getElementById("cb-input");
    const message = input.value.trim();
    if (!message) return;

    input.value = "";
    appendMessage("user", message);

    try {
      const response = await fetch(`${backendUrl}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Token": apiToken,
        },
        body: JSON.stringify({
          message,
          history,
          user_role: userRole,
          context: currentPage,
          course_id: courseId, // para control de acceso piloto
          career: career,      // para control de acceso piloto
        }),
      });

      const data = await response.json();
      appendMessage("assistant", data.reply);
      history.push({ role: "user", content: message });
      history.push({ role: "assistant", content: data.reply });

      // Mantener historial en máximo 10 turnos
      if (history.length > 20) history = history.slice(-20);
    } catch (error) {
      appendMessage(
        "assistant",
        "Ocurrió un error. Por favor intenta de nuevo.",
      );
    }
  };

  document.getElementById("cb-send").addEventListener("click", sendMessage);
  document.getElementById("cb-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  const appendMessage = (role, text) => {
    const messages = document.getElementById("cb-messages");
    const div = document.createElement("div");
    div.style.cssText = `
            padding:10px 14px;border-radius:10px;font-size:14px;max-width:85%;line-height:1.5;
            ${
              role === "user"
                ? "background:#0066cc;color:white;align-self:flex-end;"
                : "background:#f0f0f0;color:#333;align-self:flex-start;"
            }
        `;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  };
};
