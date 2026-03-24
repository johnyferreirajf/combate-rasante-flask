/**
 * COMBATE RASANTE — main.js
 * Responsabilidades: navbar mobile, smooth-scroll, utilitários globais
 */
(function () {
  "use strict";

  /* ── Navbar Mobile ──────────────────────────────────────────── */
  const toggle = document.getElementById("navToggle");
  const menu   = document.getElementById("navMenu");

  if (toggle && menu) {

    function openMenu() {
      menu.classList.add("is-open");
      toggle.setAttribute("aria-expanded", "true");
      toggle.textContent = "✕";
    }

    function closeMenu() {
      menu.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "☰";
    }

    toggle.addEventListener("click", function () {
      menu.classList.contains("is-open") ? closeMenu() : openMenu();
    });

    /* Fecha ao clicar em link dentro do menu */
    menu.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });

    /* Fecha ao clicar fora */
    document.addEventListener("click", function (e) {
      if (!menu.contains(e.target) && !toggle.contains(e.target)) {
        closeMenu();
      }
    });

    /* Fecha ao redimensionar para desktop */
    window.addEventListener("resize", function () {
      if (window.innerWidth > 768) closeMenu();
    });

    /* Fecha com Escape */
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeMenu();
    });
  }

  /* ── Flash auto-dismiss ─────────────────────────────────────── */
  var flashes = document.querySelectorAll(".flash-item");
  if (flashes.length) {
    setTimeout(function () {
      flashes.forEach(function (el) {
        el.style.transition = "opacity 0.4s ease";
        el.style.opacity = "0";
        setTimeout(function () { el.remove(); }, 420);
      });
    }, 5000);
  }

})();
