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
          '<button class="cr-pdf-btn" id="crPdfBtn" aria-label="Salvar conversa em PDF" title="Salvar conversa em PDF">📄</button>' +
        '</div>'
      : '<div class="cr-visitor-footer">Visitante? <a href="/login">Faça login</a> para chat com IA.</div>');
  document.body.appendChild(win);

  /* ── Referências ── */
  var msgs      = document.getElementById("crMsgs");
  var notif     = document.getElementById("crNotif");
  var input     = document.getElementById("crInput");
  var sendBtn   = document.getElementById("crSend");
  var pdfBtn    = document.getElementById("crPdfBtn");
  var introVid  = document.getElementById("crIntroVid");
  var historico    = [];   // contexto para a API
  var historicoLog = [];   // log completo para PDF {tipo, texto, hora}
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
    historicoLog = [];
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
    historicoLog.push({ tipo: "user", texto: texto, hora: new Date() });
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
        historicoLog.push({ tipo: "bot", texto: resp, hora: new Date() });
        // Mostrar botão de salvar na última bolha do bot
        adicionarBotaoSalvar(resp, historicoLog.length - 2);
        if (sendBtn) sendBtn.disabled = false;
        if (input) input.focus();
      })
      .catch(function () {
        removeTyping();
        addBotMsg("Erro de conexão. Verifique sua internet e tente novamente.");
        if (sendBtn) sendBtn.disabled = false;
      });
  }

  /* ── Botão salvar par pergunta/resposta ── */
  function adicionarBotaoSalvar(respostaTexto, idxUser) {
    var lastRow = msgs.lastElementChild;
    if (!lastRow || !lastRow.classList.contains("cr-bot-row")) return;

    var btnSave = document.createElement("button");
    btnSave.className   = "cr-save-pair-btn";
    btnSave.title       = "Salvar esta pergunta e resposta como PDF";
    btnSave.textContent = "💾 Salvar";
    btnSave.onclick = function () {
      var userLog = idxUser >= 0 ? historicoLog[idxUser] : null;
      var botLog  = { tipo: "bot", texto: respostaTexto, hora: new Date() };
      gerarPdfPar(userLog, botLog);
    };

    var wrap = document.createElement("div");
    wrap.style.cssText = "display:flex;justify-content:flex-start;padding-left:33px;margin-top:2px;";
    wrap.appendChild(btnSave);
    msgs.appendChild(wrap);
    scroll();
  }

  /* ── Gerar PDF de um par pergunta/resposta ── */
  function gerarPdfPar(userLog, botLog) {
    var linhas = [];
    linhas.push({ tipo: "titulo", texto: "Combate Rasante — Assistente Piloto" });
    linhas.push({ tipo: "sub",    texto: "Consulta salva em " + formatarData(botLog.hora) });
    linhas.push({ tipo: "sep" });
    if (userLog) {
      linhas.push({ tipo: "label", texto: "Sua pergunta:" });
      linhas.push({ tipo: "user",  texto: userLog.texto, hora: userLog.hora });
    }
    linhas.push({ tipo: "label", texto: "Resposta do Piloto:" });
    linhas.push({ tipo: "bot",   texto: botLog.texto, hora: botLog.hora });
    renderizarPdf(linhas, "consulta-piloto-" + Date.now() + ".pdf");
  }

  /* ── Gerar PDF de toda a conversa ── */
  function gerarPdfConversa() {
    if (historicoLog.length === 0) {
      alert("Nenhuma conversa para salvar ainda.");
      return;
    }
    var linhas = [];
    linhas.push({ tipo: "titulo", texto: "Combate Rasante — Assistente Piloto" });
    linhas.push({ tipo: "sub",    texto: "Conversa completa — " + formatarData(new Date()) });
    linhas.push({ tipo: "sep" });
    historicoLog.forEach(function (m) {
      if (m.tipo === "user") {
        linhas.push({ tipo: "label", texto: "Você perguntou:" });
        linhas.push({ tipo: "user",  texto: m.texto, hora: m.hora });
      } else {
        linhas.push({ tipo: "label", texto: "Piloto respondeu:" });
        linhas.push({ tipo: "bot",   texto: m.texto, hora: m.hora });
        linhas.push({ tipo: "sep" });
      }
    });
    renderizarPdf(linhas, "conversa-piloto-" + Date.now() + ".pdf");
  }

  /* ── Renderizar PDF via canvas (sem biblioteca externa) ── */
  function renderizarPdf(linhas, nomeArquivo) {
    // Página A4 em pontos (72dpi): 595 x 842
    var W = 595, H = 842, margin = 40, lineW = W - margin * 2;
    var pages = [[]]; // array de páginas, cada uma tem array de blocos {y, draw}
    var y = margin + 10;
    var pageIdx = 0;

    function novaPagina() {
      pages.push([]);
      pageIdx++;
      y = margin + 10;
    }

    function checkSpace(needed) {
      if (y + needed > H - margin) novaPagina();
    }

    // Quebra texto em linhas de largura máxima (aproximação proporcional)
    function quebrarTexto(texto, maxChars) {
      var palavras = texto.split(" ");
      var linhasQ = [], cur = "";
      palavras.forEach(function (p) {
        if ((cur + " " + p).trim().length > maxChars) {
          if (cur) linhasQ.push(cur.trim());
          cur = p;
        } else {
          cur = cur ? cur + " " + p : p;
        }
      });
      if (cur) linhasQ.push(cur.trim());
      return linhasQ;
    }

    // Desenhar texto com quebra automática — retorna y final
    function addTexto(page, xPos, yPos, texto, maxChars, fontSize) {
      var linhasQ = quebrarTexto(String(texto), maxChars);
      linhasQ.forEach(function (ln, idx) {
        page.push({ y: yPos + idx * (fontSize + 3), x: xPos, texto: ln, fontSize: fontSize });
      });
      return yPos + linhasQ.length * (fontSize + 3);
    }

    linhas.forEach(function (bloco) {
      if (bloco.tipo === "titulo") {
        checkSpace(28);
        pages[pageIdx].push({ y: y, x: margin, texto: bloco.texto, fontSize: 16, bold: true, color: [20, 83, 45] });
        y += 24;
      } else if (bloco.tipo === "sub") {
        checkSpace(18);
        pages[pageIdx].push({ y: y, x: margin, texto: bloco.texto, fontSize: 9, color: [120, 120, 120] });
        y += 16;
      } else if (bloco.tipo === "sep") {
        checkSpace(14);
        pages[pageIdx].push({ y: y, x: margin, w: lineW, tipo: "linha" });
        y += 12;
      } else if (bloco.tipo === "label") {
        checkSpace(16);
        pages[pageIdx].push({ y: y, x: margin, texto: bloco.texto, fontSize: 10, bold: true, color: [34, 120, 60] });
        y += 15;
      } else if (bloco.tipo === "user" || bloco.tipo === "bot") {
        var isUser = bloco.tipo === "user";
        var bgColor = isUser ? [220, 252, 231] : [241, 245, 249];
        var textColor = isUser ? [20, 83, 45] : [30, 41, 59];
        var maxChars = 78;
        var linhasQ = quebrarTexto(String(bloco.texto), maxChars);
        var boxH = linhasQ.length * 14 + 16;
        checkSpace(boxH + 14);
        pages[pageIdx].push({ y: y, x: margin, w: lineW, h: boxH, bg: bgColor, tipo: "box", radius: 6 });
        var ty = y + 10;
        linhasQ.forEach(function (ln) {
          pages[pageIdx].push({ y: ty, x: margin + 8, texto: ln, fontSize: 10, color: textColor });
          ty += 14;
        });
        if (bloco.hora) {
          pages[pageIdx].push({ y: ty - 2, x: margin + 8, texto: formatarData(bloco.hora), fontSize: 8, color: [160, 160, 160] });
        }
        y += boxH + 10;
      }
    });

    // Montar PDF usando canvas
    var pdf = buildPdf(pages, W, H, margin);
    downloadBlob(pdf, nomeArquivo, "application/pdf");
  }

  /* ── Builder PDF mínimo (formato PDF puro, sem biblioteca) ── */
  function buildPdf(pages, W, H, margin) {
    var html = "<!DOCTYPE html><html><head><meta charset='utf-8'>" +
      "<title>Combate Rasante — Piloto</title>" +
      "<style>" +
      "*{box-sizing:border-box;}" +
      "body{font-family:Arial,sans-serif;margin:0;padding:24px 32px;color:#1e293b;font-size:12px;line-height:1.45;}" +
      "h1{color:#14532d;font-size:17px;margin:0 0 2px;}" +
      ".sub{color:#888;font-size:9px;margin-bottom:14px;}" +
      "hr{border:none;border-top:1px solid #e2e8f0;margin:10px 0;}" +
      ".label{font-weight:bold;color:#166534;font-size:10px;margin:10px 0 3px;text-transform:uppercase;letter-spacing:.04em;}" +
      ".box{padding:8px 12px;border-radius:6px;margin-bottom:6px;font-size:11px;line-height:1.5;}" +
      ".user{background:#dcfce7;color:#14532d;}" +
      ".bot{background:#f1f5f9;color:#1e293b;}" +
      ".hora{font-size:8px;color:#aaa;margin-top:4px;display:block;}" +
      /* Markdown rendererizado */
      "strong{font-weight:bold;}" +
      "em{font-style:italic;}" +
      "h2,h3{font-size:12px;font-weight:bold;color:#14532d;margin:4px 0 2px;}" +
      "ul,ol{margin:3px 0 3px 18px;padding:0;}" +
      "li{margin-bottom:1px;}" +
      "@media print{" +
      "  body{padding:12px 20px;font-size:11px;}" +
      "  .box{padding:6px 10px;margin-bottom:4px;}" +
      "  .label{margin:7px 0 2px;}" +
      "  hr{margin:7px 0;}" +
      "}" +
      "</style></head><body>";

    pages.forEach(function (page) {
      page.forEach(function (el) {
        if (el.tipo === "linha") {
          html += "<hr>";
        } else if (el.tipo === "box") {
          // montado por tipo user/bot abaixo
        } else if (el.bold && el.color && el.color[0] < 50) {
          html += "<h1>" + escapeHtml(el.texto) + "</h1>";
        } else if (el.color && el.color[0] > 100 && !el.bold) {
          html += "<div class='sub'>" + escapeHtml(el.texto) + "</div>";
        } else if (el.bold) {
          html += "<div class='label'>" + escapeHtml(el.texto) + "</div>";
        } else if (el.color && el.color[0] < 50) {
          html += "<div class='box user'>" + renderMd(el.texto) + "</div>";
        } else {
          html += "<div class='box bot'>" + renderMd(el.texto) + "</div>";
        }
      });
    });

    html += "<script>window.onload=function(){window.print();}<\/script></body></html>";
    return html;
  }

  function downloadBlob(content, filename, type) {
    // Para HTML: abre em nova aba para imprimir/salvar como PDF
    var blob = new Blob([content], { type: "text/html;charset=utf-8" });
    var url  = URL.createObjectURL(blob);
    var a    = document.createElement("a");
    a.href   = url;
    a.target = "_blank";
    a.rel    = "noopener";
    a.click();
    setTimeout(function () { URL.revokeObjectURL(url); }, 3000);
  }

  function formatarData(d) {
    if (!d) return "";
    var dd = String(d.getDate()).padStart(2,"0");
    var mm = String(d.getMonth()+1).padStart(2,"0");
    var yy = d.getFullYear();
    var hh = String(d.getHours()).padStart(2,"0");
    var mi = String(d.getMinutes()).padStart(2,"0");
    return dd+"/"+mm+"/"+yy+" às "+hh+":"+mi;
  }

  function escapeHtml(t) {
    return String(t)
      .replace(/&/g,"&amp;")
      .replace(/</g,"&lt;")
      .replace(/>/g,"&gt;");
  }

  /* Renderiza markdown básico para HTML compacto */
  function renderMd(t) {
    var s = escapeHtml(t);
    // Títulos # ## ###
    s = s.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    s = s.replace(/^## (.+)$/gm,  "<h2>$1</h2>");
    s = s.replace(/^# (.+)$/gm,   "<h2>$1</h2>");
    // Negrito e itálico
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\*([^*]+)\*/g,      "<em>$1</em>");
    s = s.replace(/__([^_]+)__/g,        "<strong>$1</strong>");
    s = s.replace(/_([^_]+)_/g,          "<em>$1</em>");
    // Listas com - ou *
    s = s.replace(/^[-*•] (.+)$/gm, "<li>$1</li>");
    s = s.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");
    // Listas numeradas
    s = s.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
    // Quebras de linha → apenas espaço se linha seguinte tem conteúdo
    // Linha em branco → parágrafo
    s = s.replace(/\n\n+/g, "</p><p>").replace(/\n/g, " ");
    s = "<p>" + s + "</p>";
    // Limpar <p> vazios
    s = s.replace(/<p>\s*<\/p>/g, "");
    return s;
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
  if (pdfBtn)  pdfBtn.addEventListener("click", gerarPdfConversa);

  /* ── Notificação após 3s ── */
  setTimeout(function () {
    if (!aberto) notif.classList.add("show");
  }, 3000);

})();
