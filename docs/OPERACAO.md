# Operação, publicação e recuperação

## 1. Rotina
| Quando | O quê |
|---|---|
| Todo dia 12 (automático) | `.github/workflows/atualizar.yml` roda testes + `update` e abre um PR com os dados. O envio ao Siaps vai até o dia 10 do mês seguinte (NT 2.7). |
| Sob demanda | `Abrir Painel.bat` ou botão **Atualizar dados** (limite de 1 por minuto). |
| Mensal | Conferir `python -m siaps_pacuja status`; revisar PRs do Dependabot. |

## 2. Monitoramento e alertas
- **Última coleta bem-sucedida / última tentativa / último erro:** `data/manifest.json` → `coleta`, `GET /api/estado` e
  `python -m siaps_pacuja status` (código de saída 1 se nunca coletou, houve erro ou passou de **45 dias**).
- **No painel:** faixa de alerta para dados com mais de 45 dias ou última tentativa com falha; rodapé mostra versão,
  revisão e data da coleta de cada período.
- **Alerta automático:** se o workflow de atualização falhar, abre uma *issue* (“Falha na atualização automática do Siaps”).
- **Logs:** `logs/siaps.log` (rotativo). Não contêm dados pessoais nem segredos.
- **Disponibilidade do painel publicado:** monitor externo gratuito (ex.: UptimeRobot) apontando para <https://jardellivro1-dotcom.github.io/siaps-pacuja/> — *a configurar*.

## 3. Cópias de segurança e restauração
- **Cópia:** o repositório Git é o backup (dados + histórico + revisões). Faça `git push` para um remoto; ideal: segundo remoto/espelho.
- **Restaurar um estado anterior dos dados:** `git log -- data/` → `git checkout <commit> -- data/` →
  `python -m siaps_pacuja build`.
- **Restaurar uma revisão oficial antiga de um período:** copie `data/raw/revisoes/<período>/revNNN_<sha8>.json` para
  `data/raw/<período>.json`, ajuste a entrada no manifesto (ou rode `update` para republicar) e `build`.
- **Teste de restauração:** a cada trimestre, clone o repositório em pasta limpa, rode `python -m siaps_pacuja build` e
  `python -m unittest discover -s tests`, e confira que o painel abre. (O teste `test_dado_oficial_alterado…` garante que
  a revisão arquivada é idêntica byte a byte ao original.)
- **Plano de ação (navegador):** exportar CSV regularmente; não há cópia no servidor.

## 4. Publicação controlada
**Endereços:** repositório <https://github.com/jardellivro1-dotcom/siaps-pacuja> · painel publicado (HTTPS) <https://jardellivro1-dotcom.github.io/siaps-pacuja/>.

**Proteção da `main` (ruleset “proteger-main”, ativo):** sem push direto, sem force-push, sem apagar; histórico linear;
mudanças só por *pull request* com 1 aprovação e conversas resolvidas; ramo atualizado e **7 verificações obrigatórias**
(`qualidade` + `compatibilidade` em Ubuntu e Windows × Python 3.10/3.12/3.13). Testado: um push direto foi recusado.
Também ativos: alertas de vulnerabilidade, *secret scanning* com *push protection*, Dependabot (Actions e pip), só *squash merge*,
ramo apagado após o merge.

**Mantenedor único (situação atual):** o ruleset permite que o *admin* do repositório mescle **o próprio PR** sem a aprovação
(“bypass: somente via pull request”), mas nunca grave direto na `main` nem pule as verificações. Quando houver um segundo
revisor, adicione-o como colaborador e remova o *bypass* em *Settings → Rules → proteger-main* — a revisão passa a ser de fato independente.

**Fluxo de mudança:** branch → PR → CI verde → revisão → *squash merge* → (se mudou `dashboard/`) publicação automática.
**Fluxo de dados mensal:** `atualizar.yml` coleta, abre um PR “Atualização dos dados do Siaps” e dispara a CI no ramo;
confira `data/manifest.json`, mescle, e o `publicar.yml` publica sozinho.

1. **Desenvolvimento:** máquina local + PR; a CI roda lint, formatação, tipagem, `pip-audit`, testes com cobertura mínima de 85%
   e a matriz de compatibilidade.
2. **Homologação:** `python -m siaps_pacuja serve --somente-leitura` em máquina separada, ou *fork*/branch de teste com seu próprio
   Pages; validar com a coordenação (`VALIDACAO_USUARIOS.md`) antes de promover. *(Ambiente dedicado ainda não provisionado.)*
3. **Produção:** criar a tag `vX.Y.Z` (deve coincidir com `config.VERSAO_APP` e `CHANGELOG.md`; o workflow recusa se divergir).
4. **Identificação da versão publicada:** rodapé do painel (“Painel vX.Y.Z · metodologia NT8-2026 · revisão rN”).
5. **Reversão:** *Actions → Publicar painel → Run workflow* escolhendo a tag anterior (republica aquela versão) **e** `git revert`
   do PR problemático. Dados: seção 3.
6. **Migrações:** mudança no formato de `data/` ⇒ incrementar `config.SCHEMA_VERSAO`, escrever o conversor, testá-lo com cópia dos
   dados reais e só então aplicar; registrar no `CHANGELOG.md`.

## 5. Resposta a incidentes
| Incidente | Primeiros passos |
|---|---|
| Dados incorretos publicados | Reverter (seção 4.5); abrir issue; identificar a causa (`manifest.json` indica fonte, hora, revisão e SHA-256); corrigir com teste que reproduza; nova versão e nota no `CHANGELOG.md`. |
| Siaps fora do ar / formato mudou | A coleta falha **sem** alterar dados (alerta/issue). Verificar `ultimoErro`; se o formato mudou, ajustar `extract.CAMPOS_OBRIGATORIOS`/`metrics` com testes. |
| Fonte passou a exigir autenticação | A coleta para (`AutenticacaoExigida`). **Não** contornar: o projeto usa só acesso público. Avisar a coordenação. |
| Suspeita de vulnerabilidade | Seguir `SECURITY.md`; desligar o servidor/publicação se houver exposição; corrigir, testar e publicar nova versão. |
| Dado pessoal inserido por engano no plano | Usar “Limpar plano”, apagar CSV exportado e orientar o usuário (`PRIVACIDADE.md`). |
Após qualquer incidente: registrar causa, impacto e ação preventiva no repositório (issue/`CHANGELOG.md`).

## 6. Retenção
Dados oficiais e revisões: permanentes (pequenos, ≈ 60 KB por período). Logs: 4 × 500 KB. CSV e painel: regeneráveis.

## 7. Manutenção e responsabilidades
Mantenedor técnico: **Jardel Negreiros** (autor do projeto). Responsável pela validação de conteúdo: Secretaria Municipal de
Saúde / coordenação da APS de Pacujá (a formalizar). Trocar o mantenedor exige transferir o acesso ao repositório e ler este
documento.
