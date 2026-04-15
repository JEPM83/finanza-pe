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
  const res = await fetch('/api/admin/instituciones');
  const data = await res.json();
  const tbody = document.getElementById('tbodyInst');

  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><p>Sin instituciones registradas</p></td></tr>';
    return;
  }

  tbody.innerHTML = data.map(i => `
    <tr>
      <td style="font-weight:500;color:var(--text-bright)">${i.nombre}</td>
      <td style="font-size:.8rem;color:var(--text-dim)">${i.dominios_email || '—'}</td>
      <td>
        <span class="badge ${i.activa ? 'badge-abono' : 'badge-cargo'}">${i.activa ? 'Activa' : 'Inactiva'}</span>
      </td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="abrirModal(${i.id},'${i.nombre.replace(/'/g,"\\'")}','${i.dominios_email.replace(/'/g,"\\'")}')">Editar</button>
        <button class="btn btn-secondary btn-sm" onclick="toggleActiva(${i.id})" style="margin-left:4px">${i.activa ? 'Desactivar' : 'Activar'}</button>
      </td>
    </tr>
  `).join('');
}

function abrirModal(id = null, nombre = '', dominios = '') {
  document.getElementById('editId').value = id || '';
  document.getElementById('fNombre').value = nombre;
  document.getElementById('fDominios').value = dominios;
  document.getElementById('modalTitulo').textContent = id ? 'Editar institución' : 'Nueva institución';
  document.getElementById('modal').classList.remove('hidden');
}

function cerrarModal() {
  document.getElementById('modal').classList.add('hidden');
}

async function guardar() {
  const id = document.getElementById('editId').value;
  const body = {
    nombre: document.getElementById('fNombre').value.trim(),
    dominios_email: document.getElementById('fDominios').value.trim(),
  };
  if (!body.nombre) { toast('El nombre es requerido', 'error'); return; }

  const url = id ? `/api/admin/instituciones/${id}` : '/api/admin/instituciones';
  const method = id ? 'PATCH' : 'POST';

  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (res.ok) {
    toast(id ? 'Institución actualizada' : 'Institución creada', 'success');
    cerrarModal();
    cargar();
  } else {
    toast(data.detail || 'Error al guardar', 'error');
  }
}

async function toggleActiva(id) {
  const res = await fetch(`/api/admin/instituciones/${id}/toggle`, { method: 'PATCH' });
  const data = await res.json();
  if (res.ok) {
    toast(data.activa ? 'Institución activada' : 'Institución desactivada', 'success');
    cargar();
  } else {
    toast('Error al cambiar estado', 'error');
  }
}

cargar();
