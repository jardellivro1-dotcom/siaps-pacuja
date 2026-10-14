# Histórico de mudanças

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versionamento semântico. A versão do app
(`config.VERSAO_APP`) e a da metodologia (`config.METODOLOGIA["id"]`) são independentes: uma nova Nota Técnica
muda só a metodologia.

## [1.1.0] — 2026-10-14 · metodologia NT8-2026
### Adicionado
- Manifesto de coleta (`data/manifest.json`): fonte, filtros, horário, revisão e SHA-256 de cada arquivo.
- Revisões: se o dado oficial de um período mudar, a versão anterior é arquivada em `data/raw/revisoes/`.
- Validação de integridade (período, duplicidades, totais) e publicação atômica “tudo ou nada”.
- Coletor restrito ao host oficial, sem redirecionamentos, parada em 401/403, limite de tamanho, intervalo entre consultas.
- Trava contra coletas simultâneas e limite de 1 atualização por minuto no botão.
- Servidor: validação de `Host`/`Origin`, `GET /api/estado`, modo `--somente-leitura`, bloqueio de path traversal e de listagem.
- CSV seguro contra injeção de fórmulas; comando `status` e alerta de dados desatualizados.
- Painel: “Como ler”, tabelas alternativas dos gráficos, plano de ação local com exportação, versão/revisão no rodapé.
- Documentação em `docs/` e matriz de conformidade; testes de metodologia, segurança e higiene do repositório.
### Alterado
- Chart.js agora é servido localmente (`dashboard/vendor/`); CSP sem CDN.
- Gráfico agregado de evolução usa só o Componente III (evita somar grupos sobrepostos).
- Faixas e conceito predominante passaram do JavaScript para `metrics.py`.
- Notas “≈ aproximadas” quando o nº de equipes varia entre indicadores.
### Corrigido
- Contraste insuficiente dos selos de conceito no tema claro.

## [1.0.0] — 2026-10-14 · metodologia NT8-2026
- Primeira versão: coleta dos relatórios públicos de Pacujá, métricas da NT 8/2026, painel web, botão de atualização,
  CI e documentação inicial.
