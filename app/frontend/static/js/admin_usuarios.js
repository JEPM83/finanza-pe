'use strict';

function toast(msg, tipo = '') {
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = 'toast ' + tipo;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

async function cargar() {
  const res = await fetch('/api/admin/usuarios');
  const data = await res.json();
  const tbody = document.getElementById('tbodyUsuarios');

  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><p>Sin usuarios registrados</p></td></tr>';
    return;
  }

  tbody.innerHTML = data.map(u => `
    <tr>
      <td style="font-weight:500;color:var(--cyan)">${u.username}</td>
      <td><span class="badge ${u.activo ? 'badge-abono' : 'badge-cargo'}">${u.activo ? 'Activo' : 'Inactivo'}</span></td>
      <td style="font-size:.8rem;color:var(--text-dim)">${u.creado_en}</td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="abrirModalPass(${u.id},'${u.username}')">Reset clave</button>
        <button class="btn btn-secondary btn-sm" onclick="toggleActivo(${u.id})" style="margin-left:4px">${u.activo ? 'Desactivar' : 'Activar'}</button>
      </td>
    </tr>
  `).join('');
}

// ── Modal nuevo usuario ───────────────────────────────
function abrirModalNuevo() {
  document.getElementById('fUsername').value = '';
  document.getElementById('fPassword').value = '';
  document.getElementById('modalNuevo').classList.remove('hidden');
}

function cerrarModalNuevo() {
  document.getElementById('modalNuevo').classList.add('hidden');
}

async function crearUsuario() {
  const body = {
    username: document.getElementById('fUsername').value.trim(),
    password: document.getElementById('fPassword').value,
  };
  if (!body.username || !body.password) { toast('Completa todos los campos', 'error'); return; }

  const res = await fetch('/api/admin/usuarios', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (res.ok) {
    toast('Usuario creado', 'success');
    cerrarModalNuevo();
    cargar();
  } else {
    toast(data.detail || 'Error al crear usuario', 'error');
  }
}

// ── Modal reset password ──────────────────────────────
function abrirModalPass(id, username) {
  document.getElementById('passUserId').value = id;
  document.getElementById('passUsername').textContent = username;
  document.getElementById('fNewPass').value = '';
  document.getElementById('modalPass').classList.remove('hidden');
}

function cerrarModalPass() {
  document.getElementById('modalPass').classList.add('hidden');
}

async function resetearPass() {
  const id = document.getElementById('passUserId').value;
  const password = document.getElementById('fNewPass').value;
  if (!password) { toast('Ingresa la nueva contraseña', 'error'); return; }

  const res = await fetch(`/api/admin/usuarios/${id}/password`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  const data = await res.json();

  if (res.ok) {
    toast('Contraseña actualizada', 'success');
    cerrarModalPass();
  } else {
    toast(data.detail || 'Error al actualizar', 'error');
  }
}

// ── Toggle activo ─────────────────────────────────────
async function toggleActivo(id) {
  const res = await fetch(`/api/admin/usuarios/${id}/toggle`, { method: 'PATCH' });
  const data = await res.json();
  if (res.ok) {
    toast(data.activo ? 'Usuario activado' : 'Usuario desactivado', 'success');
    cargar();
  } else {
    toast('Error al cambiar estado', 'error');
  }
}

cargar();
