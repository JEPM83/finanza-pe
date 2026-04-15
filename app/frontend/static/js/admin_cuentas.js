'use strict';

let _instituciones = [];

function toast(msg, tipo = '') {
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = 'toast ' + tipo;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

async function inicializar() {
  const res = await fetch('/api/admin/instituciones');
  _instituciones = await res.json();

  const sel = document.getElementById('fInstitucion');
  _instituciones.forEach(i => {
    const opt = document.createElement('option');
    opt.value = i.id;
    opt.textContent = i.nombre;
    sel.appendChild(opt);
  });

  cargar();
}

async function cargar() {
  const res = await fetch('/api/admin/cuentas');
  const data = await res.json();
  const tbody = document.getElementById('tbodyCuentas');

  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><p>Sin cuentas registradas</p></td></tr>';
    return;
  }

  const tipoLabel = { ahorros: 'Ahorros', credito: 'Crédito', billetera: 'Billetera', plazo_fijo: 'Plazo fijo', efectivo: 'Efectivo' };

  tbody.innerHTML = data.map(c => `
    <tr>
      <td style="font-weight:500;color:var(--text-bright)">${c.nombre}</td>
      <td style="font-size:.82rem">${c.institucion || '—'}</td>
      <td style="font-size:.82rem">${tipoLabel[c.tipo] || c.tipo}</td>
      <td><span class="badge ${c.moneda === 'USD' ? 'badge-abono' : ''}" style="font-size:.72rem">${c.moneda}</span></td>
      <td><span class="badge ${c.activa ? 'badge-abono' : 'badge-cargo'}">${c.activa ? 'Activa' : 'Inactiva'}</span></td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick='abrirModal(${JSON.stringify(c)})'>Editar</button>
        <button class="btn btn-secondary btn-sm" onclick="toggleActiva(${c.id})" style="margin-left:4px">${c.activa ? 'Desactivar' : 'Activar'}</button>
      </td>
    </tr>
  `).join('');
}

function abrirModal(c = null) {
  document.getElementById('editId').value = c ? c.id : '';
  document.getElementById('fNombre').value = c ? c.nombre : '';
  document.getElementById('fInstitucion').value = c ? c.institucion_id : (_instituciones[0]?.id || '');
  document.getElementById('fTipo').value = c ? c.tipo : 'ahorros';
  document.getElementById('fMoneda').value = c ? c.moneda : 'PEN';
  document.getElementById('fNumero').value = c ? c.numero_cuenta : '';
  document.getElementById('modalTitulo').textContent = c ? 'Editar cuenta' : 'Nueva cuenta';
  document.getElementById('modal').classList.remove('hidden');
}

function cerrarModal() {
  document.getElementById('modal').classList.add('hidden');
}

async function guardar() {
  const id = document.getElementById('editId').value;
  const body = {
    nombre: document.getElementById('fNombre').value.trim(),
    institucion_id: parseInt(document.getElementById('fInstitucion').value),
    tipo: document.getElementById('fTipo').value,
    moneda: document.getElementById('fMoneda').value,
    numero_cuenta: document.getElementById('fNumero').value.trim(),
  };
  if (!body.nombre) { toast('El nombre es requerido', 'error'); return; }

  const url = id ? `/api/admin/cuentas/${id}` : '/api/admin/cuentas';
  const method = id ? 'PATCH' : 'POST';

  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (res.ok) {
    toast(id ? 'Cuenta actualizada' : 'Cuenta creada', 'success');
    cerrarModal();
    cargar();
  } else {
    toast(data.detail || 'Error al guardar', 'error');
  }
}

async function toggleActiva(id) {
  const res = await fetch(`/api/admin/cuentas/${id}/toggle`, { method: 'PATCH' });
  const data = await res.json();
  if (res.ok) {
    toast(data.activa ? 'Cuenta activada' : 'Cuenta desactivada', 'success');
    cargar();
  } else {
    toast('Error al cambiar estado', 'error');
  }
}

inicializar();
