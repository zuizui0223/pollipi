const cameras = {
  module3: {
    id: "module3",
    label: "Module 3 Wide",
    baseUrl: "http://zuizui.local:8000",
  },
  ai: {
    id: "ai",
    label: "AI Camera",
    baseUrl: "http://zuizui2.local:8000",
  },
};

const intervalInput = document.querySelector("#interval-input");
const syncLabel = document.querySelector("#sync-label");
const refreshButton = document.querySelector("#refresh-button");
const startAllButton = document.querySelector("#start-all");
const stopAllButton = document.querySelector("#stop-all");
const galleryGrid = document.querySelector("#gallery-grid");
const galleryCameraLabel = document.querySelector("#gallery-camera-label");
const galleryCount = document.querySelector("#gallery-count");
const gallerySize = document.querySelector("#gallery-size");
const galleryFolderPath = document.querySelector("#gallery-folder-path");
const deleteAllImagesButton = document.querySelector("#delete-all-images");
let selectedGalleryCamera = cameras.module3;

for (const camera of Object.values(cameras)) {
  camera.card = document.querySelector(`[data-camera="${camera.id}"]`);
  camera.previousImage = null;
  camera.live = false;
  camera.liveTimer = null;
  camera.card.querySelector(".start-camera").addEventListener("click", () => startCamera(camera));
  camera.card.querySelector(".stop-camera").addEventListener("click", () => stopCamera(camera));
  camera.card.querySelector(".live-camera").addEventListener("click", () => toggleLive(camera));
}

for (const button of document.querySelectorAll(".gallery-tab")) {
  button.addEventListener("click", () => {
    document.querySelector(".gallery-tab.selected").classList.remove("selected");
    button.classList.add("selected");
    selectedGalleryCamera = cameras[button.dataset.galleryCamera];
    refreshGallery();
  });
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
  camera.status = status;
  const pill = field(camera, "pill");
  pill.textContent = status.running ? "撮影中" : "停止中";
  pill.className = `pill ${status.running ? "running" : "stopped"}`;
  field(camera, "count").textContent = String(status.capture_count);
  field(camera, "interval").textContent = status.interval_sec ? `${status.interval_sec} 秒` : "-";
  field(camera, "time").textContent = formatCaptureTime(status.last_capture_time);
  field(camera, "message").textContent = status.message;

  if (!status.running && camera.live) {
    setLive(camera, false);
  }

  if (!camera.live && status.last_image && status.last_image !== camera.previousImage) {
    const image = field(camera, "image");
    image.onload = () => {
      image.classList.add("ready");
      field(camera, "empty").hidden = true;
    };
    image.src = `${camera.baseUrl}/latest?capture=${encodeURIComponent(status.last_capture_time)}`;
    camera.previousImage = status.last_image;
  } else if (!status.last_image) {
    const image = field(camera, "image");
    image.classList.remove("ready");
    image.removeAttribute("src");
    field(camera, "empty").hidden = false;
    camera.previousImage = null;
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
  await refreshGallery();
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

function setLive(camera, enabled) {
  const button = camera.card.querySelector(".live-camera");
  const image = field(camera, "image");
  camera.live = enabled;
  window.clearInterval(camera.liveTimer);
  camera.liveTimer = null;
  button.textContent = enabled ? "ライブ停止" : "ライブ確認";
  button.classList.toggle("live-active", enabled);
  if (!enabled) {
    camera.previousImage = null;
    refreshCamera(camera);
    return;
  }
  const reloadPreview = () => {
    image.onload = () => {
      image.classList.add("ready");
      field(camera, "empty").hidden = true;
    };
    image.src = `${camera.baseUrl}/preview?t=${Date.now()}`;
  };
  reloadPreview();
  camera.liveTimer = window.setInterval(reloadPreview, 1500);
}

function toggleLive(camera) {
  if (camera.live) {
    setLive(camera, false);
    return;
  }
  if (!camera.status || !camera.status.running) {
    window.alert("ライブ確認は撮影開始後に利用できます。先に撮影を開始してください。");
    return;
  }
  setLive(camera, true);
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

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function refreshGallery() {
  const camera = selectedGalleryCamera;
  galleryCameraLabel.textContent = camera.label;
  try {
    const response = await apiRequest(camera, "/images?limit=40");
    galleryCount.textContent = `${response.image_count} 枚`;
    gallerySize.textContent = formatBytes(response.total_size_bytes);
    galleryFolderPath.textContent = response.image_dir;
    galleryGrid.replaceChildren();
    if (response.images.length === 0) {
      const empty = document.createElement("p");
      empty.className = "gallery-empty";
      empty.textContent = "保存された画像はありません。";
      galleryGrid.append(empty);
      return;
    }
    for (const imageInfo of response.images) {
      galleryGrid.append(buildGalleryItem(camera, imageInfo));
    }
  } catch (error) {
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
    if (!window.confirm(`${camera.label} のこの写真を削除しますか？\n${imageInfo.filename}\n\nこの操作は元に戻せません。`)) {
      return;
    }
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
  if (camera.status && camera.status.running) {
    window.alert("全削除の前に、このカメラの撮影を停止してください。");
    return;
  }
  if (!window.confirm(`${camera.label} の保存画像をすべて削除しますか？\n\nこの操作は元に戻せません。`)) {
    return;
  }
  const confirmation = window.prompt("全削除するには DELETE_ALL と入力してください。");
  if (confirmation !== "DELETE_ALL") {
    window.alert("全削除をキャンセルしました。");
    return;
  }
  deleteAllImagesButton.disabled = true;
  try {
    const result = await apiRequest(camera, "/images", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm: confirmation }),
    });
    camera.previousImage = null;
    window.alert(`${result.deleted_count} 枚を削除しました。`);
    await Promise.all([refreshCamera(camera), refreshGallery()]);
  } catch (error) {
    window.alert(`全削除できませんでした: ${error.message}`);
  } finally {
    deleteAllImagesButton.disabled = false;
  }
}

refreshButton.addEventListener("click", refreshAll);
startAllButton.addEventListener("click", startAll);
stopAllButton.addEventListener("click", stopAll);
deleteAllImagesButton.addEventListener("click", deleteAllImages);

refreshAll();
window.setInterval(refreshAll, 4000);
