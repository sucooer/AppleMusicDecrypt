const TASK_STATE_COPY = {
  idle: '当前没有活动任务',
  starting: '准备中',
  fetching: '正在获取信息',
  downloading: '正在下载',
  decrypting: '正在解密',
  saving: '正在保存',
  retrying: '正在重试',
  done: '已完成',
  failed: '已失败',
};

const stateEls = {
  url: document.querySelector('#url'),
  force: document.querySelector('#force'),
  notice: document.querySelector('#notice'),
  wrapperBanner: document.querySelector('#wrapper-banner'),
  taskState: document.querySelector('#task-state'),
  taskDetail: document.querySelector('#task-detail'),
  albumProgress: document.querySelector('#album-progress'),
  savedPath: document.querySelector('#saved-path'),
  failedPanel: document.querySelector('#failed-panel'),
  failedTracks: document.querySelector('#failed-tracks'),
  retryFailedBtn: document.querySelector('#retry-failed-btn'),
  wmReady: document.querySelector('#wm-ready'),
  wmRegions: document.querySelector('#wm-regions'),
  downloadSpeed: document.querySelector('#download-speed'),
  decryptSpeed: document.querySelector('#decrypt-speed'),
  activeTasks: document.querySelector('#active-tasks'),
  footerEmoji: document.querySelector('#footer-emoji'),
  pageLoadTime: document.querySelector('#page-load-time'),
  serverUptime: document.querySelector('#server-uptime'),
  logOutput: document.querySelector('#log-output'),
  downloadBtn: document.querySelector('#download-btn'),
};

let lastTaskState = 'idle';
const footerEmojis = ['🎵', '🎧', '⚡', '💿'];
let footerEmojiIndex = 0;

function idleTaskSnapshot() {
  return {
    state: 'idle',
    detail: null,
    saved_path: null,
    error: null,
    total_tracks: 0,
    completed_tracks: 0,
    failed_tracks: [],
  };
}

function initialTaskSnapshot(snapshot) {
  if (snapshot && snapshot.state === 'done') {
    return idleTaskSnapshot();
  }
  return snapshot;
}

function presentTaskState(snapshot) {
  return TASK_STATE_COPY[snapshot.state] || snapshot.state || TASK_STATE_COPY.idle;
}

function presentWrapperStatus(status) {
  return status.ready ? '已连接' : '解密服务未连接';
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;

  if (days) return `${days}天 ${hours}小时`;
  if (hours) return `${hours}小时 ${minutes}分`;
  if (minutes) return `${minutes}分 ${secs}秒`;
  return `${secs}秒`;
}

function renderPageLoadTime() {
  const navigation = performance.getEntriesByType('navigation')[0];
  const timing = performance.timing;
  const modernLoadMs = navigation && navigation.responseEnd > navigation.requestStart
    ? navigation.responseEnd - navigation.requestStart
    : 0;
  const legacyLoadMs = timing && timing.responseEnd && timing.requestStart
    ? timing.responseEnd - timing.requestStart
    : 0;
  const loadMs = modernLoadMs || legacyLoadMs || performance.now();
  stateEls.pageLoadTime.textContent = `${Math.max(1, Math.round(loadMs))}ms`;
}

function renderFooterEmoji() {
  footerEmojiIndex = (footerEmojiIndex + 1) % footerEmojis.length;
  stateEls.footerEmoji.textContent = footerEmojis[footerEmojiIndex];
}

function normalizeErrorMessage(error) {
  if (error instanceof Error && typeof error.message === 'string') {
    if (error.message && error.message !== '[object Object]') return error.message;
  }

  if (typeof error === 'string' && error.trim()) {
    return error;
  }

  if (error && typeof error === 'object') {
    if (typeof error.detail === 'string' && error.detail.trim()) {
      return error.detail;
    }
    if (typeof error.message === 'string' && error.message.trim() && error.message !== '[object Object]') {
      return error.message;
    }
    try {
      const serialized = JSON.stringify(error);
      if (serialized && serialized !== '{}') return serialized;
    } catch {
      // Ignore JSON serialization failures and fall through to the default message.
    }
  }

  return '发生未知错误，请查看实时日志。';
}

function showNotice(message, type = 'info') {
  stateEls.notice.textContent = message;
  stateEls.notice.className = `notice ${type}`;
  stateEls.notice.hidden = false;
}

function showActionError(error) {
  const message = normalizeErrorMessage(error);
  showNotice(message, 'error');
  appendLog({
    timestamp: new Date().toISOString(),
    source: 'system',
    level: 'ERROR',
    message,
  });
}

function appendLog(line) {
  const row = document.createElement('div');
  const label = line.item_name ? ` ${line.item_name}` : '';
  row.textContent = `[${line.timestamp}] ${line.source.toUpperCase()}${label} ${line.level}: ${line.message}`;
  stateEls.logOutput.prepend(row);
}

function renderFailedTracks(snapshot) {
  const failedTracks = snapshot.failed_tracks || [];
  stateEls.failedTracks.replaceChildren();
  stateEls.failedPanel.hidden = false;
  stateEls.retryFailedBtn.disabled = failedTracks.length === 0 || snapshot.state === 'retrying';

  for (const track of failedTracks) {
    const item = document.createElement('li');
    const title = document.createElement('strong');
    const error = document.createElement('span');
    title.textContent = track.title || track.id || '未知歌曲';
    error.textContent = track.error || '未知错误';
    item.append(title, error);
    stateEls.failedTracks.append(item);
  }
}

function renderTask(snapshot) {
  const nextState = snapshot.state || 'idle';
  const stateCopy = presentTaskState(snapshot);

  stateEls.taskState.textContent = stateCopy;
  stateEls.taskDetail.textContent = snapshot.detail || snapshot.url || '等待新的下载任务';
  stateEls.albumProgress.textContent = snapshot.total_tracks
    ? `${snapshot.completed_tracks || 0} / ${snapshot.total_tracks}`
    : '—';
  stateEls.savedPath.textContent = snapshot.saved_path || '下载完成后会显示';
  renderFailedTracks(snapshot);

  if (nextState === 'failed' && lastTaskState !== 'failed') {
    showNotice(`下载失败：${snapshot.error || '请查看实时日志'}`, 'error');
  } else if (nextState === 'retrying' && lastTaskState !== 'retrying') {
    showNotice('正在重试失败歌曲', 'info');
  }

  lastTaskState = nextState;
}

function renderSystem(status) {
  stateEls.wmReady.textContent = presentWrapperStatus(status);
  stateEls.wmRegions.textContent = (status.regions || []).join(', ') || '暂无可用区域';
  stateEls.downloadSpeed.textContent = status.download_speed;
  stateEls.decryptSpeed.textContent = status.decrypt_speed;
  stateEls.activeTasks.textContent = String(status.active_tasks);
  stateEls.serverUptime.textContent = formatDuration(status.server_uptime_seconds);

  if (status.ready) {
    stateEls.wrapperBanner.hidden = true;
  } else {
    stateEls.wrapperBanner.hidden = false;
    stateEls.wrapperBanner.textContent = '解密服务未连接，页面可访问，但当前无法开始下载。';
  }
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`请求失败 (${response.status})`);
  }
  if (!response.ok) throw new Error(data.detail || data.message || 'Request failed');
  return data;
}

async function refreshStatus() {
  const [systemStatus, taskStatus] = await Promise.all([
    fetch('/api/system/status').then((res) => res.json()),
    fetch('/api/task/current').then((res) => res.json()),
  ]);
  renderSystem(systemStatus);
  renderTask(initialTaskSnapshot(taskStatus));
}

async function startDownload() {
  stateEls.downloadBtn.disabled = true;
  stateEls.downloadBtn.textContent = '正在提交…';
  try {
    const data = await postJSON('/api/task/download', {
      url: stateEls.url.value,
      force: stateEls.force.checked,
    });
    showNotice('下载任务已提交', 'info');
    renderTask(data);
  } finally {
    stateEls.downloadBtn.disabled = false;
    stateEls.downloadBtn.textContent = '下载';
  }
}

async function retryFailedTracks() {
  const data = await postJSON('/api/task/retry-failed', {});
  showNotice('已提交失败歌曲重试', 'info');
  renderTask(data);
}

function attachEvents() {
  stateEls.downloadBtn.addEventListener('click', () => startDownload().catch(showActionError));
  stateEls.retryFailedBtn.addEventListener('click', () => retryFailedTracks().catch(showActionError));
}

function connectEvents() {
  const stream = new EventSource('/api/events');
  stream.addEventListener('task.log', (event) => appendLog(JSON.parse(event.data)));
  stream.addEventListener('task.state', (event) => renderTask(JSON.parse(event.data)));
  stream.addEventListener('system.status', (event) => renderSystem(JSON.parse(event.data)));
}

attachEvents();
refreshStatus().catch(showActionError);
connectEvents();
if (document.readyState === 'complete') {
  requestAnimationFrame(renderPageLoadTime);
} else {
  window.addEventListener('load', () => requestAnimationFrame(renderPageLoadTime), { once: true });
}
setInterval(renderFooterEmoji, 2200);
