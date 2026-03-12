(function () {
  const tiles = [
    {
      badge: "ATIVO",
      icon: "✈",
      title: "ATIVIDADES",
      desc: "Operações em campo",
      items: ["Pulverização de Soja", "Controle de Pragas", "Adubação Foliar"],
      url: "/atividades"
    },
    {
      badge: "CLIENTES",
      icon: "🧑‍🌾",
      title: "CLIENTES",
      desc: "Atendimento e histórico",
      items: ["Painéis por safra", "Galeria de análises", "Relatórios organizados"],
      url: "/clientes"
    },
    {
      badge: "NOVO",
      icon: "🤝",
      title: "PARCERIAS",
      desc: "Empresas e produtores",
      items: ["Acordos estratégicos", "Relacionamento", "Resultados compartilhados"],
      url: "/parcerias"
    },
    {
      badge: "TIME",
      icon: "👥",
      title: "EQUIPE",
      desc: "Gestão e contatos",
      items: ["Responsáveis", "Escalas", "Comunicação interna"],
      url: "/equipe"
    },
    {
      badge: "EVENTOS",
      icon: "📅",
      title: "EVENTOS",
      desc: "Agenda e novidades",
      items: ["Dias de campo", "Treinamentos", "Atualizações"],
      url: "/eventos"
    }
  ];

  const track = document.getElementById("streamTrack");
  const dotsWrap = document.getElementById("streamDots");
  const prevBtn = document.querySelector(".stream-prev");
  const nextBtn = document.querySelector(".stream-next");

  if (!track || !dotsWrap) return;

  track.innerHTML = tiles.map((t) => `
    <a class="stream-tile" href="${t.url}">
      <div class="tile-top">
        <span class="tile-badge">${t.badge}</span>
      </div>

      <div class="tile-icon">${t.icon}</div>

      <h3 class="tile-title">${t.title}</h3>
      <p class="tile-desc">${t.desc}</p>

      <ul class="tile-list">
        ${t.items.map((i) => `<li>${i}</li>`).join("")}
      </ul>
    </a>
  `).join("");

  function getTilesPerView() {
    const w = window.innerWidth;
    if (w <= 768) return 2;
    if (w <= 980) return 2;
    return 3;
  }

  function getPageCount() {
    const per = getTilesPerView();
    return Math.max(1, Math.ceil(tiles.length / per));
  }

  function buildDots() {
    const pages = getPageCount();
    dotsWrap.innerHTML = "";
    for (let i = 0; i < pages; i++) {
      const d = document.createElement("span");
      d.className = "dot" + (i === 0 ? " dot-active" : "");
      d.dataset.page = String(i);
      dotsWrap.appendChild(d);
    }
  }

  function setActiveDot(page) {
    const all = dotsWrap.querySelectorAll(".dot");
    all.forEach((d, idx) => {
      d.classList.toggle("dot-active", idx === page);
    });
  }

  function getStep() {
    const tile = track.querySelector(".stream-tile");
    if (!tile) return track.clientWidth;
    const style = window.getComputedStyle(track);
    const gap = parseFloat(style.columnGap || style.gap || "0") || 0;
    return tile.getBoundingClientRect().width + gap;
  }

  function getCurrentPage() {
    const per = getTilesPerView();
    const step = getStep();
    const page = Math.round(track.scrollLeft / (step * per));
    return Math.max(0, Math.min(getPageCount() - 1, page));
  }

  function goToPage(page) {
    const per = getTilesPerView();
    const step = getStep();
    const max = track.scrollWidth - track.clientWidth;
    const target = Math.max(0, Math.min(max, page * per * step));
    track.scrollTo({ left: target, behavior: "smooth" });
    window.setTimeout(() => setActiveDot(getCurrentPage()), 300);
  }

  function nextPage() {
    const current = getCurrentPage();
    const total = getPageCount();
    goToPage(current >= total - 1 ? 0 : current + 1);
  }

  function prevPage() {
    const current = getCurrentPage();
    const total = getPageCount();
    goToPage(current <= 0 ? total - 1 : current - 1);
  }

  prevBtn?.addEventListener("click", prevPage);
  nextBtn?.addEventListener("click", nextPage);

  dotsWrap.addEventListener("click", (e) => {
    const dot = e.target.closest(".dot");
    if (!dot) return;
    const page = parseInt(dot.dataset.page, 10) || 0;
    goToPage(page);
  });

  let timer = null;

  function startAuto() {
    if (window.innerWidth <= 980) return;
    stopAuto();
    timer = setInterval(nextPage, 5500);
  }

  function stopAuto() {
    if (timer) clearInterval(timer);
    timer = null;
  }

  track.addEventListener("mouseenter", stopAuto);
  track.addEventListener("mouseleave", startAuto);
  track.addEventListener("touchstart", stopAuto, { passive: true });

  let raf = null;
  track.addEventListener("scroll", () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => setActiveDot(getCurrentPage()));
  });

  window.addEventListener("resize", () => {
    buildDots();
    setActiveDot(getCurrentPage());
    if (window.innerWidth <= 980) {
      stopAuto();
    } else {
      startAuto();
    }
  });

  buildDots();
  setActiveDot(0);
  startAuto();
})();
