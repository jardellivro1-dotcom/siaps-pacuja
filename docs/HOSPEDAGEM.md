# Hospedagem e deploy (gratuito)

**Painel publicado:** <https://jardellivro1-dotcom.github.io/siaps-pacuja/> · custo: **R$ 0** (GitHub Pages + GitHub Actions
em repositório público).

## Arquitetura de hospedagem
```
 cron (GitHub Actions, dia 12)         PR de dados          CI (7 verificações)        merge             deploy
 atualizar.yml ── coleta Siaps ─────►  dados/atualizacao-*  ──────────────────►  (mantenedor)  ──►  publicar.yml ──► GitHub Pages (HTTPS, CDN)
                                                                                                                      ▲
 monitor.yml (diário): site responde? dados < 45 dias? ──► issue de alerta (e-mail do GitHub) ◄───────────────────────┘
 backup.yml  (mensal): data/ → Release "backup-AAAA-MM" (12 mais recentes)
```
- **Só a pasta estática `dashboard/` é publicada.** Não há servidor, banco, endpoint de escrita nem segredo na internet.
  O servidor Python (`serve`) é **apenas para uso local** e **não deve ser exposto à internet** nesta versão.
- **Limites do plano gratuito** (documentados pelo GitHub, limites brandos): site publicado ≤ 1 GB e ~100 GB/mês de banda; este
  site tem ≈ 0,3 MB. Minutos de Actions gratuitos para repositório público.
- **Dependência do provedor:** se o GitHub estiver fora do ar, o painel e as automações também ficam. Mitigação: o painel é
  100% estático e portátil (qualquer hospedagem de arquivos serve: Cloudflare Pages, Netlify, S3+CDN).

## Como refazer o deploy do zero (fork)
1. Fork do repositório → *Settings → Pages → Source: GitHub Actions*.
2. *Settings → Environments → github-pages*: permitir ramo `main` e tags `v*`.
3. *Settings → Actions → General*: permissões padrão “read”; marcar “Allow GitHub Actions to create and approve pull requests”.
4. *Actions → Atualizar dados do Siaps → Run workflow*; mesclar o PR de dados; o `publicar.yml` publica.
5. Trocar `@jardellivro1-dotcom` em `.github/CODEOWNERS` e a URL no `monitor.yml` não é necessário (usa o nome do repositório).

## Pré-requisitos para hospedagem e uso compartilhado — situação
O que **já** vale para o painel público estático publicado, e o que continua **obrigatório antes** de qualquer uso além disso.

| # | Pré-requisito | Situação | Detalhe |
|---|---|---|---|
| 1 | Autenticação e autorização | ➖ **Não implementada** | Desnecessária para o painel de dados públicos (somente leitura). **Obrigatória** antes de plano de ação compartilhado ou de expor a coleta: contas (gov.br/OIDC), MFA de administradores, permissões no servidor. Ver `SEGURANCA.md` §5. |
| 2 | Banco compartilhado | ➖ **Não implementado** | Sem plano compartilhado não há o que gravar. Se a Secretaria exigir, caminho gratuito: Postgres gerenciado com *row-level security* (ex.: Supabase, plano gratuito), com esquema, migrações e trilha de auditoria — decisão a tomar com a Secretaria. |
| 3 | HTTPS / proxy seguro | ✅ | HTTPS forçado e HSTS pelo GitHub Pages; certificado gerenciado; não há servidor próprio nem proxy a expor. |
| 4 | Agendador independente do computador pessoal | ✅ | `atualizar.yml` (cron no GitHub). **Exercitado de ponta a ponta em 2026-10-14**: coleta real → PR → 7 verificações → merge → deploy → dado novo no ar. |
| 5 | Backup externo | 🟡 | Histórico Git no GitHub + `backup.yml` (Release mensal com SHA-256). Está fora do computador do mantenedor, **mas na mesma plataforma**; falta um espelho em outro provedor. |
| 6 | Alertas externos | 🟡 | `monitor.yml` diário (site no ar + dados < 45 dias) e issue em falha da coleta; o GitHub notifica por e-mail. Falta canal de plantão (SMS/WhatsApp) se a Secretaria exigir. |
| 7 | Teste de carga | 🟡 | `tools/teste_carga.py` (600 requisições, 25 simultâneas, servidor local): 0 erros, mediana ≈ 27 ms, **p95 ≈ 70 ms** (meta < 250 ms), ≈ 250 req/s. O teste achou e corrigiu um gargalo (fila de conexões). Não se faz carga contra o GitHub Pages (CDN de terceiros, política de uso). |
| 8 | Outros navegadores e leitor de tela | ⏳ **Pendente (humano)** | Testado só no Chromium embutido e por CI em Linux/Windows (sem navegador). Falta Chrome/Edge/Firefox/Safari-iOS e NVDA/VoiceOver na máquina da gestão. |
| 9 | Gestão de dados pessoais | 🟡 | Nenhum dado pessoal é coletado, armazenado ou enviado (`PRIVACIDADE.md`); plano de ação fica no navegador com aviso. Falta parecer do encarregado/DPO da Secretaria. |
| 10 | Aceite municipal | ⏳ **Pendente (humano)** | Roteiro em `VALIDACAO_USUARIOS.md`. Não pode ser feito pelo desenvolvedor. |
| 11 | Implantação e rollback | 🟡 | Deploy automatizado por tag/merge. **Rollback exercitado** (republicação da tag anterior pelo `publicar.yml`, em 2026-10-14). Falta homologação em ambiente separado. |

> **Conclusão:** hospedar o painel **público e estático** é seguro e já está feito. Os itens 1–2 só passam a ser exigidos se o
> escopo crescer (plano compartilhado/contas); os itens 8 e 10 dependem de pessoas.

## Rotina de operação
Ver `OPERACAO.md`. Resumo: dia 12 coleta e PR de dados → mesclar após conferir `data/manifest.json` → publicação automática;
dia 14 backup; diariamente o monitor verifica o site; falha ⇒ issue com label `monitor`.
