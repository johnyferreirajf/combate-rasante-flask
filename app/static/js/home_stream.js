/**
 * COMBATE RASANTE — home_stream.js
 * Carrossel da Central de Atividades
 * Padrão: IIFE, sem dependências externas
 */
(function () {
  "use strict";

  /* ── Dados das tiles ─────────────────────────────────────── */
  var TILES = [
    {
      badge: "ATIVO",
      icon:  "✈",
      title: "ATIVIDADES",
      desc:  "Operações em campo",
      items: ["Pulverização de Soja", "Controle de Pragas", "Adubação Foliar"],
      url:   "/atividades"
    },
    {
      badge: "CLIENTES",
      icon:  "🧑‍🌾",
      title: "CLIENTES",
      desc:  "Atendimento e histórico",
      items: ["Painéis por safra", "Galeria de análises", "Relatórios organizados"],
      url:   "/clientes"
    },
    {
      badge: "NOVO",
      icon:  "🤝",
      title: "PARCERIAS",
      desc:  "Empresas e produtores",
      items: ["Acordos estratégicos", "Relacionamento", "Resultados compartilhados"],
      url:   "/parcerias"
    },
    {
      badge: "TIME",
      icon:  "👥",
      title: "EQUIPE",
      desc:  "Gestão e contatos",
      items: ["Responsáveis", "Escalas", "Comunicação interna"],
      url:   "/equipe"
    },
    {
      badge: "EVENTOS",
      icon:  "📅",
      title: "EVENTOS",
      desc:  "Agenda e novidades",
      items: ["Dias de campo", "Treinamentos", "Atualizações"],
      url:   "/eventos"
    }
  ];

  /* ── DOM ─────────────────────────────────────────────────── */
  var track    = document.getElementById("streamTrack");
  var dotsWrap = document.getElementById("streamDots");
  var prevBtn  = document.querySelector(".stream-carousel__btn--prev");
  var nextBtn  = document.querySelector(".stream-carousel__btn--next");

  if (!track || !dotsWrap) return;

  /* ── Render das tiles ────────────────────────────────────── */
  track.innerHTML = TILES.map(function (t) {
    var items = t.items.map(function (i) { return "<li>" + i + "</li>"; }).join("");
    return (
      '<a class="stream-tile" href="' + t.url + '">' +
        '<div class="stream-tile__top">' +
          '<span class="stream-tile__badge">' + t.badge + "</span>" +
        "</div>" +
        '<div class="stream-tile__icon">' + t.icon + "</div>" +
        '<h3 class="stream-tile__title">' + t.title + "</h3>" +
        '<p class="stream-tile__desc">' + t.desc + "</p>" +
        '<ul class="stream-tile__list">' + items + "</ul>" +
      "</a>"
    );
  }).join("");

  /* ── Helpers ─────────────────────────────────────────────── */
  function tilesPerView() {
    var w = window.innerWidth;
    if (w <= 768) return 1;
    if (w <= 980) return 2;
    return 3;
  }

  function pageCount() {
    return Math.max(1, Math.ceil(TILES.length / tilesPerView()));
  }

  function stepWidth() {
    var tile = track.querySelector(".stream-tile");
    if (!tile) return track.clientWidth;
    var gap = parseFloat(window.getComputedStyle(track).gap) || 14;
    return tile.getBoundingClientRect().width + gap;
  }

  function currentPage() {
    var perView = tilesPerView();
    var page = Math.round(track.scrollLeft / (stepWidth() * perView));
    return Math.max(0, Math.min(pageCount() - 1, page));
  }

  function goToPage(page) {
    var perView = tilesPerView();
    var step    = stepWidth();
    var max     = track.scrollWidth - track.clientWidth;
    var left    = Math.max(0, Math.min(max, page * perView * step));
    track.scrollTo({ left: left, behavior: "smooth" });
    setTimeout(function () { setActiveDot(currentPage()); }, 320);
  }

  /* ── Dots ────────────────────────────────────────────────── */
  function buildDots() {
    var pages = pageCount();
    dotsWrap.innerHTML = "";
    for (var i = 0; i < pages; i++) {
      var dot = document.createElement("span");
      dot.className = "stream-dot" + (i === 0 ? " stream-dot--active" : "");
      dot.dataset.page = String(i);
      dotsWrap.appendChild(dot);
    }
  }

  function setActiveDot(page) {
    dotsWrap.querySelectorAll(".stream-dot").forEach(function (d, idx) {
      d.classList.toggle("stream-dot--active", idx === page);
    });
  }

  dotsWrap.addEventListener("click", function (e) {
    var dot = e.target.closest(".stream-dot");
    if (!dot) return;
    goToPage(parseInt(dot.dataset.page, 10) || 0);
  });

  /* ── Setas ───────────────────────────────────────────────── */
  prevBtn && prevBtn.addEventListener("click", function () {
    var p = currentPage();
    goToPage(p <= 0 ? pageCount() - 1 : p - 1);
  });

  nextBtn && nextBtn.addEventListener("click", function () {
    var p = currentPage();
    goToPage(p >= pageCount() - 1 ? 0 : p + 1);
  });

  /* ── Scroll sync ─────────────────────────────────────────── */
  var raf = null;
  track.addEventListener("scroll", function () {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(function () { setActiveDot(currentPage()); });
  });

  /* ── Auto-play (desktop apenas) ─────────────────────────── */
  var timer = null;

  function startAuto() {
    if (window.innerWidth <= 980) return;
    stopAuto();
    timer = setInterval(function () {
      var p = currentPage();
      goToPage(p >= pageCount() - 1 ? 0 : p + 1);
    }, 5500);
  }

  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  track.addEventListener("mouseenter", stopAuto);
  track.addEventListener("mouseleave", startAuto);
  track.addEventListener("touchstart", stopAuto, { passive: true });

  /* ── Resize ──────────────────────────────────────────────── */
  window.addEventListener("resize", function () {
    buildDots();
    setActiveDot(currentPage());
    window.innerWidth <= 980 ? stopAuto() : startAuto();
  });

  /* ── Init ────────────────────────────────────────────────── */
  buildDots();
  setActiveDot(0);
  startAuto();

})();
