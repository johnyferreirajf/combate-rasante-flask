/**
 * COMBATE RASANTE — Piloto Bot
 * Visitantes: menu interativo por balões
 * Autenticados: chat livre com IA
 */
(function () {
  "use strict";

  var IS_AUTH = document.body.dataset.crAuth === "1";
  var AVATAR  = "/static/img/weikren-avatar.png";
  var VIDEO   = "/static/video/weikren-bot.mp4";

  /* ── Conteúdo do menu de visitantes ── */
  var MENU_PRINCIPAL = [
    { id: "sobre",        label: "🏢 Sobre a Combate Rasante" },
    { id: "agricultura",  label: "🌿 Aviação Agrícola"        },
    { id: "frota",        label: "✈️ Conheça Nossa Frota"     },
    { id: "precisao",     label: "🎯 Precisão na Aplicação"   },
    { id: "seguranca",    label: "🛡️ Segurança Operacional"   },
    { id: "tecnologia",   label: "📡 Tecnologia Embarcada"    },
    { id: "cultura",      label: "🌾 Culturas Atendidas"      },
    { id: "manutencao",   label: "🔧 Manutenção Preventiva"   },
    { id: "contato",      label: "📞 Falar com a Equipe"      },
  ];

  var CONTEUDO = {
    sobre: {
      texto: "A Combate Rasante Aviação Agrícola é uma empresa especializada em aplicação aérea de defensivos e insumos agrícolas, referência no cerrado goiano e Triângulo Mineiro.\n\nAtuamos com foco em eficiência operacional, rastreabilidade total e comprometimento com o resultado do produtor — levando tecnologia, segurança e agilidade para o campo.",
      subs: [
        { id: "sobre_missao",      label: "🎯 Nossa Missão e Diferenciais" },
        { id: "sobre_localizacao", label: "📍 Onde Estamos"                },
        { id: "frota",             label: "✈️ Nossa Frota"                 },
      ]
    },
    sobre_missao: {
      texto: "Nossos principais diferenciais:\n\n✅ Pilotos e aeronaves certificados pela ANAC\n✅ Operações licenciadas pelo MAPA\n✅ Receituário agronômico e ART em todas as operações\n✅ GPS de bordo com sobreposição inferior a 3% entre passadas\n✅ Voo entre 2 e 5m do dossel — mínima deriva\n✅ Relatório georreferenciado entregue após cada operação\n✅ Sem compactação do solo\n✅ Centenas de hectares por dia, independente das condições do terreno",
      subs: [
        { id: "sobre_localizacao", label: "📍 Onde Estamos" },
      ]
    },
    sobre_localizacao: {
      texto: "Nossas unidades:\n\n📍 Matriz\nRod. GO 320, Km 82\nVicentinópolis / GO — CEP 75.555-000\n\n📍 Filial\nAeroporto Municipal, Hangar 10\nItuiutaba / MG",
      subs: [
        { id: "contato", label: "📞 Falar com a Equipe" },
      ]
    },
    frota: {
      texto: "Contamos com uma frota composta por aeronaves de perfis complementares, formando uma estrutura versátil e preparada para diferentes perfis de operação no campo. São elas: Cessna 188 Agtruck, Piper PA-36-375, Neiva EMB-201A e, na categoria de grande porte, o Air Tractor AT402B.",
      subs: [
        { id: "frota_padrao", label: "🛩️ Perfil Padrão/Médio" },
        { id: "frota_grande", label: "✈️ Perfil Grande Porte"  },
        { id: "frota_faixas", label: "📏 Faixas de Aplicação"  },
      ]
    },
    frota_padrao: {
      texto: "Aeronaves de perfil padrão e médio:\n\n🛩️ Cessna A188B Agtruck — agilidade e eficiência operacional\n🛩️ Neiva EMB-201A — tradição, precisão e consistência\n\nEssas aeronaves reúnem equilíbrio entre agilidade, eficiência e segurança, atendendo com qualidade diferentes demandas da aplicação aérea. Trabalham com faixa de aplicação de 21 metros, com ajustes realizados conforme a regulagem e necessidade específica de cada operação.",
      subs: [
        { id: "frota_grande", label: "✈️ Ver Perfil Grande Porte" },
      ]
    },
    frota_grande: {
      texto: "Aeronaves de grande porte:\n\n✈️ Piper PA-36-375 Brave — potência e robustez operacional\n✈️ Air Tractor AT402B — capacidade máxima de trabalho\n\nEssas aeronaves representam maior porte e potência dentro da operação, agregando robustez, presença operacional e capacidade de atendimento ampliada. Trabalham com faixa de aplicação de 28 metros, fortalecendo a frota para diferentes cenários do campo.",
      subs: [
        { id: "frota_faixas", label: "📏 Ver Faixas de Aplicação" },
      ]
    },
    frota_faixas: {
      texto: "Faixas de aplicação da frota:\n\n📏 Perfil padrão/médio (Cessna A188B e Neiva EMB-201A)\n→ Faixa de 21 metros\n\n📏 Perfil grande porte (Piper PA-36-375 e Air Tractor AT402B)\n→ Faixa de 28 metros\n\nTodos os ajustes são realizados conforme a regulagem e a necessidade específica de cada operação, garantindo precisão e eficiência em campo.",
      subs: []
    },
    agricultura: {
      texto: "A aviação agrícola é hoje uma das ferramentas mais eficientes do agronegócio. Com capacidade de cobrir centenas de hectares por dia, as aeronaves permitem aplicações de defensivos, fertilizantes e fungicidas com rapidez e uniformidade impossíveis de atingir por equipamentos terrestres — especialmente em lavouras densas ou em condições de solo úmido.",
      subs: [
        { id: "produtividade", label: "🚀 Produtividade no Campo" },
        { id: "vantagens",     label: "✅ Vantagens vs Terrestre" },
      ]
    },
    precisao: {
      texto: "Nossas aeronaves voam entre 2 e 5 metros do dossel das plantas, garantindo cobertura uniforme e mínima deriva. Com controle GPS de faixa, a sobreposição entre passagens é inferior a 3%, eliminando falhas e retrabalho. Cada operação gera um relatório georreferenciado com mapa do talhão tratado.",
      subs: []
    },
    seguranca: {
      texto: "A segurança é a base de cada voo. Todos os pilotos são certificados pela ANAC, as operações são licenciadas pelo MAPA, e seguimos rigorosamente as faixas de segurança, ART e respeito às áreas de proteção ambiental. Cultura de segurança não é opção — é compromisso.",
      subs: [
        { id: "checklist",  label: "📋 Checklist Pré-Voo"    },
        { id: "manutencao", label: "🔧 Manutenção Preventiva" },
      ]
    },
    tecnologia: {
      texto: "Nossas aeronaves são equipadas com GPS de alta precisão, controle automático de faixa e bicos de pulverização controlados eletronicamente. Monitoramos em tempo real a velocidade, altitude, largura de faixa e volume aplicado. O produtor recebe um relatório completo com rastreabilidade total.",
      subs: []
    },
    cultura: {
      texto: "Atendemos as principais culturas do cerrado goiano e Triângulo Mineiro:\n\n🌱 Soja — controle de pragas, doenças e plantas daninhas\n🌽 Milho — dessecação, fungicidas e nutrição foliar\n🎋 Cana-de-Açúcar — maturadores, herbicidas e adubação\n☕ Café — fungicidas e nutrição foliar\n🌾 Algodão e outros grãos",
      subs: []
    },
    manutencao: {
      texto: "Manutenção preventiva é sinônimo de segurança e disponibilidade. Seguimos rigorosos planos de manutenção homologados pela ANAC, com inspeções periódicas de motor, sistemas de pulverização, estrutura e aviônicos. Aeronaves bem mantidas garantem regularidade operacional e proteção máxima ao piloto.",
      subs: [{ id: "checklist", label: "📋 Checklist Pré-Voo" }]
    },
    checklist: {
      texto: "O checklist pré-voo inclui:\n\n• Verificação de combustível e óleo\n• Inspeção visual do motor e fuselagem\n• Teste dos sistemas de pulverização\n• Verificação do GPS e comunicação\n• Confirmação das condições meteorológicas\n• Briefing com a equipe de apoio\n\nNenhum voo parte sem a conclusão completa do checklist.",
      subs: []
    },
    produtividade: {
      texto: "A aviação agrícola potencializa resultados ao aplicar defensivos na janela ideal de eficácia — mesmo quando o solo está úmido ou a lavoura já fechou. Estudos comprovam ganhos de 8 a 15% na produtividade com aplicações aéreas no momento certo.",
      subs: []
    },
    vantagens: {
      texto: "Comparado aos equipamentos terrestres:\n\n✅ Velocidade — centenas de ha/dia sem depender do solo\n✅ Acesso — funciona em lavouras fechadas ou encharcadas\n✅ Uniformidade — cobertura regular sem compactar o solo\n✅ Agilidade — aplicação na janela ideal\n✅ Rastreabilidade — relatório georreferenciado de cada voo",
      subs: []
    },
    contato: {
      texto: "📞 Entre em contato com nossa equipe:\n\n• Tel: (64) 99983-6005\n• Tel: (64) 99221-7002\n• Email: weikren@combateaviacao.com.br\n\n📍 Matriz: Rod. GO 320, Km 82 — Vicentinópolis/GO\n📍 Filial: Aeroporto Municipal — Ituiutaba/MG",
      subs: [],
      link: { label: "💬 Solicitar Orçamento", href: "/contato" }
    },
  };

  /* ── Criar elementos ── */

  // Vídeo intro
  var intro = document.createElement("div");
  intro.id = "cr-intro";
  intro.innerHTML = '<video id="crIntroVid" muted playsinline>' +
    '<source src="' + VIDEO + '" type="video/mp4"></video>';
  document.body.appendChild(intro);

  // Botão flutuante com avatar
  var btn = document.createElement("button");
  btn.id = "cr-chat-btn";
  btn.setAttribute("aria-label", "Abrir assistente Piloto");
  btn.innerHTML =
    '<img src="' + AVATAR + '" alt="Piloto">' +
    '<span class="cr-notif" id="crNotif"></span>';
  document.body.appendChild(btn);

  // Balão de saudação
  var hello = document.createElement("div");
  hello.id = "cr-hello-bubble";
  hello.textContent = "👋 Oi! Sou o Piloto. Posso te ajudar?";
  hello.onclick = abrir;
  document.body.appendChild(hello);

  // Janela do chat
  var win = document.createElement("div");
  win.id = "cr-chat-win";
  win.setAttribute("role", "dialog");
  win.innerHTML =
    '<div class="cr-header">' +
      '<div class="cr-header-avatar">' +
        '<img src="' + AVATAR + '" alt="Piloto">' +
      '</div>' +
      '<div class="cr-header-info">' +
        '<div class="cr-header-name">Piloto</div>' +
        '<div class="cr-header-role">Assistente Combate Rasante</div>' +
        '<div class="cr-header-status">Online</div>' +
      '</div>' +
      '<button class="cr-close" id="crClose" aria-label="Fechar">✕</button>' +
    '</div>' +
    '<div class="cr-msgs" id="crMsgs"></div>' +
    (IS_AUTH
      ? '<div class="cr-input-row">' +
          '<textarea id="crInput" placeholder="Digite sua pergunta sobre aviação agrícola..." rows="1"></textarea>' +
          '<button class="cr-send" id="crSend" aria-label="Enviar">➤</button>' +
        '</div>'
      : '<div class="cr-visitor-footer">Visitante? <a href="/login">Faça login</a> para chat com IA.</div>');
  document.body.appendChild(win);

  /* ── Referências ── */
  var msgs      = document.getElementById("crMsgs");
  var notif     = document.getElementById("crNotif");
  var input     = document.getElementById("crInput");
  var sendBtn   = document.getElementById("crSend");
  var introVid  = document.getElementById("crIntroVid");
  var historico = [];
  var aberto    = false;

  /* ── Helpers ── */
  function scroll() {
    setTimeout(function () { msgs.scrollTop = msgs.scrollHeight; }, 60);
  }

  // Bolha do bot com mini avatar do Piloto
  function addBotMsg(texto) {
    var row = document.createElement("div");
    row.className = "cr-bot-row";
    row.innerHTML =
      '<div class="cr-bot-mini"><img src="' + AVATAR + '" alt="P"></div>' +
      '<div class="cr-bubble bot" style="white-space:pre-wrap">' + texto + '</div>';
    msgs.appendChild(row);
    scroll();
    return row;
  }

  // Bolha do usuário
  function addUserMsg(texto) {
    var b = document.createElement("div");
    b.className = "cr-bubble user";
    b.textContent = texto;
    msgs.appendChild(b);
    scroll();
  }

  // Typing com mini avatar
  function addTyping() {
    var row = document.createElement("div");
    row.className = "cr-typing-row";
    row.id = "crTyping";
    row.innerHTML =
      '<div class="cr-bot-mini"><img src="' + AVATAR + '" alt="P"></div>' +
      '<div class="cr-typing"><span></span><span></span><span></span></div>';
    msgs.appendChild(row);
    scroll();
  }

  function removeTyping() {
    var t = document.getElementById("crTyping");
    if (t) t.remove();
  }

  // Botões de opção
  function addOptions(lista, onBack) {
    var back = null;
    if (onBack) {
      back = document.createElement("button");
      back.className = "cr-back-btn";
      back.textContent = "← Voltar ao menu";
      back.onclick = onBack;
      msgs.appendChild(back);
    }
    var wrap = document.createElement("div");
    wrap.className = "cr-options";
    lista.forEach(function (item) {
      var b = document.createElement("button");
      b.className = "cr-opt-btn";
      b.textContent = item.label;
      b.onclick = function () {
        wrap.remove();
        if (back) back.remove();
        handleOpcao(item.id);
      };
      wrap.appendChild(b);
    });
    msgs.appendChild(wrap);
    scroll();
  }

  /* ── Menu de visitantes ── */
  function menuPrincipal() {
    setTimeout(function () {
      addBotMsg("O que você gostaria de saber?");
      addOptions(MENU_PRINCIPAL, null);
    }, 300);
  }

  function handleOpcao(id) {
    var dados = CONTEUDO[id];
    if (!dados) return menuPrincipal();

    addBotMsg(dados.texto);

    if (dados.link) {
      var a = document.createElement("a");
      a.href = dados.link.href;
      a.style.cssText = "display:inline-block;margin:6px 0 0 33px;padding:9px 16px;" +
        "background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;" +
        "border-radius:10px;font-size:13px;font-weight:700;text-decoration:none;";
      a.textContent = dados.link.label;
      msgs.appendChild(a);
    }

    var prox = dados.subs && dados.subs.length ? dados.subs : null;
    setTimeout(function () {
      if (prox) {
        addBotMsg("Deseja saber mais?");
        addOptions(prox, menuPrincipal);
      } else {
        addBotMsg("Posso te ajudar com mais alguma informação?");
        addOptions(MENU_PRINCIPAL, null);
      }
    }, 500);
    scroll();
  }

  /* ── Boas-vindas ── */
  function bemVindo() {
    msgs.innerHTML = "";
    historico = [];
    setTimeout(function () {
      addBotMsg("Olá! Sou o Piloto, assistente virtual da Combate Rasante Aviação Agrícola! ✈️");
    }, 200);
    if (IS_AUTH) {
      setTimeout(function () {
        addBotMsg("Pode me perguntar qualquer coisa sobre aviação agrícola, culturas, tecnologia e segurança!");
      }, 800);
    } else {
      setTimeout(menuPrincipal, 800);
    }
  }

  /* ── Vídeo intro ── */
  function playIntro(callback) {
    intro.classList.add("show");
    introVid.currentTime = 0;
    introVid.play().catch(function () {
      intro.classList.remove("show");
      if (callback) callback();
    });
    introVid.onended = function () {
      intro.classList.remove("show");
      if (callback) callback();
    };
    // Fallback: se demorar demais
    setTimeout(function () {
      if (intro.classList.contains("show")) {
        intro.classList.remove("show");
        if (callback) callback();
      }
    }, 4000);
  }

  /* ── Enviar (autenticados) ── */
  function enviar() {
    if (!input) return;
    var texto = input.value.trim();
    if (!texto) return;

    addUserMsg(texto);
    historico.push({ role: "user", content: texto });
    input.value = "";
    input.style.height = "auto";
    if (sendBtn) sendBtn.disabled = true;

    addTyping();

    fetch("/api/chatbot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensagem: texto, historico: historico }),
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        removeTyping();
        var resp = d.resposta || "Desculpe, não consegui processar sua pergunta.";
        addBotMsg(resp);
        historico.push({ role: "assistant", content: resp });
        if (sendBtn) sendBtn.disabled = false;
        if (input) input.focus();
      })
      .catch(function () {
        removeTyping();
        addBotMsg("Erro de conexão. Verifique sua internet e tente novamente.");
        if (sendBtn) sendBtn.disabled = false;
      });
  }

  /* ── Abrir / fechar ── */
  function abrir() {
    if (aberto) return;
    aberto = true;
    hello.classList.add("hide");
    notif.classList.remove("show");

    // Toca vídeo intro na primeira abertura, depois abre direto
    if (msgs.children.length === 0) {
      playIntro(function () {
        win.classList.add("open");
        bemVindo();
        if (input) setTimeout(function () { input.focus(); }, 300);
      });
    } else {
      win.classList.add("open");
      if (input) setTimeout(function () { input.focus(); }, 300);
    }
  }

  function fechar() {
    aberto = false;
    win.classList.remove("open");
    intro.classList.remove("show");
    if (introVid) { introVid.pause(); introVid.currentTime = 0; }
  }

  /* ── Eventos ── */
  btn.addEventListener("click", function () { aberto ? fechar() : abrir(); });
  document.getElementById("crClose").addEventListener("click", fechar);
  hello.addEventListener("click", abrir);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && aberto) fechar();
  });

  if (input) {
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); }
    });
    input.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 90) + "px";
    });
  }
  if (sendBtn) sendBtn.addEventListener("click", enviar);

  /* ── Notificação após 3s ── */
  setTimeout(function () {
    if (!aberto) notif.classList.add("show");
  }, 3000);

})();
