const STORAGE_KEY = "pollipi.observationDevices.v2";
const MONITOR_WIDTH = 640;
const MONITOR_HEIGHT = 360;
const MIN_ROI_SIZE = 8;

const intervalInput = document.querySelector("#interval-input");
const autoModeInput = document.querySelector("#auto-mode");
const motionTriggerInput = document.querySelector("#motion-trigger-mode");
const hybridModeInput = document.querySelector("#hybrid-mode");
const autonomousModeInput = document.querySelector("#autonomous-mode");
const mlAssistModeInput = document.querySelector("#ml-assist-mode");
const autoSettings = document.querySelector("#auto-settings");
const autoSettingsHelp = document.querySelector("#auto-settings-help");
const idleIntervalInput = document.querySelector("#idle-interval");
const detectionIntervalInput = document.querySelector("#detection-interval");
const pixelDifferenceInput = document.querySelector("#pixel-difference-input");
const motionRatioInput = document.querySelector("#motion-ratio-input");
const idleSetting = document.querySelector("#idle-setting");
const detectionSettingLabel = document.querySelector("#detection-setting-label");
const siteIdInput = document.querySelector("#site-id-input");
const flowerIdInput = document.querySelector("#flower-id-input");
const plantSpeciesInput = document.querySelector("#plant-species-input");
const observerInput = document.querySelector("#observer-input");
const notesInput = document.querySelector("#notes-input");
const comparisonSessionInput = document.querySelector("#comparison-session-input");
const cameraRoleInput = document.querySelector("#camera-role-input");
const methodModeInput = document.querySelector("#method-mode-input");
const roiXInput = document.querySelector("#roi-x-input");
const roiYInput = document.querySelector("#roi-y-input");
const roiWInput = document.querySelector("#roi-w-input");
const roiHInput = document.querySelector("#roi-h-input");
const syncLabel = document.querySelector("#sync-label");
const refreshButton = document.querySelector("#refresh-button");
const startAllButton = document.querySelector("#start-all");
const stopAllButton = document.querySelector("#stop-all");
const reviewEventsButton = document.querySelector("#review-events-button");
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
const downloadZipLink = document.querySelector("#download-zip");
const allImagesTab = document.querySelector("#all-images-tab");
const positiveImagesTab = document.querySelector("#positive-images-tab");
const negativeImagesTab = document.querySelector("#negative-images-tab");
const eventCameraLabel = document.querySelector("#event-camera-label");
const eventCount = document.querySelector("#event-count");
const eventGrid = document.querySelector("#event-grid");
const downloadEventLabelsLink = document.querySelector("#download-event-labels");
const positiveCount = document.querySelector("#positive-count");
const negativeCount = document.querySelector("#negative-count");
const trainingModel = document.querySelector("#training-model");
const trainingMessage = document.querySelector("#training-message");
const trainingStartButton = document.querySelector("#training-start");
const trainingResetButton = document.querySelector("#training-reset");

let cameras = loadCameras();
let selectedGalleryCamera = null;
let selectedCollection = "all";

function loadCameras() {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
  } catch (_) {
    return [];
  }
}

function saveCameras() {
  const persistent = cameras.map((camera) => ({
    address: camera.address,
    baseUrl: camera.baseUrl,
    device_id: camera.device_id,
    device_name: camera.device_name,
    camera_label: camera.camera_label,
    camera_model: camera.camera_model,
    camera_profile: camera.camera_profile,
    is_ai_camera: camera.is_ai_camera,
    is_noir: camera.is_noir,
    is_wide: camera.is_wide,
    roi: camera.roi || null,
    angle_confirmed: Boolean(camera.angle_confirmed),
    roi_stale: Boolean(camera.roi_stale),
    roi_pending: Boolean(camera.roi_pending),
    roi_tracking: Boolean(camera.roi_tracking),
    roi_search_margin: camera.roi_search_margin || 30,
    roi_tracking_min_score: camera.roi_tracking_min_score || 0.45,
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

function optionalValue(input) {
  const value = input && input.value ? input.value.trim() : "";
  return value || undefined;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function normalizeRoi(rawRoi) {
  if (!rawRoi) return null;
  let x = Math.round(Number(rawRoi.roi_x));
  let y = Math.round(Number(rawRoi.roi_y));
  let w = Math.round(Number(rawRoi.roi_w));
  let h = Math.round(Number(rawRoi.roi_h));
  if (![x, y, w, h].every(Number.isFinite) || w <= 0 || h <= 0) return null;
  x = clamp(x, 0, MONITOR_WIDTH - 1);
  y = clamp(y, 0, MONITOR_HEIGHT - 1);
  w = clamp(w, 1, MONITOR_WIDTH - x);
  h = clamp(h, 1, MONITOR_HEIGHT - y);
  return { roi_x: x, roi_y: y, roi_w: w, roi_h: h };
}

function fillRoiInputs(roi) {
  if (!roi) {
    [roiXInput, roiYInput, roiWInput, roiHInput].forEach((input) => { input.value = ""; });
    return;
  }
  roiXInput.value = roi.roi_x;
  roiYInput.value = roi.roi_y;
  roiWInput.value = roi.roi_w;
  roiHInput.value = roi.roi_h;
}

function readRoiInputs({ quiet = false } = {}) {
  const values = [roiXInput, roiYInput, roiWInput, roiHInput].map(optionalValue);
  if (values.every((value) => value === undefined)) return undefined;
  if (values.some((value) => value === undefined)) {
    if (!quiet) window.alert("ROI requires roi_x, roi_y, roi_w, and roi_h together.");
    return null;
  }
  const roi = normalizeRoi({ roi_x: values[0], roi_y: values[1], roi_w: values[2], roi_h: values[3] });
  if (!roi) {
    if (!quiet) window.alert("ROI must fit inside the 640 x 360 monitoring frame.");
    return null;
  }
  return roi;
}

function getSessionMetadata() {
  return {
    site_id: optionalValue(siteIdInput),
    flower_id: optionalValue(flowerIdInput),
    plant_species: optionalValue(plantSpeciesInput),
    observer: optionalValue(observerInput),
    notes: optionalValue(notesInput),
    comparison_session_id: optionalValue(comparisonSessionInput),
    camera_role: optionalValue(cameraRoleInput),
    method_mode: optionalValue(methodModeInput),
  };
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
  const pixelDifference = Number(pixelDifferenceInput.value || 30);
  const motionRatio = Number(motionRatioInput.value || 0.01);
  if ((autoModeInput.checked || motionTriggerInput.checked || hybridModeInput.checked) && (
    !Number.isFinite(idle) || idle < 1 || idle > 3600 ||
    !Number.isFinite(detection) || detection < 1 || detection > 3600
  )) {
    window.alert("自動間隔は 1 秒以上 3600 秒以下で入力してください。");
    return null;
  }
  if (!Number.isFinite(pixelDifference) || pixelDifference < 1 || pixelDifference > 255) {
    window.alert("pixel_difference は 1 以上 255 以下で入力してください。");
    return null;
  }
  if (!Number.isFinite(motionRatio) || motionRatio < 0.0001 || motionRatio > 1) {
    window.alert("motion_ratio は 0.0001 以上 1 以下で入力してください。");
    return null;
  }
  return {
    auto_mode: autoModeInput.checked,
    motion_trigger_mode: motionTriggerInput.checked,
    hybrid_mode: hybridModeInput.checked,
    ml_assist_mode: mlAssistModeInput.checked,
    autonomous_mode: autonomousModeInput.checked,
    idle_interval_sec: idle,
    detection_interval_sec: detection,
    pixel_difference: Math.round(pixelDifference),
    motion_ratio: motionRatio,
  };
}

function getRoiTrackingSettings(camera, hasRoi) {
  if (!hasRoi) return {};
  const trackingInput = field(camera, "roi-tracking");
  const tracking = Boolean(trackingInput && trackingInput.checked);
  camera.roi_tracking = tracking;
  if (!tracking) {
    saveCameras();
    return { roi_tracking: false };
  }
  const margin = Number(field(camera, "roi-search-margin").value || 30);
  const minScore = Number(field(camera, "roi-tracking-min-score").value || 0.45);
  if (!Number.isFinite(margin) || margin < 0 || margin > 160) {
    window.alert("roi_search_margin は 0 以上 160 以下で入力してください。");
    return null;
  }
  if (!Number.isFinite(minScore) || minScore < -1 || minScore > 1) {
    window.alert("roi_tracking_min_score は -1 以上 1 以下で入力してください。");
    return null;
  }
  camera.roi_search_margin = Math.round(margin);
  camera.roi_tracking_min_score = minScore;
  saveCameras();
  return {
    roi_tracking: true,
    roi_search_margin: Math.round(margin),
    roi_tracking_min_score: minScore,
  };
}

function getStartPayload(camera) {
  const interval = getInterval();
  const automaticSettings = getAutomaticSettings();
  if (interval === null || automaticSettings === null) return null;
  const metadata = getSessionMetadata();
  const drawnRoi = normalizeRoi(camera && camera.roi);
  const manualRoi = drawnRoi ? undefined : readRoiInputs({ quiet: true });
  if (manualRoi === null) return null;
  const roi = drawnRoi || manualRoi;
  if (drawnRoi && (!camera.angle_confirmed || camera.roi_stale || camera.roi_pending)) {
    window.alert("画角を変更した場合は、ROIをもう一度指定してください。静止画像で花を囲み、「この花を使う」を押してから開始してください。");
    return null;
  }
  const payload = { interval_sec: interval, ...automaticSettings, ...metadata };
  if (roi) {
    const tracking = getRoiTrackingSettings(camera, true);
    if (tracking === null) return null;
    Object.assign(payload, roi, tracking);
  }
  return payload;
}

async function apiRequest(camera, path, options = {}) {
  const response = await fetch(`${camera.baseUrl}${path}`, options);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
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
    const old = existing >= 0 ? cameras[existing] : {};
    Object.assign(camera, {
      roi: old.roi || null,
      angle_confirmed: Boolean(old.angle_confirmed),
      roi_stale: Boolean(old.roi_stale),
      roi_pending: Boolean(old.roi_pending),
      roi_tracking: Boolean(old.roi_tracking),
      roi_search_margin: old.roi_search_margin || 30,
      roi_tracking_min_score: old.roi_tracking_min_score || 0.45,
    });
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
  camera.aiMonitoring = false;
  field(camera, "device").textContent = `OBSERVATION UNIT ${index + 1} / ${camera.device_name || camera.device_id}`;
  field(camera, "label").textContent = camera.camera_label || "PolliPi Camera";
  field(camera, "sensor").textContent = `${camera.camera_model || "-"} / ${camera.camera_profile || "unspecified"} / ${camera.baseUrl}`;
  card.classList.toggle("noir-card", Boolean(camera.is_noir));
  updateCameraBadges(camera);
  restoreRoiControls(camera);
  setupFieldWorkflowLabels(camera);
  card.querySelector(".start-camera").addEventListener("click", () => startCamera(camera));
  card.querySelector(".stop-camera").addEventListener("click", () => stopCamera(camera));
  card.querySelector(".monitor-camera").addEventListener("click", () => openAngleMonitor(camera));
  card.querySelector(".angle-check-camera").addEventListener("click", () => openAngleMonitor(camera));
  card.querySelector(".angle-accept-camera").addEventListener("click", () => confirmCameraAngle(camera));
  card.querySelector(".monitor-close-camera").addEventListener("click", () => closeAngleMonitor(camera));
  card.querySelector(".roi-preview-camera").addEventListener("click", () => openRoiPreview(camera));
  card.querySelector(".roi-clear-camera").addEventListener("click", () => clearCameraRoi(camera));
  card.querySelector(".roi-use-camera").addEventListener("click", () => acceptFlowerRoi(camera));
  card.querySelector(".roi-redraw-camera").addEventListener("click", () => redrawFlowerRoi(camera));
  card.querySelector(".angle-readjust-camera").addEventListener("click", () => readjustCameraAngle(camera));
  card.querySelector(".roi-cancel-camera").addEventListener("click", () => cancelRoiEditing(camera));
  const aiButton = card.querySelector(".ai-monitor-camera");
  if (camera.is_ai_camera || (camera.camera_model || "").toLowerCase() === "imx500") {
    aiButton.hidden = false;
    aiButton.addEventListener("click", () => toggleMonitor(camera, true));
  }
  card.querySelector(".remove-camera").addEventListener("click", () => removeCamera(camera));
  setupRoiDrawing(camera);
  renderCameraRoi(camera);
  renderFieldWorkflow(camera);
  return card;
}

function restoreRoiControls(camera) {
  camera.roi = normalizeRoi(camera.roi);
  const tracking = field(camera, "roi-tracking");
  const margin = field(camera, "roi-search-margin");
  const score = field(camera, "roi-tracking-min-score");
  tracking.checked = Boolean(camera.roi_tracking && camera.roi && !camera.roi_stale && !camera.roi_pending);
  tracking.disabled = false;
  camera.roi_tracking = tracking.checked;
  margin.value = camera.roi_search_margin || 30;
  score.value = camera.roi_tracking_min_score || 0.45;
  renderTrackingToggle(camera);
  tracking.addEventListener("change", () => {
    if (tracking.checked && !normalizeRoi(camera.roi)) {
      window.alert("先に「花を囲む」で観察したい花や花序を囲んでください。");
      tracking.checked = false;
    }
    camera.roi_tracking = tracking.checked;
    saveCameras();
    renderTrackingToggle(camera);
    renderTrackingStatus(camera);
  });
  margin.addEventListener("change", () => {
    camera.roi_search_margin = Number(margin.value || 30);
    saveCameras();
  });
  score.addEventListener("change", () => {
    camera.roi_tracking_min_score = Number(score.value || 0.45);
    saveCameras();
  });
}

function renderTrackingToggle(camera) {
  const tracking = field(camera, "roi-tracking");
  if (!tracking) return;
  const label = tracking.closest("label");
  const text = label ? label.querySelector("span") : null;
  if (text) text.textContent = `花の揺れに追従: ${tracking.checked ? "ON" : "OFF"}`;
}

function setupFieldWorkflowLabels(camera) {
  camera.card.querySelector(".start-camera").textContent = "撮影開始";
  camera.card.querySelector(".stop-camera").textContent = "停止";
  camera.card.querySelector(".monitor-camera").hidden = true;
  camera.card.querySelector(".angle-check-camera").textContent = "画角を確認";
  camera.card.querySelector(".angle-accept-camera").textContent = "この画角でOK";
  camera.card.querySelector(".monitor-close-camera").textContent = "閉じる";
  camera.card.querySelector(".roi-preview-camera").textContent = "花を囲む";
  camera.card.querySelector(".roi-clear-camera").textContent = "ROIを解除";
  const note = camera.card.querySelector(".roi-note");
  if (note) note.textContent = "画角を変更した場合は、ROIをもう一度指定してください。ROIは640 x 360の監視フレーム上で保存されます。";
}

function renderFieldWorkflow(camera) {
  const roi = normalizeRoi(camera.roi);
  const angleStatus = field(camera, "angle-status");
  const roiStatusDetail = field(camera, "roi-status-detail");
  const angleOk = camera.card.querySelector(".angle-accept-camera");
  const monitorClose = camera.card.querySelector(".monitor-close-camera");
  const roiButton = camera.card.querySelector(".roi-preview-camera");
  if (angleStatus) angleStatus.textContent = `画角: ${camera.angle_confirmed ? "確認済み" : "未確認"}`;
  if (roiStatusDetail) {
    roiStatusDetail.textContent = `ROI: ${roi && !camera.roi_stale && !camera.roi_pending ? "設定済み" : roi && camera.roi_pending ? "選択中" : roi && camera.roi_stale ? "再指定が必要" : "未設定"}`;
  }
  if (angleOk) angleOk.hidden = !camera.monitoring || camera.aiMonitoring;
  if (monitorClose) monitorClose.hidden = !camera.monitoring || camera.aiMonitoring;
  if (roiButton) roiButton.disabled = !camera.angle_confirmed;
  renderTrackingToggle(camera);
}

function markRoiStaleForAngleChange(camera) {
  if (normalizeRoi(camera.roi)) {
    camera.roi_stale = true;
    camera.roi_pending = false;
    camera.angle_confirmed = false;
    saveCameras();
    field(camera, "message").textContent = "画角を変更した場合は、ROIをもう一度指定してください。";
  }
}

function openAngleMonitor(camera) {
  const drawer = field(camera, "roi-drawer");
  if (drawer) drawer.hidden = true;
  camera.angle_confirmed = false;
  markRoiStaleForAngleChange(camera);
  saveCameras();
  toggleMonitor(camera, false, { forceOpen: true });
  field(camera, "message").textContent = "画角確認中です。花が画面中央付近に入るようにカメラを調整してください。";
  renderFieldWorkflow(camera);
}

function closeAngleMonitor(camera) {
  setMonitor(camera, false);
  field(camera, "message").textContent = "画角確認を閉じました。調整した場合は、もう一度「画角を確認」から確認してください。";
  renderFieldWorkflow(camera);
}

async function confirmCameraAngle(camera) {
  setMonitor(camera, false);
  camera.angle_confirmed = true;
  camera.roi = null;
  camera.roi_stale = true;
  camera.roi_pending = false;
  fillRoiInputs(null);
  saveCameras();
  renderCameraRoi(camera);
  renderFieldWorkflow(camera);
  await openRoiPreview(camera, {
    message: "画角を固定しました。静止画像の上で観察したい花を囲んでください。",
    forceReselect: true,
  });
}

function renderCameras() {
  cameraGrid.replaceChildren();
  cameraEmpty.hidden = cameras.length !== 0;
  if (cameras.length === 0) {
    cameraGrid.append(cameraEmpty);
  } else {
    cameras.forEach((camera, index) => cameraGrid.append(buildCameraCard(camera, index)));
  }
  renderGallerySelection();
  if (!selectedGalleryCamera || !cameras.some((camera) => camera.baseUrl === selectedGalleryCamera.baseUrl)) {
    selectedGalleryCamera = cameras[0] || null;
  }
}

function updateCameraBadges(camera) {
  const badges = field(camera, "badges");
  badges.replaceChildren();
  [
    camera.is_ai_camera ? "AI" : null,
    camera.is_noir ? "IR / NoIR" : null,
    camera.is_wide ? "Wide" : null,
    camera.camera_profile || null,
    camera.camera_role || (camera.status && camera.status.camera_role) || null,
    camera.comparison_session_id || (camera.status && camera.status.comparison_session_id) || null,
  ].filter(Boolean).forEach((value) => {
    const badge = document.createElement("span");
    badge.className = "camera-badge";
    badge.textContent = value;
    badges.append(badge);
  });
}

function renderGallerySelection() {
  gallerySwitch.replaceChildren();
  cameras.forEach((camera) => {
    const button = document.createElement("button");
    button.className = `gallery-tab${selectedGalleryCamera && selectedGalleryCamera.baseUrl === camera.baseUrl ? " selected" : ""}`;
    button.type = "button";
    button.textContent = camera.camera_label || camera.device_name || camera.baseUrl;
    button.addEventListener("click", async () => {
      selectedGalleryCamera = camera;
      await Promise.all([refreshGallery(), refreshEvents(), refreshTraining()]);
    });
    gallerySwitch.append(button);
  });
}

function removeCamera(camera) {
  if (!window.confirm(`${camera.camera_label} の登録をこの iPad から削除しますか？\n撮影画像は Raspberry Pi に残ります。`)) return;
  cameras = cameras.filter((item) => item.baseUrl !== camera.baseUrl);
  if (selectedGalleryCamera && selectedGalleryCamera.baseUrl === camera.baseUrl) selectedGalleryCamera = null;
  saveCameras();
  renderCameras();
  refreshGallery();
  refreshEvents();
}

function setCameraRoi(camera, roi, { fillInputs = true, pending = true } = {}) {
  const normalized = normalizeRoi(roi);
  if (!normalized) return false;
  camera.roi = normalized;
  camera.roi_pending = Boolean(pending);
  camera.roi_stale = false;
  if (fillInputs) fillRoiInputs(normalized);
  saveCameras();
  renderCameraRoi(camera);
  renderTrackingToggle(camera);
  renderFieldWorkflow(camera);
  return true;
}

function clearCameraRoi(camera) {
  camera.roi = null;
  camera.roi_stale = false;
  camera.roi_pending = false;
  fillRoiInputs(null);
  camera.roi_tracking = false;
  const tracking = field(camera, "roi-tracking");
  if (tracking) tracking.checked = false;
  saveCameras();
  renderCameraRoi(camera);
  renderTrackingToggle(camera);
  renderFieldWorkflow(camera);
  field(camera, "message").textContent = "ROIを解除しました。動き検出は全画面で行います。";
}

function useFullFrame(camera) {
  clearCameraRoi(camera);
}

function renderCameraRoi(camera) {
  const status = field(camera, "roi-status");
  const previewBox = field(camera, "roi-box");
  const monitorBox = field(camera, "monitor-roi-box");
  const statusInfo = camera.status || {};
  const trackedRoi = statusInfo.tracked_roi_w ? normalizeRoi({
    roi_x: statusInfo.tracked_roi_x,
    roi_y: statusInfo.tracked_roi_y,
    roi_w: statusInfo.tracked_roi_w,
    roi_h: statusInfo.tracked_roi_h,
  }) : null;
  const roi = statusInfo.roi_tracking && trackedRoi ? trackedRoi : normalizeRoi(camera.roi);
  if (!roi) {
    status.textContent = "ROI: 未設定";
    previewBox.style.display = "";
    monitorBox.style.display = "";
    renderTrackingStatus(camera);
    renderFieldWorkflow(camera);
    return;
  }
  status.textContent = camera.roi_stale
    ? "ROI: 再指定が必要"
    : camera.roi_pending
      ? `ROI: 選択中 x=${roi.roi_x}, y=${roi.roi_y}, w=${roi.roi_w}, h=${roi.roi_h}`
      : `ROI: 設定済み x=${roi.roi_x}, y=${roi.roi_y}, w=${roi.roi_w}, h=${roi.roi_h}`;
  renderRoiBoxOnImage(previewBox, field(camera, "roi-preview"), field(camera, "roi-wrap"), roi);
  renderRoiBoxOnImage(monitorBox, field(camera, "image"), field(camera, "image-frame"), roi);
  renderTrackingStatus(camera);
  renderFieldWorkflow(camera);
}

function renderRoiBoxOnImage(box, image, wrap, roi) {
  if (!box || !image || !wrap) return;
  if (!(image.complete && image.clientWidth > 0 && image.clientHeight > 0)) return;
  const imageRect = image.getBoundingClientRect();
  const wrapRect = wrap.getBoundingClientRect();
  box.style.display = "block";
  box.style.left = `${imageRect.left - wrapRect.left + roi.roi_x / MONITOR_WIDTH * imageRect.width}px`;
  box.style.top = `${imageRect.top - wrapRect.top + roi.roi_y / MONITOR_HEIGHT * imageRect.height}px`;
  box.style.width = `${roi.roi_w / MONITOR_WIDTH * imageRect.width}px`;
  box.style.height = `${roi.roi_h / MONITOR_HEIGHT * imageRect.height}px`;
}

function renderTrackingStatus(camera) {
  const node = field(camera, "roi-tracking-status");
  if (!node) return;
  const status = camera.status || {};
  const roi = normalizeRoi(camera.roi);
  if (!roi && !status.tracked_roi_w) {
    node.textContent = "花の揺れに追従: OFF";
  } else if (!status.roi_tracking && !field(camera, "roi-tracking").checked) {
    node.textContent = "花の揺れに追従: OFF";
  } else {
    const score = status.roi_tracking_score == null ? "-" : Number(status.roi_tracking_score).toFixed(2);
    const ok = status.roi_tracking_success ? "追跡中" : "前回ROIを保持";
    const sx = status.roi_shift_x == null ? "-" : status.roi_shift_x;
    const sy = status.roi_shift_y == null ? "-" : status.roi_shift_y;
    node.textContent = `花の揺れに追従: ON / score ${score} / ${ok} / shift x=${sx}, y=${sy}`;
  }
}

function pointInImage(event, image) {
  const rect = image.getBoundingClientRect();
  const source = event.touches ? event.touches[0] || event.changedTouches[0] : event;
  if (!source || rect.width <= 0 || rect.height <= 0) return null;
  return {
    x: clamp(source.clientX - rect.left, 0, rect.width),
    y: clamp(source.clientY - rect.top, 0, rect.height),
    width: rect.width,
    height: rect.height,
  };
}

function displayRectToRoi(start, end) {
  const left = Math.min(start.x, end.x);
  const top = Math.min(start.y, end.y);
  const width = Math.abs(end.x - start.x);
  const height = Math.abs(end.y - start.y);
  if (width < MIN_ROI_SIZE || height < MIN_ROI_SIZE) return null;
  return normalizeRoi({
    roi_x: Math.round(left * MONITOR_WIDTH / start.width),
    roi_y: Math.round(top * MONITOR_HEIGHT / start.height),
    roi_w: Math.round(width * MONITOR_WIDTH / start.width),
    roi_h: Math.round(height * MONITOR_HEIGHT / start.height),
  });
}

function drawRoiBoxFromPoints(box, start, end) {
  const left = Math.min(start.x, end.x);
  const top = Math.min(start.y, end.y);
  const width = Math.abs(end.x - start.x);
  const height = Math.abs(end.y - start.y);
  drawRoiBoxFromDisplayRect(box, { left, top, width, height });
}

function drawRoiBoxFromDisplayRect(box, rect) {
  box.style.display = "block";
  box.style.left = `${rect.left}px`;
  box.style.top = `${rect.top}px`;
  box.style.width = `${rect.width}px`;
  box.style.height = `${rect.height}px`;
}

function roiToDisplayRect(roi, image) {
  const normalized = normalizeRoi(roi);
  if (!normalized) return null;
  const imageRect = image.getBoundingClientRect();
  if (imageRect.width <= 0 || imageRect.height <= 0) return null;
  return {
    left: normalized.roi_x * imageRect.width / MONITOR_WIDTH,
    top: normalized.roi_y * imageRect.height / MONITOR_HEIGHT,
    width: normalized.roi_w * imageRect.width / MONITOR_WIDTH,
    height: normalized.roi_h * imageRect.height / MONITOR_HEIGHT,
  };
}

function displayRectToRoiRect(rect, displayWidth, displayHeight) {
  if (!rect || rect.width < MIN_ROI_SIZE || rect.height < MIN_ROI_SIZE) return null;
  return normalizeRoi({
    roi_x: Math.round(rect.left * MONITOR_WIDTH / displayWidth),
    roi_y: Math.round(rect.top * MONITOR_HEIGHT / displayHeight),
    roi_w: Math.round(rect.width * MONITOR_WIDTH / displayWidth),
    roi_h: Math.round(rect.height * MONITOR_HEIGHT / displayHeight),
  });
}

function getRoiDragMode(point, rect) {
  if (!rect) return { type: "draw" };
  const handle = 18;
  const insideX = point.x >= rect.left && point.x <= rect.left + rect.width;
  const insideY = point.y >= rect.top && point.y <= rect.top + rect.height;
  if (!insideX || !insideY) return { type: "draw" };
  const nearLeft = Math.abs(point.x - rect.left) <= handle;
  const nearRight = Math.abs(point.x - (rect.left + rect.width)) <= handle;
  const nearTop = Math.abs(point.y - rect.top) <= handle;
  const nearBottom = Math.abs(point.y - (rect.top + rect.height)) <= handle;
  if (nearLeft || nearRight || nearTop || nearBottom) {
    return {
      type: "resize",
      left: nearLeft,
      right: nearRight,
      top: nearTop,
      bottom: nearBottom,
    };
  }
  return { type: "move" };
}

function clampDisplayRoiRect(rect, displayWidth, displayHeight) {
  const width = clamp(rect.width, MIN_ROI_SIZE, displayWidth);
  const height = clamp(rect.height, MIN_ROI_SIZE, displayHeight);
  return {
    left: clamp(rect.left, 0, displayWidth - width),
    top: clamp(rect.top, 0, displayHeight - height),
    width,
    height,
  };
}

function updateDisplayRoiRect(mode, baseRect, start, point) {
  const dx = point.x - start.x;
  const dy = point.y - start.y;
  let next = { ...baseRect };
  if (mode.type === "move") {
    next.left += dx;
    next.top += dy;
  } else if (mode.type === "resize") {
    if (mode.left) {
      next.left = baseRect.left + dx;
      next.width = baseRect.width - dx;
    }
    if (mode.right) next.width = baseRect.width + dx;
    if (mode.top) {
      next.top = baseRect.top + dy;
      next.height = baseRect.height - dy;
    }
    if (mode.bottom) next.height = baseRect.height + dy;
  }
  if (next.width < 0) {
    next.left += next.width;
    next.width = Math.abs(next.width);
  }
  if (next.height < 0) {
    next.top += next.height;
    next.height = Math.abs(next.height);
  }
  return clampDisplayRoiRect(next, point.width, point.height);
}

function setupRoiDrawing(camera) {
  setupRoiDrawingTarget(camera, field(camera, "roi-wrap"), field(camera, "roi-preview"), field(camera, "roi-box"), "preview");
}

function setupRoiDrawingTarget(camera, wrap, image, box, sourceName) {
  let drawing = false;
  let startPoint = null;
  let previousRoi = null;
  let dragMode = { type: "draw" };
  let baseRect = null;
  let currentRect = null;
  let usedPointer = false;
  const begin = (event) => {
    if (event.type.startsWith("touch") && usedPointer) return;
    const point = pointInImage(event, image);
    if (!point) return;
    event.preventDefault();
    drawing = true;
    startPoint = point;
    previousRoi = normalizeRoi(camera.roi);
    baseRect = roiToDisplayRect(previousRoi, image);
    dragMode = getRoiDragMode(point, baseRect);
    currentRect = dragMode.type === "draw" ? null : baseRect;
    if (currentRect) drawRoiBoxFromDisplayRect(box, currentRect);
    else drawRoiBoxFromPoints(box, point, point);
    if (event.pointerId !== undefined && wrap.setPointerCapture) {
      usedPointer = true;
      wrap.setPointerCapture(event.pointerId);
    }
  };
  const move = (event) => {
    if (event.type.startsWith("touch") && usedPointer) return;
    if (!drawing || !startPoint) return;
    const point = pointInImage(event, image);
    if (!point) return;
    event.preventDefault();
    if (dragMode.type === "draw") {
      drawRoiBoxFromPoints(box, startPoint, point);
    } else {
      currentRect = updateDisplayRoiRect(dragMode, baseRect, startPoint, point);
      drawRoiBoxFromDisplayRect(box, currentRect);
    }
  };
  const end = (event) => {
    if (event.type.startsWith("touch") && usedPointer) return;
    if (!drawing || !startPoint) return;
    const point = pointInImage(event, image);
    const origin = startPoint;
    drawing = false;
    startPoint = null;
    if (!point) return;
    event.preventDefault();
    const roi = dragMode.type === "draw"
      ? displayRectToRoi(origin, point)
      : displayRectToRoiRect(currentRect, point.width, point.height);
    if (roi) {
      setCameraRoi(camera, roi, { pending: true });
      field(camera, "message").textContent = "花を囲みました。よければ「この花を使う」を押してください。";
    } else {
      camera.roi = previousRoi;
      renderCameraRoi(camera);
      field(camera, "message").textContent = "ROI is too small. Please draw a larger rectangle.";
    }
  };
  if (window.PointerEvent) {
    wrap.addEventListener("pointerdown", begin);
    wrap.addEventListener("pointermove", move);
    wrap.addEventListener("pointerup", end);
    wrap.addEventListener("pointercancel", end);
  }
  wrap.addEventListener("touchstart", begin, { passive: false });
  wrap.addEventListener("touchmove", move, { passive: false });
  wrap.addEventListener("touchend", end, { passive: false });
  wrap.addEventListener("mousedown", begin);
  wrap.addEventListener("mousemove", move);
  wrap.addEventListener("mouseup", end);
}

async function openRoiPreview(camera, options = {}) {
  if (!camera.angle_confirmed && !options.forceReselect) {
    window.alert("先に「画角を確認」して、「この画角でOK」を押してください。");
    return;
  }
  setMonitor(camera, false);
  const drawer = field(camera, "roi-drawer");
  const image = field(camera, "roi-preview");
  camera.roiBeforeEdit = normalizeRoi(camera.roi);
  camera.roi_pending = Boolean(normalizeRoi(camera.roi));
  if (options.forceReselect) {
    camera.roiBeforeEdit = null;
    camera.roi = null;
    camera.roi_pending = false;
    fillRoiInputs(null);
  }
  drawer.hidden = false;
  image.classList.remove("ready");
  image.onload = () => {
    image.classList.add("ready");
    renderCameraRoi(camera);
    const message = options.message || "静止画像の上で観察したい花を囲んでください。";
    const editorMessage = field(camera, "roi-editor-message");
    if (editorMessage) editorMessage.textContent = message;
    field(camera, "message").textContent = message;
  };
  image.onerror = () => {
    image.classList.remove("ready");
    field(camera, "message").textContent = "プレビューを取得できません。カメラ接続を確認してください。";
  };
  image.src = `${camera.baseUrl}/preview?t=${Date.now()}`;
  field(camera, "message").textContent = "静止画像を読み込み中...";
  saveCameras();
  renderFieldWorkflow(camera);
}

function acceptFlowerRoi(camera) {
  const roi = normalizeRoi(camera.roi);
  if (!roi) {
    window.alert("静止画像の上で観察したい花を囲んでください。");
    return;
  }
  camera.angle_confirmed = true;
  camera.roi_pending = false;
  camera.roi_stale = false;
  delete camera.roiBeforeEdit;
  field(camera, "roi-drawer").hidden = true;
  saveCameras();
  renderCameraRoi(camera);
  renderFieldWorkflow(camera);
  field(camera, "message").textContent = "この花をROIとして設定しました。";
}

function redrawFlowerRoi(camera) {
  camera.roi = null;
  camera.roi_pending = false;
  camera.roi_stale = true;
  fillRoiInputs(null);
  saveCameras();
  renderCameraRoi(camera);
  renderFieldWorkflow(camera);
  field(camera, "message").textContent = "やり直し中です。静止画像の上で花をもう一度囲んでください。";
}

function readjustCameraAngle(camera) {
  clearCameraRoi(camera);
  camera.angle_confirmed = false;
  camera.roi_stale = false;
  delete camera.roiBeforeEdit;
  saveCameras();
  field(camera, "roi-drawer").hidden = true;
  openAngleMonitor(camera);
  field(camera, "message").textContent = "画角を変更した場合は、ROIをもう一度指定してください。";
}

function cancelRoiEditing(camera) {
  const previous = normalizeRoi(camera.roiBeforeEdit);
  camera.roi = previous;
  camera.roi_pending = false;
  camera.roi_stale = previous ? Boolean(camera.roi_stale) : false;
  if (previous) fillRoiInputs(previous);
  else fillRoiInputs(null);
  delete camera.roiBeforeEdit;
  field(camera, "roi-drawer").hidden = true;
  saveCameras();
  renderCameraRoi(camera);
  renderFieldWorkflow(camera);
  field(camera, "message").textContent = "ROI指定をキャンセルしました。";
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

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "-";
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function updateCard(camera, status) {
  camera.status = status;
  Object.assign(camera, {
    device_id: status.device_id || camera.device_id,
    device_name: status.device_name || camera.device_name,
    camera_label: status.camera_label || camera.camera_label,
    camera_model: status.camera_model || camera.camera_model,
    camera_profile: status.camera_profile || camera.camera_profile,
    is_ai_camera: Boolean(status.is_ai_camera),
    is_noir: Boolean(status.is_noir),
    is_wide: Boolean(status.is_wide),
    camera_role: status.camera_role || camera.camera_role,
    comparison_session_id: status.comparison_session_id || camera.comparison_session_id,
  });
  field(camera, "sensor").textContent = `${camera.camera_model} / ${camera.camera_profile || "unspecified"} / ${camera.baseUrl}`;
  updateCameraBadges(camera);
  const pill = field(camera, "pill");
  pill.textContent = status.running ? "撮影中" : "停止中";
  pill.className = `pill ${status.running ? "running" : "stopped"}`;
  field(camera, "count").textContent = String(status.capture_count);
  field(camera, "interval").textContent = status.interval_sec ? `${status.interval_sec} 秒` : "-";
  field(camera, "time").textContent = formatCaptureTime(status.last_capture_time);
  const score = status.motion_score === null ? "基準作成中" : `${(Number(status.motion_score || 0) * 100).toFixed(2)}%`;
  field(camera, "detection").textContent = status.auto_mode ? `${status.motion_type || "motion"} / ${score}` : "OFF";
  const message = status.auto_mode && status.interval_reason ? status.interval_reason : status.message;
  field(camera, "message").textContent = `${message}${status.autonomous_mode && status.running ? " / 自律運行" : ""}`;
  renderCameraRoi(camera);
  if (!camera.monitoring && status.last_image && status.last_image !== camera.previousImage) {
    const image = field(camera, "image");
    image.onload = () => {
      image.classList.add("ready");
      field(camera, "empty").hidden = true;
      renderCameraRoi(camera);
    };
    image.src = `${camera.baseUrl}/latest?capture=${encodeURIComponent(status.last_capture_time || Date.now())}`;
    camera.previousImage = status.last_image;
    camera.manualPreview = false;
  } else if (!status.last_image && !camera.manualPreview) {
    const image = field(camera, "image");
    image.classList.remove("ready");
    image.removeAttribute("src");
    field(camera, "empty").hidden = false;
  }
}

async function updateSystemCard(camera) {
  try {
    const system = await apiRequest(camera, "/system");
    field(camera, "storage").textContent = `${formatBytes(system.storage_free_bytes)} 空き`;
    field(camera, "power").textContent = system.undervoltage_now ? "電圧低下中" : system.undervoltage_occurred ? "電圧低下履歴" : "電圧OK";
  } catch (_) {
    field(camera, "storage").textContent = "-";
    field(camera, "power").textContent = "-";
  }
}

function setOffline(camera, error) {
  setMonitor(camera, false);
  const pill = field(camera, "pill");
  pill.textContent = "接続なし";
  pill.className = "pill offline";
  field(camera, "message").textContent = `接続できません: ${error.message}`;
}

async function refreshCamera(camera) {
  try {
    updateCard(camera, await apiRequest(camera, "/status"));
    await updateSystemCard(camera);
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
  await Promise.all([refreshGallery(), refreshEvents(), refreshTraining()]);
}

async function startCamera(camera) {
  const payload = getStartPayload(camera);
  if (!payload) return;
  setMonitor(camera, false);
  setBusy(camera, true);
  try {
    const status = await apiRequest(camera, "/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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

function setMonitor(camera, monitoring, aiDetection = false) {
  const button = camera.card.querySelector(".monitor-camera");
  const aiButton = camera.card.querySelector(".ai-monitor-camera");
  const image = field(camera, "image");
  camera.monitoring = monitoring;
  camera.aiMonitoring = monitoring && aiDetection;
  button.classList.toggle("active", monitoring && !aiDetection);
  aiButton.classList.toggle("active", camera.aiMonitoring);
  button.textContent = monitoring && !aiDetection ? "閉じる" : "画角を確認";
  aiButton.textContent = camera.aiMonitoring ? "AIモニター停止" : "AI検出モニター";
  if (!monitoring) {
    if (camera.status && camera.status.last_image) {
      image.src = `${camera.baseUrl}/latest?capture=${encodeURIComponent(camera.status.last_capture_time || Date.now())}`;
    } else {
      image.classList.remove("ready");
      image.removeAttribute("src");
      field(camera, "empty").hidden = false;
    }
  }
  renderFieldWorkflow(camera);
}

function toggleMonitor(camera, aiDetection = false, options = {}) {
  if (camera.monitoring && camera.aiMonitoring === aiDetection && !options.forceOpen) {
    setMonitor(camera, false);
    field(camera, "message").textContent = aiDetection ? "AI検出モニターを停止しました。" : "画角モニターを停止しました。";
    return;
  }
  if (aiDetection && camera.status && camera.status.running) {
    window.alert("AI検出モニターは撮影を停止してから使用してください。");
    return;
  }
  const image = field(camera, "image");
  image.onload = () => {
    image.classList.add("ready");
    field(camera, "empty").hidden = true;
    renderCameraRoi(camera);
  };
  image.onerror = () => {
    setMonitor(camera, false);
    setOffline(camera, new Error("画面を取得できません"));
  };
  setMonitor(camera, true, aiDetection);
  image.src = `${camera.baseUrl}/mjpeg?detect=${aiDetection ? "true" : "false"}&t=${Date.now()}`;
  camera.manualPreview = true;
  field(camera, "message").textContent = aiDetection
    ? "AI検出モニター表示中（保存されません）。"
    : "画角確認中です。花が画面中央付近に入るようにカメラを調整してください。";
  renderFieldWorkflow(camera);
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

async function refreshGallery() {
  const camera = selectedGalleryCamera;
  renderGallerySelection();
  allImagesTab.classList.toggle("selected", selectedCollection === "all");
  positiveImagesTab.classList.toggle("selected", selectedCollection === "positive");
  negativeImagesTab.classList.toggle("selected", selectedCollection === "negative");
  deleteAllImagesButton.hidden = selectedCollection !== "all";
  if (!camera) {
    galleryCameraLabel.textContent = "観察機未選択";
    galleryCount.textContent = "-";
    gallerySize.textContent = "";
    galleryFolderPath.textContent = "観察機を追加すると保存画像を表示できます。";
    galleryGrid.innerHTML = `<p class="gallery-empty">観察機が登録されていません。</p>`;
    downloadZipLink.classList.add("disabled");
    downloadZipLink.removeAttribute("href");
    return;
  }
  downloadZipLink.classList.remove("disabled");
  downloadZipLink.href = `${camera.baseUrl}/exports/images.zip?collection=${selectedCollection}`;
  downloadZipLink.textContent = selectedCollection === "all" ? "全画像とログをZIP保存" : `${selectedCollection} をZIP保存`;
  galleryCameraLabel.textContent = `${camera.camera_label} / ${selectedCollection}`;
  try {
    const response = await apiRequest(camera, `/images?limit=40&collection=${selectedCollection}`);
    if (selectedCollection === "all") camera.imageCount = response.image_count;
    galleryCount.textContent = `${response.image_count} 枚`;
    gallerySize.textContent = formatBytes(response.total_size_bytes);
    galleryFolderPath.textContent = response.image_dir;
    galleryGrid.replaceChildren();
    if (!response.images.length) {
      galleryGrid.innerHTML = `<p class="gallery-empty">画像はまだありません。</p>`;
      return;
    }
    response.images.forEach((imageInfo) => galleryGrid.append(buildGalleryItem(camera, imageInfo)));
  } catch (error) {
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
  detail.innerHTML = `<span>${formatCaptureTime(imageInfo.captured_at)}</span><span>${formatBytes(imageInfo.size_bytes)}</span>`;
  const labelBadge = document.createElement("p");
  labelBadge.className = `label-badge ${imageInfo.review_status || "unlabeled"}`;
  labelBadge.textContent = `${imageInfo.label || "未分類"} / ${imageInfo.review_status || "unlabeled"}`;
  const downloadLink = document.createElement("a");
  downloadLink.className = "download-image";
  downloadLink.href = `${camera.baseUrl}${imageInfo.url}${imageInfo.url.includes("?") ? "&" : "?"}download=true`;
  downloadLink.download = imageInfo.filename;
  downloadLink.textContent = "iPadに保存";
  const actions = document.createElement("div");
  actions.className = "review-actions";
  const confirmButton = document.createElement("button");
  confirmButton.className = "label-confirm";
  confirmButton.type = "button";
  confirmButton.textContent = "この分類でOK";
  confirmButton.disabled = !imageInfo.label || imageInfo.review_status === "reviewed";
  confirmButton.addEventListener("click", () => reviewLabel(camera, imageInfo.filename, "confirmed"));
  const positiveButton = document.createElement("button");
  positiveButton.className = "label-positive";
  positiveButton.type = "button";
  positiveButton.textContent = "positiveに修正";
  positiveButton.addEventListener("click", () => reviewLabel(camera, imageInfo.filename, "positive"));
  const negativeButton = document.createElement("button");
  negativeButton.className = "label-negative";
  negativeButton.type = "button";
  negativeButton.textContent = "negativeに修正";
  negativeButton.addEventListener("click", () => reviewLabel(camera, imageInfo.filename, "negative"));
  actions.append(confirmButton, positiveButton, negativeButton);
  const deleteButton = document.createElement("button");
  deleteButton.className = "delete-image";
  deleteButton.type = "button";
  deleteButton.textContent = "削除";
  deleteButton.addEventListener("click", async () => {
    if (!window.confirm(`${camera.camera_label} のこの写真を削除しますか？\n${imageInfo.filename}`)) return;
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
  item.append(image, detail, labelBadge, downloadLink, actions, deleteButton);
  return item;
}

async function reviewLabel(camera, filename, label) {
  try {
    await apiRequest(camera, `/images/${encodeURIComponent(filename)}/label`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label }),
    });
    await refreshGallery();
  } catch (error) {
    window.alert(`ラベルを保存できませんでした: ${error.message}`);
  }
}

async function refreshEvents() {
  const camera = selectedGalleryCamera;
  eventGrid.replaceChildren();
  if (!camera) {
    eventCameraLabel.textContent = "観察機未選択";
    eventCount.textContent = "events -";
    downloadEventLabelsLink.classList.add("disabled");
    downloadEventLabelsLink.removeAttribute("href");
    return;
  }
  eventCameraLabel.textContent = camera.camera_label;
  downloadEventLabelsLink.classList.remove("disabled");
  downloadEventLabelsLink.href = `${camera.baseUrl}/events/export_labels.csv`;
  try {
    const response = await apiRequest(camera, "/events?limit=50");
    eventCount.textContent = `${response.event_count} events`;
    if (!response.events.length) {
      eventGrid.innerHTML = `<p class="gallery-empty">イベント候補はまだありません。</p>`;
      return;
    }
    response.events.forEach((eventInfo) => eventGrid.append(buildEventItem(camera, eventInfo)));
  } catch (error) {
    eventGrid.innerHTML = `<p class="gallery-empty">イベントを取得できません: ${error.message}</p>`;
  }
}

function buildEventItem(camera, eventInfo) {
  const item = document.createElement("article");
  item.className = "event-item";
  const image = document.createElement("img");
  image.src = eventInfo.image_url ? `${camera.baseUrl}${eventInfo.image_url}` : "";
  image.alt = eventInfo.image_filename || eventInfo.event_id;
  image.loading = "lazy";
  const meta = document.createElement("div");
  meta.className = "event-meta";
  meta.innerHTML = `
    <strong>${eventInfo.timestamp || "-"}</strong>
    <span>${eventInfo.device_name || camera.camera_label} / ${eventInfo.camera_profile || "-"}</span>
    <span>site ${eventInfo.site_id || "-"} / flower ${eventInfo.flower_id || "-"} / plant ${eventInfo.plant_species || "-"}</span>
    <span>motion ${eventInfo.motion_score || "-"} / changed ${eventInfo.changed_area_ratio || "-"} / wind ${eventInfo.wind_like_motion || "-"}</span>
    <span>label: ${eventInfo.manual_label || "unreviewed"}</span>
  `;
  const form = document.createElement("div");
  form.className = "event-review-form";
  const labelSelect = document.createElement("select");
  ["", "insect", "non_insect", "unclear"].forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value || "manual label";
    option.selected = value === (eventInfo.manual_label || "");
    labelSelect.append(option);
  });
  const taxon = document.createElement("input");
  taxon.placeholder = "manual taxon";
  taxon.value = eventInfo.manual_taxon || "";
  const reason = document.createElement("select");
  ["", "wind", "shadow", "flower_movement", "camera_shake", "non_insect_object", "lighting_change", "unclear", "other"].forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value || "false positive reason";
    option.selected = value === (eventInfo.false_positive_reason || "");
    reason.append(option);
  });
  const notes = document.createElement("input");
  notes.placeholder = "manual notes";
  notes.value = eventInfo.manual_notes || "";
  const actions = document.createElement("div");
  actions.className = "event-review-actions";
  [["insect", "insect"], ["non_insect", "non insect"], ["unclear", "unclear"]].forEach(([value, text]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text;
    button.className = eventInfo.manual_label === value ? "selected-label" : "";
    button.addEventListener("click", () => {
      labelSelect.value = value;
      saveEventReview(camera, eventInfo.event_id, {
        manual_label: value,
        manual_taxon: taxon.value,
        false_positive_reason: reason.value,
        manual_notes: notes.value,
      });
    });
    actions.append(button);
  });
  const saveButton = document.createElement("button");
  saveButton.type = "button";
  saveButton.className = "label-confirm";
  saveButton.textContent = "Save label";
  saveButton.addEventListener("click", () => {
    if (!labelSelect.value) {
      window.alert("manual_labelを選んでください。");
      return;
    }
    saveEventReview(camera, eventInfo.event_id, {
      manual_label: labelSelect.value,
      manual_taxon: taxon.value,
      false_positive_reason: reason.value,
      manual_notes: notes.value,
    });
  });
  actions.append(saveButton);
  form.append(labelSelect, taxon, reason, notes, actions);
  item.append(image, meta, form);
  return item;
}

async function saveEventReview(camera, eventId, payload) {
  try {
    await apiRequest(camera, `/events/${encodeURIComponent(eventId)}/label`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await refreshEvents();
  } catch (error) {
    window.alert(`Event reviewを保存できませんでした: ${error.message}`);
  }
}

async function refreshTraining() {
  const camera = selectedGalleryCamera;
  if (!camera) return;
  try {
    const status = await apiRequest(camera, "/training/status");
    positiveCount.textContent = status.positive_count;
    negativeCount.textContent = status.negative_count;
    trainingModel.textContent = status.model_available ? "available" : "none";
    trainingMessage.textContent = status.message;
  } catch (error) {
    trainingMessage.textContent = `学習状態を取得できません: ${error.message}`;
  }
}

async function startTraining() {
  const camera = selectedGalleryCamera;
  if (!camera) return;
  if (!window.confirm(`${camera.camera_label} の positive / negative を使って再学習しますか？`)) return;
  try {
    await apiRequest(camera, "/training/start", { method: "POST" });
    await refreshTraining();
  } catch (error) {
    window.alert(`再学習できませんでした: ${error.message}`);
  }
}

async function resetTrainingModel() {
  const camera = selectedGalleryCamera;
  if (!camera) return;
  if (!window.confirm(`${camera.camera_label} の学習済みモデルを破棄しますか？`)) return;
  try {
    await apiRequest(camera, "/training/model", { method: "DELETE" });
    await refreshTraining();
  } catch (error) {
    window.alert(`モデルを破棄できませんでした: ${error.message}`);
  }
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
  }
}

function selectExclusiveMode(selectedInput) {
  if (selectedInput.checked) {
    [autoModeInput, motionTriggerInput, hybridModeInput].forEach((input) => {
      if (input !== selectedInput) input.checked = false;
    });
  }
  updateAutomaticControls();
}

function updateAutomaticControls() {
  const enabled = autoModeInput.checked || motionTriggerInput.checked || hybridModeInput.checked;
  autoSettings.classList.toggle("active", enabled);
  idleSetting.hidden = motionTriggerInput.checked || hybridModeInput.checked;
  detectionSettingLabel.textContent = (motionTriggerInput.checked || hybridModeInput.checked) ? "候補チェック" : "動き候補あり";
  autoSettingsHelp.textContent = hybridModeInput.checked
    ? "研究用: 定間隔写真を必ず保存し、動き候補があれば追加撮影します。"
    : motionTriggerInput.checked
    ? "低解像度で動きを見て、候補が出た時だけ保存します。"
    : "背景差分で候補がない時は間隔を長くし、候補があれば短くします。";
}

deviceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const camera = await registerCamera(deviceAddressInput.value);
  if (camera) deviceAddressInput.value = "";
});
refreshButton.addEventListener("click", refreshAll);
autoModeInput.addEventListener("change", () => selectExclusiveMode(autoModeInput));
motionTriggerInput.addEventListener("change", () => selectExclusiveMode(motionTriggerInput));
hybridModeInput.addEventListener("change", () => selectExclusiveMode(hybridModeInput));
startAllButton.addEventListener("click", startAll);
stopAllButton.addEventListener("click", stopAll);
reviewEventsButton.addEventListener("click", () => {
  document.querySelector(".event-review-panel").scrollIntoView({ behavior: "smooth", block: "start" });
});
allImagesTab.addEventListener("click", () => { selectedCollection = "all"; refreshGallery(); });
positiveImagesTab.addEventListener("click", () => { selectedCollection = "positive"; refreshGallery(); });
negativeImagesTab.addEventListener("click", () => { selectedCollection = "negative"; refreshGallery(); });
deleteAllImagesButton.addEventListener("click", deleteAllImages);
trainingStartButton.addEventListener("click", startTraining);
trainingResetButton.addEventListener("click", resetTrainingModel);

async function initialize() {
  updateAutomaticControls();
  renderCameras();
  if (cameras.length === 0 && /^https?:$/.test(window.location.protocol)) {
    await registerCamera(window.location.origin, true);
  }
  await refreshAll();
}

initialize();
window.setInterval(refreshAll, 4000);
