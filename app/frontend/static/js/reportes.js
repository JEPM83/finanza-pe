/* Reportes — Finanza PE */
'use strict';

const FMT = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmt = n => FMT.format(n);

const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
               'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

let _chartEv = null;
let _chartCat = null;

// ── Inicializar selectores ─────────────────────────────────────────────────
function inicializar() {
  const hoy   = new Date();
  const anio  = hoy.getFullYear();
  const mesAct = hoy.getMonth(); // 0-indexed

  const selMes  = document.getElementById('selectorMes');
  const selAnio = document.getElementById('selectorAnio');

  MESES.forEach((m, i) => {
    const opt = document.createElement('option');
    opt.value = i + 1;
    opt.textContent = m;
    if (i === mesAct) opt.selected = true;
    selMes.appendChild(opt);
  });

  for (let y = anio; y >= anio - 3; y--) {
    const opt = document.createElement('option');
    opt.value = y;
    opt.textContent = y;
    selAnio.appendChild(opt);
  }

  cargarReporte();
}

async function cargarReporte() {
  const mes  = parseInt(document.getElementById('selectorMes').value);
  const anio = parseInt(document.getElementById('selectorAnio').value);
  const label = `${MESES[mes-1]} ${anio}`;

  document.getElementById('labelCatMes').textContent = label;
  document.getElementById('labelComMes').textContent = label;

  const [evolucion, categorias, comercios] = await Promise.all([
    fetch('/api/reportes/evolucion-mensual?meses=6').then(r => r.json()),
    fetch(`/api/reportes/gastos-por-categoria?anio=${anio}&mes=${mes}`).then(r => r.json()),
    fetch(`/api/reportes/top-comercios?anio=${anio}&mes=${mes}&limite=10`).then(r => r.json()),
  ]);

  renderEvolucion(evolucion);
  renderCategorias(categorias);
  renderComercios(comercios);
}

// ── Gráfico evolución mensual ──────────────────────────────────────────────
function renderEvolucion(data) {
  if (_chartEv) _chartEv.destroy();
  const ctx = document.getElementById('chartEvolucion').getContext('2d');
  _chartEv = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.mes),
      datasets: [
        {
          label: 'Gastos',
          data: data.map(d => d.gastos),
          backgroundColor: 'rgba(217,48,37,.7)',
          borderColor: 'rgba(217,48,37,1)',
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: 'Ingresos',
          data: data.map(d => d.ingresos),
          backgroundColor: 'rgba(30,142,62,.7)',
          borderColor: 'rgba(30,142,62,1)',
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          callbacks: {
            label: ctx => ` S/ ${fmt(ctx.raw)}`,
          },
        },
      },
      scales: {
        y: {
          ticks: {
            callback: v => 'S/ ' + fmt(v),
          },
          beginAtZero: true,
        },
      },
    },
  });
}

// ── Gráfico categorías ─────────────────────────────────────────────────────
function renderCategorias(data) {
  if (_chartCat) _chartCat.destroy();

  if (!data.length) {
    document.getElementById('leyendaCat').innerHTML =
      '<p style="text-align:center;color:var(--text-muted);font-size:.875rem">Sin gastos en el mes seleccionado</p>';
    return;
  }

  const ctx = document.getElementById('chartCategorias').getContext('2d');
  const total = data.reduce((s, c) => s + c.total, 0);
  _chartCat = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.map(c => `${c.icono} ${c.categoria}`),
      datasets: [{
        data: data.map(c => c.total),
        backgroundColor: data.map(c => c.color),
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` S/ ${fmt(ctx.raw)} (${((ctx.raw/total)*100).toFixed(1)}%)`,
          },
        },
      },
    },
  });

  document.getElementById('leyendaCat').innerHTML = data.slice(0, 6).map(c => `
    <div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);font-size:.82rem">
      <span style="display:flex;align-items:center;gap:6px">
        <span style="width:10px;height:10px;border-radius:50%;background:${c.color};flex-shrink:0"></span>
        ${c.icono} ${c.categoria}
      </span>
      <span>
        <strong>S/ ${fmt(c.total)}</strong>
        <span style="color:var(--text-muted);margin-left:4px">${((c.total/total)*100).toFixed(1)}%</span>
      </span>
    </div>`).join('');
}

// ── Tabla top comercios ────────────────────────────────────────────────────
function renderComercios(data) {
  const tbody = document.getElementById('tbodyComercio');
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><p>Sin datos</p></td></tr>';
    return;
  }
  tbody.innerHTML = data.map((c, i) => `
    <tr>
      <td style="color:var(--text-muted);font-weight:700">${i+1}</td>
      <td>${c.comercio}</td>
      <td style="text-align:right" class="amount-cargo">S/ ${fmt(c.total)}</td>
      <td style="text-align:center;color:var(--text-muted)">${c.cantidad}</td>
    </tr>`).join('');
}

inicializar();
