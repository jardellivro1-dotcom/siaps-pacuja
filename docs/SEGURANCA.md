# Avaliação de riscos e controles de segurança

Referência: [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) (capítulos da v4.0.3).
Nível-alvo: **ASVS nível 1** para o painel/servidor local; capítulos de autenticação e sessão **não se aplicam**
enquanto não houver contas (ver seção 5). Política de reporte de vulnerabilidades: [`../SECURITY.md`](../SECURITY.md).

## 1. O que precisa ser protegido
| Ativo | Por quê | Quem acessa |
|---|---|---|
| Integridade dos dados e da metodologia | Decisões da gestão dependem deles; erro silencioso é o pior risco | Mantenedor (escrita); todos (leitura) |
| Disponibilidade da coleta e do painel | Acompanhar o quadrimestre | Mantenedor / usuários |
| Máquina do usuário (servidor local) | Alvo de páginas maliciosas no mesmo navegador | — |
| Texto livre do plano de ação | Pode receber dado pessoal por engano | Só o navegador do usuário |
| Reputação da fonte (Siaps) | Coleta abusiva pode ser bloqueada | — |

Não há segredos, credenciais, contas, banco de dados nem dados pessoais de pacientes ou profissionais.

## 2. Entradas que podem ser manipuladas
(a) respostas do Siaps (conteúdo externo); (b) requisições HTTP ao servidor local (caminho, `Host`, `Origin`, cabeçalhos);
(c) texto do plano de ação digitado no navegador; (d) linha de comando (`--port`).

## 3. Riscos → controles → testes
| Risco | Controle | Verificação |
|---|---|---|
| **V5 – Resposta do Siaps malformada ou alterada** | Valida esquema, tipos, contagens ≥ 0 inteiras, município/UF, período, duplicidades, totais; limite de 5 MB; identificadores de período por regex `^\d{4}Q[1-3]$` | `Esquema`, `Integridade`, `test_limite_de_tamanho…`, `test_lista_so_quadrimestres_validos…` |
| **V5 – XSS** no painel | Todo texto vindo dos dados/usuário é escapado (`esc()`); CSP `script-src 'self'` sem `unsafe-eval`; sem `innerHTML` com entrada não escapada | `test_cabecalhos_de_seguranca`; verificação manual no navegador |
| **V5/V12 – CSV injection** | Células `= + - @ \t \r` recebem `'` na gravação dos CSV e na exportação do plano | `test_neutraliza_formulas`, `test_arquivo_gravado_sem_formulas…`; verificado no navegador |
| **V12 – Acesso indevido a arquivos** (path traversal, `..`, `\`, `%2e`, NUL, listagem) | `translate_path` só devolve caminhos resolvidos dentro de `dashboard/`; sem listagem de diretório | `test_nao_serve_arquivos_fora_do_dashboard`, `test_sem_listagem_de_diretorios` |
| **V13/V12 – SSRF / destinos não autorizados** | Coletor só aceita `https` + host `apisiaps.saude.gov.br`, sem credenciais na URL, **sem seguir redirecionamentos** | `test_recusa_destinos_nao_autorizados`, `test_nao_segue_redirecionamento` |
| **V9 – Comunicação insegura** | Certificado e nome do host verificados (`ssl.create_default_context`); painel hospedado deve usar HTTPS (GitHub Pages força) | `test_certificado_e_verificado` |
| **V13 – CSRF** na única operação de escrita | Exige `X-Requested-With: painel` (cabeçalho custom ⇒ pré-verificação CORS que o servidor não concede) + checagem de `Origin` | `test_post_sem_cabecalho_csrf…`, `test_origem_externa_e_rejeitada` |
| **DNS rebinding** (site externo apontando para 127.0.0.1) | Valida `Host` em toda requisição (421 se diferente de `127.0.0.1:porta`/`localhost:porta`) | `test_host_diferente_e_barrado…` |
| **V14 – Exposição na rede** | Escuta só em `127.0.0.1`; não há opção de abrir para a rede; modo `--somente-leitura` desliga a escrita | `test_escuta_so_em_localhost`, `SomenteLeitura` |
| **V11 – Abuso da coleta / sobrecarga da fonte** | 1 coleta por vez (trava em arquivo + memória), 1 por minuto, 1 s entre consultas, ≤ 3 tentativas, timeout 60 s | `Trava`, `LimiteDeTaxa`, `test_respeita_intervalo…` |
| **V7 – Vazamento de detalhes em erros** | Resposta de erro genérica; detalhe só no log local | `test_erro_nao_vaza_detalhes` |
| **V7 – Logs** | Log rotativo sem dados pessoais/segredos (não há ambos) | revisão de código |
| **V4 – Fonte exige autenticação** | Interrompe a coleta; nunca tenta contornar | `test_autenticacao_exigida_interrompe…` |
| **V10/Cadeia de fornecimento** | Zero dependências de runtime; Chart.js local com versão/hash/licença em `dashboard/vendor/README.md`; Dependabot para GitHub Actions; `pip-audit` das ferramentas de desenvolvimento na CI | CI |
| **V14 – Cabeçalhos** | CSP, `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cross-Origin-Resource-Policy`, `Cache-Control: no-store`; sem banner de versão | `test_cabecalhos_de_seguranca`, `test_nao_revela_versao_do_python` |
| **Segredos no repositório** | Nenhum segredo existe; teste varre arquivos versionados; `.env`, `logs/` no `.gitignore`; *secret scanning* e *push protection* do GitHub ativos | `test_repo_higiene`; configuração do repositório |
| **Mudança indevida na `main` / cadeia de entrega** | Ruleset: sem push direto, PR + aprovação + 7 verificações obrigatórias; só *squash merge*; workflows com permissões mínimas | push direto recusado (testado) |
| **Negação de serviço local** (conexões lentas) | `timeout = 30 s` por conexão | revisão de código |

## 4. Proteção de segredos e infraestrutura
- O projeto **não usa segredos**. Se algum for necessário no futuro: variáveis de ambiente/cofre (GitHub Secrets), nunca no
  código, navegador ou repositório.
- Privilégio mínimo: o servidor roda como o usuário comum, só escreve em `data/`, `dashboard/` e `logs/`. Os
  workflows do GitHub declaram `permissions` mínimas (`ci.yml`: leitura; `atualizar.yml`: escrita em conteúdo e issues).
- Ambientes: desenvolvimento (máquina local), homologação (`OPERACAO.md`, seção 4) e produção (Pages), separados.

## 5. Autenticação e autorização (decisão)
- **Painel de dados públicos:** aberto, por desenho (os dados são públicos).
- **Escrita hoje:** só existe o disparo de coleta, restrito ao servidor local (localhost + CSRF + Host + taxa) e desligável
  (`--somente-leitura`). Na hospedagem estática (Pages) **não há endpoint de escrita**.
- **Plano de ação:** local ao navegador; não há compartilhamento, logo não há o que autorizar.
- **Condição de gatilho:** se a Secretaria quiser um plano de ação **compartilhado**, ou expor a coleta na rede, é
  obrigatório antes: contas (idealmente gov.br/OIDC), sessões seguras (cookies `HttpOnly`/`Secure`/`SameSite`, expiração e
  revogação), recuperação de acesso, **MFA para administradores**, verificação de permissão **no servidor** por perfil
  (leitor, editor do plano, administrador), trilha de auditoria das alterações e armazenamento no servidor com
  migrações. Nada disso está implementado — está registrado como **limitação conhecida**.

## 6. Risco residual
Dependência de uma API pública não documentada (pode mudar sem aviso — mitigado por validação de esquema e alerta);
plano de ação local pode ser perdido (mitigado por exportação); ausência de revisão de segurança independente.
