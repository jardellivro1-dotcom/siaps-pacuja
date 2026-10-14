# Arquitetura

```
 Siaps (API pública)
        │  https, só host oficial, sem redirecionamento, tempo limite, tentativas, limite de tamanho
        ▼
  client.py ──► extract.py ──► data/raw/*.json  (resposta original)  ┐
  (coleta)      (validação,    data/raw/revisoes/ (histórico)        │ fonte da verdade
                 integridade,  data/manifest.json (rastreabilidade)  │
                 publicação    data/csv/*.csv                        ┘
                 atômica)            │
                                     ▼
                              metrics.py (regras da NT 8/2026)
                                     ▼
                              pipeline.py ──► dashboard/data.js + csv/   (artefatos estáticos)
                                     ▼
   server.py (localhost: estáticos + /api/estado + /api/atualizar)  ◄── navegador: dashboard/ (HTML/CSS/JS)
```

## Responsabilidades
| Módulo | Faz | Não faz |
|---|---|---|
| `config.py` | Constantes: recorte Pacujá/CE, pesos, pontos, janelas, limites, **versão do app e da metodologia** | Lógica |
| `client.py` | Falar com a API: valida destino (https + host oficial), certificado, sem redirecionamento, timeout, retentativas, tamanho máximo, para em 401/403 | Interpretar dados |
| `extract.py` | Validar esquema/município/integridade, **publicar atomicamente**, revisões, manifesto, CSV seguro, trava de execução | Calcular indicadores |
| `metrics.py` | **Todas as regras metodológicas**: conceito→pontos, pesos, nota média, faixas, prioridades, aproximação | I/O de rede |
| `pipeline.py` | Montar `painel.json`, `data.js` e copiar CSV | Regras de negócio |
| `server.py` | Servir o painel e a API mínima com controles de segurança | Coleta (delega a `extract`) |
| `__main__.py` | Linha de comando (`update`, `build`, `serve`, `status`) e logs | — |
| `dashboard/app.js` | Apresentar o que já veio calculado; plano de ação local | **Não contém regras metodológicas** (faixas, conceito predominante e nota vêm prontos de `metrics.py`) |

## Fluxo de dados e invariantes
1. `update` coleta e valida **tudo em memória**; só depois grava (troca atômica de arquivos).
2. Falha em qualquer etapa ⇒ nada é publicado; a última revisão válida permanece (`manifest.coleta.ultimoErro` registra o motivo).
3. A resposta original é preservada; se o dado oficial mudar, a versão anterior vai para `raw/revisoes/revNNN_<sha8>.json`.
4. `metrics` lê apenas `data/raw`; o painel é regenerável a qualquer momento (`build`).
5. Formato dos arquivos versionado por `schemaVersao` (manifesto e `_meta`); mudanças futuras exigem migração documentada (`OPERACAO.md`).

## Decisões
- **Sem dependências de runtime** (biblioteca padrão): menor superfície de ataque e instalação trivial.
- **Armazenamento em arquivos + Git**: dados pequenos (≈ 60 KB), auditáveis, com histórico e rollback por commit.
- **Painel estático**: pode ser hospedado sem servidor; a escrita (atualização) existe só no servidor local.
- **Chart.js incluído localmente** (`dashboard/vendor/`, versão e hash registrados): sem CDN, CSP `script-src 'self'`.
