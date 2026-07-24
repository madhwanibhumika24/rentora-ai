const API_BASE = "http://localhost:8000";

function getToken() {
  return localStorage.getItem('rentora_token');
}

function getRole() {
  return localStorage.getItem('rentora_role');
}

function requireAuth() {
  const token = getToken();
  if (!token) {
    window.location.href = 'login.html';
  }
  return token;
}

// A small styled "are you sure?" box, used instead of the browser's plain
// confirm() popup so it matches the rest of the app. onConfirm only runs
// if the user actually clicks the confirm button.
function showConfirm(title, subText, confirmLabel, onConfirm) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML =
    '<div class="modal-box">' +
    '<p class="modal-title">' + title + '</p>' +
    '<p class="modal-sub">' + subText + '</p>' +
    '<div class="modal-actions">' +
    '<button class="btn-secondary btn-small" id="modalCancelBtn">Cancel</button>' +
    '<button class="btn-primary" style="width:auto;padding:9px 18px" id="modalConfirmBtn">' + confirmLabel + '</button>' +
    '</div>' +
    '</div>';
  document.body.appendChild(overlay);

  // Clicking the dark background also cancels, like most real dialogs.
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) {
      overlay.remove();
    }
  });

  document.getElementById('modalCancelBtn').addEventListener('click', function () {
    overlay.remove();
  });

  document.getElementById('modalConfirmBtn').addEventListener('click', function () {
    overlay.remove();
    onConfirm();
  });
}

function logout() {
  showConfirm(
    'Log out of Rentora?',
    'You will need to sign in again to access your account.',
    'Log out',
    function () {
      localStorage.removeItem('rentora_token');
      localStorage.removeItem('rentora_role');
      localStorage.removeItem('rentora_user_id');
      window.location.href = 'login.html';
    }
  );
}

// If the server rejected the request, FastAPI usually sends back
// { "detail": "some readable message" }. This pulls that message out so
// pages can show the real reason instead of just "Request failed: 400".
async function readErrorMessage(res) {
  const body = await res.json().catch(function () { return {}; });
  return body.detail || ("Request failed: " + res.status);
}

async function apiGet(path, token) {
  const res = await fetch(API_BASE + path, {
    headers: token ? { Authorization: "Bearer " + token } : {},
  });
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return res.json();
}

async function apiPost(path, body, token) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return res.json();
}

async function apiPatch(path, body, token) {
  const res = await fetch(API_BASE + path, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return res.json();
}

async function apiDelete(path, token) {
  const res = await fetch(API_BASE + path, {
    method: "DELETE",
    headers: token ? { Authorization: "Bearer " + token } : {},
  });
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return res.json();
}