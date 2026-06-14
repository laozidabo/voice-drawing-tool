/* ── 语音绘图工具 — 纯语音 Web UI ───────────────── */

const $ = (sel) => document.querySelector(sel);

// ── Socket.IO ──────────────────────────────────────────
const socket = io({ transports: ["websocket", "polling"] });

socket.on("connect", () => {
  $("#status-badge").textContent = "● 已连接";
  $("#status-badge").classList.remove("offline");
  refreshCanvas();
});

socket.on("disconnect", () => {
  $("#status-badge").textContent = "● 断开";
  $("#status-badge").classList.add("offline");
  setVoiceLabel("连接断开", true);
});

socket.on("canvas_update", (data) => {
  $("#canvas-img").src = "data:image/png;base64," + data.image;
});

socket.on("state_update", (state) => {
  $("#cmd-count").textContent = state.cmd_count;
  const mm = String(Math.floor(state.session_duration / 60)).padStart(2, "0");
  const ss = String(state.session_duration % 60).padStart(2, "0");
  $("#duration").textContent = `${mm}:${ss}`;
  if (state.feedback) showToast(state.feedback, !state.feedback.startsWith("⚠"));
});

socket.on("command_result", (result) => {
  showToast(result.feedback, result.ok);
  refreshCanvas();
  // 语音播报结果
  speakResult(result);
});

socket.on("speech", (data) => {
  showToast("🎤 " + data.text, true);
});

// ── Helpers ────────────────────────────────────────────
function refreshCanvas() {
  $("#canvas-img").src = "/api/preview?t=" + Date.now();
}

let toastTimer;
function showToast(msg, ok) {
  const toast = $("#feedback-toast");
  toast.textContent = msg;
  toast.className = "toast " + (ok ? "success" : "error");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add("hidden"), 3500);
}

function setVoiceLabel(text, isError) {
  const indicator = $("#voice-indicator");
  const label = $("#voice-label");
  label.textContent = text;
  indicator.classList.toggle("error", !!isError);
}

// ── 语音播报（Web Speech Synthesis）──────────────────
function speakResult(result) {
  if (!result.ok) return;
  if (!window.speechSynthesis) return;
  const text = result.description || result.feedback || "";
  // 取简短摘要
  let summary = text.replace(/draw /, "").replace(/at \(\d+,\d+\)/, "").trim();
  if (summary.length > 20) summary = summary.slice(0, 20);
  if (!summary) return;
  try {
    const utter = new SpeechSynthesisUtterance(summary);
    utter.lang = "zh-CN";
    utter.rate = 1.2;
    utter.volume = 0.6;
    speechSynthesis.cancel();
    speechSynthesis.speak(utter);
  } catch (e) {}
}

// ── Web Speech API（纯语音识别）───────────────────────
let recognition = null;
let isListening = false;

function sendVoiceCommand(text) {
  fetch("/api/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  })
    .then((r) => r.json())
    .then((data) => {
      showToast(data.feedback, data.ok);
      refreshCanvas();
      speakResult(data);
    })
    .catch(() => showToast("⚠ 网络错误", false));
}

function startVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    setVoiceLabel("浏览器不支持语音（请用 Chrome/Edge）", true);
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = "zh-CN";
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.maxAlternatives = 3;

  recognition.onstart = () => {
    isListening = true;
    setVoiceLabel("正在聆听…", false);
  };

  recognition.onend = () => {
    isListening = false;
    // 自动重启保持连续聆听
    if (recognition._active) {
      try { recognition.start(); } catch (e) {}
    } else {
      setVoiceLabel("语音已暂停", true);
    }
  };

  recognition.onresult = (event) => {
    const last = event.results[event.results.length - 1];
    if (!last.isFinal) return;
    for (let i = 0; i < last.length; i++) {
      const text = last[i].transcript.trim();
      if (text && text.length >= 1) {
        setVoiceLabel("🎤 " + text, false);
        sendVoiceCommand(text);
        break;
      }
    }
  };

  recognition.onerror = (event) => {
    if (event.error === "no-speech") return;
    if (event.error === "aborted") return;
    if (event.error === "not-allowed") {
      setVoiceLabel("请允许麦克风权限", true);
      return;
    }
    console.warn("Speech error:", event.error);
  };

  recognition._active = true;
  try {
    recognition.start();
  } catch (e) {
    setVoiceLabel("语音启动失败", true);
  }
}

// ── 初始化 ────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // 点击启动按钮开始语音识别
  const startBtn = $("#start-mic");
  if (startBtn) {
    startBtn.addEventListener("click", () => {
      $("#welcome-overlay").classList.add("hidden");
      startVoice();
    });
  }

  // 获取初始状态
  fetch("/api/state")
    .then((r) => r.json())
    .then((s) => {
      $("#cmd-count").textContent = s.cmd_count;
    })
    .catch(() => {});
});
