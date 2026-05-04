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
      url:   "/atividades",
      bg:    "/static/img/tiles/atividades.png"
    },
    {
      badge: "CLIENTES",
      icon:  "🧑‍🌾",
      title: "CLIENTES",
      desc:  "Atendimento e histórico",
      items: ["Painéis por safra", "Galeria de análises", "Relatórios organizados"],
      url:   "/clientes",
      bg:    "/static/img/tiles/clientes.png"
    },
    {
      badge: "NOVO",
      icon:  "🤝",
      title: "PARCERIAS",
      desc:  "Empresas e produtores",
      items: ["Acordos estratégicos", "Relacionamento", "Resultados compartilhados"],
      url:   "/parcerias",
      bg:    "/static/img/tiles/parceria.png"
    },
    {
      badge: "TIME",
      icon:  "👥",
      title: "EQUIPE",
      desc:  "Gestão e contatos",
      items: ["Responsáveis", "Escalas", "Comunicação interna"],
      url:   "/equipe",
      bg:    "/static/img/tiles/equipe.png"
    },
    {
      badge: "EVENTOS",
      icon:  "📅",
      title: "EVENTOS",
      desc:  "Agenda e novidades",
      items: ["Dias de campo", "Treinamentos", "Atualizações"],
      url:   "/eventos",
      bg:    "/static/img/tiles/eventos.png"
    }
  ];

  /* Tile "Em Campo" — sempre primeiro no carrossel */
  (function () {
    var p = window.ULTIMO_POST;
    TILES.unshift(p ? {
      badge:  "EM CAMPO",
      icon:   "📸",
      title:  p.titulo,
      desc:   p.data,
      foto:   p.foto,   // pode ser foto real ou thumbnail de vídeo Cloudinary
      url:    "/em-campo",
      emcampo: true
    } : {
      badge:  "EM CAMPO",
      icon:   "📸",
      title:  "EM CAMPO",
      desc:   "Acompanhe nossas operações",
      items:  ["Fotos do campo", "Vídeos das aplicações", "Novidades da equipe"],
      url:    "/em-campo",
      emcampo: true
    });
  })();

  /* ── DOM ─────────────────────────────────────────────────── */
  var track    = document.getElementById("streamTrack");
  var dotsWrap = document.getElementById("streamDots");
  var prevBtn  = document.querySelector(".stream-carousel__btn--prev");
  var nextBtn  = document.querySelector(".stream-carousel__btn--next");

  if (!track || !dotsWrap) return;

  /* ── Render das tiles ────────────────────────────────────── */
  track.innerHTML = TILES.map(function (t) {
    if (t.emcampo && t.foto) {
      /* Tile com imagem de fundo — usa aspect-ratio para funcionar no mobile */
      return (
        '<a class="stream-tile stream-tile--foto" href="' + t.url + '">' +
          '<img src="' + t.foto + '" alt="Em Campo" class="stream-tile__foto-bg">' +
          '<div class="stream-tile__foto-overlay"></div>' +
          '<div class="stream-tile__foto-content">' +
            '<span class="stream-tile__badge">' + t.badge + '</span>' +
            '<div>' +
              '<h3 class="stream-tile__title stream-tile__title--foto">' + t.title + '</h3>' +
              '<p class="stream-tile__desc stream-tile__desc--foto">📅 ' + t.desc + '</p>' +
            '</div>' +
          '</div>' +
        '</a>'
      );
    }
    var items = (t.items || []).map(function (i) { return "<li>" + i + "</li>"; }).join("");
    var bgStyle = t.bg ? ' style="background-image:url(' + t.bg + ')"' : '';
    var tileClass = t.bg ? 'stream-tile stream-tile--has-bg' : 'stream-tile';
    return (
      '<a class="' + tileClass + '" href="' + t.url + '"' + bgStyle + '>' +
        (t.bg ? '<div class="stream-tile__bg-overlay"></div>' : '') +
        '<div class="stream-tile__content">' +
          '<div class="stream-tile__top">' +
            '<span class="stream-tile__badge">' + t.badge + '</span>' +
          '</div>' +
          '<div class="stream-tile__icon">' + t.icon + '</div>' +
          '<h3 class="stream-tile__title">' + t.title + '</h3>' +
          '<p class="stream-tile__desc">' + t.desc + '</p>' +
          '<ul class="stream-tile__list">' + items + '</ul>' +
        '</div>' +
      '</a>'
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
