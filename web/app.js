const cameras = {
  module3: {
    id: "module3",
    baseUrl: "http://zuizui.local:8000",
  },
  ai: {
    id: "ai",
    baseUrl: "http://zuizui2.local:8000",
  },
};

const intervalInput = document.querySelector("#interval-input");
const syncLabel = document.querySelector("#sync-label");
const refreshButton = document.querySelector("#refresh-button");
const startAllButton = document.querySelector("#start-all");
const stopAllButton = document.querySelector("#stop-all");

for (const camera of Object.values(cameras)) {
  camera.card = document.querySelector(`[data-camera="${camera.id}"]`);
  camera.previousImage = null;
  camera.card.querySelector(".start-camera").addEventListener("click", () => startCamera(camera));
  camera.card.querySelector(".stop-camera").addEventListener("click", () => stopCamera(camera));
}

function field(camera, name) {
  return camera.card.querySelector(`[data-field="${name}"]`);
}

function getInterval() {
  const interval = Number(intervalInput.value);
  if (!Number.isFinite(interval) || interval < 1 || interval > 3600) {
    window.alert("撮影間隔は 1 秒以上 3600 秒以下で入力してください。");
    return null;
  }
  return interval;
}

function setBusy(camera, busy) {
  camera.card.querySelector(".start-camera").disabled = busy;
  camera.card.querySelector(".stop-camera").disabled = busy;
}

function formatCaptureTime(value) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function updateCard(camera, status) {
  const pill = field(camera, "pill");
  pill.textContent = status.running ? "撮影中" : "停止中";
  pill.className = `pill ${status.running ? "running" : "stopped"}`;
  field(camera, "count").textContent = String(status.capture_count);
  field(camera, "interval").textContent = status.interval_sec ? `${status.interval_sec} 秒` : "-";
  field(camera, "time").textContent = formatCaptureTime(status.last_capture_time);
  field(camera, "message").textContent = status.message;

  if (status.last_image && status.last_image !== camera.previousImage) {
    const image = field(camera, "image");
    image.onload = () => {
      image.classList.add("ready");
      field(camera, "empty").hidden = true;
    };
    image.src = `${camera.baseUrl}/latest?capture=${encodeURIComponent(status.last_capture_time)}`;
    camera.previousImage = status.last_image;
  }
}

function setOffline(camera, error) {
  const pill = field(camera, "pill");
  pill.textContent = "接続なし";
  pill.className = "pill offline";
  field(camera, "message").textContent = `接続できません: ${error.message}`;
}

async function apiRequest(camera, path, options = {}) {
  const response = await fetch(`${camera.baseUrl}${path}`, options);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function refreshCamera(camera) {
  try {
    const status = await apiRequest(camera, "/status");
    updateCard(camera, status);
  } catch (error) {
    setOffline(camera, error);
  }
}

async function refreshAll() {
  refreshButton.disabled = true;
  await Promise.all(Object.values(cameras).map(refreshCamera));
  syncLabel.textContent = `最終更新 ${new Intl.DateTimeFormat("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date())}`;
  refreshButton.disabled = false;
}

async function startCamera(camera) {
  const interval = getInterval();
  if (interval === null) {
    return;
  }
  setBusy(camera, true);
  try {
    const status = await apiRequest(camera, "/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interval_sec: interval }),
    });
    camera.previousImage = null;
    updateCard(camera, status);
  } catch (error) {
    setOffline(camera, error);
  } finally {
    setBusy(camera, false);
    await refreshCamera(camera);
  }
}

async function stopCamera(camera) {
  setBusy(camera, true);
  try {
    updateCard(camera, await apiRequest(camera, "/stop", { method: "POST" }));
  } catch (error) {
    setOffline(camera, error);
  } finally {
    setBusy(camera, false);
  }
}

async function startAll() {
  if (getInterval() === null) {
    return;
  }
  startAllButton.disabled = true;
  await Promise.all(Object.values(cameras).map(startCamera));
  startAllButton.disabled = false;
}

async function stopAll() {
  stopAllButton.disabled = true;
  await Promise.all(Object.values(cameras).map(stopCamera));
  stopAllButton.disabled = false;
}

refreshButton.addEventListener("click", refreshAll);
startAllButton.addEventListener("click", startAll);
stopAllButton.addEventListener("click", stopAll);

refreshAll();
window.setInterval(refreshAll, 4000);
