/**
 * COMBATE RASANTE — Chatbot Flutuante
 * Visitantes: menu interativo por balões
 * Autenticados: chat com IA (Claude via API backend)
 */
(function () {
  "use strict";

  /* ── Detectar se o usuário está autenticado ── */
  var IS_AUTH = document.body.dataset.crAuth === "1";

  /* ── Conteúdo do menu de visitantes ── */
  var MENU_PRINCIPAL = [
    { id: "agricultura",  label: "🌿 Aviação Agrícola"        },
    { id: "precisao",     label: "🎯 Precisão na Aplicação"   },
    { id: "seguranca",    label: "🛡️ Segurança Operacional"   },
    { id: "tecnologia",   label: "📡 Tecnologia Embarcada"    },
    { id: "cultura",      label: "🌾 Culturas Atendidas"      },
    { id: "manutencao",   label: "🔧 Manutenção Preventiva"   },
    { id: "contato",      label: "📞 Falar com a Equipe"      },
  ];

  var CONTEUDO = {
    agricultura: {
      texto: "A aviação agrícola é hoje uma das ferramentas mais eficientes do agronegócio. Com capacidade de cobrir centenas de hectares por dia, as aeronaves agrícolas permitem aplicações de defensivos, fertilizantes e fungicidas com rapidez e uniformidade impossíveis de atingir por equipamentos terrestres — especialmente em lavouras densas ou em condições de solo úmido.",
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
      texto: "A segurança é a base de cada voo. Todos os pilotos são certificados pela ANAC, as operações são licenciadas pelo MAPA, e seguimos rigorosamente as faixas de segurança, ART e respeito às áreas de proteção ambiental. O checklist antes de cada voo é obrigatório e auditado. Cultura de segurança não é opção — é compromisso.",
      subs: [
        { id: "checklist",  label: "📋 Checklist Pré-Voo" },
        { id: "manutencao", label: "🔧 Manutenção Preventiva" },
      ]
    },
    tecnologia: {
      texto: "Nossas aeronaves são equipadas com GPS de alta precisão, controle automático de faixa e bicos de pulverização controlados eletronicamente. Monitoramos em tempo real a velocidade, altitude, largura de faixa e volume aplicado. Ao final da operação, o produtor recebe um relatório completo com rastreabilidade total.",
      subs: []
    },
    cultura: {
      texto: "Atendemos as principais culturas do cerrado goiano e Triângulo Mineiro:\n\n🌱 Soja — controle de pragas, doenças e plantas daninhas\n🌽 Milho — dessecação, fungicidas e nutrição foliar\n🎋 Cana-de-Açúcar — maturadores, herbicidas e adubação\n☕ Café — fungicidas e nutrição foliar\n🌾 Algodão e outros grãos",
      subs: []
    },
    manutencao: {
      texto: "Manutenção preventiva é sinônimo de segurança e disponibilidade. Seguimos rigorosos planos de manutenção homologados pela ANAC, com inspeções periódicas de motor, sistemas de pulverização, estrutura e aviônicos. Aeronaves bem mantidas garantem regularidade operacional e proteção máxima ao piloto e ao produtor.",
      subs: [
        { id: "checklist", label: "📋 Checklist Pré-Voo" },
      ]
    },
    checklist: {
      texto: "O checklist pré-voo é uma lista sistemática de verificações realizadas antes de cada decolagem. Inclui:\n\n• Verificação de combustível e óleo\n• Inspeção visual do motor e fuselagem\n• Teste dos sistemas de pulverização\n• Verificação do GPS e comunicação\n• Confirmação das condições meteorológicas\n• Briefing com a equipe de apoio\n\nNenhum voo parte sem a conclusão completa do checklist.",
      subs: []
    },
    produtividade: {
      texto: "A aviação agrícola potencializa resultados ao aplicar defensivos na janela ideal de eficácia — mesmo quando o solo está úmido ou a lavoura já fechou. Isso reduz perdas por doença ou praga, melhora a uniformidade de maturação e eleva a produtividade. Estudos comprovam ganhos de 8 a 15% na produtividade com aplicações aéreas no momento certo.",
      subs: []
    },
    vantagens: {
      texto: "Comparado aos equipamentos terrestres, a aviação agrícola oferece:\n\n✅ Velocidade — centenas de ha/dia sem depender do solo\n✅ Acesso — funciona mesmo em lavouras fechadas ou encharcadas\n✅ Uniformidade — cobertura regular sem compactar o solo\n✅ Agilidade — aplicação na janela ideal de eficiência\n✅ Rastreabilidade — relatório georreferenciado de cada voo",
      subs: []
    },
    contato: {
      texto: "📞 Entre em contato com nossa equipe:\n\n• Tel: (64) 99983-6005\n• Tel: (64) 99221-7002\n• Email: weikren@combateaviacao.com.br\n\n📍 Matriz: Rod. GO 320, Km 82 — Vicentinópolis/GO\n📍 Filial: Aeroporto Municipal — Ituiutaba/MG",
      subs: [],
      link: { label: "💬 Solicitar Orçamento", href: "/contato" }
    },
  };

  /* ── Construir DOM ── */
  var btn = document.createElement("button");
  btn.id = "cr-chat-btn";
  btn.setAttribute("aria-label", "Abrir assistente virtual");
  btn.innerHTML = '<span>✈</span><span class="cr-notif" id="crNotif"></span>';

  var win = document.createElement("div");
  win.id = "cr-chat-win";
  win.setAttribute("role", "dialog");
  win.setAttribute("aria-label", "Assistente Combate Rasante");

  win.innerHTML =
    '<div class="cr-header">' +
      '<div class="cr-header-avatar">' +
        '<img src="/static/img/logo-combate.jpeg" alt="CR" onerror="this.style.display=\'none\'">' +
      '</div>' +
      '<div class="cr-header-info">' +
        '<div class="cr-header-name">Assistente CR</div>' +
        '<div class="cr-header-status">Online — Aviação Agrícola</div>' +
      '</div>' +
      '<button class="cr-close" id="crClose" aria-label="Fechar">✕</button>' +
    '</div>' +
    '<div class="cr-msgs" id="crMsgs"></div>' +
    (IS_AUTH
      ? '<div class="cr-input-row" id="crInputRow">' +
          '<textarea id="crInput" placeholder="Digite sua pergunta sobre aviação agrícola..." rows="1"></textarea>' +
          '<button class="cr-send" id="crSend" aria-label="Enviar">➤</button>' +
        '</div>'
      : '<div class="cr-visitor-footer">Visitante? <a href="/login">Faça login</a> para chat completo com IA.</div>');

  document.body.appendChild(btn);
  document.body.appendChild(win);

  /* ── Referências ── */
  var msgs    = document.getElementById("crMsgs");
  var notif   = document.getElementById("crNotif");
  var input   = document.getElementById("crInput");
  var sendBtn = document.getElementById("crSend");
  var historico = [];
  var aberto    = false;

  /* ── Funções helpers ── */
  function scroll() {
    setTimeout(function () { msgs.scrollTop = msgs.scrollHeight; }, 50);
  }

  function addMsg(texto, quem) {
    var b = document.createElement("div");
    b.className = "cr-bubble " + quem;
    b.style.whiteSpace = "pre-wrap";
    b.textContent = texto;
    msgs.appendChild(b);
    scroll();
    return b;
  }

  function addTyping() {
    var t = document.createElement("div");
    t.className = "cr-typing";
    t.id = "crTyping";
    t.innerHTML = "<span></span><span></span><span></span>";
    msgs.appendChild(t);
    scroll();
    return t;
  }

  function removeTyping() {
    var t = document.getElementById("crTyping");
    if (t) t.remove();
  }

  function addOptions(lista, onBack) {
    // Botão voltar (se não for menu principal)
    if (onBack) {
      var back = document.createElement("button");
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

  /* ── Lógica visitante ── */
  function menuPrincipal() {
    setTimeout(function () {
      addMsg("O que você gostaria de saber?", "bot");
      addOptions(MENU_PRINCIPAL, null);
    }, 300);
  }

  function handleOpcao(id) {
    var dados = CONTEUDO[id];
    if (!dados) return menuPrincipal();

    addMsg(dados.texto, "bot");

    if (dados.link) {
      var a = document.createElement("a");
      a.href = dados.link.href;
      a.style.cssText = "display:inline-block;margin-top:6px;padding:9px 16px;background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;border-radius:10px;font-size:13px;font-weight:700;text-decoration:none;";
      a.textContent = dados.link.label;
      msgs.appendChild(a);
    }

    var prox = dados.subs && dados.subs.length ? dados.subs : null;
    if (prox) {
      setTimeout(function () {
        addMsg("Deseja saber mais sobre:", "bot");
        addOptions(prox, menuPrincipal);
      }, 500);
    } else {
      setTimeout(function () {
        addMsg("Posso te ajudar com mais alguma informação?", "bot");
        addOptions(MENU_PRINCIPAL, null);
      }, 700);
    }
    scroll();
  }

  /* ── Boas-vindas ── */
  function bemVindo() {
    msgs.innerHTML = "";
    historico = [];
    setTimeout(function () {
      addMsg("Olá! Sou o assistente virtual da Combate Rasante Aviação Agrícola. ✈️", "bot");
    }, 200);

    if (IS_AUTH) {
      setTimeout(function () {
        addMsg("Pode me perguntar qualquer coisa sobre aviação agrícola, culturas, tecnologia, segurança e muito mais!", "bot");
      }, 700);
    } else {
      setTimeout(menuPrincipal, 700);
    }
  }

  /* ── Enviar mensagem (autenticados) ── */
  function enviar() {
    if (!input) return;
    var texto = input.value.trim();
    if (!texto) return;

    addMsg(texto, "user");
    historico.push({ role: "user", content: texto });
    input.value = "";
    input.style.height = "auto";
    if (sendBtn) sendBtn.disabled = true;

    var typing = addTyping();

    fetch("/api/chatbot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensagem: texto, historico: historico }),
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        removeTyping();
        var resp = d.resposta || "Desculpe, não consegui processar sua pergunta.";
        addMsg(resp, "bot");
        historico.push({ role: "assistant", content: resp });
        if (sendBtn) sendBtn.disabled = false;
        input.focus();
      })
      .catch(function () {
        removeTyping();
        addMsg("Erro de conexão. Verifique sua internet e tente novamente.", "bot");
        if (sendBtn) sendBtn.disabled = false;
      });
  }

  /* ── Abrir / fechar ── */
  function abrir() {
    aberto = true;
    win.classList.add("open");
    btn.style.transform = "rotate(10deg) scale(.92)";
    notif.classList.remove("show");
    if (msgs.children.length === 0) bemVindo();
    if (input) setTimeout(function () { input.focus(); }, 300);
  }

  function fechar() {
    aberto = false;
    win.classList.remove("open");
    btn.style.transform = "";
  }

  btn.addEventListener("click", function () {
    aberto ? fechar() : abrir();
  });

  document.getElementById("crClose").addEventListener("click", fechar);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && aberto) fechar();
  });

  /* ── Input autenticados ── */
  if (input) {
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        enviar();
      }
    });
    input.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 90) + "px";
    });
  }
  if (sendBtn) {
    sendBtn.addEventListener("click", enviar);
  }

  /* ── Notificação inicial após 3s ── */
  setTimeout(function () {
    if (!aberto) notif.classList.add("show");
  }, 3000);

})();
