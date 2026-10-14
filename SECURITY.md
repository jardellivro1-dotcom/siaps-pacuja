# Política de segurança

## Escopo e modelo de ameaças
- O projeto usa **somente dados públicos** do Siaps (`apisiaps.saude.gov.br/api/public`). Não acessa a área restrita,
  não usa credenciais e não armazena dados pessoais (os relatórios são agregados por município).
- O servidor local escuta **apenas em 127.0.0.1**. O único endpoint de escrita (`POST /api/atualizar`) exige o
  cabeçalho `X-Requested-With: painel` (proteção contra CSRF), responde sem detalhes internos em caso de erro e
  não permite atualizações simultâneas.
- O painel aplica Content-Security-Policy, `nosniff`, `X-Frame-Options: DENY` e carrega o Chart.js com
  versão fixa e Subresource Integrity.
- Se for publicado na internet (GitHub Pages), use apenas a pasta `dashboard/` (estática); **não exponha** o servidor
  `serve`/`/api/atualizar` publicamente.

## Como reportar uma vulnerabilidade
Abra uma *security advisory* privada no repositório (aba Security) ou envie e-mail ao mantenedor
com passos para reproduzir. Não publique detalhes antes da correção.

## Boas práticas adotadas
Validação de esquema da API, recusa de dados fora de Pacujá/CE, URLs restritas a `https`, sem segredos no
código, sem dependências de runtime, lint de segurança (Ruff/Bandit `S`) e testes na CI.
