/* Dashboard — Finanza PE */
'use strict';

const FMT = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmt = n => FMT.format(n);

function toast(msg, tipo = '') {
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = 'toast ' + tipo;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Modal efectivo ──────────────────────────────────────────────────────────
let _cats = [];

async function abrirModalEfectivo() {
  if (!_cats.length) {
    const res = await fetch('/api/categorias/');
    _cats = await res.json();
    const sel = document.getElementById('efectivoCat');
    sel.innerHTML = _cats.map(c => `<option value="${c.nombre}">${c.icono} ${c.nombre}</option>`).join('');
  }
  document.getElementById('modalEfectivo').classList.remove('hidden');
}

function cerrarModal() {
  document.getElementById('modalEfectivo').classList.add('hidden');
}

async function guardarEfectivo() {
  const tipo   = document.getElementById('efectivoTipo').value;
  const monto  = parseFloat(document.getElementById('efectivoMonto').value);
  const desc   = document.getElementById('efectivoDesc').value.trim();
  const catNom = document.getElementById('efectivoCat').value;

  if (!desc || !monto || monto <= 0) {
    toast('Completa todos los campos', 'error');
    return;
  }

  const params = new URLSearchParams({ tipo, monto, descripcion: desc, categoria_nombre: catNom });
  const res = await fetch('/api/transacciones/efectivo?' + params, { method: 'POST' });
  const data = await res.json();

  if (data.error) {
    toast(data.error, 'error');
    return;
  }

  toast('Transacción registrada', 'success');
  cerrarModal();
  document.getElementById('efectivoMonto').value = '';
  document.getElementById('efectivoDesc').value = '';
  cargarDashboard();
}

// ── Dashboard data ──────────────────────────────────────────────────────────
let _chartCat = null;

async function cargarDashboard() {
  const hoy  = new Date();
  const anio = hoy.getFullYear();
  const mes  = hoy.getMonth() + 1;

  const meses_es = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                    'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
  document.getElementById('statMes').textContent    = `${meses_es[mes-1]} ${anio}`;
  document.getElementById('mesLabel').textContent   = `${meses_es[mes-1]} ${anio}`;

  const [resumen, categorias, recientes] = await Promise.all([
    fetch(`/api/reportes/resumen-mes?anio=${anio}&mes=${mes}`).then(r => r.json()),
    fetch(`/api/reportes/gastos-por-categoria?anio=${anio}&mes=${mes}`).then(r => r.json()),
    fetch('/api/transacciones/recientes?limite=10').then(r => r.json()),
  ]);

  // Stats
  let gastosPEN = 0, gastosCnt = 0, ingresosPEN = 0, ingresosCnt = 0;
  for (const r of resumen) {
    if (r.moneda === 'PEN' && r.tipo === 'cargo')  { gastosPEN  = r.total; gastosCnt  = r.cantidad; }
    if (r.moneda === 'PEN' && r.tipo === 'abono')  { ingresosPEN = r.total; ingresosCnt = r.cantidad; }
  }
  const balancePEN = ingresosPEN - gastosPEN;

  document.getElementById('statGastos').textContent    = 'S/ ' + fmt(gastosPEN);
  document.getElementById('statGastosCnt').textContent = `${gastosCnt} transacciones`;
  document.getElementById('statIngresos').textContent  = 'S/ ' + fmt(ingresosPEN);
  document.getElementById('statIngresosCnt').textContent = `${ingresosCnt} transacciones`;
  document.getElementById('statBalance').textContent   = (balancePEN >= 0 ? 'S/ ' : '-S/ ') + fmt(Math.abs(balancePEN));
  document.getElementById('statBalance').style.color   = balancePEN >= 0 ? 'var(--income)' : 'var(--expense)';
  document.getElementById('statTotal').textContent     = gastosCnt + ingresosCnt;

  // Donut chart
  if (categorias.length) {
    const labels = categorias.map(c => `${c.icono} ${c.categoria}`);
    const data   = categorias.map(c => c.total);
    const colors = categorias.map(c => c.color);

    if (_chartCat) _chartCat.destroy();
    const ctx = document.getElementById('chartCategoria').getContext('2d');
    _chartCat = new Chart(ctx, {
      type: 'doughnut',
      data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 1, borderColor: '#0b0b18' }] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#10102a',
            borderColor: '#00f5ff',
            borderWidth: 1,
            titleColor: '#00f5ff',
            bodyColor: '#b8cce0',
            callbacks: {
              label: ctx => ` S/ ${fmt(ctx.raw)} (${((ctx.raw / data.reduce((a,b)=>a+b,0))*100).toFixed(1)}%)`,
            },
          },
        },
      },
    });

    // Leyenda manual
    const top5 = categorias.slice(0, 5);
    document.getElementById('leyendaCategoria').innerHTML = top5
      .map(c => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);font-size:.82rem">
          <span style="display:flex;align-items:center;gap:6px">
            <span style="width:10px;height:10px;border-radius:50%;background:${c.color};flex-shrink:0"></span>
            ${c.icono} ${c.categoria}
          </span>
          <strong>S/ ${fmt(c.total)}</strong>
        </div>`)
      .join('');
  } else {
    document.getElementById('leyendaCategoria').innerHTML =
      '<p style="font-size:.8rem;color:var(--text-dim);text-align:center">Sin gastos este mes</p>';
  }

  // Tabla recientes
  const tbody = document.getElementById('tbodyRecientes');
  if (!recientes.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><p>Sin transacciones recientes</p></td></tr>';
    return;
  }
  tbody.innerHTML = recientes.map(tx => {
    const fecha = tx.fecha.slice(0, 10);
    const desc  = tx.comercio || tx.descripcion.slice(0, 40);
    const cls   = tx.tipo === 'cargo' ? 'amount-cargo' : 'amount-abono';
    const signo = tx.tipo === 'cargo' ? '-' : '+';
    const mon   = tx.moneda === 'USD' ? '$' : 'S/';
    return `<tr>
      <td style="color:var(--cyan-dim);font-size:.8rem">${fecha}</td>
      <td title="${tx.descripcion}">${desc}</td>
      <td style="font-size:.8rem;color:var(--text-dim)">${tx.cuenta_nombre || '—'}</td>
      <td style="text-align:right" class="${cls}">${signo}${mon} ${fmt(tx.monto)}</td>
    </tr>`;
  }).join('');
}

cargarDashboard();
