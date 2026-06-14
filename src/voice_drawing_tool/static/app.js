/* ── Voice Drawing Tool — Web UI ────────────────────────────── */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── Socket.IO ──────────────────────────────────────────────
const socket = io({ transports: ["websocket", "polling"] });

socket.on("connect", () => {
  $("#status-badge").textContent = "● 已连接";
  $("#status-badge").classList.remove("offline");
  refreshCanvas();
});

socket.on("disconnect", () => {
  $("#status-badge").textContent = "● 断开";
  $("#status-badge").classList.add("offline");
});

socket.on("canvas_update", (data) => {
  const img = $("#canvas-img");
  img.src = "data:image/png;base64," + data.image;
});

socket.on("state_update", (state) => {
  updateStateUI(state);
});

socket.on("command_result", (result) => {
  showToast(result.feedback, result.ok);
  if (result.ok) refreshCanvas();
});

socket.on("speech", (data) => {
  showToast("🎤 " + data.text, true);
});

// ── State ──────────────────────────────────────────────────
let currentColor = "red";
let cmdHistory = [];

function updateStateUI(s) {
  $("#cursor-pos").textContent = `(${s.cursor_x},${s.cursor_y})`;
  $("#shape-count").textContent = s.shape_count;
  $("#cmd-count").textContent = s.cmd_count;
  const mm = String(Math.floor(s.session_duration / 60)).padStart(2, "0");
  const ss = String(s.session_duration % 60).padStart(2, "0");
  $("#duration").textContent = `${mm}:${ss}`;
  if (s.pen_color) {
    currentColor = s.pen_color;
    $$(".color-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.color === currentColor);
    });
  }
  if (s.pen_width) {
    $("#width-slider").value = s.pen_width;
    $("#width-display").textContent = s.pen_width;
  }
}

// ── API helpers ────────────────────────────────────────────
async function sendCommand(text) {
  try {
    const res = await fetch("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    addHistory(text, data.ok);
    showToast(data.feedback, data.ok);
    refreshCanvas();
    return data;
  } catch (e) {
    showToast("⚠ 网络错误", false);
  }
}

async function postAction(action) {
  try {
    const res = await fetch(`/api/${action}`, { method: "POST" });
    const data = await res.json();
    showToast(data.feedback, data.ok);
    refreshCanvas();
  } catch (e) {
    showToast("⚠ 网络错误", false);
  }
}

function refreshCanvas() {
  const img = $("#canvas-img");
  img.src = "/api/preview?t=" + Date.now();
}

// ── UI Updates ─────────────────────────────────────────────
function showToast(msg, ok) {
  const toast = $("#feedback-toast");
  toast.textContent = msg;
  toast.className = "toast " + (ok ? "success" : "error");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 3000);
}

function addHistory(text, ok) {
  cmdHistory.unshift({ text, ok });
  if (cmdHistory.length > 20) cmdHistory.pop();
  renderHistory();
}

function renderHistory() {
  const el = $("#cmd-history");
  el.innerHTML = cmdHistory
    .map(
      (h) =>
        `<div class="history-item ${h.ok ? "success" : "error"}" title="${h.text}">${h.text}</div>`
    )
    .join("");
  el.querySelectorAll(".history-item").forEach((item, i) => {
    item.addEventListener("click", () => {
      $("#cmd-input").value = cmdHistory[i].text;
      $("#cmd-input").focus();
    });
  });
}

// ── Event Bindings ─────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Command input
  const input = $("#cmd-input");
  const sendBtn = $("#cmd-send");

  function submitCmd() {
    const text = input.value.trim();
    if (text) {
      sendCommand(text);
      input.value = "";
    }
  }

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitCmd();
    }
  });
  sendBtn.addEventListener("click", submitCmd);

  // Shape buttons
  $$(".shape-btn").forEach((btn) => {
    btn.addEventListener("click", () => sendCommand(btn.dataset.cmd));
  });

  // Color buttons
  $$(".color-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      currentColor = btn.dataset.color;
      fetch("/api/set_color", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ color: currentColor }),
      });
      $$(".color-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });

  // Width slider
  const slider = $("#width-slider");
  slider.addEventListener("input", () => {
    $("#width-display").textContent = slider.value;
  });
  slider.addEventListener("change", () => {
    fetch("/api/set_width", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ width: parseInt(slider.value) }),
    });
  });

  // Action buttons (data-cmd)
  $$(".action-btn[data-cmd]").forEach((btn) => {
    btn.addEventListener("click", () => sendCommand(btn.dataset.cmd));
  });

  // Position buttons
  $$(".pos-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pos = btn.dataset.cmd;
      const shape = "画" + currentColor + "圆";
      sendCommand(shape + pos);
    });
  });

  // Special buttons
  $("#btn-undo").addEventListener("click", () => postAction("undo"));
  $("#btn-redo").addEventListener("click", () => postAction("redo"));
  $("#btn-clear").addEventListener("click", () => {
    if (confirm("确定清空画布？")) postAction("clear");
  });
  $("#btn-save").addEventListener("click", () => postAction("save"));
  $("#btn-download").addEventListener("click", () => {
    window.open("/api/download", "_blank");
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.target === input) return;
    if (e.ctrlKey || e.metaKey) {
      if (e.key === "z") {
        e.preventDefault();
        postAction("undo");
      } else if (e.key === "y") {
        e.preventDefault();
        postAction("redo");
      }
    }
  });

  // Initial state fetch
  fetch("/api/state")
    .then((r) => r.json())
    .then(updateStateUI)
    .catch(() => {});
});
