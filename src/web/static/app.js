const stateEls = {
  url: document.querySelector('#url'),
  codec: document.querySelector('#codec'),
  language: document.querySelector('#language'),
  force: document.querySelector('#force'),
  notice: document.querySelector('#notice'),
  taskState: document.querySelector('#task-state'),
  taskDetail: document.querySelector('#task-detail'),
  albumProgress: document.querySelector('#album-progress'),
  savedPath: document.querySelector('#saved-path'),
  taskError: document.querySelector('#task-error'),
  failedPanel: document.querySelector('#failed-panel'),
  failedTracks: document.querySelector('#failed-tracks'),
  retryFailedBtn: document.querySelector('#retry-failed-btn'),
  wmReady: document.querySelector('#wm-ready'),
  wmRegions: document.querySelector('#wm-regions'),
  downloadSpeed: document.querySelector('#download-speed'),
  decryptSpeed: document.querySelector('#decrypt-speed'),
  activeTasks: document.querySelector('#active-tasks'),
  qualityOutput: document.querySelector('#quality-output'),
  logOutput: document.querySelector('#log-output'),
};

let lastTaskState = 'idle';

function showNotice(message, type = 'info') {
  stateEls.notice.textContent = message;
  stateEls.notice.className = `notice ${type}`;
  stateEls.notice.hidden = false;
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
  stateEls.failedPanel.hidden = failedTracks.length === 0;
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
  stateEls.taskState.textContent = snapshot.state || 'idle';
  stateEls.taskDetail.textContent = snapshot.detail || snapshot.url || '-';
  stateEls.albumProgress.textContent = snapshot.total_tracks
    ? `${snapshot.completed_tracks || 0} / ${snapshot.total_tracks}`
    : '-';
  stateEls.savedPath.textContent = snapshot.saved_path || '-';
  stateEls.taskError.textContent = snapshot.error || '-';
  renderFailedTracks(snapshot);

  if (nextState === 'done' && lastTaskState !== 'done') {
    showNotice(`下载完成：${snapshot.saved_path || '文件已保存'}`, 'success');
  } else if (nextState === 'failed' && lastTaskState !== 'failed') {
    showNotice(`下载失败：${snapshot.error || '请查看实时日志'}`, 'error');
  } else if (nextState === 'retrying' && lastTaskState !== 'retrying') {
    showNotice('正在重试失败歌曲', 'info');
  }

  lastTaskState = nextState;
}

function renderSystem(status) {
  stateEls.wmReady.textContent = String(status.ready);
  stateEls.wmRegions.textContent = (status.regions || []).join(', ') || '-';
  stateEls.downloadSpeed.textContent = status.download_speed;
  stateEls.decryptSpeed.textContent = status.decrypt_speed;
  stateEls.activeTasks.textContent = String(status.active_tasks);
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
  renderSystem(await fetch('/api/system/status').then((res) => res.json()));
  renderTask(await fetch('/api/task/current').then((res) => res.json()));
}

async function startDownload() {
  const data = await postJSON('/api/task/download', {
    url: stateEls.url.value,
    codec: stateEls.codec.value,
    language: stateEls.language.value,
    force: stateEls.force.checked,
  });
  showNotice('下载任务已提交', 'info');
  renderTask(data);
}

async function lookupQuality() {
  const data = await postJSON('/api/task/quality', { url: stateEls.url.value });
  stateEls.qualityOutput.textContent = JSON.stringify(data.items, null, 2);
}

async function retryFailedTracks() {
  const data = await postJSON('/api/task/retry-failed', {});
  showNotice('已提交失败歌曲重试', 'info');
  renderTask(data);
}

function attachEvents() {
  document.querySelector('#download-btn').addEventListener('click', () => startDownload().catch((error) => appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'ERROR', message: error.message })));
  document.querySelector('#quality-btn').addEventListener('click', () => lookupQuality().catch((error) => appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'ERROR', message: error.message })));
  stateEls.retryFailedBtn.addEventListener('click', () => retryFailedTracks().catch((error) => appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'ERROR', message: error.message })));
}

function connectEvents() {
  const stream = new EventSource('/api/events');
  stream.addEventListener('task.log', (event) => appendLog(JSON.parse(event.data)));
  stream.addEventListener('task.state', (event) => renderTask(JSON.parse(event.data)));
  stream.addEventListener('system.status', (event) => renderSystem(JSON.parse(event.data)));
}

attachEvents();
refreshStatus().catch(console.error);
connectEvents();
