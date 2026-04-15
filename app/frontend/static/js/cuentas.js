/* Cuentas — Finanza PE */
'use strict';

const FMT = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmt = n => FMT.format(n);

const TIPO_LABELS = {
  ahorros:     'Ahorros',
  credito:     'Crédito',
  plazo_fijo:  'Plazo fijo',
  billetera:   'Billetera',
  efectivo:    'Efectivo',
};

async function cargarCuentas() {
  const cuentas = await fetch('/api/cuentas/').then(r => r.json());

  let totalPEN = 0, totalUSD = 0, deudaCrePEN = 0;

  const grid = document.getElementById('accountsGrid');
  if (!cuentas.length) {
    grid.innerHTML = '<div class="empty-state"><p>No hay cuentas activas</p></div>';
    return;
  }

  grid.innerHTML = cuentas.map(c => {
    const balance  = c.balance_calculado;
    const esCred   = c.tipo === 'credito';
    // Para crédito: balance negativo = deuda. Para ahorros: balance positivo = saldo.
    let balanceCls = 'neutral';
    if (esCred) {
      balanceCls = balance < 0 ? 'negative' : 'positive';
    } else {
      balanceCls = balance > 0 ? 'positive' : (balance < 0 ? 'negative' : 'neutral');
    }

    if (c.moneda === 'PEN' && !esCred) totalPEN += balance;
    if (c.moneda === 'USD')             totalUSD += balance;
    if (esCred && c.moneda === 'PEN' && balance < 0) deudaCrePEN += Math.abs(balance);

    const mon = c.moneda === 'USD' ? '$' : 'S/';
    const balLabel = esCred
      ? (balance < 0 ? `Deuda: ${mon} ${fmt(Math.abs(balance))}` : `A favor: ${mon} ${fmt(balance)}`)
      : `${mon} ${fmt(balance)}`;

    return `
    <div class="account-card">
      <div class="bank">${c.institucion || '—'}</div>
      <div class="name">${c.nombre}</div>
      <div class="balance-val ${balanceCls}">${balLabel}</div>
      <div class="meta">
        <span><span class="account-type-badge">${TIPO_LABELS[c.tipo] || c.tipo}</span></span>
        <span>${c.moneda}</span>
        <a href="/transacciones?cuenta_id=${c.id}" style="color:var(--cyan);text-decoration:none;font-weight:600;margin-left:auto">Ver →</a>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:.78rem;color:var(--text-dim)">
        <span>Abonos: ${mon} ${fmt(c.total_abonos)}</span>
        <span>Cargos: ${mon} ${fmt(c.total_cargos)}</span>
      </div>
    </div>`;
  }).join('');

  document.getElementById('totalPEN').textContent  = 'S/ ' + fmt(totalPEN);
  document.getElementById('totalUSD').textContent  = '$ '  + fmt(totalUSD);
  document.getElementById('totalDeuda').textContent = 'S/ ' + fmt(deudaCrePEN);
}

cargarCuentas();
