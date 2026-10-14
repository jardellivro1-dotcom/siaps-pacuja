# APS Pacujá · Painel de desempenho (Siaps)

**Painel online:** <https://jardellivro1-dotcom.github.io/siaps-pacuja/> · **Código:** <https://github.com/jardellivro1-dotcom/siaps-pacuja> · [![CI](https://github.com/jardellivro1-dotcom/siaps-pacuja/actions/workflows/ci.yml/badge.svg)](https://github.com/jardellivro1-dotcom/siaps-pacuja/actions/workflows/ci.yml)

Automação + painel web que monitora o **acesso e a qualidade da Atenção Primária à Saúde de Pacujá/CE**
(Componente II – Vínculo e Acompanhamento Territorial; Componente III – Qualidade), seguindo a
**Nota Técnica nº 8/2026-DEAPS/SAPS/MS** (Portaria GM/MS nº 3.493/2024).

## Como funciona
1. **Extração** (`src/siaps_pacuja/extract.py`): consulta a API pública que alimenta
   <https://siaps.saude.gov.br/publico> (sem login, sem área restrita), descobre os quadrimestres publicados
   e baixa só os de Pacujá (IBGE 230990). Rodar de novo é seguro: só grava o que mudou.
   Saída: `data/raw/*.json` (resposta original) e `data/csv/*.csv` (3 relatórios por quadrimestre).
2. **Métricas** (`metrics.py`): aplica pontos (Ótimo 1 · Bom 0,75 · Suficiente 0,5 · Regular 0,25), pesos da NT
   e faixas do Quadro 6 → nota média estimada por tipo de equipe, evolução e prioridades de melhoria.
3. **Painel** (`dashboard/`): HTML/JS estático (Chart.js). Funciona até abrindo `index.html` direto.
4. **Atualização automática**: `.github/workflows/atualizar.yml` roda todo dia 12 do mês, rebaixa os dados e
   faz commit se um novo quadrimestre/mês foi publicado. (Publique `dashboard/` no GitHub Pages.)

## Uso
```bash
python -m siaps_pacuja update                    # coleta + valida + publica dados novos e regenera o painel
python -m siaps_pacuja serve                     # http://127.0.0.1:8000 (botão "Atualizar dados" incluso)
python -m siaps_pacuja serve --somente-leitura   # sem endpoint de escrita
python -m siaps_pacuja status                    # última coleta, erros e alerta de dados velhos (exit 1 se houver)
```
No Windows, dê dois cliques em `Abrir Painel.bat`. Sem dependências de runtime (Python 3.10+).

## Qualidade (a CI repete tudo)
```bash
pip install -r requirements-dev.txt
ruff check . && ruff format --check .      # lint (inclui regras de segurança) e formatação
mypy                                       # tipagem estrita do código-fonte
pip-audit -r requirements-dev.txt          # vulnerabilidades das ferramentas
PYTHONPATH=src coverage run -m unittest discover -s tests && coverage report   # 82 testes, mínimo 85%
```

## Documentação
| Documento | Conteúdo |
|---|---|
| [docs/REQUISITOS.md](docs/REQUISITOS.md) | Escopo, usuários, dados, limites e critérios de aceitação |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Módulos, fluxo de dados, responsabilidades, decisões |
| [docs/METODOLOGIA.md](docs/METODOLOGIA.md) | Fórmulas, pesos, faixas, exceções, o que o painel calcula e não calcula |
| [docs/SEGURANCA.md](docs/SEGURANCA.md) · [SECURITY.md](SECURITY.md) | Riscos → controles (OWASP ASVS) → testes; autenticação/autorização |
| [docs/PRIVACIDADE.md](docs/PRIVACIDADE.md) | Inventário de dados pessoais (LGPD), retenção, regras de uso |
| [docs/OPERACAO.md](docs/OPERACAO.md) | Monitoramento, backup/restauração, publicação, reversão, incidentes |
| [docs/VALIDACAO_USUARIOS.md](docs/VALIDACAO_USUARIOS.md) | Roteiro de validação com a Secretaria (pendente) |
| [docs/CONFORMIDADE.md](docs/CONFORMIDADE.md) | Matriz dos 24 requisitos: situação, evidência e lacunas |
| [CHANGELOG.md](CHANGELOG.md) | Versões do app e da metodologia |

## Limites dos dados públicos (importante)
O Siaps público traz, por quadrimestre, **quantas equipes ficaram em cada conceito por indicador**; o resultado
quadrimestral já é a média dos meses calculada pelo Ministério. Valores mensais, percentuais e nota por equipe estão
só na área restrita e **não são usados**. O painel mostra a *nota média estimada* do município (exata quando todas as
equipes têm todos os indicadores; “≈” caso contrário) e o conceito final oficial por equipe. Detalhes em `docs/METODOLOGIA.md`.

## Segurança e licença
Veja [SECURITY.md](SECURITY.md) e `docs/SEGURANCA.md`. Licença [MIT](LICENSE). Dados: Ministério da Saúde (Siaps),
acesso público. Projeto independente, não oficial. Mantenedor: Jardel Negreiros.
