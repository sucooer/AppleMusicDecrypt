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

const AUTH_STATE_COPY = {
  idle: { label: '未登录', className: 'is-idle' },
  loading: { label: '处理中', className: 'is-starting' },
  success: { label: '登录成功', className: 'is-success' },
  need_2fa: { label: '需要 2FA', className: 'is-need-2fa' },
  failed: { label: '登录失败', className: 'is-failed' },
};

const AUTH_STORAGE_KEY = 'amd.wrapper.username';

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
  authUsername: document.querySelector('#auth-username'),
  authPassword: document.querySelector('#auth-password'),
  authTwoFactor: document.querySelector('#auth-twofa'),
  twoFactorField: document.querySelector('#twofa-field'),
  authPill: document.querySelector('#auth-pill'),
  authSummary: document.querySelector('#auth-summary'),
  authNotice: document.querySelector('#auth-notice'),
  accountPanel: document.querySelector('#account-panel'),
  accountBody: document.querySelector('#account-body'),
  accountToggle: document.querySelector('#account-toggle'),
  accountChevron: document.querySelector('#account-chevron'),
  loginBtn: document.querySelector('#login-btn'),
  logoutBtn: document.querySelector('#logout-btn'),
};

let lastTaskState = 'idle';
let latestSystemStatus = null;
let accountPanelExpanded = false;
let lastAuthForceExpand = false;
const footerEmojis = ['🎵', '🎧', '⚡', '💿'];
let footerEmojiIndex = 0;

function setAccountPanelExpanded(expanded) {
  accountPanelExpanded = expanded;
  stateEls.accountPanel.classList.toggle('is-collapsed', !expanded);
  stateEls.accountToggle.setAttribute('aria-expanded', String(expanded));
  stateEls.accountBody.hidden = !expanded;
  stateEls.accountChevron.textContent = expanded ? '收起' : '展开';
}

function loadStoredUsername() {
  try {
    return window.localStorage.getItem(AUTH_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

function storeUsername(username) {
  try {
    if (username) {
      window.localStorage.setItem(AUTH_STORAGE_KEY, username);
    } else {
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  } catch {
    // Ignore storage failures and continue with in-memory state only.
  }
}

const authState = {
  status: 'idle',
  message: '',
  username: loadStoredUsername(),
  requiresTwoFactor: false,
  busy: false,
};

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

function normalizeSystemStatus(status) {
  return {
    ready: Boolean(status?.ready),
    wrapper_state: status?.wrapper_state || 'unreachable',
    wrapper_message: status?.wrapper_message || '解密服务未连接，页面可访问，但当前无法开始下载。',
    regions: Array.isArray(status?.regions) ? status.regions : [],
    download_speed: status?.download_speed || '0.00 kB/s',
    decrypt_speed: status?.decrypt_speed || '0.00 kB/s',
    active_tasks: Number(status?.active_tasks || 0),
    server_uptime_seconds: Number(status?.server_uptime_seconds || 0),
  };
}

function presentTaskState(snapshot) {
  return TASK_STATE_COPY[snapshot.state] || snapshot.state || TASK_STATE_COPY.idle;
}

function presentWrapperStatus(status) {
  switch (status.wrapper_state) {
    case 'ready':
      return '已连接';
    case 'no_account':
      return '无可用账号';
    case 'degraded':
      return '准备中';
    default:
      return '解密服务未连接';
  }
}

function presentWrapperBanner(status) {
  switch (status.wrapper_state) {
    case 'ready':
      return '';
    case 'no_account':
      return '解密服务可访问，但当前无可用账号，请先登录。';
    case 'degraded':
      return '解密服务已连接，但正在准备可用实例，请稍后再试。';
    default:
      return '解密服务未连接，页面可访问，但当前无法开始下载。';
  }
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

function setNotice(target, message, type = 'info') {
  if (!message) {
    target.hidden = true;
    target.textContent = '';
    target.className = 'notice';
    return;
  }
  target.textContent = message;
  target.className = `notice ${type}`;
  target.hidden = false;
}

function showNotice(message, type = 'info') {
  setNotice(stateEls.notice, message, type);
}

function showAuthNotice(message, type = 'info') {
  setNotice(stateEls.authNotice, message, type);
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

function deriveAuthPresentation(status) {
  const knownUsername = stateEls.authUsername.value.trim() || authState.username;

  if (authState.busy) {
    return {
      pill: { label: '处理中', className: 'is-starting' },
      summary: '正在处理账号请求，请稍候。',
    };
  }

  if (authState.status === 'need_2fa') {
    return {
      pill: AUTH_STATE_COPY.need_2fa,
      summary: authState.message || '请输入两步验证码后再次提交登录。',
    };
  }

  if (authState.status === 'failed') {
    return {
      pill: AUTH_STATE_COPY.failed,
      summary: authState.message || (knownUsername
        ? `账号：${knownUsername}。登录失败，请重试。`
        : '登录失败，请检查日志或重试。'),
    };
  }

  if (authState.status === 'success' && status.wrapper_state !== 'ready') {
    return {
      pill: AUTH_STATE_COPY.success,
      summary: '登录已提交，正在刷新解密服务状态。',
    };
  }

  switch (status.wrapper_state) {
    case 'ready':
      return {
        pill: { label: '已连接', className: 'is-ready' },
        summary: knownUsername
          ? `账号：${knownUsername}。`
          : '已有可用账号。',
      };
    case 'no_account':
      return {
        pill: { label: '待登录', className: 'is-warning' },
        summary: knownUsername
          ? `账号：${knownUsername}。请重新登录或清除账号。`
          : '当前无可用账号，请先登录。',
      };
    case 'degraded':
      return {
        pill: { label: '准备中', className: 'is-degraded' },
        summary: status.wrapper_message,
      };
    default:
      return {
        pill: { label: '服务离线', className: 'is-unreachable' },
        summary: status.wrapper_message,
      };
  }
}

function syncAuthButtons() {
  const username = stateEls.authUsername.value.trim() || authState.username;
  stateEls.loginBtn.disabled = authState.busy;
  stateEls.logoutBtn.disabled = authState.busy || !username;
  stateEls.twoFactorField.hidden = !authState.requiresTwoFactor;
}

function renderAuthPanel(status = latestSystemStatus) {
  if (!status) return;
  const presentation = deriveAuthPresentation(status);
  stateEls.authPill.textContent = presentation.pill.label;
  stateEls.authPill.className = `state-pill ${presentation.pill.className}`;
  stateEls.authSummary.textContent = presentation.summary;
  if (!stateEls.authUsername.value.trim() && authState.username) {
    stateEls.authUsername.value = authState.username;
  }
  const shouldForceExpand = authState.busy || authState.requiresTwoFactor || authState.status === 'failed';
  if (shouldForceExpand && !lastAuthForceExpand) {
    setAccountPanelExpanded(true);
  }
  lastAuthForceExpand = shouldForceExpand;
  syncAuthButtons();
}

function renderSystem(status) {
  latestSystemStatus = normalizeSystemStatus(status);
  stateEls.wmReady.textContent = presentWrapperStatus(latestSystemStatus);
  stateEls.wmRegions.textContent = latestSystemStatus.regions.join(', ') || '暂无可用区域';
  stateEls.downloadSpeed.textContent = latestSystemStatus.download_speed;
  stateEls.decryptSpeed.textContent = latestSystemStatus.decrypt_speed;
  stateEls.activeTasks.textContent = String(latestSystemStatus.active_tasks);
  stateEls.serverUptime.textContent = formatDuration(latestSystemStatus.server_uptime_seconds);

  if (latestSystemStatus.wrapper_state === 'ready') {
    stateEls.wrapperBanner.hidden = true;
  } else {
    stateEls.wrapperBanner.hidden = false;
    stateEls.wrapperBanner.textContent = presentWrapperBanner(latestSystemStatus);
  }

  renderAuthPanel(latestSystemStatus);
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

async function loginAccount() {
  const username = stateEls.authUsername.value.trim();
  const password = stateEls.authPassword.value;
  const twoFactorCode = stateEls.authTwoFactor.value.trim();

  if (!username) {
    showAuthNotice('请输入 Apple Music 用户名。', 'error');
    return;
  }

  authState.busy = true;
  authState.status = 'loading';
  authState.message = '';
  authState.username = username;
  renderAuthPanel();
  showAuthNotice('正在提交登录请求…', 'info');

  try {
    const data = await postJSON('/api/auth/login', {
      username,
      password,
      two_step_code: twoFactorCode || null,
    });

    authState.status = data.status;
    authState.message = data.message || '';

    if (data.status === 'success') {
      authState.requiresTwoFactor = false;
      authState.username = username;
      storeUsername(username);
      stateEls.authPassword.value = '';
      stateEls.authTwoFactor.value = '';
      showAuthNotice('登录成功，正在刷新解密服务状态。', 'success');
      try {
        await refreshStatus();
      } catch (error) {
        showAuthNotice(`登录成功，但状态刷新失败：${normalizeErrorMessage(error)}`, 'warning');
      }
    } else if (data.status === 'need_2fa') {
      authState.requiresTwoFactor = true;
      authState.username = username;
      storeUsername(username);
      showAuthNotice(data.message || '需要两步验证码，请填写后再次提交。', 'warning');
      stateEls.authTwoFactor.focus();
    } else {
      authState.requiresTwoFactor = false;
      authState.username = username;
      storeUsername(username);
      showAuthNotice(data.message || '登录失败，请重试。', 'error');
    }
  } catch (error) {
    authState.status = 'failed';
    authState.message = normalizeErrorMessage(error);
    authState.requiresTwoFactor = false;
    authState.username = username;
    storeUsername(username);
    showAuthNotice(authState.message, 'error');
  } finally {
    authState.busy = false;
    renderAuthPanel();
  }
}

async function logoutAccount() {
  const username = stateEls.authUsername.value.trim() || authState.username;
  if (!username) {
    showAuthNotice('请输入要登出的账号用户名。', 'error');
    return;
  }

  authState.busy = true;
  authState.status = 'loading';
  authState.message = '';
  renderAuthPanel();
  showAuthNotice('正在清除当前账号…', 'info');

  try {
    const data = await postJSON('/api/auth/logout', { username });
    authState.status = data.status === 'success' ? 'idle' : 'failed';
    authState.message = data.message || '';
    authState.requiresTwoFactor = false;

    if (data.status === 'success') {
      authState.username = '';
      storeUsername('');
      stateEls.authUsername.value = '';
      stateEls.authPassword.value = '';
      stateEls.authTwoFactor.value = '';
      showAuthNotice('已清除当前账号，正在刷新解密服务状态。', 'success');
      try {
        await refreshStatus();
      } catch (error) {
        showAuthNotice(`账号已清除，但状态刷新失败：${normalizeErrorMessage(error)}`, 'warning');
      }
    } else {
      showAuthNotice(data.message || '清除账号失败，请重试。', 'error');
    }
  } catch (error) {
    authState.status = 'failed';
    authState.message = normalizeErrorMessage(error);
    showAuthNotice(authState.message, 'error');
  } finally {
    authState.busy = false;
    renderAuthPanel();
  }
}

function attachEvents() {
  stateEls.downloadBtn.addEventListener('click', () => startDownload().catch(showActionError));
  stateEls.retryFailedBtn.addEventListener('click', () => retryFailedTracks().catch(showActionError));
  stateEls.loginBtn.addEventListener('click', () => loginAccount());
  stateEls.logoutBtn.addEventListener('click', () => logoutAccount());
  stateEls.authUsername.addEventListener('input', () => renderAuthPanel());
  stateEls.accountToggle.addEventListener('click', () => setAccountPanelExpanded(!accountPanelExpanded));
}

function connectEvents() {
  const stream = new EventSource('/api/events');
  stream.addEventListener('task.log', (event) => appendLog(JSON.parse(event.data)));
  stream.addEventListener('task.state', (event) => renderTask(JSON.parse(event.data)));
  stream.addEventListener('system.status', (event) => renderSystem(JSON.parse(event.data)));
}

setAccountPanelExpanded(false);
attachEvents();
refreshStatus().catch(showActionError);
connectEvents();
if (document.readyState === 'complete') {
  requestAnimationFrame(renderPageLoadTime);
} else {
  window.addEventListener('load', () => requestAnimationFrame(renderPageLoadTime), { once: true });
}
setInterval(renderFooterEmoji, 2200);
