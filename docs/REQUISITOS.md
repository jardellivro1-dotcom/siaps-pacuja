# Escopo, requisitos e critérios de aceitação

## 1. Escopo
**Objetivo:** monitorar o acesso e a qualidade dos serviços da Atenção Primária à Saúde (APS) de **Pacujá/CE**
(Componente II – Vínculo e Acompanhamento Territorial; Componente III – Qualidade), para que a Secretaria de Saúde
e a coordenação municipal da APS planejem ações de melhoria. Metodologia: Nota Técnica nº 8/2026-DEAPS/SAPS/MS.

**Recorte fixo (não configurável pela interface):** UF `CE`, município `Pacujá` (IBGE 230990). O coletor envia só esse
filtro e **recusa** qualquer linha de outro município (`extract._so_pacuja`).

**Fonte permitida:** exclusivamente o acesso público do Siaps — API `https://apisiaps.saude.gov.br/api/public`, a
mesma usada por <https://siaps.saude.gov.br/publico>. É proibido usar a área restrita, credenciais ou qualquer fonte
que exija autenticação (o coletor **interrompe** ao receber HTTP 401/403).

### Usuários
| Perfil | Uso | Acesso |
|---|---|---|
| Secretário(a) de Saúde | Ver situação geral e prioridades | Painel (leitura) |
| Coordenação municipal da APS | Analisar indicadores, montar plano de ação, baixar CSV | Painel + plano local + CSV |
| Mantenedor técnico | Atualizar dados, publicar versões, operar | Linha de comando / servidor local |

### Dados armazenados
| Dado | Onde | Pessoal? | Retenção |
|---|---|---|---|
| Resposta original da API (por quadrimestre) | `data/raw/*.json` (+ `revisoes/`) | Não (agregado por município) | Permanente (histórico oficial) |
| CSV derivados | `data/csv/`, `dashboard/csv/` | Não | Regenerável |
| Manifesto de coleta (fonte, filtros, hora, revisão, SHA-256) | `data/manifest.json` | Não | Permanente |
| Painel processado | `data/processed/`, `dashboard/data.js` | Não | Regenerável |
| Plano de ação | `localStorage` do navegador do usuário | Pode conter texto livre (ver `PRIVACIDADE.md`) | Até o usuário apagar |
| Logs de execução | `logs/siaps.log` (rotativo, 4 × 500 KB) | Não | Rotação automática |

### Limites do aplicativo
- Os dados públicos são **contagens de equipes por conceito**, não valores mensais nem notas por equipe.
- Não calcula nem prevê valores de incentivo financeiro; não substitui o Siaps oficial.
- Sem contas de usuário, sem banco de dados e sem plano de ação compartilhado (ver `SEGURANCA.md`, seção 5).
- Projeto independente, não oficial.

## 2. Critérios de aceitação
Cada critério aponta o teste automatizado que o verifica (`tests/`), quando existe.

### Coleta e atualização
| ID | Situação | Comportamento esperado | Verificação |
|---|---|---|---|
| CA-01 | Fonte com quadrimestres novos | Descobre os períodos publicados, baixa só Pacujá/CE, grava raw + 3 CSV + manifesto | `test_extract.Atualizar` |
| CA-02 | Nada mudou | Não cria revisão nem altera dados (idempotente) | `test_baixa_so_com_dados…` |
| CA-03 | Dado oficial de um período mudou | Nova revisão; a anterior é arquivada byte a byte em `data/raw/revisoes/` | `test_dado_oficial_alterado…` |
| CA-04 | Fonte indisponível / erro 5xx / tempo esgotado | Até 3 tentativas com espera crescente; depois falha com mensagem; **dados anteriores intactos**; erro registrado no manifesto | `test_client`, `test_falha_preserva…` |
| CA-05 | Fonte pede autenticação (401/403) | Interrompe imediatamente, sem repetir nem contornar | `test_autenticacao_exigida…` |
| CA-06 | Formato dos relatórios mudou (campo ausente, tipo errado, total inconsistente, duplicidade, período divergente) | Falha clara; **nada é publicado**, nem os períodos válidos | `Esquema`, `Integridade`, `test_mudanca_de_formato…` |
| CA-07 | Linhas de outro município/UF | Coleta rejeitada | `test_recusa_outro_municipio…` |
| CA-08 | Duas coletas ao mesmo tempo (botão, CLI, agendador) | A segunda é recusada (HTTP 409 / `ColetaEmAndamento`) | `Trava`, `test_requisicoes_simultaneas…` |
| CA-09 | Botão clicado repetidamente | No máximo 1 coleta por minuto (HTTP 429 + `Retry-After`) | `LimiteDeTaxa` |
| CA-10 | Período sem dados para Pacujá | Ignorado e registrado; se **nenhum** período tiver dados, a coleta falha sem alterar nada | `test_fonte_sem_nenhum_dado…` |
| CA-11 | Coleta com vários períodos | Intervalo de 1 s entre consultas (cortesia com a fonte) | `test_respeita_intervalo…` |

### Painel
| ID | Funcionalidade | Comportamento esperado |
|---|---|---|
| CA-12 | Filtro de quadrimestre | Lista só períodos existentes; ao atualizar, mantém o período escolhido |
| CA-13 | Cartões | Por tipo de equipe: nota média estimada (marcada “≈” quando aproximada), conceito, variação e distribuição **com números em texto** |
| CA-14 | Gráficos | Cada gráfico tem descrição para leitor de tela **e** tabela equivalente; não dependem só de cor |
| CA-15 | Dados ausentes | Indicador sem equipes mostra “—” (nunca 0) e não entra em médias |
| CA-16 | Dados desatualizados | Faixa de alerta se a última coleta bem-sucedida for mais antiga que 45 dias ou se a última tentativa falhou |
| CA-17 | Exportação CSV | Arquivos por quadrimestre (UTF-8 com BOM, `;`), células iniciadas por `= + - @` neutralizadas |
| CA-18 | Plano de ação | Até 4 campos por prioridade; salvo só no navegador, com aviso da limitação, exportação CSV e sem nomes de pessoas |
| CA-19 | Botão “Atualizar dados” | Só aparece com o servidor local (não em hospedagem estática nem em modo somente leitura) |
| CA-20 | Indisponibilidade ao atualizar | Mensagem clara e dados anteriores mantidos |

## 3. Desempenho (metas)
Painel carrega em < 2 s em computador comum (≈ 60 KB de dados + Chart.js local de 200 KB); processar 40
quadrimestres em < 2 s (`test_historico_grande_processa_rapido`); coleta completa < 30 s com a fonte saudável.
