# Política de segurança

Avaliação de riscos completa, controles e testes: [docs/SEGURANCA.md](docs/SEGURANCA.md).

## Escopo e modelo de ameaças
- O projeto usa **somente dados públicos** do Siaps (`apisiaps.saude.gov.br/api/public`). Não acessa a área restrita,
  não usa credenciais e não armazena dados pessoais (os relatórios são agregados por município).
- O servidor local escuta **apenas em 127.0.0.1**, valida `Host` e `Origin`, e o único endpoint de escrita
  (`POST /api/atualizar`) exige o cabeçalho `X-Requested-With: painel` (CSRF), permite 1 atualização por minuto e uma
  por vez, e responde sem detalhes internos em caso de erro. `--somente-leitura` desliga a escrita.
- O painel aplica Content-Security-Policy (só scripts da própria origem), `nosniff` e `X-Frame-Options: DENY`; o Chart.js
  é servido localmente (sem CDN), com versão e hash registrados.
- Se for publicado na internet (GitHub Pages), use apenas a pasta `dashboard/` (estática); **não exponha** o servidor
  `serve`/`/api/atualizar` publicamente.

## Como reportar uma vulnerabilidade
Abra uma *security advisory* privada no repositório (aba Security) ou envie e-mail ao mantenedor
com passos para reproduzir. Não publique detalhes antes da correção.

## Boas práticas adotadas
Validação de esquema da API, recusa de dados fora de Pacujá/CE, URLs restritas a `https`, sem segredos no
código, sem dependências de runtime, lint de segurança (Ruff/Bandit `S`) e testes na CI.
