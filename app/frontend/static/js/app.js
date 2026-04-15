/* app.js — lógica compartida: sidebar responsive + helpers */
'use strict';

// ── Sidebar toggle (mobile) ─────────────────────────────────────────────────
(function () {
  const sidebar  = document.querySelector('.sidebar');
  const overlay  = document.getElementById('sidebarOverlay');
  const btnOpen  = document.getElementById('btnMenuOpen');
  const btnClose = document.getElementById('btnMenuClose');

  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('visible');
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('visible');
  }

  if (btnOpen)  btnOpen.addEventListener('click', openSidebar);
  if (btnClose) btnClose.addEventListener('click', closeSidebar);
  if (overlay)  overlay.addEventListener('click', closeSidebar);

  // Cerrar automáticamente al hacer click en un nav-link (navega a otra página)
  document.querySelectorAll('.nav-link').forEach(a => {
    a.addEventListener('click', closeSidebar);
  });
})();
