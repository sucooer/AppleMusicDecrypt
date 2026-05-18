const stateEls = {
  url: document.querySelector('#url'),
  codec: document.querySelector('#codec'),
  language: document.querySelector('#language'),
  force: document.querySelector('#force'),
  notice: document.querySelector('#notice'),
  taskState: document.querySelector('#task-state'),
  taskDetail: document.querySelector('#task-detail'),
  savedPath: document.querySelector('#saved-path'),
  taskError: document.querySelector('#task-error'),
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
  row.textContent = `[${line.timestamp}] ${line.source.toUpperCase()} ${line.level}: ${line.message}`;
  stateEls.logOutput.prepend(row);
}

function renderTask(snapshot) {
  const nextState = snapshot.state || 'idle';
  stateEls.taskState.textContent = snapshot.state || 'idle';
  stateEls.taskDetail.textContent = snapshot.detail || snapshot.url || '-';
  stateEls.savedPath.textContent = snapshot.saved_path || '-';
  stateEls.taskError.textContent = snapshot.error || '-';

  if (nextState === 'done' && lastTaskState !== 'done') {
    showNotice(`下载完成：${snapshot.saved_path || '文件已保存'}`, 'success');
  } else if (nextState === 'failed' && lastTaskState !== 'failed') {
    showNotice(`下载失败：${snapshot.error || '请查看实时日志'}`, 'error');
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

function attachEvents() {
  document.querySelector('#download-btn').addEventListener('click', () => startDownload().catch((error) => appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'ERROR', message: error.message })));
  document.querySelector('#quality-btn').addEventListener('click', () => lookupQuality().catch((error) => appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'ERROR', message: error.message })));
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
