/* Transacciones — Finanza PE */
'use strict';

const FMT = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmt = n => FMT.format(n);

let _offset = 0;
const LIMIT  = 100;
let _total   = 0;
let _cats    = [];
let _txActual = null;

function toast(msg, tipo = '') {
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = 'toast ' + tipo;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Inicializar filtros ────────────────────────────────────────────────────
async function inicializar() {
  const [cuentas, cats] = await Promise.all([
    fetch('/api/cuentas/').then(r => r.json()),
    fetch('/api/categorias/').then(r => r.json()),
  ]);
  _cats = cats;

  const fCuenta = document.getElementById('fCuenta');
  cuentas.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = c.nombre;
    fCuenta.appendChild(opt);
  });

  const fCat = document.getElementById('fCategoria');
  cats.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = `${c.icono} ${c.nombre}`;
    fCat.appendChild(opt);
  });

  // Poblar selector modal categoría
  const selCat = document.getElementById('modalCatSelect');
  cats.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = `${c.icono} ${c.nombre}`;
    selCat.appendChild(opt);
  });

  // Aplicar filtros de URL si vienen de otra página (ej: cuenta_id desde /cuentas)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('cuenta_id')) {
    document.getElementById('fCuenta').value = urlParams.get('cuenta_id');
  }

  buscar();
}

// ── Construir URL de query ─────────────────────────────────────────────────
function buildQuery() {
  const params = new URLSearchParams();
  const busqueda  = document.getElementById('fBusqueda').value.trim();
  const cuentaId  = document.getElementById('fCuenta').value;
  const catId     = document.getElementById('fCategoria').value;
  const tipo      = document.getElementById('fTipo').value;
  const desde     = document.getElementById('fDesde').value;
  const hasta     = document.getElementById('fHasta').value;

  if (busqueda)  params.set('busqueda', busqueda);
  if (cuentaId)  params.set('cuenta_id', cuentaId);
  if (catId)     params.set('categoria_id', catId);
  if (tipo)      params.set('tipo', tipo);
  if (desde)     params.set('desde', desde + 'T00:00:00');
  if (hasta)     params.set('hasta', hasta + 'T23:59:59');
  params.set('limit', LIMIT);
  params.set('offset', _offset);
  return params.toString();
}

async function buscar(resetOffset = true) {
  if (resetOffset) _offset = 0;
  const tbody = document.getElementById('tbodyTx');
  tbody.innerHTML = '<tr><td colspan="7"><div class="spinner"></div></td></tr>';

  const res  = await fetch('/api/transacciones/?' + buildQuery());
  const data = await res.json();
  _total = data.total;

  document.getElementById('totalInfo').textContent = `${_total} resultado(s)`;

  if (!data.items.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><p>Sin resultados para los filtros aplicados</p></td></tr>';
    document.getElementById('paginacion').innerHTML = '';
    return;
  }

  tbody.innerHTML = data.items.map(tx => {
    const _d      = new Date(tx.fecha);
    const fecha   = _d.toLocaleDateString('es-PE');
    const hora    = _d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false });
    const desc    = tx.descripcion.length > 45 ? tx.descripcion.slice(0, 45) + '…' : tx.descripcion;
    const comercio = tx.comercio ? `<br><small style="color:var(--text-dim)">${tx.comercio}</small>` : '';
    const catColor = tx.categoria_color || '#aaa';
    const catNom   = tx.categoria_nombre || '—';
    const catIcon  = tx.categoria_icono  || '📦';
    const badgeCls = tx.tipo === 'cargo' ? 'badge-cargo' : 'badge-abono';
    const badgeTxt = tx.tipo === 'cargo' ? 'Cargo' : 'Abono';
    const amtCls   = tx.moneda === 'USD' ? 'amount-usd' : (tx.tipo === 'cargo' ? 'amount-cargo' : 'amount-abono');
    const signo    = tx.tipo === 'cargo' ? '-' : '+';
    const mon      = tx.moneda === 'USD' ? '$' : 'S/';
    return `<tr>
      <td style="font-size:.8rem">
        <span style="color:var(--text)">${fecha}</span><br>
        <span style="color:var(--text-dim)">${hora}</span>
      </td>
      <td>${desc}${comercio}</td>
      <td style="font-size:.82rem;color:var(--text-dim)">${tx.cuenta_nombre || '—'}</td>
      <td>
        <span class="badge-cat" style="background:${catColor}22;color:${catColor};font-size:.72rem;padding:3px 8px;border-radius:20px">
          ${catIcon} ${catNom}
        </span>
      </td>
      <td><span class="badge ${badgeCls}">${badgeTxt}</span></td>
      <td style="text-align:right;white-space:nowrap" class="${amtCls}">${signo}${mon} ${fmt(tx.monto)}</td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="abrirModalCat(${tx.id},'${(tx.descripcion||'').replace(/'/g,"\\'")}',${tx.categoria_id || 'null'})">
          Categ.
        </button>
      </td>
    </tr>`;
  }).join('');

  renderPaginacion();
}

function limpiarFiltros() {
  ['fBusqueda','fCuenta','fCategoria','fTipo','fDesde','fHasta'].forEach(id => {
    document.getElementById(id).value = '';
  });
  buscar();
}

// ── Paginación ─────────────────────────────────────────────────────────────
function renderPaginacion() {
  const total_pages = Math.ceil(_total / LIMIT);
  const current = Math.floor(_offset / LIMIT) + 1;
  const pag = document.getElementById('paginacion');

  if (total_pages <= 1) { pag.innerHTML = ''; return; }

  let html = '';
  if (current > 1) html += `<button class="btn btn-secondary btn-sm" onclick="irPagina(${current-2})">← Anterior</button>`;
  html += `<span class="page-info">Página ${current} de ${total_pages} (${_total} resultados)</span>`;
  if (current < total_pages) html += `<button class="btn btn-secondary btn-sm" onclick="irPagina(${current})">Siguiente →</button>`;
  pag.innerHTML = html;
}

function irPagina(pageIndex) {
  _offset = pageIndex * LIMIT;
  buscar(false);
  window.scrollTo(0, 0);
}

// ── Modal categoría ─────────────────────────────────────────────────────────
function abrirModalCat(txId, desc, catActual) {
  _txActual = txId;
  document.getElementById('modalCatDesc').textContent = desc;
  if (catActual) document.getElementById('modalCatSelect').value = catActual;
  document.getElementById('modalCat').classList.remove('hidden');
}

function cerrarModalCat() {
  document.getElementById('modalCat').classList.add('hidden');
  _txActual = null;
}

async function guardarCategoria() {
  if (!_txActual) return;
  const catId = document.getElementById('modalCatSelect').value;
  const res = await fetch(`/api/transacciones/${_txActual}/categoria?categoria_id=${catId}`, { method: 'PATCH' });
  const data = await res.json();
  if (data.ok) {
    toast('Categoría actualizada', 'success');
    cerrarModalCat();
    buscar(false);
  } else {
    toast(data.error || 'Error al actualizar', 'error');
  }
}

// ── Enter key en búsqueda ───────────────────────────────────────────────────
document.getElementById('fBusqueda').addEventListener('keydown', e => {
  if (e.key === 'Enter') buscar();
});

inicializar();
