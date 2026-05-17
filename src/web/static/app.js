const stateEls = {
  url: document.querySelector('#url'),
  codec: document.querySelector('#codec'),
  language: document.querySelector('#language'),
  force: document.querySelector('#force'),
  taskState: document.querySelector('#task-state'),
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

function appendLog(line) {
  const row = document.createElement('div');
  row.textContent = `[${line.timestamp}] ${line.source.toUpperCase()} ${line.level}: ${line.message}`;
  stateEls.logOutput.prepend(row);
}

function renderTask(snapshot) {
  stateEls.taskState.textContent = snapshot.state || 'idle';
  stateEls.savedPath.textContent = snapshot.saved_path || '-';
  stateEls.taskError.textContent = snapshot.error || '-';
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
  const data = await response.json();
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
  renderTask(data);
}

async function lookupQuality() {
  const data = await postJSON('/api/task/quality', { url: stateEls.url.value });
  stateEls.qualityOutput.textContent = JSON.stringify(data.items, null, 2);
}

async function login() {
  const username = window.prompt('Apple ID username');
  if (!username) return;
  const password = window.prompt('Password');
  const result = await postJSON('/api/auth/login', { username, password });
  appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'INFO', message: result.message });
  await refreshStatus();
}

async function logout() {
  const username = window.prompt('Apple ID username');
  if (!username) return;
  const result = await postJSON('/api/auth/logout', { username });
  appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'INFO', message: result.message });
  await refreshStatus();
}

function attachEvents() {
  document.querySelector('#download-btn').addEventListener('click', () => startDownload().catch((error) => appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'ERROR', message: error.message })));
  document.querySelector('#quality-btn').addEventListener('click', () => lookupQuality().catch((error) => appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'ERROR', message: error.message })));
  document.querySelector('#login-btn').addEventListener('click', () => login().catch((error) => appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'ERROR', message: error.message })));
  document.querySelector('#logout-btn').addEventListener('click', () => logout().catch((error) => appendLog({ timestamp: new Date().toISOString(), source: 'system', level: 'ERROR', message: error.message })));
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
