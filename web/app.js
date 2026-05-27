const STORAGE_KEY = "pollipi.observationDevices.v1";

const intervalInput = document.querySelector("#interval-input");
const autoModeInput = document.querySelector("#auto-mode");
const autonomousModeInput = document.querySelector("#autonomous-mode");
const autoSettings = document.querySelector("#auto-settings");
const idleIntervalInput = document.querySelector("#idle-interval");
const detectionIntervalInput = document.querySelector("#detection-interval");
const syncLabel = document.querySelector("#sync-label");
const refreshButton = document.querySelector("#refresh-button");
const startAllButton = document.querySelector("#start-all");
const stopAllButton = document.querySelector("#stop-all");
const cameraGrid = document.querySelector("#camera-grid");
const cameraEmpty = document.querySelector("#camera-empty");
const cameraTemplate = document.querySelector("#camera-template");
const deviceForm = document.querySelector("#device-form");
const deviceAddressInput = document.querySelector("#device-address");
const gallerySwitch = document.querySelector("#gallery-switch");
const galleryGrid = document.querySelector("#gallery-grid");
const galleryCameraLabel = document.querySelector("#gallery-camera-label");
const galleryCount = document.querySelector("#gallery-count");
const gallerySize = document.querySelector("#gallery-size");
const galleryFolderPath = document.querySelector("#gallery-folder-path");
const deleteAllImagesButton = document.querySelector("#delete-all-images");

let cameras = loadCameras();
let selectedGalleryCamera = null;

function loadCameras() {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
  } catch (_) {
    return [];
  }
}

function saveCameras() {
  const persistent = cameras.map(({ address, baseUrl, device_id, device_name, camera_label, camera_model }) => ({
    address,
    baseUrl,
    device_id,
    device_name,
    camera_label,
    camera_model,
  }));
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(persistent));
}

function resolveBaseUrl(value) {
  let input = value.trim();
  if (/^https?:\/\//i.test(input)) {
    const url = new URL(input);
    url.pathname = "";
    url.search = "";
    url.hash = "";
    return url.origin;
  }
  const hostname = input.includes("@") ? input.split("@").pop() : input;
  if (!hostname || /[/?#]/.test(hostname)) throw new Error("Invalid device name");
  const localHostname = hostname.includes(".") ? hostname : `${hostname}.local`;
  return `http://${localHostname}:8000`;
}

function field(camera, name) {
  return camera.card.querySelector(`[data-field="${name}"]`);
}

async function registerCamera(rawAddress, quiet = false) {
  let baseUrl;
  try {
    baseUrl = resolveBaseUrl(rawAddress);
  } catch (_) {
    if (!quiet) window.alert("観察機名を確認してください。例: zuizui0223@zuizui2");
    return null;
  }
  try {
    const response = await fetch(`${baseUrl}/device`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const device = await response.json();
    const camera = { ...device, address: rawAddress.trim(), baseUrl };
    const existing = cameras.findIndex((item) => item.baseUrl === baseUrl || item.device_id === camera.device_id);
    if (existing >= 0) cameras[existing] = camera;
    else cameras.push(camera);
    saveCameras();
    renderCameras();
    await refreshAll();
    return camera;
  } catch (error) {
    if (!quiet) window.alert(`観察機に接続できません: ${error.message}`);
    return null;
  }
}

function buildCameraCard(camera, index) {
  const card = cameraTemplate.content.firstElementChild.cloneNode(true);
  camera.card = card;
  camera.previousImage = null;
  camera.manualPreview = false;
  camera.monitoring = false;
  field(camera, "device").textContent = `OBSERVATION UNIT ${index + 1} / ${camera.device_name}`;
  field(camera, "label").textContent = camera.camera_label;
  field(camera, "sensor").textContent = `${camera.camera_model} / ${camera.baseUrl}`;
  card.querySelector(".start-camera").addEventListener("click", () => startCamera(camera));
  card.querySelector(".stop-camera").addEventListener("click", () => stopCamera(camera));
  card.querySelector(".monitor-camera").addEventListener("click", () => toggleMonitor(camera));
  card.querySelector(".remove-camera").addEventListener("click", () => removeCamera(camera));
  return card;
}

function renderCameras() {
  cameraGrid.replaceChildren();
  cameraEmpty.hidden = cameras.length !== 0;
  if (cameras.length === 0) {
    cameraGrid.append(cameraEmpty);
  } else {
    cameras.forEach((camera, index) => cameraGrid.append(buildCameraCard(camera, index)));
  }
  gallerySwitch.replaceChildren();
  cameras.forEach((camera) => {
    const button = document.createElement("button");
    button.className = `gallery-tab${selectedGalleryCamera && selectedGalleryCamera.baseUrl === camera.baseUrl ? " selected" : ""}`;
    button.type = "button";
    button.textContent = camera.camera_label;
    button.addEventListener("click", () => {
      selectedGalleryCamera = camera;
      renderGallerySelection();
      refreshGallery();
    });
    gallerySwitch.append(button);
  });
  if (!selectedGalleryCamera || !cameras.some((camera) => camera.baseUrl === selectedGalleryCamera.baseUrl)) {
    selectedGalleryCamera = cameras[0] || null;
    renderGallerySelection();
  }
}

function renderGallerySelection() {
  for (const button of gallerySwitch.querySelectorAll(".gallery-tab")) {
    button.classList.toggle("selected", selectedGalleryCamera && button.textContent === selectedGalleryCamera.camera_label);
  }
}

function removeCamera(camera) {
  if (!window.confirm(`${camera.camera_label} の登録をこの iPad から削除しますか？\n撮影画像は Raspberry Pi に残ります。`)) return;
  cameras = cameras.filter((item) => item.baseUrl !== camera.baseUrl);
  if (selectedGalleryCamera && selectedGalleryCamera.baseUrl === camera.baseUrl) selectedGalleryCamera = null;
  saveCameras();
  renderCameras();
  refreshGallery();
}

function getInterval() {
  const interval = Number(intervalInput.value);
  if (!Number.isFinite(interval) || interval < 1 || interval > 3600) {
    window.alert("撮影間隔は 1 秒以上 3600 秒以下で入力してください。");
    return null;
  }
  return interval;
}

function getAutomaticSettings() {
  const idle = Number(idleIntervalInput.value);
  const detection = Number(detectionIntervalInput.value);
  if (autoModeInput.checked && (
    !Number.isFinite(idle) || idle < 1 || idle > 3600 ||
    !Number.isFinite(detection) || detection < 1 || detection > 3600
  )) {
    window.alert("自動間隔は 1 秒以上 3600 秒以下で入力してください。");
    return null;
  }
  return {
    auto_mode: autoModeInput.checked,
    autonomous_mode: autonomousModeInput.checked,
    idle_interval_sec: idle,
    detection_interval_sec: detection,
  };
}

function setBusy(camera, busy) {
  camera.card.querySelector(".start-camera").disabled = busy;
  camera.card.querySelector(".stop-camera").disabled = busy;
}

function formatCaptureTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ja-JP", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).format(new Date(value));
}

function updateCard(camera, status) {
  camera.status = status;
  const pill = field(camera, "pill");
  pill.textContent = status.running ? "撮影中" : "停止中";
  pill.className = `pill ${status.running ? "running" : "stopped"}`;
  field(camera, "count").textContent = String(status.capture_count);
  field(camera, "interval").textContent = status.interval_sec ? `${status.interval_sec} 秒` : "-";
  field(camera, "time").textContent = formatCaptureTime(status.last_capture_time);
  if (status.auto_mode) {
    const score = status.motion_score === null ? "基準作成中" : `${(status.motion_score * 100).toFixed(2)}%`;
    field(camera, "detection").textContent = status.insect_candidate ? `候補あり ${score}` : score;
  } else {
    field(camera, "detection").textContent = "OFF";
  }
  const autonomous = status.autonomous_mode && status.running ? " / 自律運行" : "";
  const message = status.auto_mode && status.interval_reason ? status.interval_reason : status.message;
  field(camera, "message").textContent = `${message}${autonomous}`;
  if (!camera.monitoring && status.last_image && status.last_image !== camera.previousImage) {
    const image = field(camera, "image");
    image.onload = () => {
      image.classList.add("ready");
      field(camera, "empty").hidden = true;
    };
    image.src = `${camera.baseUrl}/latest?capture=${encodeURIComponent(status.last_capture_time)}`;
    camera.previousImage = status.last_image;
    camera.manualPreview = false;
  } else if (!status.last_image && !camera.manualPreview) {
    const image = field(camera, "image");
    image.classList.remove("ready");
    image.removeAttribute("src");
    field(camera, "empty").hidden = false;
    camera.previousImage = null;
  }
}

function setOffline(camera, error) {
  setMonitor(camera, false);
  const pill = field(camera, "pill");
  pill.textContent = "接続なし";
  pill.className = "pill offline";
  field(camera, "message").textContent = `接続できません: ${error.message}`;
}

async function apiRequest(camera, path, options = {}) {
  const response = await fetch(`${camera.baseUrl}${path}`, options);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function refreshCamera(camera) {
  try {
    updateCard(camera, await apiRequest(camera, "/status"));
  } catch (error) {
    setOffline(camera, error);
  }
}

async function refreshAll() {
  refreshButton.disabled = true;
  await Promise.all(cameras.map(refreshCamera));
  syncLabel.textContent = `最終更新 ${new Intl.DateTimeFormat("ja-JP", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).format(new Date())}`;
  refreshButton.disabled = false;
  await refreshGallery();
}

async function startCamera(camera) {
  const interval = getInterval();
  const automaticSettings = getAutomaticSettings();
  if (interval === null || automaticSettings === null) return;
  setMonitor(camera, false);
  setBusy(camera, true);
  try {
    const status = await apiRequest(camera, "/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interval_sec: interval, ...automaticSettings }),
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
  setMonitor(camera, false);
  setBusy(camera, true);
  try {
    updateCard(camera, await apiRequest(camera, "/stop", { method: "POST" }));
  } catch (error) {
    setOffline(camera, error);
  } finally {
    setBusy(camera, false);
  }
}

function setMonitor(camera, monitoring) {
  const button = camera.card.querySelector(".monitor-camera");
  const image = field(camera, "image");
  camera.monitoring = monitoring;
  button.classList.toggle("active", monitoring);
  button.textContent = monitoring ? "モニター停止" : "画角モニター";
  if (!monitoring) {
    if (camera.status && camera.status.last_image) {
      image.src = `${camera.baseUrl}/latest?capture=${encodeURIComponent(camera.status.last_capture_time)}`;
    } else {
      image.classList.remove("ready");
      image.removeAttribute("src");
      field(camera, "empty").hidden = false;
    }
  }
}

function toggleMonitor(camera) {
  if (camera.monitoring) {
    setMonitor(camera, false);
    field(camera, "message").textContent = "画角モニターを停止しました。";
    return;
  }
  const image = field(camera, "image");
  image.onload = () => {
    image.classList.add("ready");
    field(camera, "empty").hidden = true;
  };
  image.onerror = () => {
    setMonitor(camera, false);
    setOffline(camera, new Error("画面を取得できません"));
  };
  setMonitor(camera, true);
  image.src = `${camera.baseUrl}/mjpeg?t=${Date.now()}`;
  camera.manualPreview = true;
  field(camera, "message").textContent = "画角を低負荷モニター表示しています（保存されません）。";
}

async function startAll() {
  if (getInterval() === null || getAutomaticSettings() === null) return;
  startAllButton.disabled = true;
  await Promise.all(cameras.map(startCamera));
  startAllButton.disabled = false;
}

async function stopAll() {
  stopAllButton.disabled = true;
  await Promise.all(cameras.map(stopCamera));
  stopAllButton.disabled = false;
}

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function refreshGallery() {
  const camera = selectedGalleryCamera;
  renderGallerySelection();
  if (!camera) {
    galleryCameraLabel.textContent = "観察機未選択";
    galleryCount.textContent = "-";
    gallerySize.textContent = "";
    galleryFolderPath.textContent = "観察機を追加すると保存画像を表示できます。";
    galleryGrid.innerHTML = `<p class="gallery-empty">観察機が登録されていません。</p>`;
    return;
  }
  galleryCameraLabel.textContent = camera.camera_label;
  try {
    const response = await apiRequest(camera, "/images?limit=40");
    camera.imageCount = response.image_count;
    galleryCount.textContent = `${response.image_count} 枚`;
    gallerySize.textContent = formatBytes(response.total_size_bytes);
    galleryFolderPath.textContent = response.image_dir;
    galleryGrid.replaceChildren();
    if (response.images.length === 0) {
      galleryGrid.innerHTML = `<p class="gallery-empty">保存された画像はありません。</p>`;
      return;
    }
    response.images.forEach((imageInfo) => galleryGrid.append(buildGalleryItem(camera, imageInfo)));
  } catch (error) {
    camera.imageCount = null;
    galleryCount.textContent = "接続できません";
    gallerySize.textContent = "";
    galleryFolderPath.textContent = "-";
    galleryGrid.innerHTML = `<p class="gallery-empty">画像一覧を取得できません: ${error.message}</p>`;
  }
}

function buildGalleryItem(camera, imageInfo) {
  const item = document.createElement("article");
  item.className = "gallery-item";
  const image = document.createElement("img");
  image.src = `${camera.baseUrl}${imageInfo.url}`;
  image.alt = imageInfo.filename;
  image.loading = "lazy";
  const detail = document.createElement("div");
  detail.className = "gallery-detail";
  const timestamp = document.createElement("span");
  timestamp.textContent = formatCaptureTime(imageInfo.captured_at);
  const size = document.createElement("span");
  size.textContent = formatBytes(imageInfo.size_bytes);
  detail.append(timestamp, size);
  const deleteButton = document.createElement("button");
  deleteButton.className = "delete-image";
  deleteButton.type = "button";
  deleteButton.textContent = "削除";
  deleteButton.addEventListener("click", async () => {
    if (!window.confirm(`${camera.camera_label} のこの写真を削除しますか？\n${imageInfo.filename}\n\nこの操作は元に戻せません。`)) return;
    deleteButton.disabled = true;
    try {
      await apiRequest(camera, `/images/${encodeURIComponent(imageInfo.filename)}`, { method: "DELETE" });
      camera.previousImage = null;
      await Promise.all([refreshCamera(camera), refreshGallery()]);
    } catch (error) {
      window.alert(`削除できませんでした: ${error.message}`);
      deleteButton.disabled = false;
    }
  });
  item.append(image, detail, deleteButton);
  return item;
}

async function deleteAllImages() {
  const camera = selectedGalleryCamera;
  if (!camera) return;
  if (camera.status && camera.status.running) {
    window.alert("全削除の前に、この観察機の撮影を停止してください。");
    return;
  }
  const count = Number.isFinite(camera.imageCount) ? `${camera.imageCount} 枚の` : "";
  if (!window.confirm(`${camera.camera_label} の${count}保存画像をすべて削除しますか？\n\n削除後は元に戻せません。`)) return;
  deleteAllImagesButton.disabled = true;
  deleteAllImagesButton.textContent = "削除中...";
  try {
    const result = await apiRequest(camera, "/images", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm: "DELETE_ALL" }),
    });
    camera.previousImage = null;
    window.alert(`${result.deleted_count} 枚を削除しました。`);
    await Promise.all([refreshCamera(camera), refreshGallery()]);
  } catch (error) {
    window.alert(`全削除できませんでした: ${error.message}`);
  } finally {
    deleteAllImagesButton.disabled = false;
    deleteAllImagesButton.textContent = "この観察機の写真を全削除";
  }
}

deviceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const camera = await registerCamera(deviceAddressInput.value);
  if (camera) deviceAddressInput.value = "";
});
refreshButton.addEventListener("click", refreshAll);
autoModeInput.addEventListener("change", () => {
  autoSettings.hidden = !autoModeInput.checked;
});
startAllButton.addEventListener("click", startAll);
stopAllButton.addEventListener("click", stopAll);
deleteAllImagesButton.addEventListener("click", deleteAllImages);

async function initialize() {
  renderCameras();
  if (cameras.length === 0 && /^https?:$/.test(window.location.protocol)) {
    await registerCamera(window.location.origin, true);
  }
  await refreshAll();
}

initialize();
window.setInterval(refreshAll, 4000);
