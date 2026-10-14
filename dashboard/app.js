(() => {
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
  const charts = {};
  let tabEq = null;

  const quads = P.quadrimestres;
  if (!quads.length) { document.querySelector("main").innerHTML = '<p class="empty">Nenhum dado extraído ainda. Rode: python -m siaps_pacuja update</p>'; return; }

  const sel = $("quad");
  quads.forEach(q => sel.add(new Option(q.rotulo, q.id)));
  const salvo = sessionStorage.getItem("quad");
  sel.value = quads.some(q => q.id === salvo) ? salvo : quads[quads.length - 1].id;
  sessionStorage.removeItem("quad");
  const msg = sessionStorage.getItem("msg");
  if (msg) { sessionStorage.removeItem("msg"); setTimeout(() => status(msg, "ok"), 0); }
  sel.onchange = render;

  const idx = () => quads.findIndex(q => q.id === sel.value);
  const cur = () => quads[idx()];
  const prev = () => quads[idx() - 1];

  function stackBar(d) {
    const t = sum(d) || 1, c = COR();
    return `<div class="stack" role="img" aria-label="${CONC.map(k => `${k}: ${d[k]}`).join(", ")}">` +
      CONC.map(k => d[k] ? `<i style="width:${100 * d[k] / t}%;background:${c[k]}" title="${k}: ${d[k]}"></i>` : "").join("") + "</div>";
  }
  const legend = () => `<div class="legend">${CONC.map(k => `<span><b style="background:${COR()[k]}"></b>${k}</span>`).join("")}</div>`;
  function deltaHtml(a, b) {
    if (a == null || b == null) return "";
    const d = a - b;
    if (Math.abs(d) < 0.005) return '<span class="delta eq">= estável vs. quadrimestre anterior</span>';
    return `<span class="delta ${d > 0 ? "up" : "down"}">${d > 0 ? "▲" : "▼"} ${fmt(Math.abs(d))} vs. anterior</span>`;
  }

  function cards() {
    const q = cur(), p = prev(), out = [];
    for (const [eq, d] of ord(q.componente3)) {
      const c = d.classificacaoNotaMedia, pd = p?.componente3[eq];
      out.push(`<article class="card c-${c}">
        <p class="lbl">Qualidade · ${esc(EQUIPE[eq] || eq)} · ${d.equipes ?? "?"} equipe(s)</p>
        <p class="big">${fmt(d.notaMedia)}<small> / 10</small></p>
        <span class="badge b-${c}">${c}</span> ${deltaHtml(d.notaMedia, pd?.notaMedia)}
        ${d.distFinal ? stackBar(d.distFinal) : ""}
        <p class="lbl">Conceito final oficial das equipes</p></article>`);
    }
    for (const [eq, d] of ord(q.componente2)) {
      const dom = CONC.find(k => d.distFinal[k] === Math.max(...CONC.map(x => d.distFinal[x])));
      out.push(`<article class="card c-${dom}">
        <p class="lbl">Vínculo e Acomp. Territorial · ${esc(EQUIPE[eq] || eq)} · ${d.equipes} equipe(s)</p>
        <p class="big">${CONC.filter(k => d.distFinal[k]).map(k => `${d.distFinal[k]} ${k}`).join(" · ")}</p>
        ${stackBar(d.distFinal)}<p class="lbl">Conceito final oficial das equipes</p></article>`);
    }
    $("cards").innerHTML = out.join("") + `<div style="grid-column:1/-1">${legend()}</div>`;
    $("quad-desc").textContent = q.descricao;
  }

  function prio() {
    $("prio").innerHTML = cur().prioridades.map(i => `<li>
      <span class="code">${i.codigo}</span>
      <div><strong>${esc(i.curto)}</strong> · ${esc(EQUIPE[i.equipe] || i.equipe)}
        <small>Peso ${i.peso} · pontuação média ${fmt(i.pontuacaoMedia)} · janela de monitoramento ${esc(i.janela)}</small>
        ${stackBar(i.dist)}</div>
      <span class="gain" title="Pontos de nota que ainda podem ser ganhos">+${fmt(i.potencial)} pt</span></li>`).join("");
  }

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

    const tot = Object.fromEntries(CONC.map(k => [k, quads.map(q =>
      [...Object.values(q.componente2), ...Object.values(q.componente3)].reduce((a, d) => a + (d.distFinal?.[k] || 0), 0))]));
    const o2 = baseOpts(); o2.scales.x.stacked = true; o2.scales.y.stacked = true;
    mk("c-dist", { type: "bar", data: { labels, datasets: CONC.map(k => ({ label: k, data: tot[k], backgroundColor: COR()[k] })) }, options: o2 });
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

    const heat = i => quads.map(qq => qq.componente3[tabEq]?.indicadores.find(x => x.codigo === i.codigo));
    $("heat").innerHTML = `<thead><tr><th>Indicador</th><th class="n">Peso</th>${quads.map(x => `<th class="n">${esc(x.rotulo)}</th>`).join("")}</tr></thead><tbody>` +
      inds.map(i => `<tr><td><strong>${i.codigo}</strong> ${esc(i.curto)}<br><small style="color:var(--muted)">${esc(i.janela)}</small></td><td class="n">${i.peso}</td>` +
        heat(i).map(x => {
          if (!x || x.pontuacaoMedia == null) return '<td class="cell">—</td>';
          const m = x.pontuacaoMedia, k = m >= 1 ? "Ótimo" : m >= .75 ? "Bom" : m >= .5 ? "Suficiente" : "Regular";
          return `<td class="cell" style="background:var(${TINT[k]});color:var(--ink)" title="${k}">${fmt(m)}</td>`;
        }).join("") + "</tr>").join("") + "</tbody>";
  }

  function cvat() {
    const q = cur(), c = COR();
    const blocos = ord(q.componente2).map(([eq, d]) => `<figure>
      <figcaption>${esc(EQUIPE[eq] || eq)} · ${d.equipes} equipe(s)</figcaption>
      <p class="lbl" style="margin:0">Conceito final</p>${stackBar(d.distFinal)}
      ${d.dimensoes.map(x => `<p class="lbl" style="margin:14px 0 0">${esc(x.nome)}</p>${stackBar(x.dist)}`).join("")}
      ${legend()}</figure>`);
    $("cvat").innerHTML = blocos.join("") || '<p class="empty">Sem dados de Vínculo para este quadrimestre.</p>';
  }

  function rodape() {
    const m = P.meta;
    $("metodo").innerHTML = `
      <p><strong>Fonte:</strong> relatórios públicos do <a href="${m.fonte}">Siaps</a> (Avaliação do Quadrimestre) — apenas dados de ${esc(m.municipio)}/${m.uf}, sem acesso à área restrita.</p>
      <p><strong>Metodologia:</strong> ${esc(m.notaTecnica)}. O resultado quadrimestral já vem calculado pelo Ministério (média dos meses monitorados); o painel não o recalcula. Cada conceito vale Ótimo 1,00 · Bom 0,75 · Suficiente 0,50 · Regular 0,25.</p>
      <p><strong>Nota média estimada (Componente III):</strong> como a nota final é a soma de <em>peso × pontos</em>, a média das notas das equipes do município é obtida exatamente por Σ(peso × pontuação média do indicador). É uma média municipal; a nota oficial de cada equipe (e o valor do incentivo) depende dos dados por equipe, disponíveis só na área restrita. Faixas: Ótimo &gt; 7,5 · Bom 5–7,5 · Suficiente &gt; 2,5 e &lt; 5 · Regular ≤ 2,5.</p>
      <p><strong>Componente II:</strong> exibe o conceito final oficial e as dimensões Cadastro e Acompanhamento (a nota do componente depende de dados por equipe e de bônus de Satisfação do Usuário, não públicos).</p>`;
    $("csv").innerHTML = (P.csv || []).map(f => `<li><a href="csv/${f}" download>${f}</a></li>`).join("");
    $("foot").innerHTML = `Dados atualizados em ${esc(m.geradoEm)}. Projeto independente de portfólio, não oficial. Código-fonte e automação: veja o README.`;
  }

  function status(txt, cls = "") { const e = $("status"); e.textContent = txt; e.className = "status " + cls; }

  const btn = $("btn-atualizar");
  btn.onclick = async () => {
    if (location.protocol === "file:") return status("Para atualizar, abra o painel pelo 'Abrir Painel.bat' (modo servidor).", "err");
    btn.disabled = true; btn.classList.add("spin"); status("Consultando o Siaps… pode levar alguns segundos.");
    try {
      const r = await fetch("/api/atualizar", { method: "POST", headers: { "X-Requested-With": "painel" } });
      const j = await r.json();
      if (!j.ok) throw new Error(j.erro || "erro desconhecido");
      sessionStorage.setItem("quad", sel.value);
      sessionStorage.setItem("msg", j.alterados.length
        ? `Dados atualizados: ${j.alterados.join(", ")}.` : "Dados conferidos agora: já estavam em dia.");
      location.reload();
    } catch (e) {
      status(String(e.message || e), "err");
      btn.disabled = false; btn.classList.remove("spin");
    }
  };

  function render() { cards(); prio(); indicadores(); cvat(); }
  evolucao(); render(); rodape();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { evolucao(); render(); });
})();
