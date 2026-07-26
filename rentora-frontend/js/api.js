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

// Keeps each account on its own set of pages - an owner account typing
// in explore.html's URL gets sent back to their dashboard instead of
// seeing the tenant search page, and the same the other way round.
// Call this right after requireAuth() on pages that are role-specific.
function requireRole(expectedRole) {
  const role = getRole();
  if (role && role !== expectedRole) {
    window.location.href = (role === 'owner') ? 'owner.html' : 'explore.html';
  }
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
      localStorage.removeItem('rentora_user_name');
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

// ---- Navbar profile dropdown -----------------------------------------
// Every page has the same "R Rentora ... avatar+name" navbar (see
// .nav-profile in style.css). This fills in the name/initial from
// whatever was saved at login, and handles opening/closing the menu.
// It's self-running so pages don't each need to call it themselves.

function toggleNavProfile() {
  const menu = document.getElementById('navProfileMenu');
  if (menu) menu.classList.toggle('open');
}

function initNavProfile() {
  const nameEl = document.getElementById('navProfileName');
  const menuNameEl = document.getElementById('navProfileMenuName');
  const avatarEl = document.getElementById('navAvatar');
  if (!nameEl && !avatarEl) return; // page doesn't have the profile dropdown

  const name = localStorage.getItem('rentora_user_name') || 'Account';
  const initial = name.trim().charAt(0).toUpperCase() || 'A';

  if (nameEl) nameEl.textContent = name;
  if (menuNameEl) menuNameEl.textContent = name;
  if (avatarEl) avatarEl.textContent = initial;

  // Close the dropdown if the user clicks anywhere outside it.
  document.addEventListener('click', function (e) {
    const profile = document.querySelector('.nav-profile');
    const menu = document.getElementById('navProfileMenu');
    if (!profile || !menu) return;
    if (!profile.contains(e.target)) menu.classList.remove('open');
  });
}

initNavProfile();