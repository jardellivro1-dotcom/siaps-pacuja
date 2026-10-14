# APS Pacujá · Painel de desempenho (Siaps)

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
python -m siaps_pacuja update    # baixa dados novos + regenera o painel
python -m siaps_pacuja serve     # http://127.0.0.1:8000
```
Sem dependências de runtime (Python 3.10+). O botão **↻ Atualizar dados** do painel consulta o Siaps na hora
(`POST /api/atualizar`, só disponível pelo servidor local / `Abrir Painel.bat`).

## Qualidade (rode antes de cada commit; a CI repete tudo)
```bash
pip install ruff mypy coverage
ruff check . && ruff format --check .     # lint (inclui regras de segurança) e formatação
mypy                                       # tipagem estrita do código-fonte
PYTHONPATH=src coverage run -m unittest discover -s tests && coverage report   # 28 testes, cobertura mínima 85%
```
Os testes incluem os exemplos numéricos da NT 8/2026, o cliente da API (com mocks), a validação de esquema,
a idempotência da extração e a segurança do servidor (cabeçalhos, CSRF, vazamento de erros, path traversal).

## Segurança e licença
Veja [SECURITY.md](SECURITY.md). Licença [MIT](LICENSE). Dados: Ministério da Saúde (Siaps), acesso público.

## Limites dos dados públicos (importante)
O Siaps público traz, por quadrimestre, **quantas equipes ficaram em cada conceito por indicador**; o
resultado quadrimestral já é a média dos meses calculada pelo Ministério. Valores mensais, percentuais e
nota por equipe estão só na área restrita e **não são usados**. Por isso o painel mostra a *nota média
estimada* do município (exata por linearidade: Σ peso × pontuação média) e o conceito final oficial por equipe.
Para o Componente II exibe-se o conceito oficial e as dimensões Cadastro/Acompanhamento.
Projeto independente, não oficial.
