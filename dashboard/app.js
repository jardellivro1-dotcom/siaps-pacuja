(() => {
  "use strict";
  const P = window.PAINEL;
  const CONC = ["Ótimo", "Bom", "Suficiente", "Regular"];
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const COR = () => ({ "Ótimo": css("--otimo"), "Bom": css("--bom"), "Suficiente": css("--suf"), "Regular": css("--reg") });
  const TINT = { "Ótimo": "--otimo-t", "Bom": "--bom-t", "Suficiente": "--suf-t", "Regular": "--reg-t" };
  const EQUIPE = { eSF: "Saúde da Família (eSF)", eAP: "Atenção Primária (eAP)", eSB: "Saúde Bucal (eSB)", eMulti: "eMulti" };
  const ORDEM = ["eSF", "eAP", "eSB", "eMulti"];
  const ord = o => Object.entries(o).sort((a, b) => ORDEM.indexOf(a[0]) - ORDEM.indexOf(b[0]));
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n, d = 2) => n == null ? "—" : n.toFixed(d).replace(".", ",");
  const sum = d => CONC.reduce((a, c) => a + (d?.[c] || 0), 0);
  // Regras de cálculo ficam no servidor (metrics.py); aqui só se apresenta o que já veio calculado.
  const charts = {};
  let tabEq = null;

  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); return true; } catch { return false; } },
    del(k) { try { localStorage.removeItem(k); } catch { /* sem armazenamento */ } },
  };
  const ss = {
    get(k) { try { return sessionStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch { /* ignora */ } },
    del(k) { try { sessionStorage.removeItem(k); } catch { /* ignora */ } },
  };

  const quads = P.quadrimestres;
  if (!quads.length) {
    document.querySelector("main").innerHTML = '<p class="empty">Nenhum dado extraído ainda. Rode: python -m siaps_pacuja update</p>';
    return;
  }

  const sel = $("quad");
  quads.forEach(q => sel.add(new Option(q.rotulo, q.id)));
  const salvo = ss.get("quad");
  sel.value = quads.some(q => q.id === salvo) ? salvo : quads[quads.length - 1].id;
  ss.del("quad");
  sel.onchange = render;

  const idx = () => quads.findIndex(q => q.id === sel.value);
  const cur = () => quads[idx()];
  const prev = () => quads[idx() - 1];

  // ---------------------------------------------------------------- helpers de apresentação
  const resumoTexto = d => CONC.filter(k => d[k]).map(k => `${k} ${d[k]}`).join(" · ") || "sem equipes";
  function stackBar(d) {
    const t = sum(d) || 1, c = COR();
    return `<div class="stack" role="img" aria-label="${esc(resumoTexto(d))}">` +
      CONC.map(k => d[k] ? `<i style="width:${100 * d[k] / t}%;background:${c[k]}"></i>` : "").join("") +
      `</div><p class="num">${esc(resumoTexto(d))}</p>`;
  }
  const legend = () => `<div class="legend">${CONC.map(k => `<span><b style="background:${COR()[k]}"></b>${k}</span>`).join("")}</div>`;
  function deltaHtml(a, b) {
    if (a == null || b == null) return "";
    const d = a - b;
    if (Math.abs(d) < 0.005) return '<span class="delta eq">= estável vs. quadrimestre anterior</span>';
    return `<span class="delta ${d > 0 ? "up" : "down"}">${d > 0 ? "▲" : "▼"} ${fmt(Math.abs(d))} vs. anterior</span>`;
  }
  function tabela(cab, linhas) {
    return `<table><thead><tr>${cab.map(c => `<th scope="col">${esc(c)}</th>`).join("")}</tr></thead><tbody>` +
      linhas.map(l => `<tr>${l.map((c, i) => i ? `<td class="n">${esc(c)}</td>` : `<th scope="row">${esc(c)}</th>`).join("")}</tr>`).join("") +
      "</tbody></table>";
  }
  function status(txt, cls = "") { const e = $("status"); e.textContent = txt; e.className = "status " + cls; }

  // ---------------------------------------------------------------- avisos de dados
  function avisos() {
    const c = P.meta.coleta || {}, msgs = [];
    const dias = c.ultimaBemSucedida ? (Date.now() - Date.parse(c.ultimaBemSucedida)) / 864e5 : null;
    if (dias == null) msgs.push("Não há registro de coleta bem-sucedida.");
    else if (dias > P.meta.obsoletoAposDias)
      msgs.push(`Os dados foram coletados há ${Math.floor(dias)} dias (limite: ${P.meta.obsoletoAposDias}). Podem estar desatualizados.`);
    if (c.ultimoErro) msgs.push("A última tentativa de atualização falhou; estão sendo exibidos os últimos dados válidos.");
    $("aviso").hidden = !msgs.length;
    $("aviso").innerHTML = msgs.map(m => `<p>${esc(m)}</p>`).join("");
  }

  // ---------------------------------------------------------------- resumo / prioridades
  function cards() {
    const q = cur(), p = prev(), out = [];
    for (const [eq, d] of ord(q.componente3)) {
      const c = d.classificacaoNotaMedia, pd = p?.componente3[eq];
      out.push(`<article class="card c-${c}">
        <p class="lbl">Qualidade · ${esc(EQUIPE[eq] || eq)} · ${d.equipes ?? "?"} equipe(s)</p>
        <p class="big">${d.notaAproximada ? "≈ " : ""}${fmt(d.notaMedia)}<small> / 10 (nota média estimada)</small></p>
        <span class="badge b-${c}">${c}</span> ${deltaHtml(d.notaMedia, pd?.notaMedia)}
        ${d.notaAproximada ? '<p class="lbl">Aproximada: o nº de equipes avaliadas varia entre indicadores.</p>' : ""}
        ${d.distFinal ? stackBar(d.distFinal) : ""}
        <p class="lbl">Conceito final oficial das equipes (nº de equipes)</p></article>`);
    }
    for (const [eq, d] of ord(q.componente2)) {
      out.push(`<article class="card c-${d.predominante}">
        <p class="lbl">Vínculo e Acomp. Territorial · ${esc(EQUIPE[eq] || eq)} · ${d.equipes} equipe(s)</p>
        <p class="big">${esc(resumoTexto(d.distFinal))}</p>
        ${stackBar(d.distFinal)}<p class="lbl">Conceito final oficial das equipes (nº de equipes)</p></article>`);
    }
    $("cards").innerHTML = out.join("") + `<div class="full">${legend()}</div>`;
    $("quad-desc").textContent = q.descricao;
  }

  function prio() {
    $("prio").innerHTML = cur().prioridades.map(i => `<li>
      <span class="code">${esc(i.codigo)}</span>
      <div><strong>${esc(i.curto)}</strong> · ${esc(EQUIPE[i.equipe] || i.equipe)}
        <small>Peso ${i.peso} · pontuação média ${fmt(i.pontuacaoMedia)} · janela de monitoramento ${esc(i.janela)}</small>
        ${stackBar(i.dist)}</div>
      <span class="gain" title="Pontos de nota que ainda podem ser ganhos">+${fmt(i.potencial)} pt</span></li>`).join("");
  }

  // ---------------------------------------------------------------- plano de ação (somente neste navegador)
  const PLANO_KEY = "planoAcao:v1";
  const SITUACOES = ["A fazer", "Em andamento", "Concluída"];
  const planoLer = () => { try { return JSON.parse(store.get(PLANO_KEY) || "{}") || {}; } catch { return {}; } };
  const chaveItem = i => `${cur().id}|${i.equipe}|${i.codigo}`;
  const limpa = (v, max) => String(v ?? "").slice(0, max);

  function plano() {
    const dados = planoLer();
    $("plano").innerHTML = cur().prioridades.map((i, n) => {
      const d = dados[chaveItem(i)] || {}, k = esc(chaveItem(i));
      return `<fieldset class="pl" data-k="${k}"><legend>${esc(i.codigo)} · ${esc(i.curto)} · ${esc(EQUIPE[i.equipe] || i.equipe)}</legend>
        <label>Ação planejada<textarea maxlength="400" rows="2" data-f="acao">${esc(d.acao || "")}</textarea></label>
        <label>Setor responsável (não informe nomes de pessoas)<input maxlength="80" data-f="setor" value="${esc(d.setor || "")}"></label>
        <label>Prazo<input type="date" data-f="prazo" value="${esc(d.prazo || "")}"></label>
        <label>Situação<select data-f="situacao">${SITUACOES.map(s => `<option${d.situacao === s ? " selected" : ""}>${s}</option>`).join("")}</select></label>
      </fieldset>`;
    }).join("");
    $("plano").querySelectorAll("fieldset").forEach(fs => {
      const salvar = () => {
        const todos = planoLer(), v = {};
        fs.querySelectorAll("[data-f]").forEach(c => { v[c.dataset.f] = limpa(c.value, c.dataset.f === "acao" ? 400 : 80); });
        todos[fs.dataset.k] = v;
        if (!store.set(PLANO_KEY, JSON.stringify(todos))) status("Não foi possível salvar o plano neste navegador. Use Exportar.", "err");
      };
      fs.addEventListener("change", salvar);
      fs.addEventListener("input", salvar);
    });
  }

  // Neutraliza fórmulas (=, +, -, @) ao abrir o CSV no Excel/Planilhas (CSV injection).
  const celulaCsv = v => {
    let s = String(v ?? "");
    if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  };
  $("plano-export").onclick = () => {
    const dados = planoLer();
    const linhas = [["Quadrimestre", "Equipe", "Indicador", "Ação", "Setor responsável", "Prazo", "Situação"]];
    Object.entries(dados).sort().forEach(([k, v]) => {
      const [q, eq, cod] = k.split("|");
      const rot = quads.find(x => x.id === q)?.rotulo || q;
      linhas.push([rot, eq, cod, v.acao, v.setor, v.prazo, v.situacao]);
    });
    const csv = "﻿" + linhas.map(l => l.map(celulaCsv).join(";")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = "plano-de-acao-pacuja.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  $("plano-limpar").onclick = () => {
    if (!confirm(`Apagar as ações deste quadrimestre (${cur().rotulo}) neste navegador?`)) return;
    const dados = planoLer();
    Object.keys(dados).filter(k => k.startsWith(cur().id + "|")).forEach(k => delete dados[k]);
    store.set(PLANO_KEY, JSON.stringify(dados));
    plano();
  };

  // ---------------------------------------------------------------- gráficos
  function mk(id, cfg) { charts[id]?.destroy(); charts[id] = new Chart($(id), cfg); }
  const baseOpts = () => ({
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: css("--ink"), boxWidth: 12 } } },
    scales: { x: { ticks: { color: css("--muted") }, grid: { color: css("--line") } },
              y: { ticks: { color: css("--muted") }, grid: { color: css("--line") } } },
  });

  function evolucao() {
    const labels = quads.map(q => q.rotulo);
    const eqs = [...new Set(quads.flatMap(q => Object.keys(q.componente3)))].sort((a, b) => ORDEM.indexOf(a) - ORDEM.indexOf(b));
    const palette = [css("--brand"), css("--otimo"), css("--suf"), css("--reg")];
    const o = baseOpts(); o.scales.y.min = 0; o.scales.y.max = 10;
    mk("c-nota", { type: "line", data: { labels, datasets: eqs.map((e, i) => ({
      label: EQUIPE[e] || e, data: quads.map(q => q.componente3[e]?.notaMedia ?? null),
      borderColor: palette[i % 4], backgroundColor: palette[i % 4], tension: .25, pointRadius: 5, spanGaps: true })) }, options: o });
    $("t-nota").innerHTML = tabela(["Quadrimestre", ...eqs.map(e => EQUIPE[e] || e)],
      quads.map(q => [q.rotulo, ...eqs.map(e => fmt(q.componente3[e]?.notaMedia) + (q.componente3[e]?.notaAproximada ? " (aprox.)" : ""))]));

    // Somente Componente III: eSF, eSB e eMulti são equipes distintas (sem sobreposição entre grupos).
    const tot = Object.fromEntries(CONC.map(k => [k, quads.map(q =>
      Object.values(q.componente3).reduce((a, d) => a + (d.distFinal?.[k] || 0), 0))]));
    const o2 = baseOpts(); o2.scales.x.stacked = true; o2.scales.y.stacked = true; o2.scales.y.ticks.precision = 0;
    mk("c-dist", { type: "bar", data: { labels, datasets: CONC.map(k => ({ label: k, data: tot[k], backgroundColor: COR()[k] })) }, options: o2 });
    $("t-dist").innerHTML = tabela(["Quadrimestre", ...CONC], quads.map((q, n) => [q.rotulo, ...CONC.map(k => tot[k][n])]));
  }

  function indicadores() {
    const q = cur(), eqs = ord(q.componente3).map(e => e[0]);
    if (!tabEq || !eqs.includes(tabEq)) tabEq = eqs[0];
    $("tabs").innerHTML = eqs.map(e => `<button role="tab" aria-selected="${e === tabEq}" data-e="${e}">${esc(EQUIPE[e] || e)}</button>`).join("");
    const bs = [...$("tabs").querySelectorAll("button")];
    bs.forEach((b, n) => {
      b.tabIndex = b.dataset.e === tabEq ? 0 : -1;
      b.onclick = () => { tabEq = b.dataset.e; indicadores(); $("tabs").querySelector("[aria-selected=true]").focus(); };
      b.onkeydown = ev => {
        const d = { ArrowRight: 1, ArrowLeft: -1 }[ev.key];
        if (d) { ev.preventDefault(); bs[(n + d + bs.length) % bs.length].click(); }
      };
    });
    $("ind-q").textContent = "· " + q.rotulo;
    const inds = q.componente3[tabEq].indicadores;
    const o = baseOpts(); o.indexAxis = "y"; o.scales.x.stacked = true; o.scales.y.stacked = true;
    o.scales.x.ticks.precision = 0;
    mk("c-ind", { type: "bar", data: { labels: inds.map(i => `${i.codigo} ${i.curto}`),
      datasets: CONC.map(k => ({ label: k, data: inds.map(i => i.dist[k]), backgroundColor: COR()[k] })) }, options: o });
    $("t-ind").innerHTML = tabela(["Indicador", ...CONC], inds.map(i => [`${i.codigo} ${i.curto}`, ...CONC.map(k => i.dist[k])]));

    const heat = i => quads.map(qq => qq.componente3[tabEq]?.indicadores.find(x => x.codigo === i.codigo));
    $("heat").innerHTML = `<caption class="sr">Pontuação média por indicador e quadrimestre; a faixa aparece em texto ao lado do valor.</caption>
      <thead><tr><th scope="col">Indicador</th><th scope="col" class="n">Peso</th>${quads.map(x => `<th scope="col" class="n">${esc(x.rotulo)}</th>`).join("")}</tr></thead><tbody>` +
      inds.map(i => `<tr><th scope="row"><strong>${esc(i.codigo)}</strong> ${esc(i.curto)}<br><small class="muted">janela ${esc(i.janela)}</small></th><td class="n">${i.peso}</td>` +
        heat(i).map(x => x && x.pontuacaoMedia != null
          ? `<td class="cell" style="background:var(${TINT[x.faixa]})">${fmt(x.pontuacaoMedia)}<small>${esc(x.faixa)}</small></td>`
          : '<td class="cell">—</td>').join("") + "</tr>").join("") + "</tbody>";
  }

  function cvat() {
    const q = cur();
    const blocos = ord(q.componente2).map(([eq, d]) => `<figure>
      <figcaption>${esc(EQUIPE[eq] || eq)} · ${d.equipes} equipe(s)</figcaption>
      <p class="lbl">Conceito final</p>${stackBar(d.distFinal)}
      ${d.dimensoes.map(x => `<p class="lbl">${esc(x.nome)}</p>${stackBar(x.dist)}`).join("")}
      ${legend()}</figure>`);
    $("cvat").innerHTML = blocos.join("") || '<p class="empty">Sem dados de Vínculo para este quadrimestre.</p>';
  }

  // ---------------------------------------------------------------- rodapé / metodologia
  function rodape() {
    const m = P.meta, q = cur();
    $("metodo").innerHTML = `
      <p><strong>Fonte:</strong> relatórios públicos do <a href="${esc(m.fonte)}">Siaps</a> (Avaliação do Quadrimestre) — apenas dados de ${esc(m.municipio)}/${esc(m.uf)}, sem acesso à área restrita.</p>
      <p><strong>Metodologia aplicada (${esc(m.metodologia.id)}):</strong> ${esc(m.metodologia.norma)} — ${esc(m.metodologia.base_legal)}; revoga a ${esc(m.metodologia.revoga)}.
        O resultado quadrimestral já vem calculado pelo Ministério (média dos meses monitorados); o painel não o recalcula. Conceito → pontos: Ótimo 1,00 · Bom 0,75 · Suficiente 0,50 · Regular 0,25.
        Os quadrimestres de 2025 foram avaliados sob a NT anterior (${esc(m.metodologia.revoga)}); o painel aplica a eles os pesos e faixas da NT 8/2026. A NT 8/2026 informa que a correção das descrições de B4/B5 não alterou a metodologia de cálculo, mas não foi verificada diferença de pesos entre as duas versões: confira antes de usar a nota estimada de 2025 como referência formal.</p>
      <p><strong>Nota média estimada (Componente III):</strong> como a nota final é a soma de <em>peso × pontos</em>, a média das notas das equipes do município é Σ(peso × pontuação média do indicador). É uma média municipal; marcada “≈” quando o nº de equipes avaliadas varia entre indicadores. A nota oficial de cada equipe (e o valor do incentivo) usa dados por equipe, disponíveis só na área restrita. Faixas: Ótimo &gt; 7,5 · Bom 5–7,5 · Suficiente &gt; 2,5 e &lt; 5 · Regular ≤ 2,5.</p>
      <p><strong>Componente II:</strong> exibe o conceito final oficial e as dimensões Cadastro e Acompanhamento (a nota do componente depende de dados por equipe e do bônus de Satisfação do Usuário, não públicos).</p>
      <p><strong>Ausência de dado não é zero:</strong> indicador sem equipes avaliadas aparece como “—” e não entra na média.</p>`;
    $("csv").innerHTML = (P.csv || []).map(f => `<li><a href="csv/${encodeURIComponent(f)}" download>${esc(f)}</a></li>`).join("");
    const o = q.origem || {};
    $("foot").innerHTML = `Painel v${esc(m.versaoApp)} · metodologia ${esc(m.metodologia.id)} · dados de ${esc(q.rotulo)}: revisão ${esc(o.revisao ?? "?")}, coletados em ${esc(o.coletadoEm ?? "?")} · painel gerado em ${esc(m.geradoEm)}.
      Projeto independente, não oficial; dados do Ministério da Saúde (acesso público). Limitações e responsáveis: veja o README e docs/.`;
  }

  // ---------------------------------------------------------------- botão de atualização (só com servidor local)
  const btn = $("btn-atualizar");
  btn.onclick = async () => {
    btn.disabled = true; btn.classList.add("spin"); status("Consultando o Siaps… pode levar alguns segundos.");
    try {
      const r = await fetch("/api/atualizar", { method: "POST", headers: { "X-Requested-With": "painel" } });
      const j = await r.json();
      if (!j.ok) throw new Error(j.erro || "erro desconhecido");
      ss.set("quad", sel.value);
      ss.set("msg", j.alterados.length ? `Dados atualizados: ${j.alterados.join(", ")}.` : "Dados conferidos agora: já estavam em dia.");
      location.reload();
    } catch (e) {
      status(String(e.message || e), "err");
      btn.disabled = false; btn.classList.remove("spin");
    }
  };
  async function detectarServidor() {
    // O endpoint só existe no servidor local; em hospedagem estática (Pages) nem tenta (evita 404 no console).
    if (!["127.0.0.1", "localhost"].includes(location.hostname)) return;
    try {
      const r = await fetch("/api/estado", { headers: { Accept: "application/json" } });
      if (r.ok && (await r.json()).atualizacaoHabilitada) btn.hidden = false;
    } catch { /* hospedagem estática: sem botão */ }
  }

  function render() { cards(); prio(); plano(); indicadores(); cvat(); rodape(); }
  const msg = ss.get("msg");
  if (msg) { ss.del("msg"); status(msg, "ok"); }
  avisos(); evolucao(); render(); detectarServidor();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { evolucao(); render(); });
})();
