const tg = window.Telegram?.WebApp;
if (tg) { tg.expand(); tg.ready(); }

const userId = String(tg?.initDataUnsafe?.user?.id || 'anon_' + Date.now());

let currentCookies = '';
let currentData = null;
let currentTokenUrl = '';

const loginView = document.getElementById('loginView');
const dashView = document.getElementById('dashboardView');

const cookiesInput = document.getElementById('cookies');
const btnCheck = document.getElementById('btnCheck');
const accountInfo = document.getElementById('accountInfo');
const qrModal = document.getElementById('qrModal');
const qrContainer = document.getElementById('qrContainer');
const toast = document.getElementById('toast');

function esc(t) {
  if (!t) return '';
  const d = document.createElement('div');
  d.textContent = t;
  return d.innerHTML;
}

function showToast(msg, duration) {
  toast.textContent = msg;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), duration || 2500);
}

async function checkCookies() {
  const input = cookiesInput.value.trim();
  if (!input) { showToast('Pega las cookies primero'); return; }

  btnCheck.disabled = true;
  btnCheck.textContent = 'Verificando...';

  const data = await apiCheck(input);
  btnCheck.disabled = false;
  btnCheck.textContent = 'Ingresar';

  if (data.error) {
    showToast('Error: ' + data.error, 4000);
    return;
  }

  currentCookies = input;
  currentData = data;
  currentTokenUrl = data.token_url || '';

  showDashboard();
}

async function apiCheck(cookies) {
  try {
    const r = await fetch('/api/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookies, user_id: userId }),
    });
    return await r.json();
  } catch {
    return { error: 'Error de conexion con el servidor' };
  }
}

function showDashboard() {
  loginView.classList.add('hidden');
  dashView.classList.remove('hidden');

  const info = currentData.account_info || {};
  const profiles = info.profiles || [];

  let html = '<div class="info-card">';
  html += '<div class="info-row"><span class="il">Email</span><span class="iv">' + esc(info.email || 'N/A') + '</span></div>';
  html += '<div class="info-row"><span class="il">Plan</span><span class="iv">' + esc(info.plan || 'N/A') + '</span></div>';
  html += '<div class="info-row"><span class="il">Pais</span><span class="iv">' + esc(info.country || 'N/A') + '</span></div>';
  const statusBadge = (info.membership_status === 'Active') ? 'badge-ok' : 'badge-warn';
  html += '<div class="info-row"><span class="il">Estado</span><span class="iv"><span class="badge ' + statusBadge + '">' + esc(info.membership_status || 'N/A') + '</span></span></div>';
  if (info.payment_method) {
    html += '<div class="info-row"><span class="il">Pago</span><span class="iv">' + esc(info.payment_method) + '</span></div>';
  }
  if (profiles.length) {
    html += '<div class="info-row"><span class="il">Perfiles (' + profiles.length + ')</span><span class="iv">';
    html += profiles.map(function(p) { return '<span class="pill">' + esc(p) + '</span>'; }).join(' ');
    html += '</span></div>';
  }
  html += '</div>';

  accountInfo.innerHTML = html;
}

function openNetflix() {
  if (!currentTokenUrl) {
    showToast('Generando token...', 3000);
    return;
  }
  if (tg && tg.openLink) {
    tg.openLink(currentTokenUrl);
  } else {
    window.open(currentTokenUrl, '_blank');
  }
}

function openNetflixApp() {
  if (!currentData.android_intent) {
    showToast('Solo disponible en Android', 3000);
    return;
  }
  window.location.href = currentData.android_intent;
}

const COOKIE_EXPORT_KEY = 'nf_cookies_json';

function exportCookies() {
  if (!currentData.cookies_json) {
    showToast('No hay datos de cookies disponibles', 3000);
    return;
  }
  navigator.clipboard.writeText(currentData.cookies_json).then(function() {
    showToast('JSON copiado al portapapeles!', 3000);
  }).catch(function() {
    showToast('No se pudo copiar. Copia manual:', 4000);
    const ta = document.createElement('textarea');
    ta.value = currentData.cookies_json;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  });
}

function showQR() {
  if (!currentData.cookies_json) {
    showToast('Primero verifica las cookies', 3000);
    return;
  }
  qrModal.classList.remove('hidden');
  qrContainer.innerHTML = '<p style="color:#46d369;font-size:14px;word-break:break-all;font-family:monospace;font-size:11px;text-align:left;max-height:300px;overflow:auto;padding:12px;background:#2a2a2a;border-radius:8px;">' + esc(currentData.cookies_json) + '</p>';
  qrContainer.innerHTML += '<button onclick="exportCookies()" class="btn-sec" style="margin-top:12px;font-size:13px;padding:10px">📋 Copiar JSON</button>';
}

function closeQR() {
  qrModal.classList.add('hidden');
}

async function checkAndOpenProxy(btn) {
  var input = cookiesInput.value.trim();
  if (!input) { showToast('Pega las cookies primero'); return; }
  btn.disabled = true;
  btn.textContent = 'Cargando Netflix...';
  try {
    var r = await fetch('/api/proxy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookies: input }),
    });
    var html = await r.text();
    document.open();
    document.write(html);
    document.close();
  } catch(e) {
    showToast('Error: ' + e.message, 4000);
    btn.disabled = false;
    btn.textContent = '🌐 Ingresar y Abrir Netflix';
  }
}

function openProxyView() {
  if (!currentData || !currentData.proxy_url) {
    showToast('Primero pegá las cookies y verificá', 3000);
    return;
  }
  window.location.href = currentData.proxy_url;
}

function goBack() {
  dashView.classList.add('hidden');
  loginView.classList.remove('hidden');
  currentCookies = '';
  currentData = null;
  currentTokenUrl = '';
}

document.getElementById('cookies').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && e.ctrlKey) {
    checkCookies();
  }
});
